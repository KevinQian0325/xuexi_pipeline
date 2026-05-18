import sqlite3
from pathlib import Path
from typing import Any

from backend import app_store
from backend.build_index import create_table
from backend.config import (
    DB_DIR,
    STATUS_AUDIO_DONE,
    STATUS_ASR_DONE,
    STATUS_DOCX_DONE,
    STATUS_FAILED,
    STATUS_M3U8_DONE,
    STATUS_NEW,
    STATUS_VIDEO_DONE,
    page_url_to_site_name,
)
from backend.process_video import sync_video_statuses_with_local_artifacts


ARTIFACT_LABELS = {
    "mp4_path": "视频文件",
    "wav_path": "音频文件",
    "docx_path": "Word 文档",
}

STATUS_LABELS = {
    STATUS_NEW: "待处理",
    STATUS_M3U8_DONE: "已解析视频地址",
    STATUS_VIDEO_DONE: "已下载视频",
    STATUS_AUDIO_DONE: "已提取音频",
    STATUS_ASR_DONE: "已完成转写",
    STATUS_DOCX_DONE: "已生成文档",
    STATUS_FAILED: "处理失败",
}


def existing_file(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path).expanduser()
    return candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0


def expected_status_for_row(row: sqlite3.Row) -> str:
    if existing_file(row["docx_path"]):
        return STATUS_DOCX_DONE
    if existing_file(row["wav_path"]):
        return STATUS_AUDIO_DONE
    if existing_file(row["mp4_path"]):
        return STATUS_VIDEO_DONE
    if row["m3u8_url"]:
        return STATUS_M3U8_DONE
    return STATUS_NEW


def missing_artifacts_for_row(row: sqlite3.Row) -> list[str]:
    missing = []
    for field_name, label in ARTIFACT_LABELS.items():
        stored_path = row[field_name]
        if stored_path and not existing_file(stored_path):
            missing.append(label)
    return missing


def has_processing_trace(row: sqlite3.Row) -> bool:
    return (
        row["status"] != STATUS_NEW
        or bool(row["m3u8_url"])
        or bool(row["mp4_path"])
        or bool(row["wav_path"])
        or bool(row["docx_path"])
    )


def processed_time_bounds(conn: sqlite3.Connection) -> tuple[str | None, str | None]:
    row = conn.execute("""
    SELECT MIN(publish_time), MAX(publish_time)
    FROM videos
    WHERE status != ?
       OR m3u8_url IS NOT NULL
       OR mp4_path != ''
       OR wav_path != ''
       OR docx_path != ''
    """, (STATUS_NEW,)).fetchone()
    if row is None:
        return None, None
    return row[0], row[1]


def db_paths_for_site(page_url: str) -> list[Path]:
    site_name = page_url_to_site_name(page_url)
    site_db_dir = DB_DIR / site_name
    if not site_db_dir.exists():
        return []
    return sorted(site_db_dir.glob("*.db"))


def load_sites(site_ids: list[int]) -> list[dict[str, Any]]:
    sites = []
    for site_id in sorted({int(value) for value in site_ids}):
        site = app_store.get_listener_site(site_id)
        if site is not None:
            sites.append(site)
    return sites


def check_sites(site_ids: list[int]) -> dict[str, Any]:
    sites = load_sites(site_ids)
    details = []
    total_records = 0
    checked_db_count = 0
    missing_file_count = 0
    status_mismatch_count = 0

    for site in sites:
        db_paths = db_paths_for_site(site["pageUrl"])
        if not db_paths:
            details.append({
                "id": f"site-{site['id']}-missing-db",
                "siteId": site["id"],
                "siteRemark": site["remark"],
                "pageUrl": site["pageUrl"],
                "videoTitle": "暂无",
                "currentStatus": "NO_DB",
                "currentStatusLabel": "未找到运行数据库",
                "suggestedStatus": "",
                "suggestedStatusLabel": "",
                "missingArtifacts": ["运行数据库"],
                "message": "该网页还没有运行数据库，可能尚未运行过爬取任务。",
                "fixable": False,
            })
            missing_file_count += 1
            continue

        for db_path in db_paths:
            checked_db_count += 1
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                create_table(conn)
                rows = conn.execute("""
                SELECT
                    item_id,
                    title,
                    detail_url,
                    publish_time,
                    status,
                    m3u8_url,
                    mp4_path,
                    wav_path,
                    docx_path
                FROM videos
                ORDER BY publish_time DESC
                """).fetchall()
            finally:
                conn.close()

            rows = [row for row in rows if has_processing_trace(row)]
            for row in rows:
                total_records += 1
                missing_artifacts = missing_artifacts_for_row(row)
                expected_status = expected_status_for_row(row)
                status_mismatch = row["status"] != expected_status
                if missing_artifacts:
                    missing_file_count += 1
                if status_mismatch:
                    status_mismatch_count += 1

                if not missing_artifacts and not status_mismatch:
                    continue

                details.append({
                    "id": f"{site['id']}-{db_path.stem}-{row['item_id']}",
                    "siteId": site["id"],
                    "siteRemark": site["remark"],
                    "pageUrl": site["pageUrl"],
                    "dbPath": str(db_path),
                    "itemId": row["item_id"],
                    "videoTitle": row["title"],
                    "detailUrl": row["detail_url"],
                    "publishTime": row["publish_time"] or "",
                    "currentStatus": row["status"],
                    "currentStatusLabel": STATUS_LABELS.get(row["status"], row["status"]),
                    "suggestedStatus": expected_status,
                    "suggestedStatusLabel": STATUS_LABELS.get(expected_status, expected_status),
                    "missingArtifacts": missing_artifacts,
                    "message": "、".join(missing_artifacts) + " 不存在" if missing_artifacts else "数据库状态与本地最高产物不一致",
                    "fixable": True,
                })

    return {
        "summary": {
            "siteCount": len(sites),
            "dbCount": checked_db_count,
            "videoCount": total_records,
            "normalCount": max(0, total_records - len([item for item in details if item.get("fixable")])),
            "issueCount": len(details),
            "missingFileCount": missing_file_count,
            "statusMismatchCount": status_mismatch_count,
            "fixableCount": len([item for item in details if item.get("fixable")]),
        },
        "details": details,
    }


def repair_sites(site_ids: list[int]) -> dict[str, Any]:
    sites = load_sites(site_ids)
    repaired_items = []
    checked_db_count = 0

    for site in sites:
        for db_path in db_paths_for_site(site["pageUrl"]):
            checked_db_count += 1
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                create_table(conn)
                start_time, end_time = processed_time_bounds(conn)
                if start_time is None and end_time is None:
                    changed_items = []
                else:
                    changed_items = sync_video_statuses_with_local_artifacts(
                        conn,
                        start_time=start_time,
                        end_time=end_time,
                    )
            finally:
                conn.close()

            for item in changed_items:
                repaired_items.append({
                    **item,
                    "siteId": site["id"],
                    "siteRemark": site["remark"],
                    "dbPath": str(db_path),
                })

    return {
        "summary": {
            "siteCount": len(sites),
            "dbCount": checked_db_count,
            "repairedCount": len(repaired_items),
        },
        "items": repaired_items,
    }
