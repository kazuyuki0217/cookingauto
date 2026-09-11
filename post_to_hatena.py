import os
from pathlib import Path
import requests
from xml.sax.saxutils import escape

HATENA_ID = os.environ["HATENA_ID"].strip()
HATENA_API_KEY = os.environ["HATENA_API_KEY"].strip()
ENDPOINT = os.environ.get(
    "HATENA_ENDPOINT",
    f"https://blog.hatena.ne.jp/{HATENA_ID}/tansinfuninkazu.hatenablog.com/atom/entry",
).strip()

title = os.environ.get("POST_TITLE", "自動投稿テスト")
body = os.environ.get("POST_BODY", "")
if not body and Path("article_final.html").exists():
    body = Path("article_final.html").read_text(encoding="utf-8")

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://purl.org/atom/ns#">
<title>{escape(title)}</title>
<content type="text/html">{escape(body)}</content>
</entry>'''

response = requests.post(
    ENDPOINT,
    auth=(HATENA_ID, HATENA_API_KEY),
    data=xml.encode("utf-8"),
    headers={"Content-Type": "application/atom+xml; charset=utf-8"},
    timeout=30,
)
print("投稿先:", ENDPOINT)
print("HTTPステータス:", response.status_code)
response.raise_for_status()
print("はてなブログへの投稿成功")
