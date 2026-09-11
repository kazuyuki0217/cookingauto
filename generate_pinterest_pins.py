import json
from pathlib import Path

BLOG_URL = "https://tansinfuninkazu.hatenablog.com/"
if Path("hatena_post_url.txt").exists():
    candidate = Path("hatena_post_url.txt").read_text(encoding="utf-8").strip()
    if candidate.startswith("http"):
        BLOG_URL = candidate

dish = Path("dish_name.txt").read_text(encoding="utf-8").strip() if Path("dish_name.txt").exists() else "料理"
image_url = Path("cooking_image_url.txt").read_text(encoding="utf-8").strip()

pins = [
    {"title": f"{dish}｜仕事終わりでも作れる簡単ごはん", "description": f"帰宅後でも作りやすい{dish}。実際の料理写真と作り方、時短・節約のポイントを紹介します。"},
    {"title": f"{dish}｜疲れて帰った日の晩ごはん", "description": f"仕事終わりに無理なく作れる{dish}。一人暮らし・単身赴任の自炊に役立つポイントをまとめました。"},
    {"title": f"{dish}｜節約しながら満足できる自炊", "description": f"食費を抑えながら、ちゃんと食べたい日に。{dish}の材料・作り方・節約のコツを紹介。"},
    {"title": f"{dish}｜一人分だから簡単に作れる", "description": f"一人暮らしの自炊は頑張りすぎないのがコツ。{dish}を作ったリアルな記録です。"},
    {"title": f"{dish}｜毎日の自炊を楽にするコツ", "description": f"{dish}を作って分かった、時短・片付け・道具選びのポイント。詳しい記事はこちら。"},
]

result = [{**p, "link": BLOG_URL, "image_url": image_url} for p in pins]
Path("pinterest_pins.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Pinterest用5パターン生成完了")
print("リンク:", BLOG_URL)
for i, p in enumerate(result, 1):
    print(f"{i}: {p['title']}")
