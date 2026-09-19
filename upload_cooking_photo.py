import base64
import hashlib
import json
import os
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _load_photo_metadata():
    path = Path("incoming/latest_photo.json")
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(base64.b64decode(raw).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        raise RuntimeError("incoming/latest_photo.json のメタデータを読み込めません。") from exc


def _verify_image(image_bytes, metadata):
    expected = str(metadata.get("sha256", "")).strip().lower()
    actual = hashlib.sha256(image_bytes).hexdigest().lower()
    if expected and expected != actual:
        raise RuntimeError(
            "写真データと料理写真コレクションのSHA-256が一致しません。"
            f" expected={expected} actual={actual}"
        )
    expected_bytes = metadata.get("bytes")
    if expected_bytes not in (None, ""):
        try:
            if int(expected_bytes) != len(image_bytes):
                raise RuntimeError(
                    "写真データのサイズとメタデータが一致しません。"
                    f" expected={expected_bytes} actual={len(image_bytes)}"
                )
        except (TypeError, ValueError) as exc:
            raise RuntimeError("写真メタデータのbytesが不正です。") from exc
    return actual


def find_input_photo():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    metadata = _load_photo_metadata()

    if explicit:
        path = Path(explicit)
        if not path.is_file() and not path.parts[:1] == ("images",):
            path = Path("images") / explicit
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            image_bytes = path.read_bytes()
            _verify_image(image_bytes, metadata)
            return path

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
                raw = raw.rstrip("=")
                raw += "=" * ((4 - len(raw) % 4) % 4)
                image_bytes = base64.b64decode(raw, validate=True)
            except Exception as exc:
                raise RuntimeError("incoming/latest_photo.b64 の画像データを復元できません。") from exc

        if not image_bytes:
            raise RuntimeError("incoming/latest_photo.b64 が空です。")

        _verify_image(image_bytes, metadata)

        restored = Path("images") / "latest_photo.jpg"
        restored.parent.mkdir(exist_ok=True)
        restored.write_bytes(image_bytes)
        print("料理写真コレクションの写真を復元しました:", restored)
        print("写真SHA-256:", hashlib.sha256(image_bytes).hexdigest())
        return restored

    incoming_jpg = Path("incoming/latest_photo.jpg")
    if incoming_jpg.is_file():
        try:
            import imghdr
            kind = imghdr.what(incoming_jpg)
        except Exception:
            kind = None
        if kind in {"jpeg", "png", "webp"} and incoming_jpg.stat().st_size > 1024:
            image_bytes = incoming_jpg.read_bytes()
            _verify_image(image_bytes, metadata)
            restored = Path("images") / "latest_photo.jpg"
            restored.parent.mkdir(exist_ok=True)
            shutil.copy2(incoming_jpg, restored)
            print("料理写真コレクションの実画像を使用します:", restored)
            return restored
        raise RuntimeError("incoming/latest_photo.jpg が実画像ではありません。プレースホルダーは禁止です。")

    raise RuntimeError("料理写真が見つかりません。料理写真コレクションから実画像を同期してください。")


def main():
    source = find_input_photo()
    metadata = _load_photo_metadata()

    dish_name = os.environ.get("COLLECTION_DISH_NAME", "").strip()
    if not dish_name:
        dish_name = str(metadata.get("dishName", "")).strip()
    if not dish_name:
        raise RuntimeError("料理名が入力されていません。料理写真コレクション登録時に料理名を必ず指定してください。")

    Path("collection_photo_name.txt").write_text(source.name, encoding="utf-8")
    Path("collection_dish_name.txt").write_text(dish_name, encoding="utf-8")

    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / source.name

    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    actual_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    Path("collection_photo_sha256.txt").write_text(actual_sha, encoding="utf-8")

    print("料理写真を画像処理フォルダへ準備しました:", destination)
    print("使用画像:", destination.name)
    print("登録料理名:", dish_name)
    print("使用画像SHA-256:", actual_sha)


if __name__ == "__main__":
    main()
