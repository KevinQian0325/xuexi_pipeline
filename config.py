import os
from pathlib import Path


def load_local_env(env_path: Path) -> None:
    """
    轻量读取项目根目录下的 .env，不额外依赖 python-dotenv。
    已存在的系统环境变量优先级更高。
    """
    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


# =========================
# 1. 项目根目录
# =========================
PROJECT_DIR = Path(__file__).resolve().parent
load_local_env(PROJECT_DIR / ".env")


# =========================
# 2. 网站入口
# 现在先手动写，后面你再改成从表格读取
# =========================
# 全部网站入口
PAGE_URLS = [
    "https://www.xuexi.cn/a191dbc3067d516c3e2e17e2e08953d6/b87d700beee2c44826a9202c75d18c85.html",
]

# 本次要处理哪些网站
# None 表示处理全部网站
TARGET_PAGE_URLS = None

# 时间范围筛选
PROCESS_START_TIME = "2026-03-05 00:00:00"
PROCESS_END_TIME = "2026-03-05 23:59:59"


# =========================
# 3. 浏览器 / 网络配置
# =========================
HEADLESS = True
WAIT_MS = 5000
REQUEST_TIMEOUT = 20
PAGE_TIMEOUT_MS = 60000


# =========================
# 4. 固定 JSON 筛选规则
# 只要某个候选 JSON 中“有效内容条目”数量达到这个阈值，就保存
# =========================
QUALIFIED_RECORD_THRESHOLD = 20


# =========================
# 5. 视频处理查询规则
# process_video.py 会用到
# 如果不给时间范围，就默认处理全部未完成视频
# =========================
DEFAULT_START_TIME = None
DEFAULT_END_TIME = None


# =========================
# 6. ASR 配置
# =========================
APP_ID = os.getenv("XUEXI_APP_ID", "")
ACCESS_TOKEN = os.getenv("XUEXI_ACCESS_TOKEN", "")
RECOGNIZE_URL = os.getenv(
    "XUEXI_RECOGNIZE_URL",
    "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash",
)
RESOURCE_ID = os.getenv("XUEXI_RESOURCE_ID", "volc.bigasr.auc_turbo")


# =========================
# 7. ffmpeg / 音频配置
# =========================
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CODEC = "pcm_s16le"


# =========================
# 8. ASR 限制与切块配置
# 只要时长或大小任一超限，就启用切块识别
# =========================
MAX_AUDIO_DURATION_MS = 2 * 60 * 60 * 1000   # 2小时
MAX_AUDIO_FILE_SIZE = 100 * 1024 * 1024      # 100MB

# 切块规则：
# 以30分钟为目标点，从目标点往前找最近静音切点；
# 最后一段如果不足30分钟，直接输出
CHUNK_TARGET_MS = 30 * 60 * 1000             # 30分钟
CUT_SEARCH_BACK_MS = 2 * 60 * 1000           # 从目标点往前找2分钟静音
MIN_SILENCE_LEN_MS = 700                     # 静音最小时长
KEEP_SILENCE_MS = 300                        # 切块时前后保留一点静音
SILENCE_THRESH_OFFSET_DB = 16                # 相对整体 dBFS 的静音阈值偏移


# =========================
# 9. 目录结构
# 程序运行文件夹/
#   json存储库/<网站名>/<固定json>.json
#   运行数据库/<网站名>/<固定json>.db
#
# 结果文件夹/
#   爬取日志/<爬取的网址>__<爬取时间>.json
#   结果文件/<网站名>/<固定json>/<视频标题>__<发布时间>/
# =========================
RUNTIME_DIR = PROJECT_DIR / "程序运行文件夹"
RESULT_OUTPUT_DIR = PROJECT_DIR / "结果文件夹"

FIXED_JSON_DIR = RUNTIME_DIR / "json存储库"
DB_DIR = RUNTIME_DIR / "运行数据库"
SUMMARY_DIR = RESULT_OUTPUT_DIR / "爬取日志"
MATERIALS_DIR = RESULT_OUTPUT_DIR / "结果文件"


# =========================
# 10. 公共请求头
# =========================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    )
}


# =========================
# 11. 状态枚举
# =========================
STATUS_NEW = "NEW"
STATUS_NOT_VIDEO = "NOT_VIDEO"
STATUS_M3U8_DONE = "M3U8_DONE"
STATUS_VIDEO_DONE = "VIDEO_DONE"
STATUS_AUDIO_DONE = "AUDIO_DONE"
STATUS_ASR_DONE = "ASR_DONE"
STATUS_DOCX_DONE = "DOCX_DONE"
STATUS_FAILED = "FAILED"


# =========================
# 12. 命名辅助函数
# =========================
def safe_name(text: str) -> str:
    """
    把不适合做路径的字符替换掉
    """
    return (
        str(text)
        .replace("://", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def page_url_to_site_name(page_url: str) -> str:
    """
    页面网址 -> 网站名
    这里先直接用清洗后的网址当网站名
    """
    return safe_name(page_url)


def json_url_to_json_name(json_url: str) -> str:
    """
    固定 JSON URL -> 固定 JSON 文件名
    例如:
    https://www.xuexi.cn/lgdata/vdppiu92n1.json
    -> vdppiu92n1.json
    """
    return Path(json_url).name


def video_folder_name(title: str, publish_time: str) -> str:
    """
    视频目录名：视频标题__发布时间
    """
    return f"{safe_name(title)}__{safe_name(publish_time)}"


# =========================
# 13. 路径生成函数
# 后面其他 py 文件直接 import 调用
# =========================
def get_fixed_json_dir(site_name: str) -> Path:
    return FIXED_JSON_DIR / site_name


def get_summary_dir(site_name: str) -> Path:
    return SUMMARY_DIR


def get_db_dir(site_name: str) -> Path:
    return DB_DIR / site_name


def get_materials_site_dir(site_name: str) -> Path:
    return MATERIALS_DIR / site_name


def get_fixed_json_path(site_name: str, json_name: str) -> Path:
    return get_fixed_json_dir(site_name) / json_name


def get_summary_path(site_name: str, json_name: str) -> Path:
    return get_summary_dir(site_name) / json_name


def get_db_path(site_name: str, json_name: str) -> Path:
    db_name = json_name.replace(".json", ".db")
    return get_db_dir(site_name) / db_name


def get_materials_json_dir(site_name: str, json_name: str) -> Path:
    json_stem = json_name.replace(".json", "")
    return get_materials_site_dir(site_name) / json_stem


def get_video_material_dir(site_name: str, json_name: str, title: str, publish_time: str) -> Path:
    return get_materials_json_dir(site_name, json_name) / video_folder_name(title, publish_time)
