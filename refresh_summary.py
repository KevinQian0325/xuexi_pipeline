import json
import sqlite3
from pathlib import Path

from config import (
    FIXED_JSON_DIR,
    STATUS_DOCX_DONE,
    get_fixed_json_path,
    get_db_path,
    get_summary_dir,
    get_summary_path,
)


# =========================================================
# 1. 基础工具
# =========================================================
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


# =========================================================
# 2. fixed_json 里的记录筛选
# =========================================================
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
    从 fixed json 中提取视频记录
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
        publish_time = str(d.get("publishTime", "")).strip()

        records.append({
            "item_id": item_id,
            "title": title,
            "publish_time": publish_time,
        })

    # 按 item_id 去重
    unique = {}
    for r in records:
        unique[r["item_id"]] = r

    # 默认按发布时间倒序
    def sort_key(x):
        return x.get("publish_time") or ""

    return sorted(unique.values(), key=sort_key, reverse=True)


# =========================================================
# 3. 读取 db 状态
# =========================================================
def load_status_map_from_db(db_path: Path) -> dict[str, str]:
    """
    从 db 里读取每个 item_id 的状态信息
    返回：
    {
        item_id: status
    }
    """
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT item_id, status
        FROM videos
    """).fetchall()

    conn.close()

    status_map = {}
    for row in rows:
        status_map[row["item_id"]] = row["status"]

    return status_map


# =========================================================
# 4. 生成单个 fixed json 的 summary
# =========================================================
def build_summary_for_one_json(site_name: str, json_name: str) -> dict:
    fixed_json_path = get_fixed_json_path(site_name, json_name)
    db_path = get_db_path(site_name, json_name)

    if not fixed_json_path.exists():
        raise FileNotFoundError(f"fixed json 不存在：{fixed_json_path}")

    with open(fixed_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    video_records = extract_video_records(data)
    status_map = load_status_map_from_db(db_path)

    summary_videos = []
    done_count = 0
    pending_count = 0

    for record in video_records:
        item_id = record["item_id"]
        raw_status = status_map.get(item_id, "NEW")

        if raw_status == STATUS_DOCX_DONE:
            display_status = "已完成"
            done_count += 1
        else:
            display_status = "未完成"
            pending_count += 1

        summary_videos.append({
            "title": record["title"],
            "status": display_status
        })

    summary_data = {
        "site_name": site_name,
        "json_name": json_name,
        "video_count": len(summary_videos),
        "done_count": done_count,
        "pending_count": pending_count,
        "videos": summary_videos,
    }

    return summary_data


def save_summary_for_one_json(site_name: str, json_name: str) -> Path:
    summary_data = build_summary_for_one_json(site_name, json_name)

    summary_dir = get_summary_dir(site_name)
    ensure_dir(summary_dir)

    summary_path = get_summary_path(site_name, json_name)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"[SUMMARY] 已保存：{summary_path}")
    return summary_path


# =========================================================
# 5. 刷新 summary
# =========================================================
def discover_summary_targets(target_site_names: list[str] | None = None) -> list[tuple[str, str]]:
    """
    返回要刷新 summary 的目标：
    [(site_name, json_name), ...]

    规则：
    - target_site_names is None -> 刷新全部网站下全部 fixed json
    - target_site_names 有值 -> 只刷新这些网站
    """
    targets = []

    if not FIXED_JSON_DIR.exists():
        return targets

    target_site_name_set = set(target_site_names) if target_site_names else None

    for site_dir in FIXED_JSON_DIR.iterdir():
        if not site_dir.is_dir():
            continue

        site_name = site_dir.name

        if target_site_name_set is not None and site_name not in target_site_name_set:
            continue

        for json_path in site_dir.glob("*.json"):
            targets.append((site_name, json_path.name))

    return targets


def refresh_summaries(target_site_names: list[str] | None = None) -> list[dict]:
    """
    刷新 summary：
    - 默认刷新全部网站
    - 也可以只刷新部分网站
    """
    targets = discover_summary_targets(target_site_names=target_site_names)

    if not targets:
        print("没有找到可刷新 summary 的目标。")
        return []

    results = []

    for site_name, json_name in targets:
        try:
            summary_path = save_summary_for_one_json(site_name, json_name)
            results.append({
                "site_name": site_name,
                "json_name": json_name,
                "summary_path": str(summary_path),
                "status": "SUCCESS",
            })
        except Exception as e:
            results.append({
                "site_name": site_name,
                "json_name": json_name,
                "summary_path": None,
                "status": "FAILED",
                "error": str(e),
            })
            print(f"[SUMMARY FAILED] {site_name}/{json_name} -> {e}")

    return results