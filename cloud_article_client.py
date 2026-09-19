import base64
import json
import os
import re
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
            candidates.extend(p for p in root.iterdir()
                             if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not candidates:
        raise RuntimeError("料理写真が見つかりません。")
    return sorted(candidates, key=lambda p: str(p))[0]


def mime_type(path):
    return {".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(path.suffix.lower(),"image/jpeg")


def build_prompt(dish_name):
    return f"""あなたは日本語の料理ブログ編集者兼コピーライターです。
添付された料理写真と、料理写真コレクションで登録された料理名「{dish_name}」を起点に、仕事終わり・一人暮らし・単身赴任で自炊する人が「自分でも作れそう」と感じる自然な記事を作成してください。
登録料理名はユーザーが指定した正式名称なので、別の料理名へ勝手に変更しないでください。写真と料理名が明らかに矛盾する場合は「MISMATCH: 写真と料理名が一致しません」とだけ返してください。
写真から確認できない材料、分量、工程、味、購入履歴などを事実として創作しないでください。
大げさな煽り、過剰なSEO、定型的なAI表現、「いかがでしたか？」は禁止です。
記事は共感→料理の魅力→材料→作り方→時短・節約・洗い物のポイント→調理中の不便と解決→まとめの流れにしてください。
楽天リンクは後工程で自然に本文へ分散するため、記事末尾に広告一覧や露骨なCTAを作らないでください。
共感、具体的な使用場面、損失回避、社会的証明、選択肢の少なさ、信頼性、自己投影を活用できますが、嘘のレビュー、人気、限定、値下げ、実体験は作らないでください。
最初の行を TITLE: 記事タイトル、2行目を DISH_NAME: 料理名、その後に本文HTMLを出力してください。"""


def generate_with_gemini(api_key, image_base64, mime, dish_name):
    prompt = build_prompt(dish_name)
    models = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
    last_error = ""
    for model in models:
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        payload = {"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":mime,"data":image_base64}}]}]}
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type":"application/json","x-goog-api-key":api_key},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
            generated = data.get("candidates",[{}])[0].get("content",{}).get("parts",[{}])[0].get("text","")
            if not generated:
                last_error = "Gemini APIから本文が返りませんでした。"
                continue
            title_match = re.search(r"(?:^|\n)TITLE:\s*(.+)", generated, re.I)
            dish_match = re.search(r"(?:^|\n)DISH_NAME:\s*(.+)", generated, re.I)
            title = title_match.group(1).strip() if title_match else "今日の一人ごはん"
            dish_name = dish_match.group(1).strip() if dish_match else title
            body = re.sub(r"(?:^|\n)TITLE:\s*.+", "", generated, count=1, flags=re.I)
            body = re.sub(r"(?:^|\n)DISH_NAME:\s*.+", "", body, count=1, flags=re.I).strip()
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
    dish_name = os.environ.get("COLLECTION_DISH_NAME", "").strip()
    if not dish_name:
        p = Path("collection_dish_name.txt")
        dish_name = p.read_text(encoding="utf-8").strip() if p.exists() else ""
    if not dish_name:
        raise RuntimeError("料理名が確定していません。料理写真コレクション登録時に料理名を指定してください。")
    title, generated_dish_name, body = generate_with_gemini(
        api_key,
        base64.b64encode(image_path.read_bytes()).decode("ascii"),
        mime_type(image_path), dish_name)
    if generated_dish_name and generated_dish_name != title and generated_dish_name != dish_name:
        print("Geminiが返した料理名:", generated_dish_name)
    dish_name = dish_name
    if not title or not body:
        raise RuntimeError("Geminiからタイトルまたは本文を取得できませんでした。")
    Path("article_title.txt").write_text(title, encoding="utf-8")
    Path("dish_name.txt").write_text(dish_name, encoding="utf-8")
    Path("article_body.txt").write_text(body, encoding="utf-8")
    print("Gemini→Claude風：料理写真の解析・記事生成完了")
    print("料理:", dish_name or title)
    print("タイトル:", title)
    print("写真:", image_path)


if __name__ == "__main__":
    main()
