"""
API レスポンス向け Pydantic スキーマ。

後処理層の dict 出力を model_validate して HTTP 境界で型を固定する。
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# フィールドキー定数（抽出器・クライアント向け）
COMMON_FIELD_KEYS = ("name", "expiry_date")
STUDENT_CARD_FIELD_KEYS = ("student_id",)
DRIVER_LICENSE_FIELD_KEYS: tuple[str, ...] = ()


class OverallStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class QrStatus(str, Enum):
    VALID = "valid"
    NOT_FOUND = "not_found"
    UNVERIFIABLE = "unverifiable"


class FieldStatus(str, Enum):
    FOUND = "found"
    MISSING = "missing"
    INFERRED = "inferred"


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    source_text: str | None = None
    status: FieldStatus


class StructuredOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_type: str
    schema_id: str
    issuer_hint: str | None = None
    extractor_name: str
    routing_score: float = 0.0
    confidence: float | None = None
    fields: dict[str, ExtractedFieldOut] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class OcrDataOut(BaseModel):
    """OCR 成功時は engine + structured、失敗時は error のみの場合がある。"""

    model_config = ConfigDict(extra="ignore")

    engine: Literal["YomiToku"] | None = None
    structured: StructuredOut | None = None
    raw_data: dict[str, Any] | None = None
    error: str | None = None


class VerifyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: OverallStatus
    qr_status: QrStatus
    message: str
    data: OcrDataOut | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
