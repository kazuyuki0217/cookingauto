import os
import base64
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

image_dir = "images"
image_files = []

for filename in os.listdir("."):
    if filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        image_files.append(filename)

if not image_files:
    raise RuntimeError("料理写真が見つかりません。")
image_path = image_files[0]

with open(image_path, "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

ext = os.path.splitext(image_path)[1].lower()

if ext in [".jpg", ".jpeg"]:
    mime = "image/jpeg"
elif ext == ".png":
    mime = "image/png"
elif ext == ".webp":
    mime = "image/webp"
else:
    mime = "image/jpeg"

prompt = """
この料理写真を詳しく分析してください。

この写真をもとに、
「51歳ホームセンター店員の単身赴任生活」
という料理ブログの記事を作成してください。

読者は、一人暮らし・単身赴任で仕事終わりに料理をする人です。

以下を記事に含めてください。

・検索されやすくクリックしたくなるタイトル
・料理名
・仕事終わりでも作りやすい魅力
・材料
・作り方
・実際に食べたような自然な感想
・節約ポイント
・時短ポイント
・失敗しにくいポイント
・この料理に合うキッチン用品を自然に紹介する文章

写真から判断できない材料や分量については、
断定せず「目安」として自然に設定してください。

料理写真の内容を最優先してください。

記事は、はてなブログにそのまま投稿できるHTML形式にしてください。

最初の1行は必ず

TITLE: 

から始め、その後に記事本文を書いてください。
"""

response = client.responses.create(
    model="gpt-5-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:{mime};base64,{image_data}",
                },
            ],
        }
    ],
)

text = response.output_text.strip()

lines = text.splitlines()

title = "仕事終わりの簡単節約ごはん"

if lines and lines[0].startswith("TITLE:"):
    title = lines[0].replace("TITLE:", "", 1).strip()
    body = "\n".join(lines[1:]).strip()
else:
    body = text

with open("article_title.txt", "w", encoding="utf-8") as f:
    f.write(title)

with open("article_body.txt", "w", encoding="utf-8") as f:
    f.write(body)

print("AI記事生成完了")
print("タイトル:", title)
