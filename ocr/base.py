from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseOCREngine(ABC):
    """
    OCRエンジンの抽象基底クラス（インターフェース）
    """

    @abstractmethod
    async def extract(self, image_path: str) -> Dict[str, Any]:
        """
        指定された画像から非同期でテキスト・レイアウト情報を抽出する抽象メソッド。
        具象クラス（各OCRエンジンの実装クラス）で必ずオーバーライドしてください。
        """
        pass
