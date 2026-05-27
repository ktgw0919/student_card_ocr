"""アップロード画像のバイト検証（マジックバイト / Pillow）。"""

from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})

_FORMAT_SUFFIX = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


def validate_image_bytes(file_bytes: bytes, *, max_bytes: int) -> str:
    """
    画像バイト列を検証し、保存用の拡張子を返す。

    Raises:
        HTTPException: 空・サイズ超過・非対応形式
    """
    if not file_bytes:
        raise HTTPException(status_code=400, detail="画像ファイルが空です。")

    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"画像サイズが上限（{max_bytes} バイト）を超えています。",
        )

    try:
        with Image.open(BytesIO(file_bytes)) as img:
            image_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise HTTPException(
            status_code=400,
            detail="対応していない画像形式です。JPEG / PNG / WebP を使用してください。",
        ) from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="対応していない画像形式です。JPEG / PNG / WebP を使用してください。",
        )

    return _FORMAT_SUFFIX[image_format]
