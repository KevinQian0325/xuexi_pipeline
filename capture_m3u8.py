from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

from config import HEADLESS, WAIT_MS, PAGE_TIMEOUT_MS

def is_real_m3u8_url(url: str) -> bool:
    parsed = urlparse(url)

    # 只保留真正的视频域名
    if parsed.netloc != "boot-video.xuexi.cn":
        return False

    # 只认路径本身以 .m3u8 结尾
    if not parsed.path.endswith(".m3u8"):
        return False

    return True

def capture_m3u8_from_detail_page(detail_url: str, headless: bool = HEADLESS, wait_ms: int = WAIT_MS) -> list[str]:
    """
    打开详情页，监听页面请求，抓取所有 m3u8 地址
    """
    m3u8_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        def handle_request(request):
            url = request.url
            if is_real_m3u8_url(url):
                print("request 捕获到 m3u8：", url)
                m3u8_urls.append(url)

        def handle_response(response):
            url = response.url
            if is_real_m3u8_url(url):
                print("response 捕获到 m3u8：", url)
                m3u8_urls.append(url)

        page.on("request", handle_request)
        page.on("response", handle_response)

        print("正在打开详情页：")
        print(detail_url)

        try:
            page.goto(detail_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        except Exception as e:
            print("page.goto 发生异常：", e)

        # 先等页面自己加载
        page.wait_for_timeout(wait_ms)

        # 如果还没抓到，尝试点播放按钮
        if not m3u8_urls:
            selectors = [
                "video",
                ".prism-big-play-btn",
                ".prism-play-btn",
                ".play-btn",
                ".vjs-big-play-button",
            ]

            for selector in selectors:
                try:
                    page.locator(selector).first.click(timeout=2000)
                    print(f"已尝试点击：{selector}")
                    page.wait_for_timeout(5000)

                    if m3u8_urls:
                        break
                except Exception:
                    continue

        browser.close()

    # 去重保序
    return list(dict.fromkeys(m3u8_urls))


def get_first_m3u8(detail_url: str, headless: bool = HEADLESS, wait_ms: int = WAIT_MS) -> str | None:
    """
    只返回第一个 m3u8
    """
    urls = capture_m3u8_from_detail_page(detail_url, headless=headless, wait_ms=wait_ms)
    return urls[0] if urls else None


def main():
    detail_url = "https://www.xuexi.cn/lgpage/detail/index.html?id=11168420022572797752&item_id=11168420022572797752"

    m3u8_list = capture_m3u8_from_detail_page(detail_url)

    print("\n最终结果：")
    if m3u8_list:
        for i, url in enumerate(m3u8_list, 1):
            print(f"{i}. {url}")
    else:
        print("没有抓到 m3u8")


if __name__ == "__main__":
    main()