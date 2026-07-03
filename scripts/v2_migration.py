#!/usr/bin/env python3
"""VocaLand v2 数据库迁移脚本。

检测旧数据库 → 备份 → 创建新表。

用法：
    python scripts/v2_migration.py                    # 迁移默认 DB
    python scripts/v2_migration.py --db path/to.db    # 指定 DB 路径

安全：
    - 迁移前自动备份到 .bak.v2 文件
    - CREATE TABLE IF NOT EXISTS 幂等操作
    - 旧表不受影响
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from line_c.config import DATABASE_PATH


def backup_db(db_path: Path) -> Path:
    """创建数据库备份。"""
    backup_path = db_path.with_suffix(db_path.suffix + ".bak.v2")
    shutil.copy2(db_path, backup_path)
    print(f"备份已创建: {backup_path} ({backup_path.stat().st_size / 1024:.0f} KB)")
    return backup_path


def run_migration(db_path: Path):
    """执行迁移。"""
    if not db_path.exists():
        print(f"数据库不存在: {db_path}，将自动创建。")

    # 备份
    if db_path.exists():
        backup_db(db_path)

    # 导入并初始化各 repository（各自的 _create_tables 会创建新表）
    from line_c.engine.user_repository import UserRepository
    from line_c.engine.chat_session_repository import ChatSessionRepository
    from line_c.engine.user_vocabulary_repository import UserVocabularyRepository

    print("创建新表...")
    ur = UserRepository(db_path)
    csr = ChatSessionRepository(db_path)
    uvr = UserVocabularyRepository(db_path)

    # 验证
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]
    conn.close()

    print(f"\n当前数据库表 ({len(table_names)}):")
    for t in table_names:
        print(f"  - {t}")

    required = ["user_profile", "chat_session", "user_vocabulary"]
    missing = [t for t in required if t not in table_names]
    if missing:
        print(f"\n警告：缺少表 {missing}")
    else:
        print("\n全部新表已就绪。")

    # 检查是否已有数据
    user_count = ur.count()
    print(f"\n角色数: {user_count}")

    ur.close()
    csr.close()
    uvr.close()

    print("\n迁移完成。原始数据未受影响。")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="VocaLand v2 数据库迁移")
    parser.add_argument("--db", type=str, default=None, help="数据库路径（默认用 config 里的）")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DATABASE_PATH
    run_migration(db_path)
