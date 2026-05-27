"""Phase 3: ヘルスチェック・認証・画像検証・レート制限・CORS のテスト。"""

from contextlib import asynccontextmanager, contextmanager
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from core.config import Settings
from core.rate_limit import RateLimiter
from core.upload import validate_image_bytes
from main import create_app

_SAMPLE_SERVICE_RESPONSE = {
    "status": "success",
    "qr_status": "valid",
    "message": "ok",
    "data": {
        "engine": "YomiToku",
        "structured": {
            "document_type": "student_card",
            "schema_id": "student_card_jp",
            "extractor_name": "StudentCardJpExtractor",
            "routing_score": 1.0,
            "fields": {
                "student_id": {
                    "value": "X00XX000",
                    "status": "found",
                },
            },
            "warnings": [],
        },
    },
}


def _make_jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="white").save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="white").save(buf, format="PNG")
    return buf.getvalue()


@contextmanager
def _test_client(settings: Settings, service_response: dict | None = None):
    mock_service = MagicMock()
    mock_service.process = AsyncMock(
        return_value=service_response or _SAMPLE_SERVICE_RESPONSE
    )

    @asynccontextmanager
    async def test_lifespan(app_instance):
        app_instance.state.settings = settings
        app_instance.state.rate_limiter = RateLimiter(
            max_calls=settings.rate_limit_per_minute,
            window_seconds=60,
        )
        app_instance.state.service = mock_service
        yield

    test_app = create_app(settings)
    test_app.router.lifespan_context = test_lifespan
    with TestClient(test_app) as client:
        yield client


class TestUploadValidation:
    def test_accepts_jpeg(self):
        suffix = validate_image_bytes(_make_jpeg_bytes(), max_bytes=1_000_000)
        assert suffix == ".jpg"

    def test_accepts_png(self):
        suffix = validate_image_bytes(_make_png_bytes(), max_bytes=1_000_000)
        assert suffix == ".png"

    def test_rejects_non_image(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_image_bytes(b"not an image", max_bytes=1_000_000)
        assert exc_info.value.status_code == 400


class TestHealthEndpoint:
    def test_health_no_auth_required(self):
        with _test_client(Settings(rate_limit_per_minute=0)) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestApiKeyAuth:
    def test_verify_requires_api_key_when_enabled(self, jpeg_bytes):
        with _test_client(
            Settings(require_api_key=True, api_key="secret", rate_limit_per_minute=0)
        ) as client:
            response = client.post(
                "/verify",
                files={"file": ("card.jpg", jpeg_bytes, "image/jpeg")},
            )
        assert response.status_code == 401

    def test_verify_with_valid_api_key(self, jpeg_bytes):
        with _test_client(
            Settings(
                require_api_key=True,
                api_key="secret",
                allow_include_raw=True,
                rate_limit_per_minute=0,
            )
        ) as client:
            response = client.post(
                "/verify",
                files={"file": ("card.jpg", jpeg_bytes, "image/jpeg")},
                headers={"X-API-Key": "secret"},
            )
        assert response.status_code == 200


class TestRateLimit:
    def test_returns_429_when_exceeded(self, jpeg_bytes):
        with _test_client(
            Settings(
                require_api_key=False,
                rate_limit_per_minute=2,
                allow_include_raw=True,
            )
        ) as client:
            files = {"file": ("card.jpg", jpeg_bytes, "image/jpeg")}
            assert client.post("/verify", files=files).status_code == 200
            assert client.post("/verify", files=files).status_code == 200
            assert client.post("/verify", files=files).status_code == 429


class TestImageValidationEndpoint:
    def test_rejects_invalid_bytes(self):
        with _test_client(Settings(rate_limit_per_minute=0)) as client:
            response = client.post(
                "/verify",
                files={"file": ("fake.jpg", b"not-image", "image/jpeg")},
            )
        assert response.status_code == 400


class TestCors:
    def test_cors_header_on_preflight(self):
        with _test_client(
            Settings(
                cors_origins="http://localhost:3000",
                rate_limit_per_minute=0,
            )
        ) as client:
            response = client.options(
                "/verify",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                },
            )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == (
            "http://localhost:3000"
        )


class TestAuthConfigValidation:
    def test_raises_when_api_key_required_but_missing(self):
        with pytest.raises(RuntimeError, match="API_KEY"):
            create_app(Settings(require_api_key=True, api_key=None))


class TestWebUi:
    def test_index_returns_html(self):
        with _test_client(Settings(rate_limit_per_minute=0)) as client:
            response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "学生証 OCR" in response.text

    def test_web_static_assets(self):
        with _test_client(Settings(rate_limit_per_minute=0)) as client:
            js = client.get("/web/app.js")
            css = client.get("/web/style.css")
        assert js.status_code == 200
        assert "submitVerify" in js.text or "VerifyResponse" in js.text
        assert css.status_code == 200
