import json
from pathlib import Path

from article_affiliate_builder import choose_products, _product_category, _social_proof_phrase


def main():
    dish_name = Path("dish_name.txt").read_text(encoding="utf-8").strip() if Path("dish_name.txt").exists() else ""
    if not dish_name:
        dish_name = Path("collection_dish_name.txt").read_text(encoding="utf-8").strip()
    if not dish_name:
        raise RuntimeError("料理名がありません。")

    products = choose_products(dish_name)
    candidates = []
    for item in products:
        candidates.append({
            "itemName": str(item.get("itemName", "")).strip(),
            "category": _product_category(item),
            "reviewAverage": item.get("reviewAverage"),
            "reviewCount": item.get("reviewCount"),
            "itemPrice": item.get("itemPrice"),
            "affiliateUrl": str(item.get("affiliateUrl") or item.get("itemUrl") or "").strip(),
            "socialProof": _social_proof_phrase(item),
        })

    Path("rakuten_candidates.json").write_text(
        json.dumps(
            {
                "dishName": dish_name,
                "candidates": candidates,
                "rule": "商品は料理との関連性・実データの評価・レビュー数・価格帯を考慮し、最大3件。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"楽天候補を{len(candidates)}件準備しました。")


if __name__ == "__main__":
    main()
