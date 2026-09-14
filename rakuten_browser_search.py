import json
import os
import re
from urllib.parse import parse_qsl, urlencode, urlparse

import requests
from playwright.sync_api import sync_playwright

RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL") or os.environ.get("PINTEREST_GAS_URL", "")
RAKUTEN_AUTOMATION_SECRET = os.environ.get("PINTER_AUTOMATION_SECRET", "") or os.environ.get("PINTEREST_AUTOMATION_SECRET", "")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_EXPLORER_APP_ID = "ec65ace1-9e87-4d23-83e4-b54103335b56"
RAKUTEN_API_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RAKUTEN_OFFICIAL_PROXY = "https://webservice.rakuten.co.jp/explorer/proxy"
RAKUTEN_API_MARKER = "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/"
RAKUTEN_ALLOWED_ORIGIN = "https://tansinfuninkazu.hatenablog.com"


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
    return json.loads(text[first + 1:last].strip().rstrip(";"))


def _response_summary(parsed, body):
    if not isinstance(parsed, dict):
        return {"parsed_type": type(parsed).__name__}
    raw_items = parsed.get("Items")
    if raw_items is None:
        raw_items = parsed.get("items")
    return {"keys": list(parsed.keys())[:30], "errors": parsed.get("errors"), "count_field": parsed.get("count"), "page_count": parsed.get("pageCount"), "items_type": type(raw_items).__name__ if raw_items is not None else None, "items_length": len(raw_items) if isinstance(raw_items, list) else None, "body_head": str(body or "")[:1200]}


def _make_data_from_parsed(parsed, diagnostics=None):
    if not isinstance(parsed, dict):
        return None
    if parsed.get("error") or parsed.get("errors"):
        return {"success": False, "error": parsed.get("error_description") or parsed.get("error") or parsed.get("errors")}
    raw_items = parsed.get("Items")
    if raw_items is None:
        raw_items = parsed.get("items")
    if raw_items is None:
        raw_items = []
    result = {"success": True, "count": len(raw_items) if isinstance(raw_items, list) else 0, "items": raw_items}
    if diagnostics is not None:
        result["rakuten_diagnostics"] = diagnostics
    return result


def _search_via_official_proxy(keyword, hits):
    """Use Rakuten's own API-test-form proxy path.

    The direct openapi endpoint rejects the GitHub runner/browser request context,
    while Rakuten's official API Test Form successfully forwards the same API URL
    through /explorer/proxy. The proxy itself is not the Rakuten API; the `url`
    parameter contains the user's normal 2026-07-01 IchibaItem/Search request.
    """
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("RAKUTEN_ACCESS_KEYが設定されていません。")

    target_params = {
        "format": "json",
        "keyword": str(keyword).strip(),
        "genreId": "0",
        "applicationId": "5db6e350-5a71-4843-8dcf-894bef88df",
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": "56e8483c.b8c4995b.56e8483d.205a3086",
    }
    target_url = RAKUTEN_API_ENDPOINT + "?" + urlencode(target_params)
    proxy_params = {
        "applicationId": RAKUTEN_EXPLORER_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "url": target_url,
    }
    response = requests.get(
        RAKUTEN_OFFICIAL_PROXY,
        params=proxy_params,
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"楽天公式プロキシHTTP {response.status_code}")

    outer = response.json()
    inner_text = outer.get("content", "") if isinstance(outer, dict) else ""
    parsed = json.loads(inner_text) if inner_text else {}
    diagnostics = {
        "transport": "rakuten_official_explorer_proxy",
        "http_status": response.status_code,
        "count": parsed.get("count") if isinstance(parsed, dict) else None,
        "keyword": str(keyword),
    }
    if isinstance(parsed, dict) and (parsed.get("error") or parsed.get("errors")):
        raise RuntimeError("楽天APIエラー: " + json.dumps(parsed.get("errors") or parsed.get("error"), ensure_ascii=False)[:2000])

    data = _make_data_from_parsed(parsed, diagnostics)
    raw_items = data.get("items") if isinstance(data, dict) else []
    items = [_normalize_item(item) for item in (raw_items or [])]
    items = [item for item in items if item]
    if not items:
        raise RuntimeError("楽天公式プロキシはHTTP 200でしたが商品0件")
    return items[:hits], diagnostics


def _search_once_via_gas_browser(keyword, hits):
    if not RAKUTEN_GAS_URL:
        raise RuntimeError("楽天GASブリッジURLが設定されていません。")
    if not RAKUTEN_AUTOMATION_SECRET:
        raise RuntimeError("PINTEREST_AUTOMATION_SECRETが設定されていません。")
    query = urlencode({"service": "rakuten_browser", "secret": RAKUTEN_AUTOMATION_SECRET, "keyword": keyword, "hits": str(hits)})
    url = RAKUTEN_GAS_URL.rstrip("?") + ("&" if "?" in RAKUTEN_GAS_URL else "?") + query
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(extra_http_headers={"Origin": RAKUTEN_ALLOWED_ORIGIN, "Referer": RAKUTEN_ALLOWED_ORIGIN + "/"})
        api = p.request.new_context(extra_http_headers={"Origin": RAKUTEN_ALLOWED_ORIGIN, "Referer": RAKUTEN_ALLOWED_ORIGIN + "/"})
        try:
            page = context.new_page()
            diagnostics = {"rakuten_status": None, "rakuten_url": "", "rakuten_body": "", "rakuten_parsed": None, "rakuten_summary": None, "route_fetch_error": "", "console": [], "page_errors": [], "request_failed": []}
            def record(body, status, request_url):
                diagnostics["rakuten_status"] = status
                diagnostics["rakuten_url"] = request_url.split("accessKey=")[0] + "accessKey=[hidden]"
                diagnostics["rakuten_body"] = body[:3000]
                try:
                    parsed = _parse_jsonp(body)
                    diagnostics["rakuten_parsed"] = parsed
                    diagnostics["rakuten_summary"] = _response_summary(parsed, body)
                except Exception as e:
                    diagnostics["rakuten_parsed"] = {"parse_error": str(e)}
            def capture(response):
                if RAKUTEN_API_MARKER in response.url:
                    try: record(response.body().decode("utf-8", errors="replace"), response.status, response.url)
                    except Exception as e: diagnostics["rakuten_body"] = "BODY_READ_ERROR: " + str(e)
            def route_handler(route):
                try:
                    request_url = route.request.url
                    upstream = api.get(request_url, timeout=60000, headers={"Origin": RAKUTEN_ALLOWED_ORIGIN, "Referer": RAKUTEN_ALLOWED_ORIGIN + "/"})
                    body = upstream.body()
                    body_text = body.decode("utf-8", errors="replace")
                    record(body_text, upstream.status, request_url)
                    callback = dict(parse_qsl(urlparse(request_url).query)).get("callback", "").strip()
                    if callback:
                        try:
                            parsed = json.loads(body_text.lstrip("\ufeff \r\n\t"))
                            body = (callback + "(" + json.dumps(parsed, ensure_ascii=False, separators=(",", ":")) + ");").encode("utf-8")
                        except json.JSONDecodeError:
                            pass
                    route.fulfill(status=upstream.status, body=body, headers={"Content-Type": "application/javascript; charset=utf-8"})
                except Exception as e:
                    diagnostics["route_fetch_error"] = str(e)[:2000]
                    route.abort()
            page.on("response", capture)
            page.on("requestfailed", lambda r: diagnostics["request_failed"].append(str(r.failure or "unknown failure")[:500]) if RAKUTEN_API_MARKER in r.url else None)
            page.route("**/IchibaItem/Search/**", route_handler)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_function("window.__RAKUTEN_DONE === true", timeout=30000)
                data = page.evaluate("window.__RAKUTEN_RESULT")
            except Exception as exc:
                data = _make_data_from_parsed(diagnostics.get("rakuten_parsed"), diagnostics)
                if data is None:
                    raise RuntimeError("楽天ブラウザ検索が完了しませんでした。診断: " + json.dumps(diagnostics, ensure_ascii=False)[:8000]) from exc
        finally:
            api.dispose()
            context.close()
            browser.close()
    if not isinstance(data, dict):
        raise RuntimeError("楽天ブラウザブリッジの応答を取得できませんでした。")
    if not data.get("success"):
        raise RuntimeError("楽天ブラウザブリッジエラー: " + str(data.get("error", data)))
    raw_items = data.get("items") or data.get("Items") or []
    items = [_normalize_item(item) for item in raw_items]
    return [item for item in items if item], data.get("rakuten_diagnostics")


def _fallback_keywords(keyword):
    original = str(keyword or "").strip()
    candidates = []
    def add(value):
        value = re.sub(r"\s+", " ", str(value or "")).strip()
        if value and value not in candidates: candidates.append(value)
    add(original)
    simplified = re.sub(r"[（(].*?[）)]", " ", original)
    add(simplified)
    for category in ["フライパン", "鍋", "包丁", "まな板", "キッチン用品", "保存容器", "調味料"]:
        if category in original or category in simplified: add(category)
    if any(w in original for w in ["フライパン", "炒め", "焼き", "ステーキ", "肉"]): add("フライパン")
    elif any(w in original for w in ["包丁", "切る", "千切り"]): add("包丁")
    else: add("キッチン用品")
    return candidates


def search_rakuten_browser(keyword, hits=10, access_key=None):
    hits = max(1, min(int(hits), 30))
    keywords = _fallback_keywords(keyword)
    diagnostics = []
    for search_keyword in keywords:
        try:
            if RAKUTEN_ACCESS_KEY or access_key:
                items, detail = _search_via_official_proxy(search_keyword, hits)
            else:
                items, detail = _search_once_via_gas_browser(search_keyword, hits)
            if items:
                return items
            diagnostics.append(search_keyword + ": 商品0件 / " + json.dumps(detail or {}, ensure_ascii=False)[:5000])
        except Exception as exc:
            diagnostics.append(search_keyword + ": " + str(exc)[:5000])
    raise RuntimeError("楽天商品が見つかりません。試行検索語: " + " / ".join(keywords) + "\n楽天API診断: " + " || ".join(diagnostics))
