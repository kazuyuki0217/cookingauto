import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

prompt = """
あなたは「51歳ホームセンター店員の単身赴任生活」という料理ブログの編集者です。

仕事終わりの一人暮らし・単身赴任男性が、
「これなら自分でも作れそう」
「今日これを作ってみよう」
と思える料理記事を作成してください。

記事は以下の条件で作成してください。

・タイトルは検索されやすく、なおかつクリックしたくなるもの
・仕事終わり、簡単、節約、短時間、一人暮らし、単身赴任を意識
・実際に料理を作って食べたような自然な文章
・大げさな表現は禁止
・材料
・作り方
・食べた感想
・仕事終わりにおすすめな理由
・失敗しにくいポイント
・料理に合うキッチン用品を自然に紹介できる導線
・読者が最後まで読みやすい構成
・Markdownではなく、はてなブログでそのまま使いやすいHTMLで作成

最初の行に
TITLE: タイトル
と書き、

その次の行から本文を書いてください。
"""

response = client.responses.create(
    model="gpt-5-mini",
    input=prompt
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

print("記事生成完了")
print("タイトル:", title)
