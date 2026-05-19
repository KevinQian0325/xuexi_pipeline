import sqlite3
from pathlib import Path
from typing import Any

from backend import app_store
from backend.build_index import create_table
from backend.config import (
    DB_DIR,
    STATUS_AUDIO_DONE,
    STATUS_DOCX_DONE,
    STATUS_M3U8_DONE,
    STATUS_NEW,
    STATUS_VIDEO_DONE,
    page_url_to_site_name,
)


ARTIFACTS = [
    ("mp4_path", "视频文件", "视频文件路径缺失", "视频文件不存在"),
    ("wav_path", "音频文件", "音频文件路径缺失", "音频文件不存在"),
    ("docx_path", "Word 文档", "Word 文档路径缺失", "Word 文档不存在"),
]

STATUS_LABELS = {
    STATUS_NEW: "待处理",
    STATUS_M3U8_DONE: "已解析视频地址",
    STATUS_VIDEO_DONE: "已下载视频",
    STATUS_AUDIO_DONE: "已提取音频",
    STATUS_DOCX_DONE: "已生成文档",
}


def existing_file(path: str | None) -> bool:
    if not path:
        return False
    candidate = Path(path).expanduser()
    return candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0


def artifact_issues_for_row(row: sqlite3.Row) -> list[dict[str, str]]:
    issues = []
    for field_name, label, missing_path_label, missing_file_label in ARTIFACTS:
        stored_path = row[field_name]
        if not stored_path:
            issues.append({
                "field": field_name,
                "artifact": label,
                "message": missing_path_label,
                "path": "",
            })
        elif not existing_file(stored_path):
            issues.append({
                "field": field_name,
                "artifact": label,
                "message": missing_file_label,
                "path": stored_path,
            })
    return issues


def repair_status_for_issues(row: sqlite3.Row, issue_fields: list[str]) -> str:
    if "mp4_path" in issue_fields:
        return STATUS_M3U8_DONE if row["m3u8_url"] else STATUS_NEW
    if "wav_path" in issue_fields:
        return STATUS_VIDEO_DONE
    return STATUS_AUDIO_DONE


def reset_fields_for_repair_status(status: str) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "status": status,
        "error_step": None,
        "error_type": None,
        "error_message": None,
        "docx_done_at": None,
    }
    if status in {STATUS_NEW, STATUS_M3U8_DONE, STATUS_VIDEO_DONE}:
        fields.update({
            "audio_done_at": None,
            "asr_done_at": None,
            "wav_size": None,
            "audio_duration_ms": None,
        })
    if status in {STATUS_NEW, STATUS_M3U8_DONE}:
        fields.update({
            "video_done_at": None,
            "mp4_size": None,
        })
    if status == STATUS_NEW:
        fields["m3u8_done_at"] = None
    return fields


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
    completed_records = 0
    checked_db_count = 0
    missing_path_count = 0
    missing_file_count = 0

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
                    docx_path,
                    error_step,
                    error_type,
                    error_message
                FROM videos
                WHERE status = ?
                ORDER BY publish_time DESC
                """, (STATUS_DOCX_DONE,)).fetchall()
            finally:
                conn.close()

            for row in rows:
                completed_records += 1
                artifact_issues = artifact_issues_for_row(row)
                if not artifact_issues:
                    continue

                missing_path_count += sum(1 for issue in artifact_issues if not issue["path"])
                missing_file_count += sum(1 for issue in artifact_issues if issue["path"])
                issue_fields = [issue["field"] for issue in artifact_issues]
                rebuild_status = repair_status_for_issues(row, issue_fields)
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
                    "rebuildFromStatus": rebuild_status,
                    "rebuildFromStatusLabel": STATUS_LABELS.get(rebuild_status, rebuild_status),
                    "missingArtifacts": [issue["artifact"] for issue in artifact_issues],
                    "missingArtifactFields": issue_fields,
                    "artifactIssues": artifact_issues,
                    "mp4Path": row["mp4_path"] or "",
                    "wavPath": row["wav_path"] or "",
                    "docxPath": row["docx_path"] or "",
                    "message": "、".join(issue["message"] for issue in artifact_issues),
                    "fixable": True,
                })

    return {
        "summary": {
            "siteCount": len(sites),
            "dbCount": checked_db_count,
            "videoCount": completed_records,
            "normalCount": max(0, completed_records - len([item for item in details if item.get("fixable")])),
            "issueCount": len(details),
            "missingPathCount": missing_path_count,
            "missingFileCount": missing_file_count,
            "fixableCount": len([item for item in details if item.get("fixable")]),
        },
        "details": details,
    }


def prepare_repair_sites(site_ids: list[int]) -> dict[str, Any]:
    check_result = check_sites(site_ids)
    details = [
        detail
        for detail in check_result["details"]
        if detail.get("fixable") and detail.get("itemId") and detail.get("dbPath")
    ]

    prepared_items = []
    for detail in details:
        db_path = Path(detail["dbPath"])
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            create_table(conn)
            fields = reset_fields_for_repair_status(detail["rebuildFromStatus"])
            set_clause = ", ".join(f"{field_name} = ?" for field_name in fields)
            conn.execute(
                f"UPDATE videos SET {set_clause}, updated_at = datetime('now', 'localtime') WHERE item_id = ?",
                list(fields.values()) + [detail["itemId"]],
            )
            conn.commit()
        finally:
            conn.close()
        prepared_items.append(detail)

    targets_by_site_id: dict[int, dict[str, Any]] = {}
    sites_by_id = {site["id"]: site for site in load_sites(site_ids)}
    for detail in prepared_items:
        site_id = int(detail["siteId"])
        site = sites_by_id.get(site_id)
        if site is None:
            continue
        target = targets_by_site_id.setdefault(site_id, {
            "site": site,
            "itemIds": [],
            "details": [],
        })
        target["itemIds"].append(detail["itemId"])
        target["details"].append(detail)

    return {
        "summary": {
            **check_result["summary"],
            "preparedCount": len(prepared_items),
        },
        "items": prepared_items,
        "targets": list(targets_by_site_id.values()),
    }
