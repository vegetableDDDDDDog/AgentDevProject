#!/usr/bin/env python
"""
同步模型配置脚本

将 .env 文件中的 OPENAI_MODEL 同步到租户数据库配置
使数据库配置与 .env 保持一致

使用方法:
    python sync_model_config.py
"""

import json
import os
from dotenv import load_dotenv
from services.database import engine
from sqlalchemy import text


def sync_model_config():
    """同步 .env 中的模型配置到数据库"""

    # 1. 加载 .env 文件
    load_dotenv()
    env_model = os.getenv('OPENAI_MODEL', 'glm-4')

    print("=" * 50)
    print("模型配置同步工具")
    print("=" * 50)
    print(f"\n.env 文件中的模型: {env_model}\n")

    # 2. 读取数据库当前配置
    with engine.connect() as conn:
        result = conn.execute(text('SELECT id, name, settings FROM tenants LIMIT 1'))
        row = result.fetchone()

        if not row:
            print("❌ 错误: 没有找到租户")
            return False

        tenant_id, tenant_name, settings_json = row
        settings = json.loads(settings_json) if settings_json else {}
        current_model = settings.get('llm_model', '未配置')

        print(f"租户: {tenant_name}")
        print(f"数据库中的模型: {current_model}\n")

        # 3. 更新配置
        if current_model == env_model:
            print("✅ 配置已一致，无需更新")
            return True

        print(f"更新配置: {current_model} → {env_model}")

        settings['llm_model'] = env_model

        # 4. 保存到数据库
        conn.execute(
            text('UPDATE tenants SET settings = :settings WHERE id = :id'),
            {'settings': json.dumps(settings), 'id': tenant_id}
        )
        conn.commit()

        print(f"✅ 配置已更新为: {env_model}")
        print(f"\n现在实际使用的模型就是: {env_model}")

        return True


if __name__ == '__main__':
    try:
        success = sync_model_config()
        if success:
            print("\n" + "=" * 50)
            print("提示: 请重启后端服务使配置生效")
            print("  pkill -f 'python -m api.main'")
            print("  nohup python -m api.main > /tmp/backend.log 2>&1 &")
            print("=" * 50)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
