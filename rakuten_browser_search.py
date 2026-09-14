import json
import os
from urllib.parse import quote, urlencode

import requests

RAKUTEN_API_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RAKUTEN_APPLICATION_ID = "5db6e350-5a71-4843-8d29-cf894bef88df"
RAKUTEN_AFFILIATE_ID = "56e8483c.b8c4995b.56e8483d.205a3086"


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
    """楽天API 2026-07-01をバックエンド方式で直接呼び出す。

    関数名は既存パイプライン互換のため維持する。
    Web applicationのReferer制限を使うブラウザ経由ではなく、
    API/Backend Service向けのサーバー側HTTPリクエストを使用する。
    """
    access_key = str(access_key or os.environ.get("RAKUTEN_ACCESS_KEY", "")).strip()
    if not access_key:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")

    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))

    params = {
        "applicationId": RAKUTEN_APPLICATION_ID,
        "accessKey": access_key,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "keyword": keyword,
        "hits": str(hits),
        "page": "1",
        "format": "json",
        "formatVersion": "2",
    }

    try:
        response = requests.get(
            RAKUTEN_API_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"楽天API通信エラー: {exc}") from exc

    body = response.text
    if response.status_code < 200 or response.status_code >= 300:
        # Access Keyそのものはログに出さない。
        safe_url = response.url.replace(access_key, "***")
        raise RuntimeError(
            f"楽天API HTTP {response.status_code}: {body[:2000]} | URL={safe_url}"
        )

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "楽天API応答がJSONではありません。"
            f" Content-Type={response.headers.get('content-type', '')}"
            f" body={body[:2000]}"
        ) from exc

    error = _rakuten_error(result)
    if error:
        raise RuntimeError("楽天APIエラー: " + error)

    raw_items = result.get("Items") or result.get("items") or []
    items = [_normalize_item(item) for item in raw_items]
    items = [item for item in items if item]
    if not items:
        raise RuntimeError("楽天商品が見つかりません。検索語: " + keyword)
    return items
