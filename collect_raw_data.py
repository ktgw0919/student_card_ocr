"""
フォルダ内画像から YomiToku raw_data を収集する開発用スクリプト。

出力先 (既定: raw_data_output/) は .gitignore 対象です。
個人情報を含む JSON を Git にコミットしないでください。
詳細: docs/PRIVACY.md
"""
import argparse
import asyncio
import json
from pathlib import Path

from ocr.yomitoku_impl import YomiTokuEngine


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="フォルダ内画像をOCRして raw_data を収集する簡易スクリプト"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="OCR対象画像が入ったフォルダ",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("raw_data_output"),
        help="raw_data JSONの出力先フォルダ（既定: raw_data_output）",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="サブフォルダ配下も再帰的に探索する",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help='YomiTokuの実行デバイス（例: "cpu", "cuda"）',
    )
    return parser.parse_args()


def collect_image_paths(input_dir: Path, recursive: bool) -> list[Path]:
    if recursive:
        candidates = input_dir.rglob("*")
    else:
        candidates = input_dir.glob("*")
    return sorted(
        p for p in candidates if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


async def run() -> None:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"入力フォルダが存在しません: {input_dir}")

    image_paths = collect_image_paths(input_dir, args.recursive)
    if not image_paths:
        print(f"対象画像が見つかりませんでした: {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    engine = YomiTokuEngine(device=args.device, debug_mode=False)

    success_count = 0
    error_count = 0
    errors: list[dict[str, str]] = []

    print(f"入力フォルダ: {input_dir}")
    print(f"出力フォルダ: {output_dir}")
    print(f"対象画像数: {len(image_paths)}")

    for idx, image_path in enumerate(image_paths, start=1):
        print(f"[{idx}/{len(image_paths)}] OCR実行: {image_path.name}")
        try:
            result = await engine.extract(str(image_path))
            raw_data = result.get("raw_data", {})

            output_path = output_dir / f"{image_path.stem}.raw.json"
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            success_count += 1
        except Exception as exc:
            error_count += 1
            errors.append({"image": str(image_path), "error": str(exc)})
            print(f"  -> エラー: {exc}")

    if errors:
        error_log_path = output_dir / "_errors.json"
        with error_log_path.open("w", encoding="utf-8") as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
        print(f"エラーログを保存しました: {error_log_path}")

    print("\n--- 完了 ---")
    print(f"成功: {success_count} 件")
    print(f"失敗: {error_count} 件")


if __name__ == "__main__":
    asyncio.run(run())
