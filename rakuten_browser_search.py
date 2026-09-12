import json
import os
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

RAKUTEN_PAGES_URL = os.environ.get(
    "RAKUTEN_PAGES_URL",
    "https://kazuyuki0217.github.io/cookingauto/rakuten-test/",
).strip()
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()


def search_rakuten_browser(keyword, hits=10):
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")

    keyword = str(keyword or "").strip() or "フライパン"
    url = RAKUTEN_PAGES_URL + "?mode=automation&keyword=" + quote(keyword)
    parsed = urlparse(RAKUTEN_PAGES_URL)
    origin = parsed.scheme + "://" + parsed.netloc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Rakuten's Web-application type checks the browser request context.
        # Explicitly send the registered GitHub Pages origin and referer so the
        # JSONP request is evaluated as coming from the allowed website.
        context = browser.new_context(
            extra_http_headers={
                "Origin": origin,
                "Referer": RAKUTEN_PAGES_URL,
            }
        )
        page = context.new_page()
        page.add_init_script(
            "window.__RAKUTEN_AUTOMATION_KEY = "
            + json.dumps(RAKUTEN_ACCESS_KEY)
            + "; window.__RAKUTEN_AUTOMATION_HITS = "
            + str(max(1, min(int(hits), 30)))
            + ";"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        try:
            page.wait_for_function(
                "() => window.__RAKUTEN_DONE === true",
                timeout=30000,
            )
        except PlaywrightTimeoutError:
            text = page.locator("#result").inner_text()
            context.close()
            browser.close()
            raise RuntimeError("楽天ブラウザ検索タイムアウト: " + text[:2000])

        result = page.evaluate("() => window.__RAKUTEN_RESULT || null")
        text = page.locator("#result").inner_text()
        context.close()
        browser.close()

    if not result:
        raise RuntimeError("楽天ブラウザ検索エラー: " + text[:3000])
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError("楽天APIエラー: " + json.dumps(result, ensure_ascii=False))

    items = result.get("items") or result.get("Items") or []
    if not items:
        raise RuntimeError("楽天商品が見つかりません。検索語: " + keyword)
    return items
