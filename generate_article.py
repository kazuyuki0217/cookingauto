from pathlib import Path
import html
import os

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# 完全無料運用のため、外部AI API・APIキー・従量課金は使用しません。
# 写真ファイル名に料理名が含まれている場合は、それを利用します。
# 料理名が分からない写真でも後工程を止めないよう、汎用記事へフォールバックします。
DISH_KEYWORDS = [
    "豚にんにくステーキ", "豚肉にんにく", "豚の生姜焼き", "生姜焼き",
    "ささみ柚子胡椒", "ささみ", "無限キャベツ", "豚ハラミ", "ハラミ",
    "豆腐", "バジルチキン", "厚揚げの揚げだし豆腐", "揚げだし豆腐",
    "目玉焼きベーコン", "ベーコン目玉焼き", "厚揚げ"
]


def find_image():
    explicit_text = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit_text:
        explicit = Path(explicit_text)
        if explicit.is_file() and explicit.suffix.lower() in IMAGE_EXTENSIONS:
            return explicit

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


def detect_dish(image_path):
    name = image_path.stem.replace("_", " ").replace("-", " ")
    for keyword in DISH_KEYWORDS:
        if keyword in name:
            return keyword
    return "今日の一人暮らしごはん"


def build_article(dish):
    safe_dish = html.escape(dish)
    if dish == "今日の一人暮らしごはん":
        title = "仕事終わりに作った一人暮らしごはん｜頑張りすぎない自炊のリアル"
        intro = "仕事が終わってから作った、今日の一人暮らしごはんです。毎日の自炊は、凝った料理を作るよりも、無理なく続けられることを大切にしています。"
        material = "写真だけでは材料や分量を正確に判断できないため、ここでは断定せず、実際に使った食材を確認してから調整します。"
    else:
        title = f"{dish}｜仕事終わりでも作れる簡単な一人暮らしごはん"
        intro = f"今回作ったのは{safe_dish}。仕事終わりでも無理なく作れるよう、できるだけ手間を増やさないことを意識しました。"
        material = f"主な材料は{safe_dish}に使う食材です。写真だけでは分からない分量は、実際の調理量に合わせて調整してください。"

    body = f"""<p>{intro}</p>
<p>料理写真を見返すと、特別な日だけでなく、仕事から帰って普通に作ったごはんにも「これなら自分でも作れそう」と思える良さがあります。</p>
<h2>{safe_dish}の材料</h2>
<p>{material}</p>
<ul>
<li>主な食材：料理に合わせた食材</li>
<li>調味料：普段使っているものを中心に調整</li>
<li>油：必要量</li>
</ul>
<h2>作り方</h2>
<ol>
<li>食材を食べやすい大きさに準備します。</li>
<li>フライパンや鍋など、使いやすい調理器具で火を通します。</li>
<li>味付けをして、火が通ったことを確認します。</li>
<li>盛り付ければ完成です。</li>
</ol>
<h2>仕事終わりの自炊で意識していること</h2>
<p>帰宅後の料理は、最初から完璧を目指すと続きません。洗い物を増やさない、調理時間を短くする、余った食材を次の料理にも使う。この3つを意識すると、自炊の負担がかなり減ります。</p>
<h2>料理を楽にする道具</h2>
<p>仕事終わりに料理をするなら、食材だけでなく「切る・焼く・片付ける」を楽にしてくれる道具も重要です。特にフライパンや保存容器など、使用頻度の高いものは、使いやすいものを選ぶだけで毎日の負担を減らせます。</p>
<p>今回の料理をきっかけに、普段使っている調理道具も少しずつ見直していきます。</p>
<h2>まとめ</h2>
<p>一人暮らしの自炊は、頑張りすぎず続けられることが一番。仕事終わりでも作れる簡単な料理を少しずつ増やして、食費と手間の両方を抑えていきたいと思います。</p>"""
    return title, dish, body


image_path = find_image()
dish = detect_dish(image_path)
title, dish_name, body = build_article(dish)

Path("article_title.txt").write_text(title, encoding="utf-8")
Path("dish_name.txt").write_text(dish_name, encoding="utf-8")
Path("article_body.txt").write_text(body, encoding="utf-8")

print("無料記事生成完了")
print("料理:", dish_name)
print("タイトル:", title)
print("写真:", image_path)
