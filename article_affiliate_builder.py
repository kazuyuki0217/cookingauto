import os
from html import escape
from pathlib import Path
import requests

RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID", "5db6e350-5a71-4843-8d29-cf894bef88df")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "56e8483c.b8c4995b.56e8483d.205a3086")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def find_photo_url():
    url = os.environ.get("COOKING_IMAGE_URL", "").strip()
    if not url and Path("cooking_image_url.txt").exists():
        url = Path("cooking_image_url.txt").read_text(encoding="utf-8").strip()
    return url if url.startswith(("https://", "http://")) else ""


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
    return r.json().get("items", [])


def choose_products(dish_name):
    keywords = [f"{dish_name} フライパン", f"{dish_name} 調理器具", f"{dish_name} キッチン用品"]
    candidates, seen = [], set()
    for keyword in keywords:
        for item in search_rakuten(keyword, 10):
            url = item.get("affiliateUrl", "")
            if not item.get("itemName") or not url or url in seen:
                continue
            seen.add(url)
            candidates.append(item)
            if len(candidates) >= 9:
                break
        if len(candidates) >= 9:
            break
    candidates.sort(key=lambda x: (float(x.get("reviewAverage", 0) or 0), int(x.get("reviewCount", 0) or 0)), reverse=True)
    return candidates[:3]


def product_link(item, index):
    labels = [
        "▶ 仕事終わりの自炊に使いやすい道具を見てみる",
        "▶ この料理を作るなら、これが気になる",
        "▶ 毎日の自炊を少し楽にする道具を探す",
    ]
    return f'<p><a href="{escape(item.get("affiliateUrl", ""), quote=True)}" rel="nofollow sponsored">{labels[index]}</a></p>'


def build_article(title, body, dish_name):
    image_url = find_photo_url()
    products = choose_products(dish_name)
    parts = []
    if image_url:
        parts.append(f'<p><img src="{escape(image_url, quote=True)}" alt="{escape(dish_name, quote=True)}" loading="lazy"></p>')
    parts.append(body)
    if products:
        parts.append("<h2>この料理で気になったキッチン用品</h2>")
        parts.append("<p>今回の料理を作っていて、あると調理や片付けが少し楽になりそうなものを選びました。</p>")
        for i, item in enumerate(products):
            parts.append(f"<p><strong>{escape(item.get('itemName', 'キッチン用品'))}</strong></p>")
            parts.append(product_link(item, i))
    return "\n".join(parts)


def main():
    title = Path("article_title.txt").read_text(encoding="utf-8").strip()
    body = Path("article_body.txt").read_text(encoding="utf-8").strip()
    dish_name = os.environ.get("DISH_NAME", "").strip()
    if not dish_name and Path("dish_name.txt").exists():
        dish_name = Path("dish_name.txt").read_text(encoding="utf-8").strip()
    dish_name = dish_name or "料理"
    article = build_article(title, body, dish_name)
    Path("article_final.html").write_text(article, encoding="utf-8")
    print("完成記事生成完了")
    print("料理:", dish_name)
    print("写真URL:", "設定済み" if find_photo_url() else "未設定")
    print("楽天商品リンク: 自動選定済み")


if __name__ == "__main__":
    main()
