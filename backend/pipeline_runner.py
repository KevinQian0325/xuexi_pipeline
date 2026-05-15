import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from backend import app_store
from backend import config
from backend.build_index import build_index_for_one_json
from backend.discover_json import crawl_fixed_jsons_for_page
from backend.process_video import process_sites, update_crawl_log_path
from backend.refresh_summary import refresh_summaries


def date_to_start_time(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value} 00:00:00"


def date_to_end_time(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value} 23:59:59"


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def apply_runtime_config(env_config: dict[str, str]) -> None:
    app_id = env_config.get("xuexiAppId", "")
    access_token = env_config.get("xuexiAccessToken", "")
    result_storage_root = env_config.get("resultFilesDir") or str(config.RESULT_STORAGE_ROOT_DIR)

    os.environ["XUEXI_APP_ID"] = app_id
    os.environ["XUEXI_ACCESS_TOKEN"] = access_token
    os.environ["XUEXI_RESULT_STORAGE_ROOT_DIR"] = result_storage_root

    config.APP_ID = app_id
    config.ACCESS_TOKEN = access_token
    config.RESULT_STORAGE_ROOT_DIR = config.resolve_project_path(
        result_storage_root,
        config.PROJECT_DIR / "结果文件夹",
    )
    config.MATERIALS_DIR = config.RESULT_STORAGE_ROOT_DIR / "结果文件"

    # process_video imported these constants by value, so keep them in sync.
    from backend import process_video

    process_video.APP_ID = app_id
    process_video.ACCESS_TOKEN = access_token


def build_index_for_site(page_url: str) -> list[dict[str, Any]]:
    site_name = config.page_url_to_site_name(page_url)
    site_fixed_json_dir = config.get_fixed_json_dir(site_name)
    results = []

    if not site_fixed_json_dir.exists():
        return results

    for json_path in site_fixed_json_dir.glob("*.json"):
        results.append(build_index_for_one_json(site_name, json_path.name, json_path))

    return results


def build_processed_item_ids_by_site(process_results: list[dict[str, Any]]) -> dict[str, list[str]]:
    ids_by_site: dict[str, set[str]] = {}
    for result in process_results:
        site_name = result["site_name"]
        processed_item_ids = result.get("processed_item_ids", [])
        ids_by_site.setdefault(site_name, set()).update(processed_item_ids)
    return {
        site_name: sorted(item_ids)
        for site_name, item_ids in ids_by_site.items()
    }


def save_crawl_log_paths_to_runs(process_results: list[dict[str, Any]], crawl_log_results: list[dict[str, Any]]) -> None:
    log_path_by_site = {
        result["site_name"]: result.get("crawl_log_path")
        for result in crawl_log_results
        if result.get("status") == "SUCCESS" and result.get("crawl_log_path")
    }

    for result in process_results:
        crawl_log_path = log_path_by_site.get(result["site_name"])
        if not crawl_log_path:
            continue
        update_crawl_log_path(
            db_path=Path(result["db_path"]),
            run_id=result["run_id"],
            crawl_log_path=crawl_log_path,
        )


def load_task_details_from_process_results(process_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details = []
    for result in process_results:
        processed_item_ids = result.get("processed_item_ids", [])
        if not processed_item_ids:
            continue

        placeholders = ",".join("?" for _ in processed_item_ids)
        conn = sqlite3.connect(result["db_path"])
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(f"""
                SELECT
                    item_id,
                    title,
                    detail_url,
                    publish_time,
                    last_processed_at,
                    status,
                    docx_path
                FROM videos
                WHERE item_id IN ({placeholders})
                ORDER BY publish_time DESC
            """, processed_item_ids).fetchall()
        finally:
            conn.close()

        for row in rows:
            details.append({
                "id": row["item_id"],
                "title": row["title"],
                "detailUrl": row["detail_url"],
                "publishTime": row["publish_time"] or "",
                "executedAt": row["last_processed_at"] or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": row["status"],
                "docxPath": row["docx_path"] or "",
            })

    return sorted(details, key=lambda item: item.get("publishTime") or "", reverse=True)


def calculate_run_status(details: list[dict[str, Any]]) -> str:
    if not details:
        return "SUCCESS"

    success_count = sum(1 for detail in details if detail.get("status") == "DOCX_DONE")
    if success_count == len(details):
        return "SUCCESS"
    if success_count > 0:
        return "PARTIAL_FAILED"
    return "FAILED"


def run_real_pipeline_for_task(app_run_id: int, site: dict[str, Any]) -> None:
    started_at = time.time()
    executed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pipeline_run_id = str(uuid.uuid4())

    app_store.update_task_run_summary(
        app_run_id,
        status="RUNNING",
        executed_at=executed_at,
        duration="00:00:00",
    )

    try:
        env_config = app_store.get_env_config()
        apply_runtime_config(env_config)

        page_url = site["pageUrl"]
        config.MATERIALS_SITE_NAME_MAP[page_url] = site["remark"]
        start_time = date_to_start_time(site.get("startDate"))
        end_time = date_to_end_time(site.get("endDate"))

        crawl_fixed_jsons_for_page(page_url)
        build_index_for_site(page_url)
        process_results = process_sites(
            target_page_urls=[page_url],
            start_time=start_time,
            end_time=end_time,
            run_id=pipeline_run_id,
            run_started_at=executed_at,
        )

        processed_item_ids_by_site = build_processed_item_ids_by_site(process_results)
        crawl_log_results = refresh_summaries(
            target_page_urls=[page_url],
            processed_item_ids_by_site=processed_item_ids_by_site,
            run_id=pipeline_run_id,
        )
        save_crawl_log_paths_to_runs(process_results, crawl_log_results)

        details = load_task_details_from_process_results(process_results)
        status = calculate_run_status(details)
        app_store.replace_task_run_details(
            app_run_id,
            details,
            status=status,
            executed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration=format_duration(time.time() - started_at),
        )
    except Exception as exc:
        app_store.update_task_run_summary(
            app_run_id,
            status="FAILED",
            success_count=0,
            total_count=0,
            executed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration=format_duration(time.time() - started_at),
        )
        print(f"[API PIPELINE FAILED] app_run_id={app_run_id}, site={site.get('pageUrl')} -> {exc}")
