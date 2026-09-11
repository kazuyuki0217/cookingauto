import os
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_input_photo():
    explicit = os.environ.get("COOKING_IMAGE_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path

    candidates = []
    for root in (Path("."), Path("images")):
        if root.exists():
            candidates.extend(
                p for p in root.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: str(p))[0]


def main():
    source = find_input_photo()
    if source is None:
        raise RuntimeError("料理写真が見つかりません。COOKING_IMAGE_FILEを指定するか、images/ に画像を配置してください。")

    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / source.name
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    print("料理写真を画像処理フォルダへ準備しました:", destination)


if __name__ == "__main__":
    main()
