import json
import os
import requests

RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL") or os.environ.get("PINTEREST_GAS_URL", "")
RAKUTEN_AUTOMATION_SECRET = os.environ.get("PINTEREST_AUTOMATION_SECRET", "")


def _normalize_item(item):
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def _call_gas(keyword, hits):
    if not RAKUTEN_GAS_URL:
        raise RuntimeError("楽天GASブリッジURLが設定されていません。")
    params = {
        "service": "rakuten",
        "secret": RAKUTEN_AUTOMATION_SECRET,
        "keyword": keyword,
        "hits": str(hits),
    }
    try:
        response = requests.get(RAKUTEN_GAS_URL, params=params, timeout=45)
    except requests.RequestException as exc:
        raise RuntimeError(f"楽天GASブリッジ通信エラー: {exc}") from exc
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"楽天GASブリッジ HTTP {response.status_code}: {response.text[:1000]}")
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "楽天GASブリッジ応答がJSONではありません。"
            f" Content-Type={response.headers.get('content-type', '')}"
            f" body={response.text[:1000]}"
        ) from exc
    if data.get("error"):
        raise RuntimeError("楽天GASブリッジエラー: " + str(data["error"]))
    raw_items = data.get("items") or data.get("Items") or []
    items = [_normalize_item(item) for item in raw_items]
    items = [item for item in items if item]
    if not items:
        raise RuntimeError("楽天商品が見つかりません。検索語: " + keyword)
    return items


def search_rakuten_browser(keyword, hits=10, access_key=None):
    """既存パイプライン互換の楽天商品検索。

    GitHub Actionsから楽天APIへ直接アクセスせず、公開GASブリッジへ
    検索を委譲する。楽天のWebアプリケーション方式を維持するための
    安全な構成で、access_key引数は互換性のためだけに受け取る。
    """
    keyword = str(keyword or "").strip() or "フライパン"
    hits = max(1, min(int(hits), 30))
    return _call_gas(keyword, hits)
