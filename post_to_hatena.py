
import os
import requests
from xml.sax.saxutils import escape

HATENA_ID = os.environ["HATENA_ID"]
HATENA_API_KEY = os.environ["HATENA_API_KEY"]
HATENA_ENDPOINT = os.environ["HATENA_ENDPOINT"]

title = os.environ.get("POST_TITLE", "自動投稿テスト")
body = os.environ.get("POST_BODY", "GitHub Actionsからの自動投稿テストです。")

xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://purl.org/atom/ns#">
<title>{escape(title)}</title>
<content type="text/plain">{escape(body)}</content>
</entry>"""

response = requests.post(
    HATENA_ENDPOINT,
    auth=(HATENA_ID, HATENA_API_KEY),
    data=xml.encode("utf-8"),
    headers={"Content-Type": "application/atom+xml; charset=utf-8"},
    timeout=30,
)

print("HTTPステータス:", response.status_code)
print(response.text)

response.raise_for_status()
print("はてなブログへの投稿成功")
