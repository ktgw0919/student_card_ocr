"""API レスポンスの PII サニタイズ・Pydantic スキーマのテスト。"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from core.config import Settings
from core.rate_limit import RateLimiter
from main import create_app
from models.schemas import (
    FieldStatus,
    OcrDataOut,
    OverallStatus,
    QrStatus,
    VerifyResponse,
)
from services.response_builder import (
    build_verify_response,
    resolve_include_flags,
    sanitize_verify_payload,
)

_SAMPLE_SERVICE_RESPONSE = {
    "status": "success",
    "qr_status": "valid",
    "message": "ok",
    "data": {
        "engine": "YomiToku",
        "raw_data": {"paragraphs": [{"contents": "学籍番号 SECRET"}]},
        "structured": {
            "document_type": "student_card",
            "schema_id": "student_card_jp",
            "issuer_hint": "サンプル大学",
            "extractor_name": "StudentCardJpExtractor",
            "routing_score": 1.0,
            "confidence": 1.0,
            "fields": {
                "student_id": {
                    "value": "X00XX000",
                    "normalized_value": "X00XX000",
                    "source_text": "学籍番号 X00XX000",
                    "status": "found",
                    "confidence": 0.9,
                },
            },
            "warnings": [],
        },
    },
}


class TestResolveIncludeFlags:
    def test_defaults_exclude_raw_and_source(self):
        settings = Settings()
        raw, source, err = resolve_include_flags(
            settings, include_raw=None, include_source_text=None
        )
        assert raw is False
        assert source is False
        assert err is None

    def test_include_raw_forbidden_when_not_allowed(self):
        settings = Settings(allow_include_raw=False)
        _, _, err = resolve_include_flags(
            settings, include_raw=True, include_source_text=None
        )
        assert err is not None

    def test_include_raw_allowed_in_dev(self):
        settings = Settings(allow_include_raw=True, include_raw_default=False)
        raw, _, err = resolve_include_flags(
            settings, include_raw=True, include_source_text=None
        )
        assert raw is True
        assert err is None


class TestSanitizeVerifyPayload:
    def test_strips_raw_data_by_default(self):
        out = sanitize_verify_payload(
            _SAMPLE_SERVICE_RESPONSE,
            include_raw=False,
            include_source_text=False,
            debug_mode=False,
        )
        assert "raw_data" not in out["data"]
        assert out["data"]["structured"]["fields"]["student_id"]["value"] == "X00XX000"
        assert "source_text" not in out["data"]["structured"]["fields"]["student_id"]

    def test_keeps_raw_data_when_requested(self):
        out = sanitize_verify_payload(
            _SAMPLE_SERVICE_RESPONSE,
            include_raw=True,
            include_source_text=False,
            debug_mode=False,
        )
        assert "raw_data" in out["data"]

    def test_keeps_source_text_when_requested(self):
        out = sanitize_verify_payload(
            _SAMPLE_SERVICE_RESPONSE,
            include_raw=False,
            include_source_text=True,
            debug_mode=False,
        )
        assert (
            out["data"]["structured"]["fields"]["student_id"]["source_text"]
            == "学籍番号 X00XX000"
        )

    def test_generic_ocr_error_when_not_debug(self):
        payload = {
            "status": "error",
            "qr_status": "not_found",
            "message": "fail",
            "data": {"error": "Internal YomiToku stack trace"},
        }
        out = sanitize_verify_payload(
            payload,
            include_raw=False,
            include_source_text=False,
            debug_mode=False,
        )
        assert out["data"]["error"] == "画像のOCR処理に失敗しました。"
        assert "YomiToku" not in out["data"]["error"]

    def test_preserves_ocr_error_in_debug_mode(self):
        payload = {
            "status": "error",
            "qr_status": "not_found",
            "message": "fail",
            "data": {"error": "detailed failure"},
        }
        out = sanitize_verify_payload(
            payload,
            include_raw=False,
            include_source_text=False,
            debug_mode=True,
        )
        assert out["data"]["error"] == "detailed failure"

    def test_does_not_mutate_original(self):
        sanitize_verify_payload(
            _SAMPLE_SERVICE_RESPONSE,
            include_raw=False,
            include_source_text=False,
            debug_mode=False,
        )
        assert "raw_data" in _SAMPLE_SERVICE_RESPONSE["data"]


class TestBuildVerifyResponse:
    def test_returns_typed_model(self):
        response = build_verify_response(
            _SAMPLE_SERVICE_RESPONSE,
            include_raw=False,
            include_source_text=False,
            debug_mode=False,
        )
        assert isinstance(response, VerifyResponse)
        assert response.status == OverallStatus.SUCCESS
        assert response.qr_status == QrStatus.VALID
        assert response.data is not None
        assert response.data.engine == "YomiToku"
        assert response.data.raw_data is None
        field = response.data.structured.fields["student_id"]
        assert field.value == "X00XX000"
        assert field.status == FieldStatus.FOUND
        assert field.source_text is None

    def test_ocr_error_only_data(self):
        payload = {
            "status": "error",
            "qr_status": "unverifiable",
            "message": "failed",
            "data": {"error": "boom"},
        }
        response = build_verify_response(
            payload,
            include_raw=False,
            include_source_text=False,
            debug_mode=True,
        )
        assert response.data == OcrDataOut(error="boom")
        assert response.data.engine is None

    def test_invalid_status_raises(self):
        bad = {**_SAMPLE_SERVICE_RESPONSE, "status": "invalid"}
        with pytest.raises(ValidationError):
            build_verify_response(
                bad,
                include_raw=False,
                include_source_text=False,
                debug_mode=False,
            )


class TestOpenApiSchema:
    def test_verify_route_uses_verify_response(self):
        openapi = create_app(Settings(rate_limit_per_minute=0)).openapi()
        verify_post = openapi["paths"]["/verify"]["post"]
        ref = verify_post["responses"]["200"]["content"]["application/json"]["schema"]
        assert ref["$ref"] == "#/components/schemas/VerifyResponse"

    def test_components_include_enums(self):
        schemas = create_app(Settings(rate_limit_per_minute=0)).openapi()[
            "components"
        ]["schemas"]
        assert "OverallStatus" in schemas
        assert "QrStatus" in schemas
        assert "FieldStatus" in schemas


@pytest.fixture
def client():
    """Playwright を起動せず process をモックした TestClient。"""
    mock_service = MagicMock()
    mock_service.process = AsyncMock(return_value=_SAMPLE_SERVICE_RESPONSE)
    settings = Settings(allow_include_raw=True, rate_limit_per_minute=0)

    @asynccontextmanager
    async def test_lifespan(app_instance):
        app_instance.state.settings = settings
        app_instance.state.rate_limiter = RateLimiter(max_calls=0, window_seconds=60)
        app_instance.state.service = mock_service
        yield

    test_app = create_app(settings)
    test_app.router.lifespan_context = test_lifespan

    with TestClient(test_app) as test_client:
        yield test_client


def test_verify_endpoint_omits_raw_data_by_default(client, jpeg_bytes):
    response = client.post(
        "/verify",
        files={"file": ("card.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["qr_status"] == "valid"
    assert "raw_data" not in body.get("data", {})
    assert "source_text" not in body["data"]["structured"]["fields"]["student_id"]


def test_verify_include_raw_query(client, jpeg_bytes):
    response = client.post(
        "/verify?include_raw=true",
        files={"file": ("card.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    assert "raw_data" in response.json()["data"]


def test_verify_include_raw_forbidden(client, jpeg_bytes):
    client.app.state.settings = Settings(allow_include_raw=False, rate_limit_per_minute=0)
    response = client.post(
        "/verify?include_raw=true",
        files={"file": ("card.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 403


def test_verify_empty_file_returns_400(client):
    response = client.post(
        "/verify",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
