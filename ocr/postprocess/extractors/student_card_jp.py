import re

from ocr.postprocess.extractors.base import BaseExtractor
from ocr.postprocess.types import ExtractedField, ExtractionResult, NormalizedDocument

_STUDENT_ID_RE = re.compile(r"学籍番号\s*([A-Z0-9]+)", re.IGNORECASE)
_NAME_RE = re.compile(
    r"(?:氏\s*名|名)\s+"
    r"([\u4e00-\u9fff]{1,6}(?:\s+[\u4e00-\u9fff]{1,6})?)"
    r"(?=\s*(?:生年月|有効期限|発行日|発\s|学部|学籍|$))"
)
_EXPIRY_RE = re.compile(
    r"有効期限\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
)
_UNIVERSITY_RE = re.compile(
    r"(大阪(?:市立|府立|公立)?大学|国立大学法人[^\s]+)"
)


def _search_texts(doc: NormalizedDocument) -> list[str]:
    texts = [doc.combined_text] + [p.text for p in doc.paragraphs]
    if doc.word_texts:
        texts.append("\n".join(doc.word_texts))
    return texts


def _extract_student_id(text: str) -> tuple[str | None, str | None]:
    match = _STUDENT_ID_RE.search(text)
    if not match:
        return None, None
    value = match.group(1).strip()
    return value, match.group(0)


def _extract_name(text: str) -> tuple[str | None, str | None]:
    match = _NAME_RE.search(text)
    if not match:
        return None, None
    value = re.sub(r"\s+", " ", match.group(1)).strip()
    if not value or value in {"氏", "名"}:
        return None, None
    return value, match.group(0)


def _extract_expiry(text: str) -> tuple[str | None, str | None]:
    match = _EXPIRY_RE.search(text)
    if not match:
        return None, None
    y, m, d = match.groups()
    normalized = f"{y}-{int(m):02d}-{int(d):02d}"
    return normalized, match.group(0)


def _extract_issuer_hint(text: str) -> str | None:
    match = _UNIVERSITY_RE.search(text)
    return match.group(1) if match else None


class StudentCardJpExtractor(BaseExtractor):
    schema_id = "student_card_jp"
    document_type = "student_card"

    def can_handle(self, doc: NormalizedDocument) -> float:
        text = doc.combined_text
        score = 0.0
        if "学生証" in text:
            score += 0.5
        if "学籍番号" in text:
            score += 0.4
        if _STUDENT_ID_RE.search(text):
            score += 0.1
        if "運転免許証" in text:
            score -= 0.6
        return max(0.0, min(1.0, score))

    def extract(self, doc: NormalizedDocument) -> ExtractionResult:
        warnings: list[str] = []
        texts = _search_texts(doc)

        student_id: str | None = None
        student_id_source: str | None = None
        name: str | None = None
        name_source: str | None = None
        expiry: str | None = None
        expiry_source: str | None = None

        for text in texts:
            if student_id is None:
                student_id, student_id_source = _extract_student_id(text)
            if name is None:
                name, name_source = _extract_name(text)
            if expiry is None:
                expiry, expiry_source = _extract_expiry(text)

        issuer_hint = _extract_issuer_hint(doc.combined_text)

        fields = {
            "student_id": ExtractedField(
                value=student_id,
                normalized_value=student_id,
                confidence=0.9 if student_id else None,
                source_text=student_id_source,
                status="found" if student_id else "missing",
            ),
            "name": ExtractedField(
                value=name,
                normalized_value=name,
                confidence=0.85 if name else None,
                source_text=name_source,
                status="found" if name else "missing",
            ),
            "expiry_date": ExtractedField(
                value=expiry,
                normalized_value=expiry,
                confidence=0.9 if expiry else None,
                source_text=expiry_source,
                status="found" if expiry else "missing",
            ),
        }

        missing = [k for k, f in fields.items() if f.status == "missing"]
        if missing:
            warnings.append(f"missing_fields:{','.join(missing)}")

        found_count = sum(1 for f in fields.values() if f.status == "found")
        confidence = found_count / len(fields) if fields else 0.0

        return ExtractionResult(
            document_type=self.document_type,
            schema_id=self.schema_id,
            issuer_hint=issuer_hint,
            extractor_name=self.__class__.__name__,
            routing_score=self.can_handle(doc),
            fields=fields,
            warnings=warnings,
            confidence=confidence,
        )
