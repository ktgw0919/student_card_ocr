import re

from ocr.postprocess.extractors.base import BaseExtractor
from ocr.postprocess.types import ExtractedField, ExtractionResult, NormalizedDocument

_LICENSE_EXPIRY_RE = re.compile(
    r"(\d{4})年\s*\([^)]+\)\s*(\d{1,2})月\s*(\d{1,2})日\s*まで有効"
)
_NAME_ON_LICENSE_RE = re.compile(r"氏名\s*([\u4e00-\u9fff]+(?:\s+[\u4e00-\u9fff]+)?)")


class DriverLicenseJpExtractor(BaseExtractor):
    schema_id = "driver_license_jp"
    document_type = "driver_license"

    def can_handle(self, doc: NormalizedDocument) -> float:
        text = doc.combined_text
        score = 0.0
        if "運転免許証" in text:
            score += 0.6
        if "免許" in text and "学生証" not in text:
            score += 0.2
        if "学籍番号" in text or "学生証" in text:
            score -= 0.7
        return max(0.0, min(1.0, score))

    def extract(self, doc: NormalizedDocument) -> ExtractionResult:
        warnings: list[str] = []
        text = doc.combined_text

        expiry: str | None = None
        expiry_source: str | None = None
        match = _LICENSE_EXPIRY_RE.search(text)
        if match:
            y, m, d = match.groups()
            expiry = f"{y}-{int(m):02d}-{int(d):02d}"
            expiry_source = match.group(0)

        name: str | None = None
        name_source: str | None = None
        name_match = _NAME_ON_LICENSE_RE.search(text)
        if name_match:
            name = name_match.group(1).strip()
            name_source = name_match.group(0)

        fields = {
            "name": ExtractedField(
                value=name,
                normalized_value=name,
                confidence=0.8 if name else None,
                source_text=name_source,
                status="found" if name else "missing",
            ),
            "expiry_date": ExtractedField(
                value=expiry,
                normalized_value=expiry,
                confidence=0.85 if expiry else None,
                source_text=expiry_source,
                status="found" if expiry else "missing",
            ),
        }

        if not name and not expiry:
            warnings.append("driver_license_fields_not_implemented_fully")

        return ExtractionResult(
            document_type=self.document_type,
            schema_id=self.schema_id,
            issuer_hint=None,
            extractor_name=self.__class__.__name__,
            routing_score=self.can_handle(doc),
            fields=fields,
            warnings=warnings,
            confidence=0.5 if (name or expiry) else 0.2,
        )
