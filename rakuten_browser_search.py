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
        diagnostics = {"requests": [], "responses": [], "failures": []}

        def safe_api_url(value):
            try:
                parsed_url = urlparse(value)
                return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            except Exception:
                return "unknown"

        def on_request(request):
            if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search" in request.url:
                diagnostics["requests"].append({
                    "method": request.method,
                    "url": safe_api_url(request.url),
                    "origin": request.headers.get("origin", ""),
                    "referer": request.headers.get("referer", ""),
                })

        def on_response(response):
            if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search" in response.url:
                diagnostics["responses"].append({
                    "url": safe_api_url(response.url),
                    "status": response.status,
                    "statusText": response.status_text,
                })

        def on_request_failed(request):
            if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search" in request.url:
                diagnostics["failures"].append({
                    "url": safe_api_url(request.url),
                    "failure": request.failure,
                })

        page = context = None
        try:
            context = browser.new_context(
                extra_http_headers={
                    "Origin": origin,
                    "Referer": RAKUTEN_PAGES_URL,
                }
            )
            page = context.new_page()
            page.on("request", on_request)
            page.on("response", on_response)
            page.on("requestfailed", on_request_failed)
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
                raise RuntimeError(
                    "楽天ブラウザ検索タイムアウト: "
                    + text[:1500]
                    + " | 診断: "
                    + json.dumps(diagnostics, ensure_ascii=False)
                )

            result = page.evaluate("() => window.__RAKUTEN_RESULT || null")
            text = page.locator("#result").inner_text()
        finally:
            if context is not None:
                context.close()
            browser.close()

    if not result:
        raise RuntimeError(
            "楽天ブラウザ検索エラー: "
            + text[:2000]
            + " | 診断: "
            + json.dumps(diagnostics, ensure_ascii=False)
        )
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(
            "楽天APIエラー: "
            + json.dumps(result, ensure_ascii=False)
            + " | 診断: "
            + json.dumps(diagnostics, ensure_ascii=False)
        )

    items = result.get("items") or result.get("Items") or []
    if not items:
        raise RuntimeError(
            "楽天商品が見つかりません。検索語: "
            + keyword
            + " | 診断: "
            + json.dumps(diagnostics, ensure_ascii=False)
        )
    return items
