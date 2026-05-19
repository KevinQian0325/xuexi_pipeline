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
        mp4_path TEXT,
        wav_path TEXT,
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
        "mp4_path": "TEXT",
        "wav_path": "TEXT",
        "error_step": "TEXT",
        "error_type": "TEXT",
        "error_message": "TEXT",
        "ignored_at": "TEXT",
        "ignored_reason": "TEXT",
        "ignored_from_status": "TEXT",
    }.items():
        if column_name not in existing_detail_columns:
            conn.execute(f"ALTER TABLE task_run_details ADD COLUMN {column_name} {column_type}")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_runs_executed_at ON task_runs(executed_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_task_run_details_run_id ON task_run_details(run_id)")
    backfill_task_run_detail_artifact_paths(conn)
    conn.commit()


def backfill_task_run_detail_artifact_paths(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
    SELECT id, item_id
    FROM task_run_details
    WHERE COALESCE(mp4_path, '') = ''
       OR COALESCE(wav_path, '') = ''
       OR COALESCE(docx_path, '') = ''
    """).fetchall()
    if not rows or not config.DB_DIR.exists():
        return

    detail_ids_by_item_id: dict[str, list[int]] = {}
    for row in rows:
        detail_ids_by_item_id.setdefault(str(row["item_id"]), []).append(int(row["id"]))

    remaining_item_ids = set(detail_ids_by_item_id)
    for db_path in config.DB_DIR.glob("*/*.db"):
        if not remaining_item_ids:
            break

        runtime_conn = sqlite3.connect(db_path)
        runtime_conn.row_factory = sqlite3.Row
        try:
            item_ids = sorted(remaining_item_ids)
            for start in range(0, len(item_ids), 900):
                batch = item_ids[start:start + 900]
                placeholders = ",".join("?" for _ in batch)
                video_rows = runtime_conn.execute(f"""
                SELECT item_id, mp4_path, wav_path, docx_path
                FROM videos
                WHERE item_id IN ({placeholders})
                """, batch).fetchall()

                for video_row in video_rows:
                    item_id = str(video_row["item_id"])
                    for detail_id in detail_ids_by_item_id.get(item_id, []):
                        conn.execute("""
                        UPDATE task_run_details
                        SET mp4_path = CASE WHEN COALESCE(mp4_path, '') = '' THEN ? ELSE mp4_path END,
                            wav_path = CASE WHEN COALESCE(wav_path, '') = '' THEN ? ELSE wav_path END,
                            docx_path = CASE WHEN COALESCE(docx_path, '') = '' THEN ? ELSE docx_path END
                        WHERE id = ?
                        """, (
                            video_row["mp4_path"] or "",
                            video_row["wav_path"] or "",
                            video_row["docx_path"] or "",
                            detail_id,
                        ))
                    remaining_item_ids.discard(item_id)
        except sqlite3.Error:
            continue
        finally:
            runtime_conn.close()


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
        "resultFilesDir": os.getenv("XUEXI_RESULT_STORAGE_ROOT_DIR", ""),
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
        "mp4Path": row["mp4_path"] or "",
        "wavPath": row["wav_path"] or "",
        "docxPath": row["docx_path"] or "",
        "errorStep": row["error_step"] or "",
        "errorType": row["error_type"] or "",
        "errorMessage": row["error_message"] or "",
        "ignoredAt": row["ignored_at"] or "",
        "ignoredReason": row["ignored_reason"] or "",
        "ignoredFromStatus": row["ignored_from_status"] or "",
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
            mp4_path,
            wav_path,
            docx_path,
            error_step,
            error_type,
            error_message,
            ignored_at,
            ignored_reason,
            ignored_from_status,
            sort_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            str(detail["id"]),
            detail["title"],
            detail["detailUrl"],
            detail.get("publishTime"),
            detail["executedAt"],
            detail["status"],
            detail.get("mp4Path") or "",
            detail.get("wavPath") or "",
            detail.get("docxPath") or "",
            detail.get("errorStep") or "",
            detail.get("errorType") or "",
            detail.get("errorMessage") or "",
            detail.get("ignoredAt") or "",
            detail.get("ignoredReason") or "",
            detail.get("ignoredFromStatus") or "",
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
        WHERE status IN ('RUNNING', 'STOP_REQUESTED')
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


def recalculate_task_run_summary(conn: sqlite3.Connection, run_id: int | str) -> None:
    run_row = conn.execute(
        "SELECT status FROM task_runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if run_row is None or run_row["status"] in {"RUNNING", "STOP_REQUESTED", "STOPPED"}:
        return

    details = load_task_run_details(conn, int(run_id))
    success_count, total_count = calculate_task_run_counts_from_details(details)
    status = calculate_task_run_status(success_count, total_count)
    conn.execute("""
    UPDATE task_runs
    SET status = ?,
        success_count = ?,
        total_count = ?,
        updated_at = ?
    WHERE id = ?
    """, (
        status,
        success_count,
        total_count,
        now_string(),
        run_id,
    ))


def recalculate_task_run_summaries(conn: sqlite3.Connection, run_ids: set[int]) -> None:
    for run_id in sorted(run_ids):
        recalculate_task_run_summary(conn, run_id)


def detail_sync_values(detail: dict[str, Any]) -> dict[str, str]:
    return {
        "status": detail.get("status") or "",
        "mp4_path": detail.get("mp4Path") or "",
        "wav_path": detail.get("wavPath") or "",
        "docx_path": detail.get("docxPath") or "",
        "error_step": detail.get("errorStep") or "",
        "error_type": detail.get("errorType") or "",
        "error_message": detail.get("errorMessage") or "",
        "ignored_at": detail.get("ignoredAt") or "",
        "ignored_reason": detail.get("ignoredReason") or "",
        "ignored_from_status": detail.get("ignoredFromStatus") or "",
    }


def sync_task_run_detail_states_by_item_id(
    conn: sqlite3.Connection,
    details: list[dict[str, Any]],
    *,
    skip_run_ids: set[int] | None = None,
) -> None:
    """
    同步同一 item_id 在任务执行明细里的当前处理状态。

    保留每条任务自己的 executed_at/sort_order/run_id，只同步视频实体状态字段。
    EXISTING 是本次运行的展示分类，PROCESSING 是临时态，都不作为全局状态源。
    """
    sync_details = {
        str(detail["id"]): detail
        for detail in details
        if str(detail.get("id", "")).strip()
        and detail.get("status") not in {"EXISTING", "PROCESSING", "PENDING"}
    }
    if not sync_details:
        return

    affected_run_ids: set[int] = set()
    for item_id, detail in sync_details.items():
        rows = conn.execute(
            "SELECT DISTINCT run_id FROM task_run_details WHERE item_id = ? AND status != 'EXISTING'",
            (item_id,),
        ).fetchall()
        affected_run_ids.update(int(row["run_id"]) for row in rows)

        values = detail_sync_values(detail)
        conn.execute("""
        UPDATE task_run_details
        SET status = ?,
            mp4_path = ?,
            wav_path = ?,
            docx_path = ?,
            error_step = ?,
            error_type = ?,
            error_message = ?,
            ignored_at = ?,
            ignored_reason = ?,
            ignored_from_status = ?
        WHERE item_id = ?
          AND status != 'EXISTING'
        """, (
            values["status"],
            values["mp4_path"],
            values["wav_path"],
            values["docx_path"],
            values["error_step"],
            values["error_type"],
            values["error_message"],
            values["ignored_at"],
            values["ignored_reason"],
            values["ignored_from_status"],
            item_id,
        ))

    if skip_run_ids:
        affected_run_ids.difference_update(skip_run_ids)

    recalculate_task_run_summaries(conn, affected_run_ids)


def ignore_task_run_details(run_id: int | str, item_ids: list[str], reason: str = "") -> int:
    normalized_item_ids = sorted({str(item_id) for item_id in item_ids if str(item_id).strip()})
    if not normalized_item_ids:
        return 0

    placeholders = ",".join("?" for _ in normalized_item_ids)
    ignored_at = now_string()
    with connect() as conn:
        affected_rows = conn.execute(f"""
        SELECT DISTINCT run_id
        FROM task_run_details
        WHERE item_id IN ({placeholders})
          AND status NOT IN ('DOCX_DONE', 'EXISTING', 'IGNORED')
        """, normalized_item_ids).fetchall()
        affected_run_ids = {int(row["run_id"]) for row in affected_rows}

        cursor = conn.execute(f"""
        UPDATE task_run_details
        SET ignored_from_status = CASE
                WHEN COALESCE(ignored_from_status, '') = '' THEN status
                ELSE ignored_from_status
            END,
            status = 'IGNORED',
            ignored_at = ?,
            ignored_reason = ?,
            sort_order = sort_order
        WHERE item_id IN ({placeholders})
          AND status NOT IN ('DOCX_DONE', 'EXISTING', 'IGNORED')
        """, (
            ignored_at,
            reason,
            *normalized_item_ids,
        ))
        ignored_count = cursor.rowcount
        recalculate_task_run_summaries(conn, affected_run_ids)
        conn.commit()
    return ignored_count


def ensure_runtime_ignore_columns(conn: sqlite3.Connection) -> None:
    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(videos)").fetchall()
    }
    for column_name, column_type in {
        "ignored_at": "TEXT",
        "ignored_reason": "TEXT",
        "ignored_from_status": "TEXT",
    }.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE videos ADD COLUMN {column_name} {column_type}")


def ignore_runtime_videos(page_url: str, item_ids: list[str], reason: str = "") -> int:
    normalized_item_ids = sorted({str(item_id) for item_id in item_ids if str(item_id).strip()})
    if not normalized_item_ids or not config.DB_DIR.exists():
        return 0

    site_dir = config.DB_DIR / config.page_url_to_site_name(page_url)
    if not site_dir.exists():
        return 0

    ignored_at = now_string()
    ignored_count = 0
    placeholders = ",".join("?" for _ in normalized_item_ids)
    for db_path in site_dir.glob("*.db"):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            ensure_runtime_ignore_columns(conn)
            cursor = conn.execute(f"""
            UPDATE videos
            SET ignored_from_status = CASE
                    WHEN COALESCE(ignored_from_status, '') = '' THEN status
                    ELSE ignored_from_status
                END,
                status = 'IGNORED',
                ignored_at = ?,
                ignored_reason = ?,
                updated_at = ?
            WHERE item_id IN ({placeholders})
              AND status NOT IN ('DOCX_DONE', 'IGNORED')
            """, (
                ignored_at,
                reason,
                ignored_at,
                *normalized_item_ids,
            ))
            ignored_count += cursor.rowcount
            conn.commit()
        finally:
            conn.close()

    return ignored_count


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


def get_task_run_status(run_id: int | str) -> str | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT status FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return row["status"]


def is_task_run_stop_requested(run_id: int | str) -> bool:
    return get_task_run_status(run_id) == "STOP_REQUESTED"


def request_stop_task_run(run_id: int | str) -> bool:
    with connect() as conn:
        cursor = conn.execute("""
        UPDATE task_runs
        SET status = 'STOP_REQUESTED',
            updated_at = ?
        WHERE id = ?
          AND status = 'RUNNING'
        """, (
            now_string(),
            run_id,
        ))
        conn.commit()
        return cursor.rowcount > 0


def request_stop_running_task_runs() -> int:
    with connect() as conn:
        cursor = conn.execute("""
        UPDATE task_runs
        SET status = 'STOP_REQUESTED',
            updated_at = ?
        WHERE status = 'RUNNING'
        """, (now_string(),))
        conn.commit()
        return cursor.rowcount


def prepare_stopped_task_run_resume(run_id: int | str) -> dict[str, Any] | None:
    with connect() as conn:
        run_row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if run_row is None:
            return None
        if run_row["status"] != "STOPPED":
            return {
                "error": "INVALID_STATUS",
                "run": row_to_task_run(run_row, load_task_run_details(conn, int(run_id))),
            }

        pending_rows = conn.execute("""
        SELECT item_id
        FROM task_run_details
        WHERE run_id = ?
          AND status = 'PENDING'
        ORDER BY sort_order
        """, (run_id,)).fetchall()
        pending_item_ids = [str(row["item_id"]) for row in pending_rows]
        if not pending_item_ids:
            return {
                "error": "NO_PENDING",
                "run": row_to_task_run(run_row, load_task_run_details(conn, int(run_id))),
            }

        now = now_string()
        conn.execute("""
        UPDATE task_runs
        SET status = 'RUNNING',
            executed_at = ?,
            duration = '00:00:00',
            updated_at = ?
        WHERE id = ?
        """, (
            now,
            now,
            run_id,
        ))
        conn.execute("""
        UPDATE task_run_details
        SET status = 'PROCESSING',
            executed_at = ?,
            error_step = '',
            error_type = '',
            error_message = ''
        WHERE run_id = ?
          AND status = 'PENDING'
        """, (
            now,
            run_id,
        ))
        details = load_task_run_details(conn, int(run_id))
        success_count, total_count = calculate_task_run_counts_from_details(details)
        conn.execute("""
        UPDATE task_runs
        SET success_count = ?,
            total_count = ?,
            updated_at = ?
        WHERE id = ?
        """, (
            success_count,
            total_count,
            now,
            run_id,
        ))
        conn.commit()

    run = get_task_run(str(run_id))
    if run is None:
        return None
    return {
        "run": run,
        "pending_item_ids": pending_item_ids,
    }


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
                mp4_path,
                wav_path,
                docx_path,
                error_step,
                error_type,
                error_message,
                ignored_at,
                ignored_reason,
                ignored_from_status,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                str(detail["id"]),
                detail["title"],
                detail["detailUrl"],
                detail.get("publishTime"),
                detail.get("executedAt") or now_string(),
                detail["status"],
                detail.get("mp4Path") or "",
                detail.get("wavPath") or "",
                detail.get("docxPath") or "",
                detail.get("errorStep") or "",
                detail.get("errorType") or "",
                detail.get("errorMessage") or "",
                detail.get("ignoredAt") or "",
                detail.get("ignoredReason") or "",
                detail.get("ignoredFromStatus") or "",
                index,
            ))
        sync_task_run_detail_states_by_item_id(
            conn,
            details,
            skip_run_ids={int(run_id)},
        )
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

        success_count, total_count = calculate_task_run_counts_from_details(merged_details)
        if status in {"STOPPED"}:
            merged_status = status
        else:
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
                mp4_path,
                wav_path,
                docx_path,
                error_step,
                error_type,
                error_message,
                ignored_at,
                ignored_reason,
                ignored_from_status,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                str(detail["id"]),
                detail["title"],
                detail["detailUrl"],
                detail.get("publishTime"),
                detail.get("executedAt") or executed_at,
                detail["status"],
                detail.get("mp4Path") or "",
                detail.get("wavPath") or "",
                detail.get("docxPath") or "",
                detail.get("errorStep") or "",
                detail.get("errorType") or "",
                detail.get("errorMessage") or "",
                detail.get("ignoredAt") or "",
                detail.get("ignoredReason") or "",
                detail.get("ignoredFromStatus") or "",
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
        sync_task_run_detail_states_by_item_id(conn, details)
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


def calculate_task_run_counts_from_details(
    details: list[dict[str, Any]],
) -> tuple[int, int]:
    counted_details = [
        detail
        for detail in details
        if detail.get("status") != "EXISTING"
    ]
    success_count = sum(
        1
        for detail in counted_details
        if detail.get("status") in {"DOCX_DONE", "IGNORED"}
    )
    return success_count, len(counted_details)


def get_task_run(run_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return row_to_task_run(row, load_task_run_details(conn, row["id"]))
