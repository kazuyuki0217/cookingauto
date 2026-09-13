import json
import os
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

RAKUTEN_PAGES_URL = os.environ.get(
    "RAKUTEN_PAGES_URL",
    "https://kazuyuki0217.github.io/cookingauto/rakuten-test/",
).strip()
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()


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
    errors = result.get("errors")
    if errors:
        return json.dumps({"errors": errors}, ensure_ascii=False)
    return None


def search_rakuten_browser(keyword, hits=10):
    """Search Rakuten from GitHub Pages using browser JSONP.

    JSONP is intentional here: the browser sends the GitHub Pages Referer to
    Rakuten without depending on a CORS-enabled fetch response.
    """
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")

    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    diagnostics = {
        "page": _safe_url(RAKUTEN_PAGES_URL),
        "keyword": keyword,
        "transport": "jsonp",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            automation_url = (
                RAKUTEN_PAGES_URL.rstrip("/")
                + "/?mode=automation&keyword="
                + quote(keyword, safe="")
            )
            page.goto(automation_url, wait_until="domcontentloaded", timeout=30000)

            page.evaluate(
                """
                ({key, hits}) => {
                    window.__RAKUTEN_AUTOMATION_KEY = key;
                    window.__RAKUTEN_AUTOMATION_HITS = hits;
                }
                """,
                {"key": RAKUTEN_ACCESS_KEY, "hits": hits},
            )
            page.evaluate("window.searchRakuten()")

            page.wait_for_function(
                "window.__RAKUTEN_DONE === true",
                timeout=30000,
            )
            result = page.evaluate("window.__RAKUTEN_RESULT")

            if not result:
                raise RuntimeError(
                    "楽天APIの応答データがありません。診断: "
                    + json.dumps(diagnostics, ensure_ascii=False)
                )

            error = _rakuten_error(result)
            if error:
                raise RuntimeError(
                    "楽天APIエラー: "
                    + error
                    + " | 診断: "
                    + json.dumps(diagnostics, ensure_ascii=False)
                )

            items = result.get("Items") or result.get("items") or []
            if not items:
                raise RuntimeError(
                    "楽天商品が見つかりません。検索語: "
                    + keyword
                    + " | 診断: "
                    + json.dumps(diagnostics, ensure_ascii=False)
                )
            return items

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "楽天JSONP検索タイムアウト。診断: "
                + json.dumps(diagnostics, ensure_ascii=False)
            ) from exc
        finally:
            context.close()
            browser.close()
