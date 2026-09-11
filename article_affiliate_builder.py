import os
from html import escape
from pathlib import Path
import requests

# 楽天の認証情報はGAS側のScript Propertiesで管理する。
# GitHub Actionsへ楽天アクセスキーを渡さない構成を優先する。
RAKUTEN_GAS_URL = os.environ.get("RAKUTEN_GAS_URL", "").strip()
RAKUTEN_AUTOMATION_SECRET = os.environ.get("RAKUTEN_AUTOMATION_SECRET", "").strip()

# 旧直接API方式との互換用。ブリッジが未設定の場合のみ利用する。
RAKUTEN_APP_ID = os.environ.get("RAKUTEN_APP_ID", "5db6e350-5a71-4843-8d29-cf894bef88df")
RAKUTEN_AFFILIATE_ID = os.environ.get("RAKUTEN_AFFILIATE_ID", "56e8483c.b8c4995b.56e8483d.205a3086")
RAKUTEN_ACCESS_KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
RAKUTEN_API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


def find_photo_url():
    url = os.environ.get("COOKING_IMAGE_URL", "").strip()
    if not url and Path("cooking_image_url.txt").exists():
        url = Path("cooking_image_url.txt").read_text(encoding="utf-8").strip()
    return url if url.startswith(("https://", "http://")) else ""


def search_rakuten_via_gas(keywords):
    if not RAKUTEN_GAS_URL:
        raise RuntimeError("RAKUTEN_GAS_URL is not configured.")
    if not RAKUTEN_AUTOMATION_SECRET:
        raise RuntimeError("RAKUTEN_AUTOMATION_SECRET is not configured.")

    payload = {
        "service": "rakuten",
        "secret": RAKUTEN_AUTOMATION_SECRET,
        "keywords": keywords[:5],
    }
    response = requests.post(RAKUTEN_GAS_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise RuntimeError("GAS楽天ブリッジエラー: " + str(data.get("error", "不明なエラー")))
    return data.get("items", [])


def search_rakuten_direct(keyword, hits=10):
    if not RAKUTEN_ACCESS_KEY:
        raise RuntimeError("楽天APIの認証情報がGAS側にあるため、GitHubから直接検索できません。")
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
    keywords = [
        f"{dish_name} フライパン",
        f"{dish_name} 調理器具",
        f"{dish_name} キッチン用品",
    ]

    # 本番はGASブリッジを使用。楽天アクセスキーをGitHubへ渡さない。
    if RAKUTEN_GAS_URL and RAKUTEN_AUTOMATION_SECRET:
        candidates = search_rakuten_via_gas(keywords)
    else:
        candidates, seen = [], set()
        for keyword in keywords:
            for item in search_rakuten_direct(keyword, 10):
                url = item.get("affiliateUrl", "")
                if not item.get("itemName") or not url or url in seen:
                    continue
                seen.add(url)
                candidates.append(item)
                if len(candidates) >= 9:
                    break
            if len(candidates) >= 9:
                break

    # レビュー評価だけでなく、レビュー件数も加味して購入候補を選ぶ。
    candidates = [x for x in candidates if x.get("itemName") and (x.get("affiliateUrl") or x.get("itemUrl"))]
    candidates.sort(
        key=lambda x: (
            float(x.get("reviewAverage", 0) or 0),
            int(x.get("reviewCount", 0) or 0),
        ),
        reverse=True,
    )
    return candidates[:3]


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
    print("楽天検索方式:", "GASブリッジ（アクセスキー非公開）" if RAKUTEN_GAS_URL else "直接API（旧方式）")
    print("楽天商品リンク: 自動選定済み")


if __name__ == "__main__":
    main()
