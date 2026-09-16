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


def main():
    gas_url = os.environ.get("RAKUTEN_GAS_URL", "").strip()
    secret = os.environ.get("PINTEREST_AUTOMATION_SECRET", "").strip()
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gas_url:
        raise RuntimeError("RAKUTEN_GAS_URLが設定されていません。")
    if not secret:
        raise RuntimeError("PINTEREST_AUTOMATION_SECRETが設定されていません。")
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEYがGitHub Actionsに設定されていません。")

    image_path = find_image()
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "service": "cloud_article",
        "secret": secret,
        "mimeType": mime_type(image_path),
        "imageBase64": image_base64,
        "geminiApiKey": gemini_api_key,
    }

    request = urllib.request.Request(
        gas_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloud記事生成API HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cloud記事生成API通信エラー: {exc}") from exc

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cloud記事生成APIの応答がJSONではありません: {raw[:1000]}") from exc

    if not result.get("success"):
        raise RuntimeError(f"Cloud記事生成API失敗: {result.get('error', '不明なエラー')}")

    title = str(result.get("title", "")).strip()
    dish_name = str(result.get("dish_name", "")).strip()
    body = str(result.get("body", "")).strip()
    if not title or not body:
        raise RuntimeError("Cloud記事生成APIからタイトルまたは本文を取得できませんでした。")

    Path("article_title.txt").write_text(title, encoding="utf-8")
    Path("dish_name.txt").write_text(dish_name or title, encoding="utf-8")
    Path("article_body.txt").write_text(body, encoding="utf-8")
    print("GAS + Gemini Cloudによる写真解析・記事生成完了")
    print("料理:", dish_name or title)
    print("タイトル:", title)
    print("写真:", image_path)


if __name__ == "__main__":
    main()
