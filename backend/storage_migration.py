import shutil
import sqlite3
from pathlib import Path
from typing import Any

from backend import app_store
from backend import config
from backend.build_index import create_table


def normalize_storage_root(raw_path: str) -> Path:
    return config.resolve_project_path(
        raw_path,
        config.PROJECT_DIR / "结果文件夹",
    ).expanduser().resolve(strict=False)


def rewrite_path(value: str | None, old_root: Path, new_root: Path) -> str | None:
    if not value:
        return value

    current_path = Path(value).expanduser().resolve(strict=False)
    try:
        relative_path = current_path.relative_to(old_root)
    except ValueError:
        return value

    return str(new_root / relative_path)


def ensure_not_nested(old_root: Path, new_root: Path) -> None:
    try:
        new_root.relative_to(old_root)
    except ValueError:
        pass
    else:
        raise RuntimeError("新根目录不能放在旧根目录内部，请选择一个独立目录。")

    try:
        old_root.relative_to(new_root)
    except ValueError:
        pass
    else:
        raise RuntimeError("旧根目录不能位于新根目录内部，请选择一个独立目录。")


def migrate_root_contents(old_root: Path, new_root: Path) -> int:
    if not old_root.exists():
        new_root.mkdir(parents=True, exist_ok=True)
        return 0

    new_root.mkdir(parents=True, exist_ok=True)
    children = list(old_root.iterdir())
    for child in children:
        target = new_root / child.name
        if target.exists():
            raise RuntimeError(f"新根目录中已存在同名内容，无法迁移：{target}")

    moved_count = 0
    for child in children:
        target = new_root / child.name
        shutil.move(str(child), str(target))
        moved_count += 1

    return moved_count


def update_app_db_paths(old_root: Path, new_root: Path) -> int:
    updated_count = 0
    with app_store.connect() as conn:
        task_rows = conn.execute("SELECT id, result_dir FROM task_runs").fetchall()
        for row in task_rows:
            next_value = rewrite_path(row["result_dir"], old_root, new_root)
            if next_value != row["result_dir"]:
                conn.execute(
                    "UPDATE task_runs SET result_dir = ? WHERE id = ?",
                    (next_value, row["id"]),
                )
                updated_count += 1

        detail_rows = conn.execute("SELECT id, mp4_path, wav_path, docx_path FROM task_run_details").fetchall()
        for row in detail_rows:
            next_values = {
                "mp4_path": rewrite_path(row["mp4_path"], old_root, new_root),
                "wav_path": rewrite_path(row["wav_path"], old_root, new_root),
                "docx_path": rewrite_path(row["docx_path"], old_root, new_root),
            }
            changed_fields = {
                key: value
                for key, value in next_values.items()
                if value != row[key]
            }
            if not changed_fields:
                continue

            set_clause = ", ".join(f"{key} = ?" for key in changed_fields)
            conn.execute(
                f"UPDATE task_run_details SET {set_clause} WHERE id = ?",
                list(changed_fields.values()) + [row["id"]],
            )
            updated_count += 1

        conn.commit()

    return updated_count


def update_runtime_db_paths(old_root: Path, new_root: Path) -> int:
    updated_count = 0
    if not config.DB_DIR.exists():
        return updated_count

    for db_path in config.DB_DIR.glob("*/*.db"):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            create_table(conn)
            rows = conn.execute("""
            SELECT item_id, material_dir, mp4_path, wav_path, docx_path
            FROM videos
            """).fetchall()
            for row in rows:
                next_values = {
                    "material_dir": rewrite_path(row["material_dir"], old_root, new_root),
                    "mp4_path": rewrite_path(row["mp4_path"], old_root, new_root),
                    "wav_path": rewrite_path(row["wav_path"], old_root, new_root),
                    "docx_path": rewrite_path(row["docx_path"], old_root, new_root),
                }
                changed_fields = {
                    key: value
                    for key, value in next_values.items()
                    if value != row[key]
                }
                if not changed_fields:
                    continue

                set_clause = ", ".join(f"{key} = ?" for key in changed_fields)
                params = list(changed_fields.values()) + [row["item_id"]]
                conn.execute(
                    f"UPDATE videos SET {set_clause} WHERE item_id = ?",
                    params,
                )
                updated_count += 1
            conn.commit()
        finally:
            conn.close()

    return updated_count


def migrate_storage_root(old_raw_path: str, new_raw_path: str) -> dict[str, Any]:
    old_root = normalize_storage_root(old_raw_path)
    new_root = normalize_storage_root(new_raw_path)

    if old_root == new_root:
        return {
            "changed": False,
            "oldRoot": str(old_root),
            "newRoot": str(new_root),
            "movedCount": 0,
            "updatedPathCount": 0,
        }

    ensure_not_nested(old_root, new_root)
    moved_count = migrate_root_contents(old_root, new_root)
    app_updated_count = update_app_db_paths(old_root, new_root)
    runtime_updated_count = update_runtime_db_paths(old_root, new_root)

    return {
        "changed": True,
        "oldRoot": str(old_root),
        "newRoot": str(new_root),
        "movedCount": moved_count,
        "updatedPathCount": app_updated_count + runtime_updated_count,
    }
