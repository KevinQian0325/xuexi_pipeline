import json
import uuid
from datetime import datetime
from pathlib import Path

import config
from discover_json import crawl_fixed_jsons_for_page
from build_index import build_index_for_one_json
from process_video import process_sites, update_crawl_log_path
from refresh_summary import refresh_summaries


def get_target_page_urls() -> list[str]:
    """
    优先读取 config.TARGET_PAGE_URLS
    如果没有这个配置，就退回到 config.PAGE_URLS
    """
    target_page_urls = getattr(config, "TARGET_PAGE_URLS", None)
    if target_page_urls is None:
        return config.PAGE_URLS
    return target_page_urls


def get_process_time_range() -> tuple[str | None, str | None]:
    """
    优先读取 config.PROCESS_START_TIME / PROCESS_END_TIME
    如果没有，就默认 None
    """
    start_time = getattr(config, "PROCESS_START_TIME", None)
    end_time = getattr(config, "PROCESS_END_TIME", None)
    return start_time, end_time


def build_index_for_target_sites(target_page_urls: list[str]) -> list[dict]:
    """
    只为本次目标网站建立/更新索引
    """
    results = []

    for page_url in target_page_urls:
        site_name = config.page_url_to_site_name(page_url)
        site_fixed_json_dir = config.get_fixed_json_dir(site_name)

        if not site_fixed_json_dir.exists():
            print(f"[INDEX] JSON 存储库目录不存在，跳过：{site_fixed_json_dir}")
            continue

        for json_path in site_fixed_json_dir.glob("*.json"):
            json_name = json_path.name
            result = build_index_for_one_json(site_name, json_name, json_path)
            results.append(result)

    return results


def build_processed_item_ids_by_site(process_results: list[dict]) -> dict[str, list[str]]:
    """
    汇总本轮实际进入处理流程的视频 item_id。
    """
    ids_by_site = {}

    for result in process_results:
        site_name = result["site_name"]
        processed_item_ids = result.get("processed_item_ids", [])
        ids_by_site.setdefault(site_name, set()).update(processed_item_ids)

    return {
        site_name: sorted(item_ids)
        for site_name, item_ids in ids_by_site.items()
    }


def save_crawl_log_paths_to_runs(process_results: list[dict], crawl_log_results: list[dict]) -> None:
    """
    把本轮爬取日志路径回写到每个运行数据库的 crawl_runs 表。
    """
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


def main():
    run_id = str(uuid.uuid4())
    run_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_page_urls = get_target_page_urls()
    process_start_time, process_end_time = get_process_time_range()

    print("=" * 100)
    print("Pipeline 开始")
    print(f"运行批次 run_id：{run_id}")
    print("本次目标网站：")
    print(json.dumps(target_page_urls, ensure_ascii=False, indent=2))
    print(f"时间范围：start_time={process_start_time}, end_time={process_end_time}")
    print("=" * 100)

    # 1. 抓固定 JSON，保存到程序运行文件夹
    discover_results = []
    for page_url in target_page_urls:
        result = crawl_fixed_jsons_for_page(page_url)
        discover_results.append(result)

    # 2. 根据固定 JSON 建/更新运行数据库
    index_results = build_index_for_target_sites(target_page_urls)

    # 3. 处理视频
    process_results = process_sites(
        target_page_urls=target_page_urls,
        start_time=process_start_time,
        end_time=process_end_time,
        run_id=run_id,
        run_started_at=run_started_at,
    )

    # 4. 刷新爬取日志
    processed_item_ids_by_site = build_processed_item_ids_by_site(process_results)
    crawl_log_results = refresh_summaries(
        target_page_urls=target_page_urls,
        processed_item_ids_by_site=processed_item_ids_by_site,
        run_id=run_id,
    )
    save_crawl_log_paths_to_runs(process_results, crawl_log_results)

    final_result = {
        "run_id": run_id,
        "run_started_at": run_started_at,
        "target_page_urls": target_page_urls,
        "process_start_time": process_start_time,
        "process_end_time": process_end_time,
        "discover_results": discover_results,
        "index_results": index_results,
        "process_results": process_results,
        "crawl_log_results": crawl_log_results,
    }

    print("\n" + "=" * 100)
    print("Pipeline 全部完成")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
