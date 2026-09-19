import base64
import os
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_input_photo():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_file() and not path.parts[:1] == ("images",):
            path = Path("images") / explicit
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path
        raise RuntimeError(f"指定された料理写真が見つかりません: {explicit}")

    incoming_b64 = Path("incoming/latest_photo.b64")
    if incoming_b64.is_file():
        raw_bytes = incoming_b64.read_bytes()
        try:
            raw = raw_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            image_bytes = raw_bytes
        else:
            if raw.startswith("data:") and "," in raw:
                raw = raw.split(",", 1)[1]
            raw = "".join(raw.split())
            try:
                image_bytes = base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise RuntimeError("incoming/latest_photo.b64 の画像データを復元できません。") from exc

        if not image_bytes:
            raise RuntimeError("incoming/latest_photo.b64 が空です。")

        restored = Path("images") / "latest_photo.jpg"
        restored.parent.mkdir(exist_ok=True)
        restored.write_bytes(image_bytes)
        print("料理写真コレクションの写真を復元しました:", restored)
        return restored

    # latest_photo.jpg は実画像でなければ使用しない。
    incoming_jpg = Path("incoming/latest_photo.jpg")
    if incoming_jpg.is_file():
        try:
            import imghdr
            kind = imghdr.what(incoming_jpg)
        except Exception:
            kind = None
        if kind in {"jpeg", "png", "webp"} and incoming_jpg.stat().st_size > 1024:
            restored = Path("images") / "latest_photo.jpg"
            restored.parent.mkdir(exist_ok=True)
            shutil.copy2(incoming_jpg, restored)
            print("料理写真コレクションの実画像を使用します:", restored)
            return restored
        raise RuntimeError("incoming/latest_photo.jpg が実画像ではありません。プレースホルダーは禁止です。")

    raise RuntimeError(
        "料理写真が見つかりません。料理写真コレクションから実画像を同期してください。"
    )


def main():
    source = find_input_photo()

    dish_name = os.environ.get("COLLECTION_DISH_NAME", "").strip()
    if not dish_name:
        raise RuntimeError(
            "料理名が入力されていません。料理写真コレクション登録時に料理名を必ず指定してください。"
        )

    # 写真と料理名を同じ処理単位として保存する。
    Path("collection_photo_name.txt").write_text(source.name, encoding="utf-8")
    Path("collection_dish_name.txt").write_text(dish_name, encoding="utf-8")

    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / source.name

    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    print("料理写真を画像処理フォルダへ準備しました:", destination)
    print("使用画像:", destination.name)
    print("登録料理名:", dish_name)


if __name__ == "__main__":
    main()
