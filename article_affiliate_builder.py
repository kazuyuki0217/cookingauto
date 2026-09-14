import os
import re
from html import escape
from pathlib import Path

from rakuten_browser_search import search_rakuten_browser

RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL", "").strip()
RAKUTEN_AUTOMATION_SECRET = (
    os.environ.get("RAKUTEN_AUTOMATION_SECRET", "").strip()
    or os.environ.get("PINTEREST_AUTOMATION_SECRET", "").strip()
)
RAKUTEN_PAGES_URL = os.environ.get(
    "RAKUTEN_PAGES_URL",
    "https://tansinfuninkazu.hatenablog.com/",
).strip()


def find_photo_url():
    url = os.environ.get("COOKING_IMAGE_URL", "").strip()
    if not url and Path("cooking_image_url.txt").exists():
        url = Path("cooking_image_url.txt").read_text(encoding="utf-8").strip()
    return url if url.startswith(("https://", "http://")) else ""


def _tokens(text):
    text = str(text or "").lower()
    return {x for x in re.split(r"[^0-9a-zぁ-んァ-ヶ一-龥]+", text) if len(x) >= 2}


def _product_score(item, dish_name):
    name = str(item.get("itemName", ""))
    relevance = len(_tokens(dish_name) & _tokens(name)) * 8
    tool_terms = {
        "フライパン": 16, "鍋": 14, "包丁": 12, "まな板": 10,
        "キッチン": 8, "調理": 8, "保存容器": 7, "ボウル": 6,
        "トング": 5, "菜箸": 5, "ヘラ": 5, "油": 4,
    }
    for term, points in tool_terms.items():
        if term in name:
            relevance += points
    rating = float(item.get("reviewAverage", 0) or 0)
    review_count = int(item.get("reviewCount", 0) or 0)
    price = float(item.get("itemPrice", 0) or 0)
    score = relevance + rating * 4 + min(review_count, 1000) / 100
    if 1000 <= price <= 15000:
        score += 4
    elif 15000 < price <= 30000:
        score += 1
    return score


def _normalize_item(item):
    """Rakuten formatVersion=2 may wrap each product in an Item object."""
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def search_rakuten_via_browser(keywords, hits=10):
    """Search Rakuten through the GAS-hosted browser page.

    Rakuten credentials are intentionally not fetched into GitHub Actions.
    The GAS HTML page obtains the credentials from Script Properties and
    executes the Rakuten JSONP request in the browser context.
    """
    if not RAKUTEN_GAS_URL:
        raise RuntimeError("RAKUTEN_GAS_URLが設定されていません。")
    if not RAKUTEN_AUTOMATION_SECRET:
        raise RuntimeError("楽天ブリッジ認証Secretが設定されていません。")

    all_items = []
    for keyword in [str(x).strip() for x in keywords if str(x).strip()][:5]:
        items = search_rakuten_browser(keyword, hits)
        all_items.extend(_normalize_item(item) for item in items)
    return all_items


def choose_products(dish_name):
    keywords = [
        f"{dish_name} フライパン",
        f"{dish_name} 調理器具",
        f"{dish_name} キッチン用品",
    ]
    products = []
    seen = set()
    for item in search_rakuten_via_browser(keywords, 10):
        item = _normalize_item(item)
        url = str(item.get("affiliateUrl") or item.get("itemUrl") or "").strip()
        name = str(item.get("itemName", "")).strip()
        if not url or not name or url in seen:
            continue
        seen.add(url)
        item["_score"] = _product_score(item, dish_name)
        products.append(item)

    products.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return products[:3]


def _product_link(item, label):
    url = str(item.get("affiliateUrl") or item.get("itemUrl") or "").strip()
    name = escape(str(item.get("itemName", "")).strip())
    if not url or not name:
        return ""
    return f'<p><a href="{escape(url, quote=True)}" rel="nofollow sponsored noopener" target="_blank">{escape(label)}</a><br>{name}</p>'


def _photo_html(dish_name):
    """Insert the already-uploaded Hatena Fotolife image into the final HTML."""
    photo_url = find_photo_url()
    if not photo_url:
        print("料理写真URLが見つからないため、画像HTMLは追加しません。")
        return ""
    alt = escape(str(dish_name or "料理写真").strip() or "料理写真", quote=True)
    return (
        '<p><img src="'
        + escape(photo_url, quote=True)
        + '" alt="'
        + alt
        + '" loading="lazy" style="max-width:100%;height:auto;"></p>'
    )


def build_article(title, body, dish_name):
    photo_html = _photo_html(dish_name)
    products = choose_products(dish_name)
    labels = [
        "▶ 仕事終わりの自炊に使いやすい道具を見てみる",
        "▶ この料理を作るなら、これが気になる",
        "▶ 毎日の自炊を少し楽にする道具を探す",
    ]
    links = []
    for item, label in zip(products, labels):
        link = _product_link(item, label)
        if link:
            links.append(link)
    affiliate_html = "\n".join(links)

    # 写真は記事冒頭へ。既存の本文・楽天アフィリエイト導線は変更しない。
    if photo_html:
        body = photo_html + "\n" + body.lstrip()

    if affiliate_html:
        body = body.rstrip() + "\n\n<h3>今回の料理で使いたい道具</h3>\n" + affiliate_html
    return body


def main():
    title = Path("article_title.txt").read_text(encoding="utf-8").strip()
    body = Path("article_body.txt").read_text(encoding="utf-8")
    dish_name = Path("dish_name.txt").read_text(encoding="utf-8").strip()
    article = build_article(title, body, dish_name)
    Path("article_final.html").write_text(article, encoding="utf-8")
    print("料理写真を記事へ組み込みました。")
    print("楽天アフィリエイト商品を記事へ組み込みました。")


if __name__ == "__main__":
    main()
