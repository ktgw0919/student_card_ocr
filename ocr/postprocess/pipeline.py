from typing import Any

from ocr.postprocess.normalizer import normalize_raw_data
from ocr.postprocess.router import route_and_extract
from ocr.postprocess.types import ExtractionResult


def process_raw_data(raw_data: dict) -> dict[str, Any]:
    """
    YomiToku raw_data を正規化し、文書種別に応じて構造化データを返す。
    """
    if not raw_data:
        return ExtractionResult(
            document_type="unknown",
            schema_id="unknown",
            issuer_hint=None,
            extractor_name="none",
            routing_score=0.0,
            fields={},
            warnings=["empty_raw_data"],
            confidence=0.0,
        ).to_dict()

    doc = normalize_raw_data(raw_data)
    result = route_and_extract(doc)
    return result.to_dict()
