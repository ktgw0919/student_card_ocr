from abc import ABC, abstractmethod

from ocr.postprocess.types import ExtractionResult, NormalizedDocument


class BaseExtractor(ABC):
    schema_id: str
    document_type: str

    @abstractmethod
    def can_handle(self, doc: NormalizedDocument) -> float:
        """0.0〜1.0 の適合スコアを返す"""

    @abstractmethod
    def extract(self, doc: NormalizedDocument) -> ExtractionResult:
        pass
