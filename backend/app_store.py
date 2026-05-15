import os
import sqlite3
from datetime import datetime
from typing import Any

from backend import config


APP_DB_PATH = config.RUNTIME_DIR / "app.db"


SEED_LISTENER_SITES = [
    {
        "remark": "世界眼中的习近平",
        "pageUrl": "https://www.xuexi.cn/3960624581d7231cef96ba3ca43ec77c/d0fd85813f78b23f5e5399baa4304972.html",
        "enabled": True,
        "startDate": "2026-04-01",
        "endDate": "2026-04-30",
        "updatedAt": "2026-05-13 10:08:00",
    },
    {
        "remark": "学习重点",
        "pageUrl": "https://www.xuexi.cn/71a472c6203e03e49df7768d4d01ba31/b78fdcf1d588904b1965faf807264e6f.html",
        "enabled": True,
        "startDate": None,
        "endDate": None,
        "updatedAt": "2026-05-13 09:25:00",
    },
    {
        "remark": "传播中国",
        "pageUrl": "https://www.xuexi.cn/a191dbc3067d516c3e2e17e2e08953d6/b87d700beee2c44826a9202c75d18c85.html",
        "enabled": False,
        "startDate": "2026-05-01",
        "endDate": None,
        "updatedAt": "2026-05-12 17:42:00",
    },
]


def default_task_runs() -> list[dict[str, Any]]:
    return [
        {
            "remark": "世界眼中的习近平",
            "pageUrl": "https://www.xuexi.cn/3960624581d7231cef96ba3ca43ec77c/d0fd85813f78b23f5e5399baa4304972.html",
            "resultDir": str(config.MATERIALS_DIR / "世界眼中的习近平"),
            "status": "PARTIAL_FAILED",
            "successCount": 2,
            "totalCount": 3,
            "executedAt": "2026-05-13 10:42:18",
            "duration": "00:08:32",
            "startDate": "2026-04-01",
            "endDate": "2026-04-30",
            "details": [
                {
                    "id": "11168420022572797752",
                    "title": "习近平同蒙古国总统查波会谈",
                    "detailUrl": "https://www.xuexi.cn/lgpage/detail/index.html?id=11168420022572797752&item_id=11168420022572797752",
                    "publishTime": "2026-05-07 10:20:00",
                    "executedAt": "2026-05-13 10:44:12",
                    "status": "DOCX_DONE",
                    "docxPath": str(config.MATERIALS_DIR / "世界眼中的习近平" / "世界眼中的习近平" / "习近平同蒙古国总统查波会谈__2026-05-07" / "文本.docx"),
                },
                {
                    "id": "11168420022572797753",
                    "title": "习近平会见老挝人民革命党中央总书记、国家主席",
                    "detailUrl": "https://www.xuexi.cn/lgpage/detail/index.html?id=11168420022572797753&item_id=11168420022572797753",
                    "publishTime": "2026-05-07 09:15:00",
                    "executedAt": "2026-05-13 10:47:03",
                    "status": "AUDIO_DONE",
                    "docxPath": "",
                },
                {
                    "id": "11168420022572797754",
                    "title": "中越签署一系列合作文件",
                    "detailUrl": "https://www.xuexi.cn/lgpage/detail/index.html?id=11168420022572797754&item_id=11168420022572797754",
                    "publishTime": "2026-05-06 18:40:00",
                    "executedAt": "2026-05-13 10:50:50",
                    "status": "FAILED",
                    "docxPath": "",
                },
            ],
        },
    ]


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect() -> sqlite3.Connection:
    config.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(APP_DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    seed_defaults(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS app_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS listener_sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remark TEXT NOT NULL,
        page_url TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        start_date TEXT,
        end_date TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS env_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS task_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remark TEXT NOT NULL,
        page_url TEXT NOT NULL,
        result_dir TEXT NOT NULL,
        status TEXT NOT NULL,
        success_count INTEGER NOT NULL DEFAULT 0,
        total_count INTEGER NOT NULL DEFAULT 0,
        executed_at TEXT NOT NULL,
        duration TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS task_run_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        item_id TEXT NOT NULL,
        title TEXT NOT NULL,
        detail_url TEXT NOT NULL,
        publish_time TEXT,
        executed_at TEXT NOT NULL,
        status TEXT NOT NULL,
        docx_path TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (run_id) REFERENCES task_runs(id) ON DELETE CASCADE
    )
    """)
    existing_detail_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(task_run_details)").fetchall()
    }
    for column_name, column_type in {
        "error_step": "TEXT",
        "error_type": "TEXT",
        "error_message": "TEXT",
    }.items():
        if column_name not in existing_detail_columns:
            conn.execute(f"ALTER TABLE task_run_details ADD COLUMN {column_name} {column_type}")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_runs_executed_at ON task_runs(executed_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_run_details_run_id ON task_run_details(run_id)")
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return row["value"]


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("""
    INSERT INTO app_meta (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))


def seed_defaults(conn: sqlite3.Connection) -> None:
    defaults = {
        "xuexiAppId": os.getenv("XUEXI_APP_ID", ""),
        "xuexiAccessToken": os.getenv("XUEXI_ACCESS_TOKEN", ""),
        "resultFilesDir": str(config.RESULT_STORAGE_ROOT_DIR),
    }
    for key, value in defaults.items():
        conn.execute("""
        INSERT OR IGNORE INTO env_config (key, value)
        VALUES (?, ?)
        """, (key, value))

    conn.commit()


def row_to_listener_site(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "remark": row["remark"],
        "pageUrl": row["page_url"],
        "enabled": bool(row["enabled"]),
        "startDate": row["start_date"],
        "endDate": row["end_date"],
        "updatedAt": row["updated_at"],
    }


def list_listener_sites(keyword: str = "") -> list[dict[str, Any]]:
    normalized_keyword = keyword.strip().lower()
    with connect() as conn:
        if normalized_keyword:
            rows = conn.execute("""
            SELECT *
            FROM listener_sites
            WHERE lower(remark) LIKE ? OR lower(page_url) LIKE ?
            ORDER BY id DESC
            """, (
                f"%{normalized_keyword}%",
                f"%{normalized_keyword}%",
            )).fetchall()
        else:
            rows = conn.execute("""
            SELECT *
            FROM listener_sites
            ORDER BY id DESC
            """).fetchall()

    return [row_to_listener_site(row) for row in rows]


def create_listener_site(payload: dict[str, Any]) -> int:
    now = now_string()
    with connect() as conn:
        cursor = conn.execute("""
        INSERT INTO listener_sites (
            remark,
            page_url,
            enabled,
            start_date,
            end_date,
            created_at,
            updated_at
        )
        VALUES (?, ?, 1, ?, ?, ?, ?)
        """, (
            payload["remark"],
            payload["pageUrl"],
            payload.get("startDate"),
            payload.get("endDate"),
            now,
            now,
        ))
        conn.commit()
        return int(cursor.lastrowid)


def get_listener_site(site_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM listener_sites WHERE id = ?",
            (site_id,),
        ).fetchone()
    if row is None:
        return None
    return row_to_listener_site(row)


def update_listener_site_remark(site_id: int, remark: str) -> bool:
    with connect() as conn:
        cursor = conn.execute("""
        UPDATE listener_sites
        SET remark = ?, updated_at = ?
        WHERE id = ?
        """, (remark, now_string(), site_id))
        conn.commit()
        return cursor.rowcount > 0


def update_listener_site_time_range(site_id: int, start_date: str | None, end_date: str | None) -> bool:
    with connect() as conn:
        cursor = conn.execute("""
        UPDATE listener_sites
        SET start_date = ?, end_date = ?, updated_at = ?
        WHERE id = ?
        """, (start_date, end_date, now_string(), site_id))
        conn.commit()
        return cursor.rowcount > 0


def update_listener_site_status(site_id: int, enabled: bool) -> bool:
    with connect() as conn:
        cursor = conn.execute("""
        UPDATE listener_sites
        SET enabled = ?, updated_at = ?
        WHERE id = ?
        """, (1 if enabled else 0, now_string(), site_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_listener_site(site_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM listener_sites WHERE id = ?",
            (site_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_env_config() -> dict[str, str]:
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM env_config").fetchall()
    return {row["key"]: row["value"] for row in rows}


def update_env_config(payload: dict[str, str], allow_path_update: bool) -> None:
    allowed_keys = ["xuexiAppId", "xuexiAccessToken"]
    if allow_path_update:
        allowed_keys.append("resultFilesDir")

    with connect() as conn:
        for key in allowed_keys:
            conn.execute("""
            INSERT INTO env_config (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, payload.get(key, "")))
        conn.commit()


def row_to_task_run(row: sqlite3.Row, details: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "remark": row["remark"],
        "pageUrl": row["page_url"],
        "resultDir": row["result_dir"],
        "status": row["status"],
        "successCount": row["success_count"],
        "totalCount": row["total_count"],
        "executedAt": row["executed_at"],
        "duration": row["duration"],
        "startDate": row["start_date"],
        "endDate": row["end_date"],
        "details": details,
    }


def row_to_task_run_detail(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["item_id"],
        "title": row["title"],
        "detailUrl": row["detail_url"],
        "publishTime": row["publish_time"],
        "executedAt": row["executed_at"],
        "status": row["status"],
        "docxPath": row["docx_path"] or "",
        "errorStep": row["error_step"] or "",
        "errorType": row["error_type"] or "",
        "errorMessage": row["error_message"] or "",
    }


def load_task_run_details(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    rows = conn.execute("""
    SELECT *
    FROM task_run_details
    WHERE run_id = ?
    ORDER BY sort_order ASC, id ASC
    """, (run_id,)).fetchall()
    return [row_to_task_run_detail(row) for row in rows]


def insert_task_run(conn: sqlite3.Connection, run: dict[str, Any]) -> int:
    now = now_string()
    cursor = conn.execute("""
    INSERT INTO task_runs (
        remark,
        page_url,
        result_dir,
        status,
        success_count,
        total_count,
        executed_at,
        duration,
        start_date,
        end_date,
        created_at,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run["remark"],
        run["pageUrl"],
        run["resultDir"],
        run["status"],
        run["successCount"],
        run["totalCount"],
        run["executedAt"],
        run["duration"],
        run.get("startDate"),
        run.get("endDate"),
        now,
        now,
    ))
    run_id = int(cursor.lastrowid)

    for index, detail in enumerate(run.get("details", []), start=1):
        conn.execute("""
        INSERT INTO task_run_details (
            run_id,
            item_id,
            title,
            detail_url,
            publish_time,
            executed_at,
            status,
            docx_path,
            error_step,
            error_type,
            error_message,
            sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            str(detail["id"]),
            detail["title"],
            detail["detailUrl"],
            detail.get("publishTime"),
            detail["executedAt"],
            detail["status"],
            detail.get("docxPath") or "",
            detail.get("errorStep") or "",
            detail.get("errorType") or "",
            detail.get("errorMessage") or "",
            index,
        ))

    return run_id


def list_task_runs() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("""
        SELECT *
        FROM task_runs
        ORDER BY id DESC
        """).fetchall()
        return [
            row_to_task_run(row, load_task_run_details(conn, row["id"]))
            for row in rows
        ]


def has_running_task_runs(run_ids: list[int] | None = None) -> bool:
    params: list[int] = []
    id_filter = ""
    if run_ids:
        placeholders = ",".join("?" for _ in run_ids)
        id_filter = f" AND id IN ({placeholders})"
        params = run_ids

    with connect() as conn:
        row = conn.execute(f"""
        SELECT COUNT(*)
        FROM task_runs
        WHERE status = 'RUNNING'
        {id_filter}
        """, params).fetchone()
    return int(row[0]) > 0


def delete_task_runs(run_ids: list[int]) -> int:
    normalized_ids = sorted({int(run_id) for run_id in run_ids})
    if not normalized_ids:
        return 0

    placeholders = ",".join("?" for _ in normalized_ids)
    with connect() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) FROM task_runs WHERE id IN ({placeholders})",
            normalized_ids,
        ).fetchone()
        deleted_count = int(row[0])
        conn.execute(
            f"DELETE FROM task_run_details WHERE run_id IN ({placeholders})",
            normalized_ids,
        )
        conn.execute(
            f"DELETE FROM task_runs WHERE id IN ({placeholders})",
            normalized_ids,
        )
        conn.commit()
    return deleted_count


def clear_task_runs() -> int:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()
        deleted_count = int(row[0])
        conn.execute("DELETE FROM task_run_details")
        conn.execute("DELETE FROM task_runs")
        conn.commit()
    return deleted_count


def create_task_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    run_ids = []
    with connect() as conn:
        for run in runs:
            run_ids.append(insert_task_run(conn, run))
        conn.commit()

    created_runs = []
    with connect() as conn:
        for run_id in run_ids:
            row = conn.execute(
                "SELECT * FROM task_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is not None:
                created_runs.append(row_to_task_run(row, load_task_run_details(conn, run_id)))

    return created_runs


def update_task_run_summary(
    run_id: int | str,
    *,
    status: str,
    success_count: int | None = None,
    total_count: int | None = None,
    executed_at: str | None = None,
    duration: str | None = None,
) -> bool:
    fields = {
        "status": status,
        "updated_at": now_string(),
    }
    if success_count is not None:
        fields["success_count"] = success_count
    if total_count is not None:
        fields["total_count"] = total_count
    if executed_at is not None:
        fields["executed_at"] = executed_at
    if duration is not None:
        fields["duration"] = duration

    set_clause = ", ".join(f"{key} = ?" for key in fields)
    params = list(fields.values()) + [run_id]

    with connect() as conn:
        cursor = conn.execute(
            f"UPDATE task_runs SET {set_clause} WHERE id = ?",
            params,
        )
        conn.commit()
        return cursor.rowcount > 0


def upsert_task_run_progress_details(
    run_id: int | str,
    details: list[dict[str, Any]],
) -> dict[str, Any] | None:
    with connect() as conn:
        run_row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None:
            return None

        existing_details = load_task_run_details(conn, int(run_id))
        merged_details_by_id = {
            str(detail["id"]): detail
            for detail in existing_details
        }
        for detail in details:
            merged_details_by_id[str(detail["id"])] = detail

        merged_details = []
        seen_ids = set()
        for detail in existing_details:
            detail_id = str(detail["id"])
            merged_details.append(merged_details_by_id[detail_id])
            seen_ids.add(detail_id)

        for detail in details:
            detail_id = str(detail["id"])
            if detail_id not in seen_ids:
                merged_details.append(detail)

        conn.execute("DELETE FROM task_run_details WHERE run_id = ?", (run_id,))
        for index, detail in enumerate(merged_details, start=1):
            conn.execute("""
            INSERT INTO task_run_details (
                run_id,
                item_id,
                title,
                detail_url,
                publish_time,
                executed_at,
                status,
                docx_path,
                error_step,
                error_type,
                error_message,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                str(detail["id"]),
                detail["title"],
                detail["detailUrl"],
                detail.get("publishTime"),
                detail.get("executedAt") or now_string(),
                detail["status"],
                detail.get("docxPath") or "",
                detail.get("errorStep") or "",
                detail.get("errorType") or "",
                detail.get("errorMessage") or "",
                index,
            ))
        conn.commit()

    return get_task_run(str(run_id))


def replace_task_run_details(
    run_id: int | str,
    details: list[dict[str, Any]],
    *,
    status: str,
    executed_at: str,
    duration: str,
) -> dict[str, Any] | None:
    with connect() as conn:
        run_row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None:
            return None

        existing_details = load_task_run_details(conn, int(run_id))
        if existing_details:
            merged_details_by_id = {
                str(detail["id"]): detail
                for detail in existing_details
            }
            for detail in details:
                merged_details_by_id[str(detail["id"])] = detail

            merged_details = []
            seen_ids = set()
            for detail in existing_details:
                detail_id = str(detail["id"])
                merged_details.append(merged_details_by_id[detail_id])
                seen_ids.add(detail_id)

            for detail in details:
                detail_id = str(detail["id"])
                if detail_id not in seen_ids:
                    merged_details.append(detail)
        else:
            merged_details = details

        success_count = sum(1 for detail in merged_details if detail.get("status") == "DOCX_DONE")
        total_count = len(merged_details)
        merged_status = calculate_task_run_status(success_count, total_count)

        conn.execute("DELETE FROM task_run_details WHERE run_id = ?", (run_id,))
        for index, detail in enumerate(merged_details, start=1):
            conn.execute("""
            INSERT INTO task_run_details (
                run_id,
                item_id,
                title,
                detail_url,
                publish_time,
                executed_at,
                status,
                docx_path,
                error_step,
                error_type,
                error_message,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                str(detail["id"]),
                detail["title"],
                detail["detailUrl"],
                detail.get("publishTime"),
                detail.get("executedAt") or executed_at,
                detail["status"],
                detail.get("docxPath") or "",
                detail.get("errorStep") or "",
                detail.get("errorType") or "",
                detail.get("errorMessage") or "",
                index,
            ))

        conn.execute("""
        UPDATE task_runs
        SET status = ?,
            success_count = ?,
            total_count = ?,
            executed_at = ?,
            duration = ?,
            updated_at = ?
        WHERE id = ?
        """, (
            merged_status,
            success_count,
            total_count,
            executed_at,
            duration,
            now_string(),
            run_id,
        ))
        conn.commit()

    return get_task_run(str(run_id))


def calculate_task_run_status(success_count: int, total_count: int) -> str:
    if total_count == 0:
        return "SUCCESS"
    if success_count == total_count:
        return "SUCCESS"
    if success_count > 0:
        return "PARTIAL_FAILED"
    return "FAILED"


def get_task_run(run_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_task_run(row, load_task_run_details(conn, row["id"]))
