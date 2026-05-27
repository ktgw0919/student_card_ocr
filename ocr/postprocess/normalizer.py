import re
import unicodedata

from ocr.postprocess.types import NormalizedDocument, ParagraphToken


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # ラベル内の不要スペースを除去（発 行 日 -> 発行日）
    text = re.sub(r"発\s+行\s+日", "発行日", text)
    text = re.sub(r"生年月\s+日", "生年月日", text)
    return text


def normalize_raw_data(raw_data: dict) -> NormalizedDocument:
    paragraphs: list[ParagraphToken] = []

    for item in raw_data.get("paragraphs", []):
        contents = item.get("contents")
        if not contents or not str(contents).strip():
            continue
        paragraphs.append(
            ParagraphToken(
                text=_normalize_text(str(contents)),
                box=item.get("box"),
                order=item.get("order"),
            )
        )

    for figure in raw_data.get("figures", []):
        for item in figure.get("paragraphs", []):
            contents = item.get("contents")
            if not contents or not str(contents).strip():
                continue
            paragraphs.append(
                ParagraphToken(
                    text=_normalize_text(str(contents)),
                    box=item.get("box"),
                    order=item.get("order"),
                )
            )

    word_texts = []
    for word in raw_data.get("words", []):
        content = word.get("content")
        if content and str(content).strip():
            word_texts.append(_normalize_text(str(content)))

    combined_text = "\n".join(p.text for p in paragraphs)
    return NormalizedDocument(
        paragraphs=paragraphs,
        combined_text=combined_text,
        word_texts=word_texts,
    )
