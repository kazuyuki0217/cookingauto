import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

SOURCES = [
    {"name":"Pinterest Business｜Pin作成", "url":"https://business.pinterest.com/ja/how-to-make-pins/"},
    {"name":"Pinterest Business｜オーディエンス/トレンド", "url":"https://business.pinterest.com/ja/guides-and-education/"},
    {"name":"Pinterest Business｜クリエイティブ", "url":"https://business.pinterest.com/ja/creative-best-practices/"},
    {"name":"Pinterest Business｜成功事例", "url":"https://business.pinterest.com/ja/success-stories/"},
    {"name":"Pinterest Business｜Pinterestの強み", "url":"https://business.pinterest.com/ja/how-pinterest-works/"},
    {"name":"Google Analytics Data API", "url":"https://developers.google.com/analytics/devguides/reporting/data/v1"},
    {"name":"Google Search Console API", "url":"https://developers.google.com/webmaster-tools"},
    {"name":"楽天アフィリエイト｜レポート", "url":"https://affiliate.rakuten.co.jp/guides/report/"},
    {"name":"楽天アフィリエイト｜ガイドライン", "url":"https://affiliate.rakuten.co.jp/guideline/rule/"},
]

def fetch(url):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0 point-recipe-learning-bot/1.0"})
    with urlopen(req, timeout=25) as r:
        raw = r.read().decode("utf-8", errors="replace")
    raw = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    return text[:14000]

def main():
    out = []
    for src in SOURCES:
        try:
            text = fetch(src["url"])
            out.append({**src, "ok": True, "text": text})
            print("取得成功:", src["name"])
        except Exception as exc:
            out.append({**src, "ok": False, "error": str(exc)})
            print("取得失敗:", src["name"], exc)
    Path("learning").mkdir(exist_ok=True)
    Path("learning/research_snapshot.json").write_text(
        json.dumps({"collectedAt": datetime.now(timezone.utc).isoformat(), "sources": out},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("夜間情報収集完了:", len(out), "sources")

if __name__ == "__main__":
    main()
