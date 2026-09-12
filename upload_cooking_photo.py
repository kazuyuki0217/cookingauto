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

    candidates = []
    for root in (Path("images"), Path(".")):
        if not root.exists():
            continue
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                candidates.append(p)

    if not candidates:
        raise RuntimeError("料理写真が見つかりません。COOKING_IMAGE_FILEを指定するか、images/ に画像を配置してください。")

    return max(candidates, key=lambda p: (p.stat().st_mtime, str(p)))


def main():
    source = find_input_photo()
    output_dir = Path("images")
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / source.name

    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    print("料理写真を画像処理フォルダへ準備しました:", destination)
    print("使用画像:", destination.name)


if __name__ == "__main__":
    main()
