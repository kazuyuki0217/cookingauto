import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# 2026-09現在の無料枠対応モデル。Gemini 2.5 Flash-Liteから移行。
MODEL = "gemini-3.5-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def find_image():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            return p
    candidates = []
    for root in (Path("images"), Path(".")):
        if root.exists():
            candidates.extend(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not candidates:
        raise RuntimeError("料理写真が見つかりません。images/ に料理写真を配置してください。")
    return sorted(candidates, key=lambda p: str(p))[0]


def mime_type(path):
    return {".jpg":"image/jpeg", ".jpeg":"image/jpeg", ".png":"image/png", ".webp":"image/webp"}.get(path.suffix.lower(), "image/jpeg")


def call_gemini(image_path):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEYが設定されていません。Google AI Studioの無料枠APIキーをGitHub Secretsへ登録してください。")
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    prompt = """
この料理写真を最優先して分析し、「51歳ホームセンター店員の単身赴任生活」の記事を作成してください。
読者は、一人暮らし・単身赴任で仕事終わりに自炊する日本語読者です。
写真から確実に分からない材料・分量・調理工程は断定せず、「写真からは判断できない」と明記してください。
AIが実際に食べたような表現は禁止です。

必ず次の形式だけで出力してください。
1行目: TITLE: 検索されやすく、クリックしたくなる自然な記事タイトル
2行目: DISH_NAME: 写真から判断した料理名
3行目以降: はてなブログにそのまま使えるHTML本文

本文には、写真から分かる料理の特徴、材料、作り方、仕事終わり向けの時短・節約ポイント、失敗しにくいポイント、料理と相性の良いキッチン用品紹介、まとめを含めてください。
不明な材料や分量は推測で断定しないでください。宣伝臭を強くせず、実際の単身赴任生活の記事らしい文章にしてください。
"""
    payload = {"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":mime_type(image_path),"data":image_data}}]}],"generationConfig":{"maxOutputTokens":5000}}
    request = urllib.request.Request(API_URL + "?key=" + api_key, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code in (401, 403):
            raise RuntimeError("Gemini無料APIキーの認証に失敗しました。無料枠のAPIキーを確認してください。") from exc
        if exc.code == 429:
            raise RuntimeError("Gemini無料枠の利用上限に達したため停止しました。課金へ切り替えず、後で再実行してください。") from exc
        raise RuntimeError(f"Gemini APIエラー HTTP {exc.code}: {detail[:500]}") from exc
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Geminiから記事本文を取得できませんでした: {json.dumps(result, ensure_ascii=False)[:1000]}") from exc


def parse_article(text):
    lines = text.splitlines()
    title, dish_name, body_start = "仕事終わりの簡単節約ごはん", "今日の一人暮らしごはん", 0
    for i, line in enumerate(lines[:5]):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "", 1).strip() or title
            body_start = max(body_start, i + 1)
        elif line.startswith("DISH_NAME:"):
            dish_name = line.replace("DISH_NAME:", "", 1).strip() or dish_name
            body_start = max(body_start, i + 1)
    body = "\n".join(lines[body_start:]).strip()
    if not body:
        raise RuntimeError("Geminiが空の記事本文を返しました。")
    return title, dish_name, body


image_path = find_image()
text = call_gemini(image_path)
title, dish_name, body = parse_article(text)
Path("article_title.txt").write_text(title, encoding="utf-8")
Path("dish_name.txt").write_text(dish_name, encoding="utf-8")
Path("article_body.txt").write_text(body, encoding="utf-8")
print("Gemini無料枠による写真解析・記事生成完了")
print("料理:", dish_name)
print("タイトル:", title)
print("写真:", image_path)
