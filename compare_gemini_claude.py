import base64
import json
import os
import urllib.request
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PROMPT = """
あなたは料理ブログ編集者です。添付の料理写真を見て、写真から確実に判断できる範囲だけを使ってください。
題材は、51歳・単身赴任・仕事終わりに自炊する生活者の実体験ブログです。
以下の条件で日本語の記事を書いてください。
- タイトルは検索されやすさだけでなく、読みたくなるフックを入れる
- 冒頭で仕事終わり・一人暮らしの読者の悩みに自然に入る
- 写真から確認できない材料、分量、調理工程、味の断定は捏造しない
- 読者が「自分でも作れそう」と思える自然な文章
- 実際に食べた本人になりきって嘘の体験を作らない。写真から判断できることと一般的な説明を分ける
- 料理と相性の良いキッチン用品への自然な導線を1～2か所入れる
- 「楽天で見てみる」という定型句は使わない
- 広告感を出しすぎず、ブログとして最後まで読める文章にする
- 見出しを適切に使う
出力は TITLE: から始め、その後に本文HTMLを出してください。
"""


def find_image():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        p = Path(explicit)
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            return p
    candidates = []
    root = Path("images")
    if root.exists():
        candidates.extend(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not candidates:
        raise RuntimeError("images/ に料理写真がありません")
    return sorted(candidates, key=lambda p: str(p))[0]


def mime(path):
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}[path.suffix.lower()]


def gemini(image, key):
    data = base64.b64encode(image.read_bytes()).decode("ascii")
    body = {"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": mime(image), "data": data}}]}]}
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + key
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        obj = json.loads(r.read().decode())
    return obj["candidates"][0]["content"]["parts"][0]["text"]


def claude(image, key):
    data = base64.b64encode(image.read_bytes()).decode("ascii")
    body = {"model": "claude-sonnet-4-5", "max_tokens": 4000, "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": mime(image), "data": data}}, {"type": "text", "text": PROMPT}]}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        obj = json.loads(r.read().decode())
    return "".join(x.get("text", "") for x in obj.get("content", []))


def main():
    gkey = os.environ.get("GEMINI_API_KEY", "").strip()
    ckey = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not gkey or not ckey:
        raise RuntimeError("GEMINI_API_KEY と ANTHROPIC_API_KEY の両方が必要です")
    image = find_image()
    Path("gemini_article.txt").write_text(gemini(image, gkey), encoding="utf-8")
    Path("claude_article.txt").write_text(claude(image, ckey), encoding="utf-8")
    print("Gemini/Claude比較生成完了")
    print("入力写真:", image)


if __name__ == "__main__":
    main()
