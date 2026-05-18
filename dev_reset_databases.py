"""
开发调试用：单纯重置前端 app.db 和后端运行数据库。

这个脚本只做重置，不做备份。需要保留当前数据库时，请先运行：
    python dev_backup_databases.py

不会删除：
- 结果文件夹里的 mp4/wav/docx
- json存储库
- 爬取日志
- 运行日志

用法：
    python dev_reset_databases.py
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


def reset_databases() -> None:
    runtime_dir = config.RUNTIME_DIR
    app_db_path = app_store.APP_DB_PATH
    runtime_db_dir = config.DB_DIR

    runtime_dir.mkdir(parents=True, exist_ok=True)
    remove_if_exists(app_db_path)
    remove_if_exists(runtime_db_dir)

    runtime_db_dir.mkdir(parents=True, exist_ok=True)
    app_store.get_env_config()
    app_store.update_env_config(
        {
            "xuexiAppId": "",
            "xuexiAccessToken": "",
            "resultFilesDir": "",
        },
        allow_path_update=True,
    )


def main() -> None:
    reset_databases()
    print("数据库已重置。")
    print("未创建备份。")
    print(f"新的 app.db：{app_store.APP_DB_PATH}")
    print(f"新的运行数据库目录：{config.DB_DIR}")


if __name__ == "__main__":
    main()
