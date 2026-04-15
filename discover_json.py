import json
from urllib.parse import urlparse, urlunparse

import requests
from playwright.sync_api import sync_playwright

from config import (
    PAGE_URLS,
    HEADLESS,
    WAIT_MS,
    REQUEST_TIMEOUT,
    PAGE_TIMEOUT_MS,
    QUALIFIED_RECORD_THRESHOLD,
    HEADERS,
    page_url_to_site_name,
    json_url_to_json_name,
    get_fixed_json_dir,
    get_fixed_json_path,
)


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def normalize_url(url: str) -> str:
    """
    去掉 query 参数，只保留固定 JSON 地址
    例如：
    https://www.xuexi.cn/lgdata/vdppiu92n1.json?_st=xxx&js_v=xxx
    ->
    https://www.xuexi.cn/lgdata/vdppiu92n1.json
    """
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


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
    判断一个 dict 是否是“有效内容条目”
    这里只用于筛选“哪些固定 JSON 值得保存”
    不是最终的视频判断。
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


def has_enough_valid_records(obj, threshold: int) -> tuple[bool, int]:
    """
    递归遍历 JSON：
    只要有效内容条目数达到 threshold，就提前停止
    """
    count = 0

    def walk(x):
        nonlocal count

        if count >= threshold:
            return True

        if isinstance(x, dict):
            if is_valid_content_record(x):
                count += 1
                if count >= threshold:
                    return True

            for v in x.values():
                if walk(v):
                    return True

        elif isinstance(x, list):
            for item in x:
                if walk(item):
                    return True

        return False

    reached = walk(obj)
    return reached, count


def discover_lgdata_candidates(page_url: str, headless: bool = True, wait_ms: int = 5000) -> list[str]:
    """
    打开网站页，监听所有 lgdata/*.json 请求
    """
    found_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        def handle_response(response):
            url = response.url
            if "/lgdata/" in url and ".json" in url:
                normalized = normalize_url(url)
                print("捕获到疑似 lgdata JSON：", normalized)
                found_urls.append(normalized)

        page.on("response", handle_response)

        print(f"\n打开页面：{page_url}")

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        except Exception as e:
            print("page.goto 发生异常：", e)

        page.wait_for_timeout(wait_ms)
        browser.close()

    # 去重保序
    return list(dict.fromkeys(found_urls))


def collect_qualified_jsons(candidate_urls: list[str], threshold: int) -> list[dict]:
    """
    从候选 JSON 中筛出满足阈值的固定 JSON
    """
    qualified = []

    for url in candidate_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            reached_threshold, valid_count = has_enough_valid_records(data, threshold)

            print(f"[候选分析] {url}")
            if reached_threshold:
                print(f"  有效内容条目数已达到阈值：{valid_count}+")
                print("  -> 满足阈值，加入保存列表")
                qualified.append({
                    "url": url,
                    "valid_count": valid_count,
                    "data": data,
                })
            else:
                print(f"  有效内容条目数不足：{valid_count}")
                print("  -> 不满足阈值，跳过")

        except Exception as e:
            print(f"[候选分析失败] {url} -> {e}")

    return qualified


def save_qualified_jsons(page_url: str, qualified_jsons: list[dict]) -> list[str]:
    """
    保存固定 JSON 到：
    程序运行文件夹/json存储库/<网站名>/<固定json>.json
    """
    site_name = page_url_to_site_name(page_url)
    site_dir = get_fixed_json_dir(site_name)
    ensure_dir(site_dir)

    saved_paths = []

    for item in qualified_jsons:
        json_url = item["url"]
        data = item["data"]

        json_name = json_url_to_json_name(json_url)
        output_path = get_fixed_json_path(site_name, json_name)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        saved_paths.append(str(output_path))
        print(f"[保存成功] {output_path}")

    return saved_paths


def crawl_fixed_jsons_for_page(page_url: str) -> dict:
    """
    单个网站页完整流程：
    发现候选 -> 筛选 -> 保存固定 JSON
    """
    print("=" * 100)
    print("开始处理页面：")
    print(page_url)
    print("=" * 100)

    candidate_urls = discover_lgdata_candidates(
        page_url=page_url,
        headless=HEADLESS,
        wait_ms=WAIT_MS,
    )

    if not candidate_urls:
        print("未捕获到任何 lgdata JSON。")
        return {
            "page_url": page_url,
            "candidate_count": 0,
            "qualified_count": 0,
            "saved_paths": [],
        }

    print("\n捕获到的候选 JSON：")
    for c in candidate_urls:
        print(" -", c)

    qualified_jsons = collect_qualified_jsons(
        candidate_urls=candidate_urls,
        threshold=QUALIFIED_RECORD_THRESHOLD,
    )

    if not qualified_jsons:
        print("\n没有任何 JSON 满足阈值条件。")
        return {
            "page_url": page_url,
            "candidate_count": len(candidate_urls),
            "qualified_count": 0,
            "saved_paths": [],
        }

    saved_paths = save_qualified_jsons(
        page_url=page_url,
        qualified_jsons=qualified_jsons,
    )

    return {
        "page_url": page_url,
        "candidate_count": len(candidate_urls),
        "qualified_count": len(qualified_jsons),
        "saved_paths": saved_paths,
    }


def main():
    all_results = []

    for page_url in PAGE_URLS:
        result = crawl_fixed_jsons_for_page(page_url)
        all_results.append(result)

    print("\n" + "=" * 100)
    print("全部处理完成，最终结果：")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
