"""
开发调试用：复制当前数据库到备份文件夹。

备份内容：
- 程序运行文件夹/app.db
- 程序运行文件夹/运行数据库

不会复制：
- 结果文件夹里的 mp4/wav/docx
- json存储库
- 爬取日志
- 运行日志

用法：
    python dev_backup_databases.py
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from backend import app_store
from backend import config


def copy_if_exists(source: Path, target_dir: Path) -> bool:
    if not source.exists():
        return False

    target = target_dir / source.name
    if source.is_dir():
        shutil.copytree(source, target)
        return True

    shutil.copy2(source, target)
    return True


def backup_databases() -> Path:
    runtime_dir = config.RUNTIME_DIR
    runtime_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = runtime_dir / f"db_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    copied_app_db = copy_if_exists(app_store.APP_DB_PATH, backup_dir)
    copied_runtime_db = copy_if_exists(config.DB_DIR, backup_dir)

    if not copied_app_db and not copied_runtime_db:
        backup_dir.rmdir()
        raise RuntimeError("没有找到可备份的数据库。")

    return backup_dir


def main() -> None:
    backup_dir = backup_databases()
    print("数据库已备份。")
    print(f"备份目录：{backup_dir}")


if __name__ == "__main__":
    main()
