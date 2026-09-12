import os
import re
from html import escape
from pathlib import Path
from rakuten_browser_search import search_rakuten_browser

# 楽天Webアプリ型はサーバーからのUrlFetchでは403になるため、
# GitHub Pages上のブラウザを経由してJSONP検索する。
# RAKUTEN_ACCESS_KEYが無い場合は旧GAS方式へ戻さず、ここで明確に停止する。
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_PAGES_URL = os.environ.get(
    "RAKUTEN_PAGES_URL",
    "https://kazuyuki0217.github.io/cookingauto/rakuten-test/",
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
    tool_terms = {"フライパン":16,"鍋":14,"包丁":12,"まな板":10,"キッチン":8,"調理":8,"保存容器":7,"ボウル":6,"トング":5,"菜箸":5,"ヘラ":5,"油":4}
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


def choose_products(dish_name):
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError(
            "楽天アクセスキーがGitHub Actions Secret RAKUTEN_ACCESS_KEYに未登録です。"
            "旧GAS方式にはフォールバックしません。"
        )

    keywords = [
        f"{dish_name} フライパン",
        f"{dish_name} 調理器具",
        f"{dish_name} キッチン用品",
    ]
    candidates, seen = [], set()
    for keyword in keywords:
        for item in search_rakuten_browser(keyword, 10):
            url = item.get("affiliateUrl") or item.get("itemUrl") or ""
            if not item.get("itemName") or not url or url in seen:
                continue
            seen.add(url)
            candidates.append(item)
            if len(candidates) >= 30:
                break
        if len(candidates) >= 30:
            break

    candidates = [
        x for x in candidates
        if x.get("itemName") and (x.get("affiliateUrl") or x.get("itemUrl"))
    ]
    ranked = sorted(candidates, key=lambda x: _product_score(x, dish_name), reverse=True)
    selected, seen_names = [], set()
    for item in ranked:
        normalized = re.sub(r"\s+", "", str(item.get("itemName", ""))).lower()
        if normalized in seen_names:
            continue
        seen_names.add(normalized)
        selected.append(item)
        if len(selected) >= 3:
            break
    return selected


def product_link(item, index):
    labels = [
        "▶ 仕事終わりの自炊に使いやすい道具を見てみる",
        "▶ この料理を作るなら、これが気になる",
        "▶ 毎日の自炊を少し楽にする道具を探す",
    ]
    url = item.get("affiliateUrl") or item.get("itemUrl") or ""
    return f'<p><a href="{escape(url, quote=True)}" rel="nofollow sponsored">{labels[index]}</a></p>'


def build_article(title, body, dish_name):
    image_url = find_photo_url()
    products = choose_products(dish_name)
    parts = []
    if image_url:
        parts.append(
            f'<p><img src="{escape(image_url, quote=True)}" alt="{escape(dish_name, quote=True)}" loading="lazy"></p>'
        )
    parts.append(body)
    if products:
        parts.append("<h2>この料理で気になったキッチン用品</h2>")
        parts.append(
            "<p>今回の料理との相性、使う場面、レビューの反応などを見ながら、日々の自炊につなげやすいものを選びました。</p>"
        )
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
    print("楽天検索方式:", "GitHub Pagesブラウザ(JSONP)")
    print("楽天商品リンク: 関連性・レビュー・価格を考慮して自動選定済み")


if __name__ == "__main__":
    main()
