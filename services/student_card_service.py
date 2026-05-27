from ocr.postprocess import process_raw_data
from ocr.yomitoku_impl import YomiTokuEngine
from models.schemas import OverallStatus
from qr.verifier import QRVerifier, QRStatus


class StudentIDService:
    def __init__(
        self,
        qr_verifier: QRVerifier | None = None,
        ocr_engine: YomiTokuEngine | None = None,
    ):
        self.qr_verifier = qr_verifier or QRVerifier()
        self.ocr_engine = ocr_engine or YomiTokuEngine()

    async def process(self, image_path: str) -> dict:
        """
        デジタル学生証の真偽判定とOCR抽出を統合して実行する
        """
        # 1. QRコードによる真偽判定
        qr_status = await self.qr_verifier.verify_digital_id(image_path)

        # Enumの状態に応じたステータスとメッセージの決定
        if qr_status == QRStatus.VALID:
            overall_status = OverallStatus.SUCCESS
            message = "真正性が確認されました"
        elif qr_status == QRStatus.NOT_FOUND:
            overall_status = OverallStatus.WARNING
            message = "QRコードが検出されませんでした。テキスト抽出のみ実行します。"
        else:  # QRStatus.UNVERIFIABLE
            overall_status = OverallStatus.ERROR
            message = "無効なQRコード、または偽造の疑いがあります。"

        # 2. 本物・偽物・検出不能に関わらず、必ずOCR処理を実行（フォールバック）
        # ocr_engine.extract は定義元で async def となっているため、直接 await して呼び出す
        try:
            ocr_result = await self.ocr_engine.extract(image_path)
            if "raw_data" in ocr_result:
                ocr_result["structured"] = process_raw_data(ocr_result["raw_data"])
        except Exception as e:
            # OCR自体がクラッシュした場合のフェイルセーフ
            ocr_result = {"error": str(e)}
            overall_status = OverallStatus.ERROR
            message += " OCRの実行中にエラーが発生しました。"

        # 3. 結果を統合して返す（API 層で VerifyResponse に変換）
        return {
            "status": overall_status.value,
            "qr_status": qr_status.value,
            "message": message,
            "data": ocr_result,
        }
