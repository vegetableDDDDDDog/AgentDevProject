#!/usr/bin/env python3
"""
Agent 平台数据库初始化脚本。

此脚本通过创建所有表来初始化 SQLite 数据库。
可以从命令行运行以设置新数据库。

用法:
    python -m services.init_db                # 初始化数据库
    python -m services.init_db --force        # 删除并重新创建数据库
    python -m services.init_db --verbose      # 显示详细输出
    python -m services.init_db --force --verbose  # 两个选项
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

# 从 database.py 导入核心函数
from services.database import (
    engine,
    Base,
    SessionLocal,
    init_db,
    drop_all
)

# 常量
DATABASE_PATH = "data/agent_platform.db"


# 配置日志
def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    设置日志配置。

    Args:
        verbose: 如果为 True，将日志级别设置为 DEBUG；否则为 INFO

    Returns:
        配置的日志记录器实例
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


def ensure_data_directory() -> Path:
    """
    确保数据目录存在。

    Returns:
        数据目录的路径

    Raises:
        OSError: 如果目录创建失败
    """
    data_dir = Path("data")
    try:
        data_dir.mkdir(exist_ok=True)
        logger.debug(f"数据目录已确保存在: {data_dir.absolute()}")
        return data_dir
    except OSError as e:
        logger.error(f"创建数据目录失败: {e}")
        raise


def database_exists() -> bool:
    """
    检查数据库文件是否存在。

    Returns:
        如果数据库文件存在返回 True，否则返回 False
    """
    db_path = Path(DATABASE_PATH)
    exists = db_path.exists()
    logger.debug(f"数据库存在性检查: {exists}")
    return exists


def get_table_names() -> list:
    """
    获取数据库中的表名列表。

    Returns:
        表名列表
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.debug(f"找到 {len(tables)} 个表: {tables}")
    return tables


def drop_all_tables() -> None:
    """
    删除所有数据库表。

    注意: 此函数调用 services/database.py 中的 drop_all()。

    警告: 这将不可逆地删除所有数据。
    """
    logger.warning("正在删除所有数据库表...")
    try:
        drop_all()  # 调用 services/database.py:drop_all()
        logger.info("所有表已成功删除")
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        raise


def initialize_database() -> None:
    """
    通过创建所有表来初始化数据库。

    此函数是 services/database.py:init_db() 的包装器，
    添加了日志输出以便跟踪初始化过程。

    使用 SQLAlchemy 的 create_all，具有幂等性（可安全多次运行）。
    """
    logger.info("正在初始化数据库...")
    try:
        init_db()  # 调用 services/database.py:init_db()
        logger.info("数据库表已成功创建")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        raise


def health_check() -> dict:
    """
    对数据库执行健康检查。

    Returns:
        包含健康检查结果的字典:
        - database_exists: bool
        - tables_created: bool
        - table_count: int
        - can_query: bool
        - status: str ('healthy', 'unhealthy')
    """
    health = {
        "database_exists": False,
        "tables_created": False,
        "table_count": 0,
        "can_query": False,
        "status": "unhealthy"
    }

    try:
        # 检查数据库文件是否存在
        health["database_exists"] = database_exists()

        # 检查表是否已创建
        tables = get_table_names()
        health["table_count"] = len(tables)
        health["tables_created"] = len(tables) > 0

        # 测试基本查询
        db = SessionLocal()
        try:
            # 尝试简单查询
            db.execute(text("SELECT 1"))
            health["can_query"] = True
        finally:
            db.close()

        # 总体状态
        if all([health["database_exists"], health["tables_created"], health["can_query"]]):
            health["status"] = "healthy"

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        health["error"] = str(e)

    return health


def display_health_check(health: dict, verbose: bool = False) -> None:
    """
    显示健康检查结果。

    Args:
        health: 健康检查字典
        verbose: 如果为 True，显示详细输出
    """
    logger.info("数据库健康检查结果:")
    logger.info(f"  状态: {health['status'].upper()}")
    logger.info(f"  数据库存在: {health['database_exists']}")
    logger.info(f"  表已创建: {health['tables_created']}")
    logger.info(f"  表数量: {health['table_count']}")
    logger.info(f"  可以查询: {health['can_query']}")

    if verbose and health['table_count'] > 0:
        tables = get_table_names()
        logger.info(f"  表: {', '.join(tables)}")

    if 'error' in health:
        logger.error(f"  错误: {health['error']}")


def display_created_tables() -> None:
    """
    显示已创建表的列表。
    """
    tables = get_table_names()
    logger.info(f"已创建 {len(tables)} 个表:")
    for table_name in tables:
        logger.info(f"  - {table_name}")


def main() -> None:
    """
    主初始化函数，带有 CLI 参数解析。
    """
    parser = argparse.ArgumentParser(
        description="初始化 Agent 平台 SQLite 数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m services.init_db                 # 初始化数据库
  python -m services.init_db --force         # 删除并重新创建数据库
  python -m services.init_db --verbose       # 显示详细输出
  python -m services.init_db --force --verbose  # 两个选项
        """
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='删除所有现有表并重新创建数据库（警告：删除所有数据）'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='启用详细日志输出'
    )

    args = parser.parse_args()

    # 设置日志
    logger = setup_logging(verbose=args.verbose)

    # 打印标题
    logger.info("=" * 70)
    logger.info("Agent 平台数据库初始化")
    logger.info("=" * 70)
    logger.debug(f"启动时间: {datetime.now().isoformat()}")

    try:
        # 确保数据目录存在
        data_dir = ensure_data_directory()
        logger.info(f"数据目录: {data_dir.absolute()}")

        # 检查数据库是否已存在
        db_exists = database_exists()

        if db_exists and not args.force:
            logger.info("数据库文件已存在")
            tables = get_table_names()
            if tables:
                logger.info(f"找到现有表: {', '.join(tables)}")
                logger.info("正在创建任何缺失的表（可安全继续）...")
            else:
                logger.info("未找到现有表，正在创建新表...")
        elif db_exists and args.force:
            logger.warning("--force 标志已指定: 正在删除所有现有表！")
            logger.warning("这将不可逆地删除所有数据！")
            drop_all_tables()
            logger.info("正在继续创建新表...")
        else:
            logger.info("正在创建新数据库")

        # 初始化数据库
        initialize_database()

        # 显示已创建的表
        display_created_tables()

        # 执行健康检查
        logger.info("")
        health = health_check()
        display_health_check(health, verbose=args.verbose)

        # 最终成功消息
        db_path = Path(DATABASE_PATH)
        logger.info("")
        logger.info("=" * 70)
        if health['status'] == 'healthy':
            logger.info("✓ 数据库初始化成功！")
            logger.info(f"  位置: {db_path.absolute()}")
            logger.info(f"  表数量: {health['table_count']}")
            logger.info(f"  状态: {health['status'].upper()}")
        else:
            logger.error("✗ 数据库初始化完成但有错误")
            logger.error(f"  状态: {health['status']}")
        logger.info("=" * 70)

        # 以适当的代码退出
        sys.exit(0 if health['status'] == 'healthy' else 1)

    except KeyboardInterrupt:
        logger.warning("\n初始化被用户取消")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ 初始化期间出错: {e}")
        logger.debug("异常详情:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
