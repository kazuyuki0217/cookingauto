import os
import shutil
from pathlib import Path

# This step deliberately does not invent or expose a fake public URL.
# It prepares the supplied cooking photo for the repository's image pipeline.
# A later hosting step can publish the file and provide COOKING_IMAGE_URL.

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_input_photo():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if path.exists() and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path

    for path in sorted(Path(".").iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path
    return None


def main():
    source = find_input_photo()
    if source is None:
        raise RuntimeError("料理写真が見つかりません。COOKING_IMAGE_FILEを指定するか、画像を配置してください。")

    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / source.name
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    print("料理写真を画像処理フォルダへ準備しました:", destination)
    print("次の公開処理でCOOKING_IMAGE_URLを生成します。")


if __name__ == "__main__":
    main()
