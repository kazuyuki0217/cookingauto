import os
import base64
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_image():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            return p

    candidates = []
    for root in (Path("images"), Path(".")):
        if root.exists():
            candidates.extend(
                p for p in root.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
    if not candidates:
        raise RuntimeError("料理写真が見つかりません。images/ に料理写真を配置してください。")
    return sorted(candidates, key=lambda p: str(p))[0]


image_path = find_image()
with open(image_path, "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

ext = image_path.suffix.lower()
mime = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}.get(ext, "image/jpeg")

prompt = """
この料理写真を最優先して分析し、「51歳ホームセンター店員の単身赴任生活」の記事を作成してください。
読者は、一人暮らし・単身赴任で仕事終わりに自炊する人です。
AIが実際に食べたと誤解させる表現は避け、「写真から見て」「今回の料理では」など自然に書いてください。

必ず次の形式で出力してください。
1行目: TITLE: 検索されやすく、クリックしたくなる記事タイトル
2行目: DISH_NAME: 料理名
3行目以降: はてなブログにそのまま使えるHTML本文

本文には、料理の魅力、材料（写真から判断できないものは目安と明記）、作り方、仕事終わり向けの時短・節約ポイント、失敗しにくいポイント、自然なキッチン用品紹介を含めてください。
一般的なレシピの断定より、写真から読み取れる内容を優先してください。
"""

response = client.responses.create(
    model="gpt-5-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:{mime};base64,{image_data}"},
            ],
        }
    ],
)

text = response.output_text.strip()
lines = text.splitlines()

title = "仕事終わりの簡単節約ごはん"
dish_name = "料理"
body_start = 0

for i, line in enumerate(lines[:3]):
    if line.startswith("TITLE:"):
        title = line.replace("TITLE:", "", 1).strip() or title
        body_start = max(body_start, i + 1)
    elif line.startswith("DISH_NAME:"):
        dish_name = line.replace("DISH_NAME:", "", 1).strip() or dish_name
        body_start = max(body_start, i + 1)

body = "\n".join(lines[body_start:]).strip()

Path("article_title.txt").write_text(title, encoding="utf-8")
Path("dish_name.txt").write_text(dish_name, encoding="utf-8")
Path("article_body.txt").write_text(body, encoding="utf-8")

print("AI記事生成完了")
print("料理:", dish_name)
print("タイトル:", title)
print("写真:", image_path)
