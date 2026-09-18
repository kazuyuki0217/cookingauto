import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

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


def mime_type(path):
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def build_prompt():
    return """あなたは日本語の料理ブログ編集者兼コピーライターです。
添付された料理写真を起点に、読者が「自分の生活に置き換えて」読み進められる自然なブログ記事を作成してください。

【最重要：事実性】
写真から確認できない材料・分量・調理工程・味・購入履歴などを事実として創作しないでください。
写真だけでは断定できない内容は、一般的な提案として明確に表現してください。
AIが料理を作った、食べた、感じたという一人称の体験を創作しないでください。

【読者】
仕事終わりに一人分の料理を作る人、一人暮らし・単身赴任で自炊する人です。
料理上級者ではなく、「疲れていても作れそう」「これなら自分にもできそう」と感じる読者を想定してください。

【文章設計：Claude風】
単なるレシピ説明から始めず、仕事終わり・疲れ・食費・洗い物・料理の面倒さなど、読者が共感できる具体的な生活場面から自然に入ってください。
短い文と長い文を混ぜ、説明が続きすぎない読みやすいリズムにしてください。
「〜ですよね」「〜だったりします」のような自然な会話感は適度に使って構いませんが、多用しないでください。
大げさな煽り、過剰なSEOキーワード、定型的なAI表現、「いかがでしたか？」は禁止です。
料理の魅力だけでなく、「なぜ忙しい一人暮らしの人に役立つのか」を具体的に伝えてください。

【読者の行動を考えた構成】
読者は最初から商品を買うつもりで来ているとは限りません。
まず料理そのものへの興味、次に「自分でもできそう」という安心、その後に「これなら少しラクになりそう」という必要性が生まれる順番を意識してください。
商品を先に売ろうとせず、読者の小さな不便を文章の中で先に発見させてください。
その不便を解決する道具が自然に思い浮かぶようにしてください。

【記事構成】
1. 強いタイトル：検索意図と読みたくなるフックを両立
2. 共感を生む導入
3. 料理の魅力・食卓でのイメージ
4. 材料
5. 作り方
6. 時短・節約・洗い物などの実用ポイント
7. 調理中に実際に困りやすいポイントと、それを減らす考え方
8. まとめ

【楽天アフィリエイト導線：最重要】
記事末尾に「おすすめ商品一覧」「今回のおすすめ」「商品はこちら」などの広告コーナーを作らないでください。
商品リンクは後工程で本文中へ自然に分散挿入します。
そのため、調理器具が役立つ具体的な場面を本文の流れの中に自然に作ってください。
例：肉を焼く→フライパンの扱いやすさ、材料を切る→包丁やまな板、残りを保存→保存容器、など。
「おすすめです」「ぜひチェック」「楽天で見てみる」「購入はこちら」のような露骨なCTAを本文に作らないでください。
読者が自分で「こういう道具があるとラクかも」と気づける文章を優先してください。

【心理設計】
使える心理要素は、共感、具体的な使用場面、損失回避、社会的証明、選択肢の少なさ、信頼性、自己投影です。
ただし、嘘のレビュー数・人気・売り切れ・限定・値下げ・実体験は絶対に作らないでください。
「買わせる」より「判断しやすくする」ことを優先してください。
読者が商品ページへ進む理由は、商品そのものの宣伝ではなく、記事中で生まれた具体的な悩みや欲求と結び付けてください。

【出力】
最初の行を TITLE: 記事タイトル、2行目を DISH_NAME: 料理名、その後に本文HTMLを出力してください。
本文はブログへそのまま渡せるHTMLにしてください。
TITLE: と DISH_NAME: 以外の前置き、解説、Markdownコードブロックは不要です。"""


def generate_with_gemini(api_key, image_base64, mime):
    prompt = build_prompt()
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    last_error = ""

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model
            + ":generateContent"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": image_base64}},
                ]
            }]
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = response.read().decode("utf-8")
            data = json.loads(raw)
            generated = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            if not generated:
                last_error = "Gemini APIから本文が返りませんでした。"
                continue

            title_match = __import__("re").search(r"(?:^|\n)TITLE:\s*(.+)", generated, __import__("re").I)
            dish_match = __import__("re").search(r"(?:^|\n)DISH_NAME:\s*(.+)", generated, __import__("re").I)
            title = title_match.group(1).strip() if title_match else "今日の一人ごはん"
            dish_name = dish_match.group(1).strip() if dish_match else title
            body = __import__("re").sub(r"(?:^|\n)TITLE:\s*.+", "", generated, count=1, flags=__import__("re").I)
            body = __import__("re").sub(r"(?:^|\n)DISH_NAME:\s*.+", "", body, count=1, flags=__import__("re").I).strip()

            return title, dish_name, body
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"Gemini {model} HTTP {exc.code}: {detail[:700]}"
        except Exception as exc:
            last_error = str(exc)

    raise RuntimeError("Gemini記事生成に失敗しました: " + last_error)


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEYがGitHub Actionsに設定されていません。")

    image_path = find_image()
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    title, dish_name, body = generate_with_gemini(
        api_key, image_base64, mime_type(image_path)
    )

    if not title or not body:
        raise RuntimeError("Geminiからタイトルまたは本文を取得できませんでした。")

    Path("article_title.txt").write_text(title, encoding="utf-8")
    Path("dish_name.txt").write_text(dish_name or title, encoding="utf-8")
    Path("article_body.txt").write_text(body, encoding="utf-8")
    print("Gemini→Claude風：料理写真の解析・記事生成完了")
    print("料理:", dish_name or title)
    print("タイトル:", title)
    print("写真:", image_path)


if __name__ == "__main__":
    main()
