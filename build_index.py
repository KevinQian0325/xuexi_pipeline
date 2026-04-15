import json
import sqlite3
from datetime import datetime
from pathlib import Path

from config import (
    FIXED_JSON_DIR,
    STATUS_NEW,
    get_db_dir,
    get_db_path,
)


VIDEO_EXTRA_COLUMNS = {
    "source_page_url": "TEXT",
    "source_json_name": "TEXT",
    "material_dir": "TEXT",
    "attempt_count": "INTEGER DEFAULT 0",
    "last_run_id": "TEXT",
    "last_processed_at": "TEXT",
    "error_step": "TEXT",
    "error_type": "TEXT",
    "m3u8_done_at": "TEXT",
    "video_done_at": "TEXT",
    "audio_done_at": "TEXT",
    "asr_done_at": "TEXT",
    "docx_done_at": "TEXT",
    "mp4_size": "INTEGER",
    "wav_size": "INTEGER",
    "audio_duration_ms": "INTEGER",
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def flatten_json(obj):
    """
    递归展开 JSON，提取所有 dict
    """
    results = []

    if isinstance(obj, dict):
        results.append(obj)
        for v in obj.values():
            results.extend(flatten_json(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(flatten_json(item))

    return results


def is_valid_content_record(d: dict) -> bool:
    """
    判断一个 dict 是否是有效内容条目
    """
    if not isinstance(d, dict):
        return False

    item_id = d.get("itemId") or d.get("item_id")
    title = d.get("title")
    url = d.get("url")
    item_type = str(d.get("itemType", "")).strip()
    data_valid = d.get("dataValid", True)

    if not item_id:
        return False

    if not isinstance(title, str) or not title.strip():
        return False

    if not isinstance(url, str) or not url.strip():
        return False

    if "xuexi.cn/lgpage/detail/index.html" not in url:
        return False

    if item_type.lower() == "outerlink":
        return False

    if data_valid is False:
        return False

    return True


def is_video_record(d: dict) -> bool:
    """
    判断是否是视频内容
    """
    item_type = str(d.get("itemType", "")).strip()
    content_type = str(d.get("type", "")).strip()

    return content_type == "shipin" or item_type == "kPureVideo"


def extract_video_records(data: dict) -> list[dict]:
    """
    从固定 JSON 中提取视频记录
    """
    records = []
    dicts = flatten_json(data)

    for d in dicts:
        if not is_valid_content_record(d):
            continue

        if not is_video_record(d):
            continue

        item_id = str(d.get("itemId") or d.get("item_id"))
        title = str(d.get("title", "")).strip()
        detail_url = str(d.get("url", "")).strip()
        publish_time = str(d.get("publishTime", "")).strip()
        item_type = str(d.get("itemType", "")).strip()
        content_type = str(d.get("type", "")).strip()

        records.append({
            "item_id": item_id,
            "title": title,
            "detail_url": detail_url,
            "publish_time": publish_time,
            "item_type": item_type,
            "content_type": content_type,
        })

    # 按 item_id 去重
    unique = {}
    for r in records:
        unique[r["item_id"]] = r

    return list(unique.values())


def create_table(conn: sqlite3.Connection) -> None:
    """
    建表/迁移：每个运行数据库对应一个固定 JSON
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        item_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        detail_url TEXT NOT NULL,
        publish_time TEXT,
        item_type TEXT,
        content_type TEXT,
        status TEXT NOT NULL,
        m3u8_url TEXT,
        mp4_path TEXT,
        wav_path TEXT,
        docx_path TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    existing_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(videos)").fetchall()
    }

    for column_name, column_type in VIDEO_EXTRA_COLUMNS.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE videos ADD COLUMN {column_name} {column_type}")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS crawl_runs (
        run_id TEXT PRIMARY KEY,
        page_url TEXT NOT NULL,
        process_start_time TEXT,
        process_end_time TEXT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        target_count INTEGER DEFAULT 0,
        success_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        crawl_log_path TEXT,
        error_message TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS video_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        step TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_publish_time ON videos(publish_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_status_publish_time ON videos(status, publish_time)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_last_run_id ON videos(last_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at ON crawl_runs(started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_events_run_item ON video_events(run_id, item_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_events_step_status ON video_events(step, status)")
    conn.commit()


def upsert_video_record(conn: sqlite3.Connection, record: dict) -> None:
    """
    插入或更新视频记录：
    - 新记录：status = NEW
    - 旧记录：保留原 status 和路径，只更新基础元信息
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing = conn.execute(
        "SELECT item_id, status FROM videos WHERE item_id = ?",
        (record["item_id"],)
    ).fetchone()

    if existing is None:
        conn.execute("""
        INSERT INTO videos (
            item_id,
            title,
            detail_url,
            publish_time,
            item_type,
            content_type,
            status,
            m3u8_url,
            mp4_path,
            wav_path,
            docx_path,
            error_message,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["item_id"],
            record["title"],
            record["detail_url"],
            record["publish_time"],
            record["item_type"],
            record["content_type"],
            STATUS_NEW,
            None,
            None,
            None,
            None,
            None,
            now,
            now,
        ))
    else:
        conn.execute("""
        UPDATE videos
        SET
            title = ?,
            detail_url = ?,
            publish_time = ?,
            item_type = ?,
            content_type = ?,
            updated_at = ?
        WHERE item_id = ?
        """, (
            record["title"],
            record["detail_url"],
            record["publish_time"],
            record["item_type"],
            record["content_type"],
            now,
            record["item_id"],
        ))

    conn.commit()

    conn.execute("""
    UPDATE videos
    SET
        source_json_name = COALESCE(source_json_name, ?)
    WHERE item_id = ?
    """, (
        record.get("source_json_name"),
        record["item_id"],
    ))
    conn.commit()


def build_index_for_one_json(site_name: str, json_name: str, json_path: Path) -> dict:
    """
    单个固定 JSON -> 对应运行数据库
    """
    print("=" * 100)
    print(f"开始建索引：{json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = extract_video_records(data)

    db_dir = get_db_dir(site_name)
    ensure_dir(db_dir)
    db_path = get_db_path(site_name, json_name)

    conn = sqlite3.connect(db_path)
    create_table(conn)

    for record in records:
        record["source_json_name"] = json_name
        upsert_video_record(conn, record)

    total = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
    conn.close()

    print(f"[完成] {json_name}")
    print(f"  当前视频记录数：{total}")
    print(f"  本次提取视频数：{len(records)}")
    print(f"  数据库路径：{db_path}")

    return {
        "site_name": site_name,
        "json_name": json_name,
        "json_path": str(json_path),
        "db_path": str(db_path),
        "extracted_video_count": len(records),
        "db_total_count": total,
    }


def build_index_for_all_fixed_json() -> list[dict]:
    """
    遍历 JSON 存储库目录，为每个 网站/固定json 建立对应运行数据库
    """
    results = []

    if not FIXED_JSON_DIR.exists():
        print(f"JSON 存储库目录不存在：{FIXED_JSON_DIR}")
        return results

    for site_dir in FIXED_JSON_DIR.iterdir():
        if not site_dir.is_dir():
            continue

        site_name = site_dir.name

        for json_path in site_dir.glob("*.json"):
            json_name = json_path.name
            result = build_index_for_one_json(site_name, json_name, json_path)
            results.append(result)

    return results


def main():
    results = build_index_for_all_fixed_json()

    print("\n" + "=" * 100)
    print("全部建索引完成：")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
