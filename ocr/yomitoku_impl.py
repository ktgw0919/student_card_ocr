import cv2
import tempfile
import json
import asyncio
from pathlib import Path
from typing import Dict, Any
from ocr.base import BaseOCREngine
from yomitoku import DocumentAnalyzer


class YomiTokuEngine(BaseOCREngine):
    def __init__(self, device: str = "cpu", debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.device = device
        # YomiTokuのDocumentAnalyzerを初期化
        # GPUが使えるPCの場合は device="cuda" に変更
        # debug_mdoe が False の場合、 visualize=False にすることで画像描画処理をスキップし高速化
        self.analyzer = DocumentAnalyzer(
            visualize=self.debug_mode, device=device, ignore_ruby=True
        )

    async def extract(self, image_path: str) -> Dict[str, Any]:
        """非同期で OCR を実行し、抽出結果を返す"""

        # 1. 画像の読み込み
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"画像を読み込めませんでした: {image_path}")

        # 2. YomiToku による推論の実行
        try:
            # analyzer(img) は数秒かかる同期処理なので、to_thread で非同期化
            results, ocr_vis, layout_vis = await asyncio.to_thread(self.analyzer, img)
        except Exception as e:
            raise RuntimeError(f"YomiTokuでの推論中にエラーが発生しました: {e}")

        # 3. YomiToku の結果を JSON に変換
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "result.json"
            results.to_json(str(tmp_path), img=img)
            with open(tmp_path, "r", encoding="utf-8") as f:
                parsed_data = json.load(f)

        # 4. デバッグ時処理
        # 画像と JSON をファイルに書き出す
        if self.debug_mode:
            await asyncio.to_thread(
                self._save_debug_files, image_path, parsed_data, ocr_vis, layout_vis
            )

        # 5. 整形して返す
        return {
            "engine": "YomiToku",
            "raw_data": parsed_data,
        }

    def _save_debug_files(self, original_path: str, data: dict, ocr_vis, layout_vis):
        """デバッグ用の出力ファイルを保存する内部メソッド"""
        # 出力先ディレクトリを作成 (プロジェクトルートの debug_output フォルダ)
        output_dir = Path("debug_output")
        output_dir.mkdir(exist_ok=True)

        base_name = Path(original_path).stem

        # 生の JSON データを保存
        json_path = output_dir / f"{base_name}_result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # OCR のバウンディングボックス付き画像を保存
        if ocr_vis is not None:
            cv2.imwrite(str(output_dir / f"{base_name}_ocr_vis.jpg"), ocr_vis)

        # レイアウトの認識枠付き画像を保存
        if layout_vis is not None:
            cv2.imwrite(str(output_dir / f"{base_name}_layout_vis.jpg"), layout_vis)

        print(f"[DEBUG] デバッグファイルを {output_dir} に保存しました。")
