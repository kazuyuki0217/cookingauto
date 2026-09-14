import os
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL") or os.environ.get("PINTEREST_GAS_URL", "")
RAKUTEN_AUTOMATION_SECRET = os.environ.get("PINTEREST_AUTOMATION_SECRET", "")


def _normalize_item(item):
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def _search_once(keyword, hits):
    if not RAKUTEN_GAS_URL:
        raise RuntimeError("楽天GASブリッジURLが設定されていません。")
    if not RAKUTEN_AUTOMATION_SECRET:
        raise RuntimeError("PINTEREST_AUTOMATION_SECRETが設定されていません。")

    query = urlencode({
        "service": "rakuten_browser",
        "secret": RAKUTEN_AUTOMATION_SECRET,
        "keyword": keyword,
        "hits": str(hits),
    })
    url = RAKUTEN_GAS_URL.rstrip("?") + ("&" if "?" in RAKUTEN_GAS_URL else "?") + query

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            diagnostics = {
                "rakuten_status": None,
                "rakuten_url": "",
                "console": [],
                "page_errors": [],
                "request_failed": [],
            }

            def on_response(response):
                if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/" in response.url:
                    diagnostics["rakuten_status"] = response.status
                    diagnostics["rakuten_url"] = response.url.split("accessKey=")[0] + "accessKey=[hidden]"

            def on_console(message):
                if len(diagnostics["console"]) < 10:
                    diagnostics["console"].append(message.text[:500])

            def on_page_error(error):
                if len(diagnostics["page_errors"]) < 10:
                    diagnostics["page_errors"].append(str(error)[:500])

            def on_request_failed(request):
                if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/" in request.url:
                    diagnostics["request_failed"].append(
                        (request.failure or "unknown failure")[:500]
                    )

            page.on("response", on_response)
            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.on("requestfailed", on_request_failed)

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_function("window.__RAKUTEN_DONE === true", timeout=30000)
            except Exception as exc:
                result = page.evaluate("window.__RAKUTEN_RESULT")
                body_text = page.locator("body").inner_text(timeout=5000)[:1000]
                status = diagnostics.get("rakuten_status")
                detail = {
                    "status": status,
                    "result": result,
                    "body": body_text,
                    "console": diagnostics["console"],
                    "page_errors": diagnostics["page_errors"],
                    "request_failed": diagnostics["request_failed"],
                }
                raise RuntimeError(
                    "楽天ブラウザ検索が完了しませんでした。診断: " + str(detail)
                ) from exc

            data = page.evaluate("window.__RAKUTEN_RESULT")
        finally:
            browser.close()

    if not isinstance(data, dict):
        raise RuntimeError("楽天ブラウザブリッジの応答を取得できませんでした。")
    if not data.get("success"):
        raise RuntimeError("楽天ブラウザブリッジエラー: " + str(data.get("error", data)))

    raw_items = data.get("items") or data.get("Items") or []
    items = [_normalize_item(item) for item in raw_items]
    items = [item for item in items if item]
    if not items:
        raise RuntimeError("楽天商品が見つかりません。検索語: " + keyword)
    return items


def search_rakuten_browser(keyword, hits=10, access_key=None):
    """既存パイプライン互換の楽天商品検索。

    GitHub Actionsから楽天APIへ直接アクセスせず、GAS Webアプリの
    ブラウザページをChromiumで開き、そのページから楽天JSONPを実行する。
    access_key引数は既存呼び出しとの互換性のためだけに受け取る。
    """
    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    return _search_once(keyword, hits)
