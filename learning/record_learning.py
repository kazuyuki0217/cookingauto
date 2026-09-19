import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def read(path, default=""):
    p = Path(path)
    return p.read_text(encoding="utf-8").strip() if p.exists() else default

def main():
    dish = read("dish_name.txt", read("collection_dish_name.txt", ""))
    title = read("article_title.txt")
    hatena = read("hatena_post_url.txt")
    strategy = {}
    p = Path("learning/next_strategy.json")
    if p.exists():
        try: strategy = json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    candidates = []
    p = Path("rakuten_candidates.json")
    if p.exists():
        try: candidates = json.loads(p.read_text(encoding="utf-8")).get("candidates", [])[:3]
        except Exception: pass
    pins = []
    p = Path("pinterest_pins.json")
    if p.exists():
        try: pins = json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    publish = {}
    p = Path("pinterest_publish_result.json")
    if p.exists():
        try: publish = json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass

    record = {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "runId": os.environ.get("GITHUB_RUN_ID", ""),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "dishName": dish,
        "articleTitle": title,
        "hatenaUrl": hatena,
        "strategy": strategy,
        "rakutenCandidates": candidates,
        "pinterestPins": pins,
        "pinterestPublish": publish,
        "outcomes": {
            "ga4": None,
            "searchConsole": None,
            "pinterestAnalytics": None,
            "rakuten": None
        }
    }

    Path("learning/records").mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path("learning/records") / f"{stamp}_{os.environ.get('GITHUB_RUN_ID','run')}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run(["git", "config", "user.name", "point-recipe-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "point-recipe-bot@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", str(out), "learning/next_strategy.json"], check=True)
    subprocess.run(["git", "commit", "-m", f"ポイントレシピ学習記録: {dish or '料理'}"], check=False)
    subprocess.run(["git", "push"], check=True)
    print("学習記録を保存:", out)

if __name__ == "__main__":
    main()
