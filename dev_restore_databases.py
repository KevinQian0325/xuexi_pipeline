"""
开发调试用：从一个数据库备份文件夹恢复当前数据库。

恢复内容：
- 备份文件夹/app.db -> 程序运行文件夹/app.db
- 备份文件夹/运行数据库 -> 程序运行文件夹/运行数据库

支持恢复：
- dev_backup_databases.py 创建的 db_backup_*
- 旧版 dev_reset_databases.py 创建的 db_reset_backup_*

用法：
    python dev_restore_databases.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from backend import app_store
from backend import config


def remove_if_exists(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def is_database_backup_dir(path: Path) -> bool:
    return path.is_dir() and (
        (path / app_store.APP_DB_PATH.name).exists()
        or (path / config.DB_DIR.name).exists()
    )


def list_backup_dirs() -> list[Path]:
    runtime_dir = config.RUNTIME_DIR
    if not runtime_dir.exists():
        return []

    candidates = [
        path
        for path in runtime_dir.iterdir()
        if path.name.startswith(("db_backup_", "db_reset_backup_"))
        and is_database_backup_dir(path)
    ]
    return sorted(candidates, key=lambda path: path.name, reverse=True)


def choose_backup_dir(backup_dirs: list[Path]) -> Path:
    print("请选择要恢复的数据库备份：")
    for index, backup_dir in enumerate(backup_dirs, start=1):
        print(f"{index}. {backup_dir}")

    while True:
        raw_value = input("输入序号：").strip()
        try:
            selected_index = int(raw_value)
        except ValueError:
            print("请输入数字序号。")
            continue

        if 1 <= selected_index <= len(backup_dirs):
            return backup_dirs[selected_index - 1]

        print("序号超出范围。")


def restore_databases(backup_dir: Path) -> None:
    source_app_db = backup_dir / app_store.APP_DB_PATH.name
    source_runtime_db_dir = backup_dir / config.DB_DIR.name

    if not source_app_db.exists() and not source_runtime_db_dir.exists():
        raise RuntimeError(f"备份目录里没有数据库：{backup_dir}")

    config.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    remove_if_exists(app_store.APP_DB_PATH)
    remove_if_exists(config.DB_DIR)

    if source_app_db.exists():
        shutil.copy2(source_app_db, app_store.APP_DB_PATH)

    if source_runtime_db_dir.exists():
        shutil.copytree(source_runtime_db_dir, config.DB_DIR)
    else:
        config.DB_DIR.mkdir(parents=True, exist_ok=True)

    app_store.get_env_config()


def main() -> None:
    backup_dirs = list_backup_dirs()
    if not backup_dirs:
        raise RuntimeError("没有找到数据库备份文件夹。")

    backup_dir = choose_backup_dir(backup_dirs)
    confirm = input(f"确认用这个备份覆盖当前数据库吗？\n{backup_dir}\n输入 YES 继续：").strip()
    if confirm != "YES":
        print("已取消恢复。")
        return

    restore_databases(backup_dir)
    print("数据库已恢复。")
    print(f"来源备份：{backup_dir}")
    print(f"当前 app.db：{app_store.APP_DB_PATH}")
    print(f"当前运行数据库目录：{config.DB_DIR}")


if __name__ == "__main__":
    main()
