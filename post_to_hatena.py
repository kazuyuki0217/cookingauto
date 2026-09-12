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

title = os.environ.get("POST_TITLE", "自動投稿テスト").strip()
body = os.environ.get("POST_BODY", "")
if not body and Path("article_final.html").exists():
    body = Path("article_final.html").read_text(encoding="utf-8")


def parse_post_url(xml_bytes):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return ""
    for link in root.iter():
        if link.tag.endswith("link"):
            href = link.attrib.get("href", "").strip()
            if href.startswith("http"):
                return href
    return ""


def find_existing_post():
    """同一タイトルの記事が既に公開済みなら、そのURLを返す。"""
    response = requests.get(
        ENDPOINT,
        auth=(HATENA_ID, HATENA_API_KEY),
        headers={"Accept": "application/atom+xml, application/xml"},
        params={"max-results": 100},
        timeout=30,
    )
    print("既存記事確認HTTPステータス:", response.status_code)
    response.raise_for_status()

    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(response.content)
    except Exception:
        return ""

    for entry in root.findall("atom:entry", ns):
        title_node = entry.find("atom:title", ns)
        existing_title = (title_node.text or "").strip() if title_node is not None else ""
        if existing_title != title:
            continue

        for link in entry.findall("atom:link", ns):
            href = (link.attrib.get("href") or "").strip()
            if href.startswith("http"):
                return href

        id_node = entry.find("atom:id", ns)
        if id_node is not None and (id_node.text or "").strip().startswith("http"):
            return id_node.text.strip()

    return ""


existing_url = find_existing_post()
if existing_url:
    Path("hatena_post_url.txt").write_text(existing_url, encoding="utf-8")
    print("同一タイトルの記事が既に存在するため、重複投稿を防止しました。")
    print("既存記事URL:", existing_url)
    raise SystemExit(0)

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

post_url = parse_post_url(response.content)
if not post_url:
    post_url = "https://tansinfuninkazu.hatenablog.com/"
Path("hatena_post_url.txt").write_text(post_url, encoding="utf-8")
print("記事URL:", post_url)
print("はてなブログへの投稿成功")
