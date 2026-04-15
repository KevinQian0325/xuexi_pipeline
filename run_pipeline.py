import json

import config
from discover_json import crawl_fixed_jsons_for_page
from build_index import build_index_for_one_json
from process_video import process_sites
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
            print(f"[INDEX] fixed_json 目录不存在，跳过：{site_fixed_json_dir}")
            continue

        for json_path in site_fixed_json_dir.glob("*.json"):
            json_name = json_path.name
            result = build_index_for_one_json(site_name, json_name, json_path)
            results.append(result)

    return results


def main():
    target_page_urls = get_target_page_urls()
    process_start_time, process_end_time = get_process_time_range()

    print("=" * 100)
    print("Pipeline 开始")
    print("本次目标网站：")
    print(json.dumps(target_page_urls, ensure_ascii=False, indent=2))
    print(f"时间范围：start_time={process_start_time}, end_time={process_end_time}")
    print("=" * 100)

    # 1. 抓 fixed json
    discover_results = []
    for page_url in target_page_urls:
        result = crawl_fixed_jsons_for_page(page_url)
        discover_results.append(result)

    # 2. 根据 fixed json 建/更新 db
    index_results = build_index_for_target_sites(target_page_urls)

    # 3. 处理视频
    process_results = process_sites(
        target_page_urls=target_page_urls,
        start_time=process_start_time,
        end_time=process_end_time,
    )

    # 4. 刷新 summary
    target_site_names = [config.page_url_to_site_name(url) for url in target_page_urls]
    summary_results = refresh_summaries(target_site_names=target_site_names)

    final_result = {
        "target_page_urls": target_page_urls,
        "process_start_time": process_start_time,
        "process_end_time": process_end_time,
        "discover_results": discover_results,
        "index_results": index_results,
        "process_results": process_results,
        "summary_results": summary_results,
    }

    print("\n" + "=" * 100)
    print("Pipeline 全部完成")
    print(json.dumps(final_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()