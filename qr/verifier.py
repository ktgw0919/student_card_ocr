import asyncio
import logging
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
from playwright.async_api import (
    Browser,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

logger = logging.getLogger(__name__)


def _redact_url(url: str) -> str:
    """ログ用: クエリ・フラグメントを除いた URL を返す。"""
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return "<redacted>"


class QRStatus(Enum):
    VALID = "valid"
    NOT_FOUND = "not_found"
    UNVERIFIABLE = "unverifiable"


class QRVerifier:
    def __init__(self, debug_mode: bool = False, browser: Browser | None = None):
        self.debug_mode = debug_mode
        self.browser = browser

    def _resize_image(self, img, max_size=1024):
        """画像が大きすぎる場合、アスペクト比を維持して縮小する"""
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            return cv2.resize(
                img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        return img

    def _process_image_and_find_qr(self, image_path: str):
        """
        同期的に実行される重い画像処理とQRコード抽出。
        イベントループをブロックしないよう、必ず to_thread 経由で呼び出される。
        """
        original_img = cv2.imread(image_path)
        if original_img is None:
            return None, None, None, ""

        img = self._resize_image(original_img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        strategies = [
            ("グレースケール", gray),
            ("コントラスト強調 (CLAHE)", clahe.apply(gray)),
            (
                "適応的2値化 (標準)",
                cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 2
                ),
            ),
            (
                "適応的2値化 (粗め)",
                cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 2
                ),
            ),
            (
                "大津の2値化 (ぼかし後)",
                cv2.threshold(
                    cv2.GaussianBlur(gray, (5, 5), 0),
                    0,
                    255,
                    cv2.THRESH_BINARY + cv2.THRESH_OTSU,
                )[1],
            ),
        ]

        decoded_objects = []
        for name, processed_img in strategies:
            objects = decode(processed_img, symbols=[ZBarSymbol.QRCODE])
            if objects:
                decoded_objects = objects
                logger.debug(
                    "QR detected with strategy %s (count=%d)",
                    name,
                    len(decoded_objects),
                )
                break

        target_obj = None
        target_url = ""
        for obj in decoded_objects:
            qr_url = obj.data.decode("utf-8")
            if "app.omu.ac.jp/verify-qr" in qr_url:
                target_obj = obj
                target_url = qr_url
                break

        return img, decoded_objects, target_obj, target_url

    async def verify_digital_id(self, image_path: str) -> QRStatus:
        """非同期でQRコードの読み取りと真偽判定を行う"""

        # 1. OpenCVとpyzbarの重いCPUバウンド処理を別スレッドにオフロード
        img, decoded_objects, target_obj, target_url = await asyncio.to_thread(
            self._process_image_and_find_qr, image_path
        )

        if img is None:
            logger.warning("Failed to read image for QR extraction")
            return QRStatus.NOT_FOUND

        if not decoded_objects:
            logger.info("No QR code detected after all preprocessing strategies")
            if self.debug_mode:
                await asyncio.to_thread(
                    self._save_debug_image, img, image_path, [], None
                )
            return QRStatus.NOT_FOUND

        status = QRStatus.UNVERIFIABLE

        # 2. 正規ドメインを見つけたら非同期のPlaywrightによる真偽判定へ
        if target_url:
            status = await self._run_playwright_verification(target_url)

        # 3. デバッグ画像の保存処理もI/Oバウンドなためオフロード
        if self.debug_mode:
            await asyncio.to_thread(
                self._save_debug_image, img, image_path, decoded_objects, target_obj
            )

        return status

    def _save_debug_image(self, img, image_path: str, all_objects: list, target_obj):
        """QRコードの認識範囲を描画して保存する（to_threadで呼ばれる）"""
        output_dir = Path("debug_output")
        output_dir.mkdir(exist_ok=True)
        base_name = Path(image_path).stem

        for obj in all_objects:
            points = obj.polygon
            if len(points) == 4:
                pts = np.array([(p.x, p.y) for p in points], np.int32).reshape(
                    (-1, 1, 2)
                )
                cv2.polylines(img, [pts], True, (255, 0, 0), 2)

        if target_obj:
            points = target_obj.polygon
            if len(points) == 4:
                pts = np.array([(p.x, p.y) for p in points], np.int32).reshape(
                    (-1, 1, 2)
                )
                cv2.polylines(img, [pts], True, (0, 255, 0), 4)

        output_path = output_dir / f"{base_name}_qr_vis.jpg"
        cv2.imwrite(str(output_path), img)
        logger.debug("Saved QR debug image: %s", output_path)

    async def _run_playwright_verification(self, url: str) -> QRStatus:
        """非同期版Playwrightでページの状態を判定する内部メソッド"""
        logger.info("Verifying QR via %s", _redact_url(url))

        # FastAPIライフサイクルで共有ブラウザが注入されている場合はそれを使用する。
        # 注入されていない実行環境でも動作できるよう、フォールバックとして都度起動も残す。
        if self.browser is not None:
            return await self._verify_with_browser(self.browser, url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                return await self._verify_with_browser(browser, url)
            finally:
                await browser.close()

    async def _verify_with_browser(self, browser: Browser, url: str) -> QRStatus:
        page = await browser.new_page()
        try:
            await page.goto(url)

            # 判定用ロケーター（市立大学・府立大学・公立大学をサポート）
            success_loc_city = page.locator("text=大阪市立大学の学生であることを証明する")
            success_loc_prefectural = page.locator(
                "text=大阪府立大学の学生であることを証明する"
            )
            success_loc_public = page.locator(
                "text=大阪公立大学の学生であることを証明する"
            )
            error_loc = page.locator("text=QRコードが無効です")

            try:
                # どれかが表示されるまで待機（async版）
                await (
                    success_loc_city.or_(success_loc_prefectural)
                    .or_(success_loc_public)
                    .or_(error_loc)
                ).wait_for(state="visible", timeout=5000)
            except PlaywrightTimeoutError:
                logger.warning("Playwright verification timed out")
                return QRStatus.UNVERIFIABLE

            # JS実行後の最終的なHTMLを取得
            html_text = await page.content()

            if (
                "大阪市立大学の学生であることを証明する" in html_text
                or "大阪府立大学の学生であることを証明する" in html_text
                or "大阪公立大学の学生であることを証明する" in html_text
            ):
                logger.info("QR verification succeeded")
                return QRStatus.VALID
            if "QRコードが無効です" in html_text or "エラーが発生しました" in html_text:
                logger.info("QR verification failed: invalid or expired")
                return QRStatus.UNVERIFIABLE

            logger.warning("QR verification failed: unknown page structure")
            return QRStatus.UNVERIFIABLE
        except Exception:
            logger.exception("Browser error during QR verification")
            return QRStatus.UNVERIFIABLE
        finally:
            await page.close()
