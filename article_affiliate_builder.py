import json
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
    if isinstance(item, dict) and isinstance(item.get("Item"), dict):
        return item["Item"]
    return item if isinstance(item, dict) else {}


def search_rakuten_via_browser(keywords, hits=10):
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
    cached = Path("rakuten_candidates.json")
    if cached.exists():
        try:
            data = json.loads(cached.read_text(encoding="utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                return [dict(item) for item in candidates[:3]]
        except Exception:
            pass

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


def _product_category(item):
    name = str(item.get("itemName", ""))
    categories = [
        ("フライパン", ["フライパン", "炒め鍋", "スキレット"]),
        ("包丁", ["包丁", "ペティナイフ", "三徳"]),
        ("まな板", ["まな板", "カッティングボード"]),
        ("鍋", ["鍋", "片手鍋", "両手鍋"]),
        ("保存容器", ["保存容器", "タッパー", "密閉容器"]),
        ("調理器具", ["トング", "菜箸", "ヘラ", "キッチンツール", "調理器具"]),
        ("キッチン用品", ["キッチン"]),
    ]
    for category, terms in categories:
        if any(term in name for term in terms):
            return category
    return "キッチン用品"


def _natural_anchor(item):
    """広告らしいCTAではなく、本文中の自然な名詞句として使う。"""
    category = _product_category(item)
    name = str(item.get("itemName", "")).strip()
    short = re.sub(r"[【】\[\]]", "", name)
    short = re.sub(r"\s+", " ", short).strip()
    if len(short) > 34:
        short = short[:34].rstrip(" 、・") + "…"

    # 読者に「押してください」と命令せず、選択肢として見せる。
    if category == "フライパン":
        return "フライパン"
    if category == "包丁":
        return "包丁"
    if category == "まな板":
        return "まな板"
    if category == "鍋":
        return "鍋"
    if category == "保存容器":
        return "保存容器"
    if category == "調理器具":
        return "調理器具"
    return short or category


def _product_link(item):
    url = str(item.get("affiliateUrl") or item.get("itemUrl") or "").strip()
    if not url:
        return ""
    anchor = escape(_natural_anchor(item))
    return (
        f'<a href="{escape(url, quote=True)}" rel="nofollow sponsored noopener" '
        f'target="_blank">{anchor}</a>'
    )


def _social_proof_phrase(item):
    """楽天の商品データに実際に存在する数値だけを使う。捏造しない。"""
    rating = float(item.get("reviewAverage", 0) or 0)
    reviews = int(item.get("reviewCount", 0) or 0)
    if rating >= 4.3 and reviews >= 100:
        return f"レビューも{reviews:,}件あり、評価は{rating:.1f}でした。"
    if rating >= 4.3 and reviews >= 30:
        return f"レビューでも評価が高めだったので、候補に入れました。"
    return ""


def _context_terms(item):
    category = _product_category(item)
    mapping = {
        "フライパン": ["焼", "炒", "火", "脂", "焦", "肉"],
        "包丁": ["切", "刻", "千切", "材料"],
        "まな板": ["切", "刻", "材料"],
        "鍋": ["煮", "茹", "ゆで", "汁"],
        "保存容器": ["保存", "作り置き", "冷蔵", "残"],
        "調理器具": ["混ぜ", "炒", "焼", "盛", "調理"],
        "キッチン用品": ["料理", "自炊", "洗い物", "キッチン"],
    }
    return mapping.get(category, mapping["キッチン用品"])


def _paragraphs(body):
    return re.split(r"(</p\s*>|</li\s*>|<br\s*/?>)", body, flags=re.I)


def _insert_naturally(body, item, used_positions):
    """商品を記事末尾へまとめず、意味の近い段落の直後へ1回だけ置く。"""
    category = _product_category(item)
    proof = _social_proof_phrase(item)
    link = _product_link(item)
    if not link:
        return body

    parts = _paragraphs(body)
    terms = _context_terms(item)
    candidates = []
    for i, part in enumerate(parts):
        plain = re.sub(r"<[^>]+>", "", part)
        if any(term in plain for term in terms):
            # タイトル直後・見出しだけの場所は避ける。
            if len(plain.strip()) >= 25 and not re.match(r"^\s*#{1,3}\s", plain):
                candidates.append(i)

    # 同じ段落に複数リンクを集中させない。
    target = None
    for i in candidates:
        if i not in used_positions:
            target = i
            break

    if target is None:
        # 文脈が見つからない商品は無理に広告化せず、記事の終端近くに短い補足として1件だけ置く。
        target = next((i for i in range(len(parts) - 1, -1, -1) if len(re.sub(r"<[^>]+>", "", parts[i]).strip()) >= 25), None)

    if target is None:
        return body

    # 「おすすめ」「チェック」「見てみる」のような広告CTAを避け、
    # 読者が料理中に自然に思い浮かべる一文にする。
    if category == "フライパン":
        sentence = f"こういう料理は、毎日使う{link}の扱いやすさで意外とラクさが変わります。"
    elif category == "包丁":
        sentence = f"材料を切るところでは、{link}が扱いやすいかどうかも地味に効いてきます。"
    elif category == "まな板":
        sentence = f"切る作業が続くと、{link}の洗いやすさも気になります。"
    elif category == "鍋":
        sentence = f"煮たり温めたりする料理なら、{link}も使いやすいものを選びたいところです。"
    elif category == "保存容器":
        sentence = f"余った分を取っておくなら、{link}があると後片付けまで少しラクになります。"
    else:
        sentence = f"こういう料理を続けるなら、{link}のような道具もあると助かります。"

    if proof:
        sentence += " " + proof

    # HTML本文の自然な段落として挿入する。
    insertion = "<p>" + sentence + "</p>"
    parts.insert(target + 1, insertion)
    used_positions.add(target + 1)
    return "".join(parts)


def _photo_html(dish_name):
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

    if photo_html:
        body = photo_html + "\n" + body.lstrip()

    # 楽天リンクは「商品一覧」化せず、読者がその道具を必要と感じる文脈へ分散。
    # 1商品1導線を基本とし、最大3商品まで。
    used_positions = set()
    for item in products:
        body = _insert_naturally(body, item, used_positions)

    return body


def main():
    title = Path("article_title.txt").read_text(encoding="utf-8").strip()
    body = Path("article_body.txt").read_text(encoding="utf-8")
    dish_name = Path("dish_name.txt").read_text(encoding="utf-8").strip()
    article = build_article(title, body, dish_name)
    Path("article_final.html").write_text(article, encoding="utf-8")
    print("料理写真を記事へ組み込みました。")
    print("楽天アフィリエイト商品を本文の関連文脈へ自然分散して組み込みました。")


if __name__ == "__main__":
    main()
