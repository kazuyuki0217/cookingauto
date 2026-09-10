import base64
import os
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

POST_URI = "https://f.hatena.ne.jp/atom/post"


def wsse_headers(username, api_key):
    # Hatena Atom APIs also support WSSE authentication. The project already
    # uses the Hatena ID/API key for AtomPub, so keep credentials in secrets.
    import hashlib
    import random
    import datetime
    import base64 as b64

    nonce = os.urandom(16)
    created = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    digest = hashlib.sha1(nonce + created.encode() + api_key.encode()).digest()
    password_digest = b64.b64encode(digest).decode()
    nonce_b64 = b64.b64encode(nonce).decode()
    value = (
        f'UsernameToken Username="{username}", '
        f'PasswordDigest="{password_digest}", '
        f'Nonce="{nonce_b64}", Created="{created}"'
    )
    return {"X-WSSE": value}


def upload_photo(photo_path):
    username = os.environ["HATENA_ID"].strip()
    api_key = os.environ["HATENA_API_KEY"].strip()
    folder = os.environ.get("HATENA_FOTOLIFE_FOLDER", "料理アフィリエイト自動化").strip()

    path = Path(photo_path)
    ext = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext)
    if not mime:
        raise RuntimeError("対応していない画像形式です。JPG/PNG/WebPを使用してください。")

    encoded = base64.b64encode(path.read_bytes()).decode()
    root = ET.Element("entry", {"xmlns": "http://purl.org/atom/ns#"})
    title = ET.SubElement(root, "title")
    title.text = path.stem
    content = ET.SubElement(root, "content", {"mode": "base64", "type": mime})
    content.text = encoded
    if folder:
        dc = ET.SubElement(root, "subject", {"xmlns": "http://purl.org/dc/elements/1.1/"})
        dc.text = folder

    body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    headers = {"Content-Type": "application/xml; charset=utf-8"}
    headers.update(wsse_headers(username, api_key))
    response = requests.post(POST_URI, data=body, headers=headers, timeout=60)
    response.raise_for_status()

    xml = ET.fromstring(response.content)
    ns_hatena = "http://www.hatena.ne.jp/info/xmlns#"
    image_url = xml.findtext(f"{{{ns_hatena}}}imageurl")
    if not image_url:
        raise RuntimeError("はてなフォトライフから画像URLを取得できませんでした。")
    return image_url


def main():
    photo = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if not photo:
        candidates = [
            p for p in Path(".").iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if not candidates:
            raise RuntimeError("料理写真が見つかりません。")
        photo = str(candidates[0])

    url = upload_photo(photo)
    Path("cooking_image_url.txt").write_text(url, encoding="utf-8")
    print("はてなフォトライフへの写真アップロード成功")
    print("画像URL:", url)


if __name__ == "__main__":
    main()
