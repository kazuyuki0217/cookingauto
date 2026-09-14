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
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_function("window.__RAKUTEN_DONE === true", timeout=30000)
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
    これにより楽天のWebアプリケーション方式を維持したまま、
    UrlFetchApp由来のHTTP Referer制限を避ける。
    access_key引数は既存呼び出しとの互換性のためだけに受け取る。
    """
    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    return _search_once(keyword, hits)
