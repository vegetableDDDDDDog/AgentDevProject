"""
工具适配器 - 为 LangChain 工具注入多租户能力

为 LangChain 工具添加租户隔离、监控指标和审计日志功能。
"""
import time
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain.tools import BaseTool
from services.database import Session, ToolCallLog

# 延迟导入，避免循环依赖
def get_metrics_store():
    from api.metrics import get_metrics_store as _get_metrics_store
    return _get_metrics_store()


class ToolAdapter:
    """
    为 LangChain 工具注入多租户能力的适配器

    核心职责：
    1. 执行工具 - 调用底层工具
    2. 记录指标 - 记录成功/失败、执行时间
    3. 审计日志 - 记录工具调用日志
    4. 配额检查 - （待 Task 4 完成）

    注意：配额检查功能将在 QuotaService 实现后集成
    """

    def __init__(
        self,
        tool: Any,  # langchain.tools.BaseTool
        tenant_id: str,
        db: Session
    ):
        """
        初始化工具适配器

        Args:
            tool: LangChain 工具实例
            tenant_id: 租户 ID
            db: 数据库会话
        """
        self.tool = tool
        self.tenant_id = tenant_id
        self.db = db

        # 从工具获取属性
        self.name = getattr(tool, 'name', 'unknown_tool')
        self.description = getattr(tool, 'description', '')

        # 代理工具的方法
        if hasattr(tool, '_run'):
            self._run = tool._run
        if hasattr(tool, '_arun'):
            self._arun = self._arun

    async def _arun(self, *args, **kwargs) -> str:
        """
        执行工具调用（带多租户保护）

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            str: 工具执行结果

        Raises:
            Exception: 工具执行失败时抛出
        """
        # TODO: 配额检查 - 等待 QuotaService 实现
        # from services.quota_service import QuotaService
        # quota_service = QuotaService(self.db)
        # await quota_service.check_tool_quota(
        #     tenant_id=self.tenant_id,
        #     tool_name=self.name
        # )

        # 记录开始时间
        start_time = time.time()

        # 执行工具
        try:
            if hasattr(self.tool, '_arun'):
                result = await self.tool._arun(*args, **kwargs)
            else:
                # 如果工具不支持异步，使用同步方法
                result = self.tool._run(*args, **kwargs)

            # 记录成功指标
            execution_time = time.time() - start_time
            self._record_metrics(
                success=True,
                execution_time=execution_time
            )

            # 写入审计日志
            self._write_audit_log(
                input_data=kwargs,
                output_data=str(result),
                status='success',
                execution_time_ms=int(execution_time * 1000)
            )

            return result

        except Exception as e:
            # 记录失败指标
            execution_time = time.time() - start_time
            self._record_metrics(
                success=False,
                error=str(e),
                execution_time=execution_time
            )

            # 写入错误日志
            self._write_audit_log(
                input_data=kwargs,
                output_data=None,
                status='error',
                error_message=str(e),
                execution_time_ms=int(execution_time * 1000)
            )

            raise

    def _run(self, *args, **kwargs) -> str:
        """
        同步执行（简单委托）

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            str: 工具执行结果
        """
        return self.tool._run(*args, **kwargs)

    def _record_metrics(
        self,
        success: bool,
        error: str = None,
        execution_time: float = 0
    ):
        """
        记录工具调用指标

        Args:
            success: 是否成功
            error: 错误信息
            execution_time: 执行时间（秒）
        """
        try:
            metrics = get_metrics_store()

            # 计数器
            if hasattr(metrics, 'tool_calls_total'):
                metrics.tool_calls_total.inc()

            # 直方图
            if hasattr(metrics, 'tool_execution_duration'):
                metrics.tool_execution_duration.observe(execution_time)

        except Exception as e:
            # 记录指标失败不应影响主流程
            print(f"Warning: Failed to record metrics: {e}")

    def _write_audit_log(
        self,
        input_data: Dict,
        output_data: str,
        status: str,
        execution_time_ms: int,
        error_message: str = None
    ):
        """
        写入审计日志到数据库

        Args:
            input_data: 输入数据
            output_data: 输出数据
            status: 状态（success/error）
            execution_time_ms: 执行时间（毫秒）
            error_message: 错误信息
        """
        try:
            log = ToolCallLog(
                tenant_id=self.tenant_id,
                tool_name=self.name,
                tool_input=input_data,
                tool_output=output_data,
                status=status,
                execution_time_ms=execution_time_ms,
                error_message=error_message
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            # 日志失败不应影响主流程
            print(f"Warning: Failed to write audit log: {e}")

    def __repr__(self) -> str:
        return f"<ToolAdapter(tool={self.name}, tenant={self.tenant_id})>"
