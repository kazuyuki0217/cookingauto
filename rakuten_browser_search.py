import json
import os
import re
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL") or os.environ.get("PINTEREST_GAS_URL", "")
RAKUTEN_AUTOMATION_SECRET = os.environ.get("PINTEREST_AUTOMATION_SECRET", "")

RAKUTEN_API_MARKER = "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/"


def _normalize_item(item):
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def _parse_jsonp(text):
    text = str(text or "").lstrip("\ufeff \r\n\t")
    if not text:
        raise ValueError("楽天APIレスポンス本文が空です。")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    first = text.find("(")
    last = text.rfind(")")
    if first <= 0 or last <= first:
        raise ValueError("楽天APIレスポンスがJSON/JSONP形式ではありません。")
    payload = text[first + 1:last].strip().rstrip(";")
    return json.loads(payload)


def _make_data_from_parsed(parsed):
    if not isinstance(parsed, dict):
        return None
    if parsed.get("error"):
        return {
            "success": False,
            "error": parsed.get("error_description") or parsed.get("error"),
        }
    raw_items = parsed.get("Items") or parsed.get("items") or []
    return {
        "success": True,
        "count": len(raw_items) if isinstance(raw_items, list) else 0,
        "items": raw_items,
        "orb_fallback": True,
    }


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
                "rakuten_body": "",
                "rakuten_parsed": None,
                "route_fetch_error": "",
                "console": [],
                "page_errors": [],
                "request_failed": [],
            }

            def capture_rakuten_response(response):
                if RAKUTEN_API_MARKER not in response.url:
                    return
                diagnostics["rakuten_status"] = response.status
                diagnostics["rakuten_url"] = response.url.split("accessKey=")[0] + "accessKey=[hidden]"
                try:
                    body = response.body().decode("utf-8", errors="replace")
                    diagnostics["rakuten_body"] = body[:3000]
                    try:
                        diagnostics["rakuten_parsed"] = _parse_jsonp(body)
                    except Exception as parse_error:
                        diagnostics["rakuten_parsed"] = {"parse_error": str(parse_error)}
                except Exception as body_error:
                    diagnostics["rakuten_body"] = "BODY_READ_ERROR: " + str(body_error)

            def on_rakuten_route(route):
                try:
                    upstream = route.fetch(timeout=60000)
                    status = upstream.status
                    body_bytes = upstream.body()
                    body = body_bytes.decode("utf-8", errors="replace")
                    diagnostics["rakuten_status"] = status
                    diagnostics["rakuten_url"] = route.request.url.split("accessKey=")[0] + "accessKey=[hidden]"
                    diagnostics["rakuten_body"] = body[:3000]
                    try:
                        diagnostics["rakuten_parsed"] = _parse_jsonp(body)
                    except Exception as parse_error:
                        diagnostics["rakuten_parsed"] = {"parse_error": str(parse_error)}
                    route.fulfill(
                        status=status,
                        body=body_bytes,
                        headers={"Content-Type": "application/javascript; charset=utf-8"},
                    )
                except Exception as route_error:
                    diagnostics["route_fetch_error"] = str(route_error)[:1000]
                    route.abort()

            def on_console(message):
                if len(diagnostics["console"]) < 10:
                    diagnostics["console"].append(message.text[:500])

            def on_page_error(error):
                if len(diagnostics["page_errors"]) < 10:
                    diagnostics["page_errors"].append(str(error)[:500])

            def on_request_failed(request):
                if RAKUTEN_API_MARKER in request.url:
                    failure = request.failure or "unknown failure"
                    diagnostics["request_failed"].append(str(failure)[:500])

            page.on("response", capture_rakuten_response)
            page.on("console", on_console)
            page.on("pageerror", on_page_error)
            page.on("requestfailed", on_request_failed)
            page.route("**/IchibaItem/Search/**", on_rakuten_route)

            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_function("window.__RAKUTEN_DONE === true", timeout=30000)
                data = page.evaluate("window.__RAKUTEN_RESULT")
            except Exception as exc:
                parsed = diagnostics.get("rakuten_parsed")
                data = _make_data_from_parsed(parsed)
                if data is None:
                    result = page.evaluate("window.__RAKUTEN_RESULT")
                    body_text = page.locator("body").inner_text(timeout=5000)[:1000]
                    detail = {
                        "status": diagnostics.get("rakuten_status"),
                        "result": result,
                        "body": body_text,
                        "rakuten_body": diagnostics.get("rakuten_body", ""),
                        "route_fetch_error": diagnostics.get("route_fetch_error", ""),
                        "console": diagnostics["console"],
                        "page_errors": diagnostics["page_errors"],
                        "request_failed": diagnostics["request_failed"],
                    }
                    raise RuntimeError(
                        "楽天ブラウザ検索が完了しませんでした。診断: " + str(detail)
                    ) from exc
        finally:
            browser.close()

    if not isinstance(data, dict):
        raise RuntimeError("楽天ブラウザブリッジの応答を取得できませんでした。")
    if not data.get("success"):
        raise RuntimeError("楽天ブラウザブリッジエラー: " + str(data.get("error", data)))

    raw_items = data.get("items") or data.get("Items") or []
    items = [_normalize_item(item) for item in raw_items]
    return [item for item in items if item]


def _fallback_keywords(keyword):
    """料理名そのものを楽天検索に投げず、商品カテゴリへ段階的に絞り込む。"""
    original = str(keyword or "").strip()
    candidates = []

    def add(value):
        value = re.sub(r"\s+", " ", str(value or "")).strip()
        if value and value not in candidates:
            candidates.append(value)

    add(original)

    simplified = re.sub(r"[（(].*?[）)]", " ", original)
    simplified = re.sub(r"\s+", " ", simplified).strip()
    add(simplified)

    category_words = [
        "フライパン", "鍋", "包丁", "まな板", "キッチン用品", "保存容器", "調味料",
    ]
    for category in category_words:
        if category in original or category in simplified:
            add(category)

    for category in category_words:
        if re.search(re.escape(category) + r"\s*$", original):
            add(category)
            break

    if any(word in original for word in ["フライパン", "炒め", "焼き", "ステーキ", "肉"]):
        add("フライパン")
    elif any(word in original for word in ["包丁", "切る", "千切り"]):
        add("包丁")
    else:
        add("キッチン用品")

    return candidates


def search_rakuten_browser(keyword, hits=10, access_key=None):
    """楽天商品検索。0件なら検索語を自動簡略化して再検索し、最終的にAPI診断を含めて失敗理由を返す。"""
    hits = max(1, min(int(hits), 30))
    keywords = _fallback_keywords(keyword)
    diagnostics = []

    for search_keyword in keywords:
        try:
            items = _search_once(search_keyword, hits)
            if items:
                return items
            diagnostics.append(search_keyword + ": HTTP/JSON取得は完了したが商品0件")
        except Exception as exc:
            diagnostics.append(search_keyword + ": " + str(exc)[:1500])

    raise RuntimeError(
        "楽天商品が見つかりません。試行検索語: " + " / ".join(keywords)
        + "\n楽天API診断: " + " || ".join(diagnostics)
    )
