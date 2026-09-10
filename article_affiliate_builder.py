import os
import re
from html import escape
from pathlib import Path
import requests

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID", "5db6e350-5a71-4843-8d29-cf894bef88df")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "56e8483c.b8c4995b.56e8483d.205a3086")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def find_photo_url():
    """Use an explicitly supplied public image URL. Never invent one."""
    url = os.environ.get("COOKING_IMAGE_URL", "").strip()
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return ""


def search_rakuten(keyword, hits=10):
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("RAKUTEN_ACCESS_KEY is not configured.")
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey": RAKUTEN_ACCESS_KEY,
        "affiliateId": RAKUTEN_AFFILIATE_ID,
        "keyword": keyword,
        "hits": hits,
        "page": 1,
        "format": "json",
        "formatVersion": 2,
    }
    r = requests.get(RAKUTEN_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("items", [])


def choose_products(dish_name):
    """Select several cooking-relevant products without claiming the user owns them."""
    keywords = [
        f"{dish_name} フライパン",
        f"{dish_name} 調理器具",
        f"{dish_name} キッチン用品",
    ]
    candidates = []
    seen = set()
    for keyword in keywords:
        try:
            items = search_rakuten(keyword, 10)
        except Exception:
            continue
        for item in items:
            name = item.get("itemName", "")
            url = item.get("affiliateUrl", "")
            if not name or not url or url in seen:
                continue
            seen.add(url)
            candidates.append(item)
            if len(candidates) >= 6:
                break
        if len(candidates) >= 6:
            break

    # Prefer products with reviews and ratings, while keeping cooking relevance.
    candidates.sort(key=lambda x: (
        float(x.get("reviewAverage", 0) or 0),
        int(x.get("reviewCount", 0) or 0),
    ), reverse=True)
    return candidates[:3]


def product_link(item, index):
    names = [
        "▶ 「これなら毎日使えそう」な調理道具を見てみる",
        "▶ この料理を作るなら、これが気になる",
        "▶ 仕事終わりの自炊に使いやすい道具を探す",
    ]
    return f'<p><a href="{escape(item.get("affiliateUrl", ""), quote=True)}" rel="nofollow sponsored">{names[index]}</a></p>'


def build_article(title, body, dish_name):
    image_url = find_photo_url()
    products = choose_products(dish_name)

    parts = [f"<h1>{escape(title)}</h1>"]
    if image_url:
        parts.append(
            f'<p><img src="{escape(image_url, quote=True)}" alt="{escape(dish_name, quote=True)}" loading="lazy"></p>'
        )
    parts.append(body)

    if products:
        parts.append("<h2>この料理で気になったキッチン用品</h2>")
        parts.append("<p>料理をしていると、使いやすい道具があるだけで後片付けまで少し楽になります。気になったものを3つ選びました。</p>")
        for i, item in enumerate(products):
            parts.append(f"<p><strong>{escape(item.get('itemName', 'キッチン用品'))}</strong></p>")
            parts.append(product_link(item, i))

    return "\n".join(parts)


def main():
    title = Path("article_title.txt").read_text(encoding="utf-8").strip()
    body = Path("article_body.txt").read_text(encoding="utf-8").strip()
    dish_name = os.environ.get("DISH_NAME", "料理")
    article = build_article(title, body, dish_name)
    Path("article_final.html").write_text(article, encoding="utf-8")
    print("完成記事生成完了")
    print("写真:", "自動挿入済み" if find_photo_url() else "公開画像URL未設定")
    print("楽天商品リンク: 自動選定")


if __name__ == "__main__":
    main()
