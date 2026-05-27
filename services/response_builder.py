"""Service 層の生レスポンスを API 返却用にサニタイズし、Pydantic モデルへ変換する。"""

from copy import deepcopy
from typing import Any

from core.config import Settings
from models.schemas import VerifyResponse

OCR_ERROR_MESSAGE = "画像のOCR処理に失敗しました。"


def resolve_include_flags(
    settings: Settings,
    *,
    include_raw: bool | None,
    include_source_text: bool | None,
) -> tuple[bool, bool, str | None]:
    """
    クエリパラメータと Settings から最終的な include フラグを決定する。

    Returns:
        (include_raw, include_source_text, error_detail)
        error_detail が非 None のときは HTTP 403 用メッセージ。
    """
    raw = settings.include_raw_default if include_raw is None else include_raw
    source = (
        settings.include_source_text_default
        if include_source_text is None
        else include_source_text
    )

    if raw and not settings.allow_include_raw:
        return False, source, "raw_data の返却はこの環境では許可されていません。"

    return raw, source, None


def _strip_source_text(structured: dict[str, Any]) -> None:
    fields = structured.get("fields")
    if not isinstance(fields, dict):
        return
    for field_data in fields.values():
        if isinstance(field_data, dict) and "source_text" in field_data:
            field_data.pop("source_text", None)


def sanitize_verify_payload(
    payload: dict[str, Any],
    *,
    include_raw: bool,
    include_source_text: bool,
    debug_mode: bool,
) -> dict[str, Any]:
    """
    verify API 向けに PII・内部情報を除去したコピーを返す（dict）。

    - raw_data: include_raw が False のときキーごと削除
    - structured.fields.*.source_text: include_source_text が False のとき削除
    - data.error: debug_mode が False のとき汎用メッセージに置換
    """
    result = deepcopy(payload)
    data = result.get("data")
    if not isinstance(data, dict):
        return result

    if not include_raw:
        data.pop("raw_data", None)

    structured = data.get("structured")
    if isinstance(structured, dict) and not include_source_text:
        _strip_source_text(structured)

    if "error" in data and not debug_mode:
        data["error"] = OCR_ERROR_MESSAGE

    return result


# Phase 1 互換エイリアス
sanitize_verify_response = sanitize_verify_payload


def build_verify_response(
    payload: dict[str, Any],
    *,
    include_raw: bool,
    include_source_text: bool,
    debug_mode: bool,
) -> VerifyResponse:
    """サニタイズ後に VerifyResponse へ変換する。"""
    sanitized = sanitize_verify_payload(
        payload,
        include_raw=include_raw,
        include_source_text=include_source_text,
        debug_mode=debug_mode,
    )
    return VerifyResponse.model_validate(sanitized)
