import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
# 完全無料運用：Google GeminiのFree Tier対象モデルのみ使用。
# 一時的な503等では自動リトライし、別のFree Tier対象モデルへフォールバックする。
MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]
RETRYABLE_HTTP_CODES = {500, 502, 503, 504}
MAX_RETRIES = 3


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


def _load_product_context():
    path = Path("rakuten_candidates.json")
    if not path.exists():
        return "商品候補データはまだありません。商品を無理に具体化せず、料理上の道具ニーズだけ自然に示してください。"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "商品候補データを読み込めませんでした。商品を無理に具体化せず、料理上の道具ニーズだけ自然に示してください。"

    lines = ["記事内の購入導線を設計するための楽天商品候補です。URLそのものは本文へ書かないでください。"]
    for item in data.get("candidates", [])[:3]:
        name = str(item.get("itemName", "")).strip()
        category = str(item.get("category", "")).strip()
        rating = item.get("reviewAverage")
        reviews = item.get("reviewCount")
        price = item.get("itemPrice")
        if not name:
            continue
        lines.append(f"- {category}: {name} / 評価={rating} / レビュー数={reviews} / 価格={price}")
    return "\n".join(lines)


def build_prompt():
    official_dish = os.environ.get("COLLECTION_DISH_NAME", "").strip()
    dish_hint = (
        f"今回の料理名は「{official_dish}」です。記事ではこの料理名を基本名称として扱ってください。"
        if official_dish else ""
    )
    product_context = _load_product_context()
    strategy_context = ""
    strategy_path = Path("learning/next_strategy.json")
    if strategy_path.exists():
        try:
            strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
            strategy_context = "\n".join([
                "夜間学習エンジンから今回の記事生成へ渡された実験条件です。",
                f"原則: {strategy.get(\"principles\", [])}",
                f"今回の実験: {strategy.get(\"currentExperiment\", {})}",
                f"生成ルール: {strategy.get(\"rules\", [])}",
            ])
        except Exception:
            strategy_context = ""
    return f"""
この料理写真を最優先して分析し、「51歳ホームセンター店員の単身赴任生活」の記事を作成してください。
{dish_hint}
{product_context}

今回の目的は、広告を後付けすることではありません。
読者が写真を見て「自分も作れそう」と感じ、本文を読んで「ここが面倒」「ここをラクにしたい」と自分の問題を認識し、その問題を解決する道具として関連商品に興味を持てる文章設計にしてください。
ただし、煽り・誇張・偽の口コミ・偽の希少性・購入の強要は禁止です。

行動原理として特に重視すること:
- 自分との類似性: 一人暮らし・単身赴任・仕事終わりという具体的な生活場面を使い、「自分にもできそう」と想像しやすくする。
- 認知負荷の低減: 材料・工程・道具の役割を整理し、読むだけで次の行動が分かるようにする。
- 問題→解決の自然な因果: 「面倒だから、この道具が必要」という順番を守り、商品名から売り込まない。
- 社会的証拠: 商品候補に実在する評価・レビュー数がある場合だけ、控えめに利用する。
- 選択肢過多の回避: 商品候補を大量に並べず、料理との関連性が高い少数に絞る。
- 将来の後悔を減らす: 購入を急がせるのではなく、「この料理を続けるなら、こういう機能が役立つ」と判断材料を渡す。
- 主体性: 最後は読者自身が「自分に必要か」を判断できる書き方にする。

読者は、一人暮らし・単身赴任で仕事終わりに自炊する日本語読者です。
写真から確実に分からない材料・分量・調理工程は断定せず、「写真からは判断できない」と明記してください。
AIが実際に食べたような表現は禁止です。

必ず次の形式だけで出力してください。
1行目: TITLE: 検索されやすく、クリックしたくなる自然な記事タイトル
2行目: DISH_NAME: 写真から判断した料理名
3行目以降: はてなブログにそのまま使えるHTML本文

本文には、写真から分かる料理の特徴、材料、作り方、仕事終わり向けの時短・節約ポイント、失敗しにくいポイント、料理と相性の良いキッチン用品紹介、まとめを含めてください。
商品紹介は「おすすめです」の羅列ではなく、料理中の具体的な困りごと→必要な機能→候補商品の順番で自然につなげてください。
不明な材料や分量は推測で断定しないでください。宣伝臭を強くせず、実際の単身赴任生活の記事らしい文章にしてください。
""".strip()


def call_model(api_key, model, payload):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(
        api_url + "?key=" + api_key,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(
                    f"Geminiから記事本文を取得できませんでした: "
                    f"{json.dumps(result, ensure_ascii=False)[:1000]}"
                ) from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in (401, 403):
                raise RuntimeError(
                    "Gemini無料APIキーの認証に失敗しました。無料枠のAPIキーを確認してください。"
                ) from exc
            if exc.code == 429:
                raise RuntimeError(
                    "Gemini無料枠の利用上限に達したため停止しました。課金へ切り替えず、後で再実行してください。"
                ) from exc
            if exc.code in RETRYABLE_HTTP_CODES and attempt < MAX_RETRIES:
                wait_seconds = 2 ** attempt
                print(f"Gemini {model}: HTTP {exc.code}。{wait_seconds}秒後に再試行します ({attempt}/{MAX_RETRIES - 1})")
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(
                f"Gemini APIエラー HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            if attempt < MAX_RETRIES:
                wait_seconds = 2 ** attempt
                print(f"Gemini {model}: 通信エラー。{wait_seconds}秒後に再試行します ({attempt}/{MAX_RETRIES - 1})")
                time.sleep(wait_seconds)
                continue
            raise RuntimeError(f"Gemini通信エラー: {exc}") from exc

    raise RuntimeError(f"Gemini {model} の呼び出しに失敗しました。")


def call_gemini(image_path):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEYが設定されていません。Google AI Studioの無料枠APIキーをGitHub Secretsへ登録してください。"
        )

    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    payload = {
        "contents": [{
            "parts": [
                {"text": build_prompt()},
                {
                    "inline_data": {
                        "mime_type": mime_type(image_path),
                        "data": image_data,
                    }
                },
            ]
        }],
        "generationConfig": {"maxOutputTokens": 5000},
    }

    errors = []
    for model in MODELS:
        try:
            print(f"Gemini無料枠モデルを使用: {model}")
            return call_model(api_key, model, payload)
        except RuntimeError as exc:
            message = str(exc)
            # 認証・利用上限・プロンプト等の恒久エラーは、別モデルへ無駄に切り替えない。
            if "HTTP 401" in message or "HTTP 403" in message or "HTTP 429" in message:
                raise
            errors.append(f"{model}: {message}")
            print(f"Gemini {model} が利用できないため、次の無料モデルを試します。")

    raise RuntimeError("Gemini無料枠モデルをすべて試しましたが記事生成に失敗しました。\n" + "\n".join(errors))


def parse_article(text):
    lines = text.splitlines()
    title, dish_name, body_start = "仕事終わりの簡単節約ごはん", "今日の一人暮らしごはん", 0
    for i, line in enumerate(lines[:5]):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "", 1).strip() or title
            body_start = max(body_start, i + 1)
        elif line.startswith("DISH_NAME:"):
            dish_name = line.replace("DISH_NAME:", "", 1).strip() or dish_name
            body_start = max(body_start, i + 1)
    body = "\n".join(lines[body_start:]).strip()
    if not body:
        raise RuntimeError("Geminiが空の記事本文を返しました。")
    return title, dish_name, body


image_path = find_image()
text = call_gemini(image_path)
title, dish_name, body = parse_article(text)
official_dish = os.environ.get("COLLECTION_DISH_NAME", "").strip()
if official_dish:
    dish_name = official_dish
Path("article_title.txt").write_text(title, encoding="utf-8")
Path("dish_name.txt").write_text(dish_name, encoding="utf-8")
Path("article_body.txt").write_text(body, encoding="utf-8")
print("Gemini無料枠による写真解析・記事生成完了")
print("料理:", dish_name)
print("タイトル:", title)
print("写真:", image_path)
