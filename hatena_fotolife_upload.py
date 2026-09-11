import base64
import os
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

POST_URI = "https://f.hatena.ne.jp/atom/post"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def wsse_headers(username, api_key):
    import hashlib
    import datetime

    nonce = os.urandom(16)
    created = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    digest = hashlib.sha1(nonce + created.encode() + api_key.encode()).digest()
    password_digest = base64.b64encode(digest).decode()
    nonce_b64 = base64.b64encode(nonce).decode()
    return {
        "X-WSSE": (
            f'UsernameToken Username="{username}", '
            f'PasswordDigest="{password_digest}", '
            f'Nonce="{nonce_b64}", Created="{created}"'
        )
    }


def find_photo():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    candidates = []
    for root in (Path("images"), Path(".")):
        if root.exists():
            candidates.extend(
                p for p in root.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
    if not candidates:
        raise RuntimeError("料理写真が見つかりません。")
    return sorted(candidates, key=lambda p: str(p))[0]


def upload_photo(photo_path):
    username = os.environ["HATENA_ID"].strip()
    api_key = os.environ["HATENA_API_KEY"].strip()
    folder = os.environ.get("HATENA_FOTOLIFE_FOLDER", "料理アフィリエイト自動化").strip()

    path = Path(photo_path)
    mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(path.suffix.lower())
    if not mime:
        raise RuntimeError("対応していない画像形式です。JPG/PNG/WebPを使用してください。")

    root = ET.Element("entry", {"xmlns": "http://purl.org/atom/ns#"})
    ET.SubElement(root, "title").text = path.stem
    ET.SubElement(root, "content", {"mode": "base64", "type": mime}).text = base64.b64encode(path.read_bytes()).decode()
    if folder:
        ET.SubElement(root, "subject", {"xmlns": "http://purl.org/dc/elements/1.1/"}).text = folder

    response = requests.post(
        POST_URI,
        data=ET.tostring(root, encoding="utf-8", xml_declaration=True),
        headers={"Content-Type": "application/xml; charset=utf-8", **wsse_headers(username, api_key)},
        timeout=60,
    )
    response.raise_for_status()

    xml = ET.fromstring(response.content)
    ns = "http://www.hatena.ne.jp/info/xmlns#"
    image_url = xml.findtext(f"{{{ns}}}imageurl")
    if not image_url:
        raise RuntimeError("はてなフォトライフから画像URLを取得できませんでした。")
    return image_url


def main():
    photo = find_photo()
    url = upload_photo(photo)
    Path("cooking_image_url.txt").write_text(url, encoding="utf-8")
    print("はてなフォトライフへの写真アップロード成功")
    print("画像URL取得済み")


if __name__ == "__main__":
    main()
