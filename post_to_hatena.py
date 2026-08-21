import os
import base64
import hashlib
import secrets
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import requests

HATENA_ID = os.environ["HATENA_ID"]
HATENA_API_KEY = os.environ["HATENA_API_KEY"]
HATENA_ENDPOINT = os.environ["HATENA_ENDPOINT"].rstrip("/")

title = os.environ.get("POST_TITLE", "自動投稿テスト")
body = os.environ.get(
    "POST_BODY",
    "GitHub Actionsからの自動投稿テストです。"
)

# WSSE認証
nonce = secrets.token_bytes(16)
created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

digest = hashlib.sha1(
    nonce + created.encode("utf-8") + HATENA_API_KEY.encode("utf-8")
).digest()

password_digest = base64.b64encode(digest).decode("ascii")
nonce_b64 = base64.b64encode(nonce).decode("ascii")

wsse = (
    'UsernameToken '
    f'Username="{HATENA_ID}", '
    f'PasswordDigest="{password_digest}", '
    f'Nonce="{nonce_b64}", '
    f'Created="{created}"'
)

headers = {
    "X-WSSE": wsse,
    "Accept": "application/atom+xml, application/xml, text/xml, */*",
}

# まずAtomPubルートから投稿先URLを取得
response = requests.get(
    HATENA_ENDPOINT,
    headers=headers,
    timeout=30,
)

print("ルート取得HTTPステータス:", response.status_code)
print(response.text[:2000])

response.raise_for_status()

# AtomPubのPostURIを取得
from xml.etree import ElementTree as ET

root = ET.fromstring(response.content)

post_uri = None

for link in root.iter():
    if link.tag.endswith("link"):
        rel = link.attrib.get("rel", "")
        href = link.attrib.get("href", "")
        if rel == "service.post":
            post_uri = href
            break

if not post_uri:
    raise RuntimeError("AtomPubの投稿先(service.post)を取得できませんでした")

print("投稿先:", post_uri)

# 記事XML
xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://purl.org/atom/ns#">
<title>{escape(title)}</title>
<content type="text/plain">{escape(body)}</content>
</entry>"""

# 投稿
response = requests.post(
    post_uri,
    headers={
        "X-WSSE": wsse,
        "Content-Type": "application/atom+xml; charset=utf-8",
        "Accept": "application/atom+xml, application/xml, text/xml, */*",
    },
    data=xml.encode("utf-8"),
    timeout=30,
)

print("投稿HTTPステータス:", response.status_code)
print(response.text[:3000])

response.raise_for_status()

print("はてなブログへの投稿成功")
