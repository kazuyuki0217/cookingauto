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

    candidates = []
    for root in (Path("images"), Path(".")):
        if not root.exists():
            continue
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                candidates.append(p)

    if candidates:
        return max(candidates, key=lambda p: (p.stat().st_mtime, str(p)))

    # 料理写真コレクションから同期された incoming/latest_photo.b64 を
    # 実画像に復元して、この後の既存パイプラインへ渡す。
    incoming_b64 = Path("incoming/latest_photo.b64")
    if incoming_b64.is_file():
        raw = incoming_b64.read_text(encoding="utf-8").strip()
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(raw, validate=True)
        except Exception as exc:
            raise RuntimeError("incoming/latest_photo.b64 の画像データを復元できません。") from exc

        if not image_bytes:
            raise RuntimeError("incoming/latest_photo.b64 が空です。")

        restored = Path("images") / "latest_photo.jpg"
        restored.parent.mkdir(exist_ok=True)
        restored.write_bytes(image_bytes)
        print("料理写真コレクションの最新写真を復元しました:", restored)
        return restored

    raise RuntimeError(
        "料理写真が見つかりません。COOKING_IMAGE_FILEを指定するか、"
        "images/ または incoming/latest_photo.b64 を用意してください。"
    )


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
