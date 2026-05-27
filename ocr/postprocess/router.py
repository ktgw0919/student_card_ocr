from ocr.postprocess.extractors.base import BaseExtractor
from ocr.postprocess.extractors.driver_license_jp import DriverLicenseJpExtractor
from ocr.postprocess.extractors.student_card_jp import StudentCardJpExtractor
from ocr.postprocess.types import ExtractionResult, NormalizedDocument

ROUTING_THRESHOLD = 0.45

_DEFAULT_EXTRACTORS: list[BaseExtractor] = [
    StudentCardJpExtractor(),
    DriverLicenseJpExtractor(),
]


def route_and_extract(
    doc: NormalizedDocument,
    extractors: list[BaseExtractor] | None = None,
) -> ExtractionResult:
    extractors = extractors or _DEFAULT_EXTRACTORS

    scored: list[tuple[float, BaseExtractor]] = [
        (extractor.can_handle(doc), extractor) for extractor in extractors
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_extractor = scored[0]

    if best_score < ROUTING_THRESHOLD:
        return ExtractionResult(
            document_type="unknown",
            schema_id="unknown",
            issuer_hint=None,
            extractor_name="none",
            routing_score=best_score,
            fields={},
            warnings=["document_type_unknown"],
            confidence=0.0,
        )

    return best_extractor.extract(doc)
