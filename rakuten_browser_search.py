import json
import os
from urllib.parse import quote, urlencode, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

RAKUTEN_PAGES_URL = os.environ.get("RAKUTEN_PAGES_URL", "https://tansinfuninkazu.hatenablog.com/").strip()
RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RAKUTEN_APPLICATION_ID = "5db6e350-5a71-4843-8d29-cf894bef88df"
RAKUTEN_AFFILIATE_ID = "56e8483c.b8c4995b.56a8483d.205a3086"


def _safe_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme + "://" + parsed.netloc + parsed.path
    except Exception:
        return "unknown"


def _rakuten_error(result):
    if not isinstance(result, dict):
        return None
    if result.get("error"):
        return json.dumps(result, ensure_ascii=False)
    if result.get("errors"):
        return json.dumps({"errors": result["errors"]}, ensure_ascii=False)
    return None


def _normalize_item(item):
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def search_rakuten_browser(keyword, hits=10, access_key=None):
    access_key = str(access_key or os.environ.get("RAKUTEN_ACCESS_KEY", "")).strip()
    if not access_key:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")

    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    callback_name = "rakutenCallbackAutomation"
    diagnostics = {
        "page": _safe_url(RAKUTEN_PAGES_URL),
        "keyword": keyword,
        "transport": "jsonp",
        "access_key": "configured",
    }

    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "accessKey": access_key,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "keyword": keyword,
        "hits": str(hits),
        "page": "1",
        "format": "json",
        "formatVersion": "2",
        "callback": callback_name,
    }
    api_url = RAKUTEN_API_URL + "?" + urlencode(params, quote_via=quote)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        api_response = {}
        request_failure = {}

        def capture_response(response):
            if response.url.startswith(RAKUTEN_API_URL):
                body = ""
                try:
                    if response.status >= 400:
                        body = response.text()[:1000]
                except Exception:
                    body = ""
                api_response.update({
                    "status": response.status,
                    "status_text": response.status_text,
                    "content_type": response.headers.get("content-type", ""),
                    "url": _safe_url(response.url),
                    "body_head": body,
                })

        def capture_request_failed(request):
            if request.url.startswith(RAKUTEN_API_URL):
                request_failure.update({
                    "failure": request.failure,
                    "url": _safe_url(request.url),
                })

        page.on("response", capture_response)
        page.on("requestfailed", capture_request_failed)

        try:
            page.goto(RAKUTEN_PAGES_URL, wait_until="domcontentloaded", timeout=30000)
            result = page.evaluate(
                """
                ({src, callbackName}) => new Promise((resolve, reject) => {
                  let timer = null;
                  const cleanup = () => {
                    if (timer) clearTimeout(timer);
                    try { delete window[callbackName]; } catch (e) { window[callbackName] = undefined; }
                    const old = document.getElementById('rakuten-jsonp-automation');
                    if (old) old.remove();
                  };
                  window[callbackName] = (data) => {
                    cleanup();
                    resolve(data || null);
                  };
                  const script = document.createElement('script');
                  script.id = 'rakuten-jsonp-automation';
                  script.src = src;
                  script.referrerPolicy = 'unsafe-url';
                  script.onerror = () => {
                    cleanup();
                    reject(new Error('JSONP script load error'));
                  };
                  document.head.appendChild(script);
                  timer = setTimeout(() => {
                    cleanup();
                    reject(new Error('JSONP timeout'));
                  }, 15000);
                })
                """,
                {"src": api_url, "callbackName": callback_name},
            )

            if not result:
                raise RuntimeError(
                    "楽天APIの応答データがありません。診断: "
                    + json.dumps({**diagnostics, "api_response": api_response, "request_failure": request_failure}, ensure_ascii=False)
                )

            error = _rakuten_error(result)
            if error:
                raise RuntimeError(
                    "楽天APIエラー: " + error + " | 診断: "
                    + json.dumps({**diagnostics, "api_response": api_response, "request_failure": request_failure}, ensure_ascii=False)
                )

            raw_items = result.get("Items") or result.get("items") or []
            items = [_normalize_item(item) for item in raw_items]
            items = [item for item in items if item]
            if not items:
                raise RuntimeError(
                    "楽天商品が見つかりません。検索語: " + keyword + " | 診断: "
                    + json.dumps({**diagnostics, "api_response": api_response, "request_failure": request_failure}, ensure_ascii=False)
                )
            return items

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "楽天JSONP検索タイムアウト。診断: "
                + json.dumps({**diagnostics, "api_response": api_response, "request_failure": request_failure}, ensure_ascii=False)
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                "楽天JSONP検索に失敗しました: " + str(exc) + " | 診断: "
                + json.dumps({**diagnostics, "api_response": api_response, "request_failure": request_failure}, ensure_ascii=False)
            ) from exc
        finally:
            context.close()
            browser.close()
