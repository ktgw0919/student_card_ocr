from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParagraphToken:
    text: str
    box: list[int] | None = None
    order: int | None = None


@dataclass
class NormalizedDocument:
    paragraphs: list[ParagraphToken] = field(default_factory=list)
    combined_text: str = ""
    word_texts: list[str] = field(default_factory=list)


@dataclass
class ExtractedField:
    value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    source_text: str | None = None
    status: str = "missing"  # found | missing | inferred

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "normalized_value": self.normalized_value,
            "confidence": self.confidence,
            "source_text": self.source_text,
            "status": self.status,
        }


@dataclass
class ExtractionResult:
    document_type: str
    schema_id: str
    issuer_hint: str | None
    extractor_name: str
    routing_score: float
    fields: dict[str, ExtractedField]
    warnings: list[str] = field(default_factory=list)
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "schema_id": self.schema_id,
            "issuer_hint": self.issuer_hint,
            "extractor_name": self.extractor_name,
            "routing_score": self.routing_score,
            "confidence": self.confidence,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
            "warnings": self.warnings,
        }
