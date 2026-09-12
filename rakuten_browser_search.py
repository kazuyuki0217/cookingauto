import json
import os
from urllib.parse import urlencode, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

RAKUTEN_PAGES_URL = os.environ.get(
    "RAKUTEN_PAGES_URL",
    "https://kazuyuki0217.github.io/cookingauto/rakuten-test/",
).strip()
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_APPLICATION_ID = "5db6e350-5a71-4843-8d29-cf894bef88df"
RAKUTEN_AFFILIATE_ID = "56e8483c.b8c4995b.56e8483d.205a3086"
RAKUTEN_API_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def _safe_api_url(value):
    try:
        parsed_url = urlparse(value)
        return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    except Exception:
        return "unknown"


def _safe_diagnostics(diagnostics):
    return json.dumps(diagnostics, ensure_ascii=False)


def search_rakuten_browser(keyword, hits=10):
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")

    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    parsed = urlparse(RAKUTEN_PAGES_URL)
    origin = parsed.scheme + "://" + parsed.netloc

    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "keyword": keyword,
        "hits": str(hits),
        "page": "1",
        "format": "json",
        "formatVersion": "2",
    }
    api_url = RAKUTEN_API_ENDPOINT + "?" + urlencode(params)

    diagnostics = {"navigation": [], "responses": [], "failures": []}
    result = None
    text = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = None
        try:
            # Validation marker: test the latest Origin + Referer strategy.
            context = browser.new_context(
                extra_http_headers={
                    "Origin": origin,
                    "Referer": RAKUTEN_PAGES_URL,
                }
            )
            page = context.new_page()
            page.on(
                "requestfailed",
                lambda request: diagnostics["failures"].append({
                    "url": _safe_api_url(request.url),
                    "failure": request.failure,
                })
                if "openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search" in request.url
                else None,
            )

            page.goto(RAKUTEN_PAGES_URL, wait_until="domcontentloaded", timeout=30000)
            response = page.goto(api_url, wait_until="domcontentloaded", timeout=30000)

            if response is not None:
                diagnostics["responses"].append({
                    "url": _safe_api_url(response.url),
                    "status": response.status,
                    "statusText": response.status_text,
                    "contentType": response.headers.get("content-type", ""),
                })
                text = response.text()
            else:
                text = page.locator("body").inner_text()

            diagnostics["navigation"].append({
                "origin": origin,
                "referer": RAKUTEN_PAGES_URL,
                "api": _safe_api_url(api_url),
            })

            if not text.strip():
                raise RuntimeError(
                    "楽天APIの応答本文が空です。診断: " + _safe_diagnostics(diagnostics)
                )

            try:
                result = json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "楽天API応答をJSONとして解析できません。本文先頭: "
                    + text[:500]
                    + " | 診断: "
                    + _safe_diagnostics(diagnostics)
                ) from exc

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "楽天ブラウザ検索タイムアウト。診断: "
                + _safe_diagnostics(diagnostics)
            ) from exc
        finally:
            if context is not None:
                context.close()
            browser.close()

    if not result:
        raise RuntimeError(
            "楽天ブラウザ検索エラー: 応答データがありません。診断: "
            + _safe_diagnostics(diagnostics)
        )

    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(
            "楽天APIエラー: "
            + json.dumps(result, ensure_ascii=False)
            + " | 診断: "
            + _safe_diagnostics(diagnostics)
        )

    items = result.get("items") or result.get("Items") or []
    if not items:
        raise RuntimeError(
            "楽天商品が見つかりません。検索語: "
            + keyword
            + " | 診断: "
            + _safe_diagnostics(diagnostics)
        )
    return items
