import json
from pathlib import Path

BLOG_URL = "https://tansinfuninkazu.hatenablog.com/"
if Path("hatena_post_url.txt").exists():
    candidate = Path("hatena_post_url.txt").read_text(encoding="utf-8").strip()
    if candidate.startswith("http"):
        BLOG_URL = candidate

dish = Path("dish_name.txt").read_text(encoding="utf-8").strip() if Path("dish_name.txt").exists() else "料理"
image_url = Path("cooking_image_url.txt").read_text(encoding="utf-8").strip()

# 同じ写真でも「クリックする理由」を変える5方向に分ける。
pins = [
    {
        "title": f"{dish}｜仕事終わりでも作れた、帰宅後の簡単ごはん",
        "description": f"帰宅後に料理する気力が残っていない日でも作りやすい{dish}。実際の料理写真、作り方、時短の工夫をまとめました。"
    },
    {
        "title": f"{dish}｜食費を抑えたい一人暮らしの晩ごはん",
        "description": f"外食や惣菜に頼りすぎず、無理なく自炊したい日に。{dish}の節約ポイントと、満足感を出すコツを紹介します。"
    },
    {
        "title": f"{dish}｜一人分の自炊、何を作るか迷ったら",
        "description": f"一人暮らし・単身赴任で献立に迷った日の実例です。{dish}を実際に作った記録と、失敗しにくいポイントはこちら。"
    },
    {
        "title": f"{dish}｜洗い物を増やしたくない日の料理アイデア",
        "description": f"仕事終わりの自炊で面倒なのが片付け。{dish}を作るときに意識した時短・調理・片付けのポイントを紹介します。"
    },
    {
        "title": f"{dish}｜この料理を作るなら欲しくなるキッチン用品",
        "description": f"{dish}を作っていて『こういう道具があると楽そう』と感じたポイントを整理。料理と相性の良いキッチン用品も記事で紹介しています。"
    },
]

result = [{**p, "link": BLOG_URL, "image_url": image_url} for p in pins]
Path("pinterest_pins.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Pinterest用5パターン生成完了")
print("リンク:", BLOG_URL)
for i, p in enumerate(result, 1):
    print(f"{i}: {p['title']}")
