import pytest
from pathlib import Path
from qr.verifier import QRVerifier, QRStatus

TEST_IMAGE_DIR = Path(__file__).parent / "test_images"
STUDENT_CARD_IMAGES = [
    TEST_IMAGE_DIR / "test_student_card_01.jpg",
    TEST_IMAGE_DIR / "test_student_card_02.jpg",
]
LOCAL_IMAGE_DIR = TEST_IMAGE_DIR / "local"


def _require_student_card_image(path: Path) -> Path:
    if not path.exists():
        pytest.skip(f"テスト画像がありません: {path}")
    return path


def _local_image(name: str) -> Path | None:
    path = LOCAL_IMAGE_DIR / name
    return path if path.exists() else None


class TestQRVerifier:
    """QR検証のテスト（Git管理画像 + ローカル任意画像）"""

    @pytest.fixture
    def verifier(self):
        return QRVerifier(debug_mode=False)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("image_path", STUDENT_CARD_IMAGES)
    async def test_student_card_image_processing(self, verifier, image_path: Path):
        """匿名化サンプル学生証画像で処理が完了すること"""
        path = _require_student_card_image(image_path)
        status = await verifier.verify_digital_id(str(path))
        assert status in (QRStatus.VALID, QRStatus.NOT_FOUND, QRStatus.UNVERIFIABLE)

    @pytest.mark.asyncio
    async def test_local_no_qr_image(self, verifier):
        """ローカル配置時のみ: QRなし画像"""
        path = _local_image("no_qr.jpg")
        if path is None:
            pytest.skip("local/no_qr.jpg がありません（任意テスト）")
        status = await verifier.verify_digital_id(str(path))
        assert status == QRStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_local_unverifiable_qr(self, verifier):
        """ローカル配置時のみ: 対象外QR"""
        path = _local_image("qr_invalid.jpg")
        if path is None:
            pytest.skip("local/qr_invalid.jpg がありません（任意テスト）")
        status = await verifier.verify_digital_id(str(path))
        assert status == QRStatus.UNVERIFIABLE

    @pytest.mark.asyncio
    async def test_local_valid_student_id(self, verifier):
        """ローカル配置時のみ: 正規QR（実通信）"""
        path = _local_image("qr_valid.jpg")
        if path is None:
            pytest.skip("local/qr_valid.jpg がありません（任意テスト）")
        status = await verifier.verify_digital_id(str(path))
        assert status in (QRStatus.VALID, QRStatus.UNVERIFIABLE)

    @pytest.mark.asyncio
    async def test_student_card_debug_visualization(self):
        """学生証サンプル画像でデバッグ出力が生成されること"""
        path = _require_student_card_image(STUDENT_CARD_IMAGES[0])
        verifier = QRVerifier(debug_mode=True)
        await verifier.verify_digital_id(str(path))

        expected_output = Path("debug_output") / f"{path.stem}_qr_vis.jpg"
        assert expected_output.exists(), "デバッグ画像が生成されていません"
