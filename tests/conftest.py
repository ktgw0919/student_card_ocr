"""共有 pytest フィクスチャ。"""

from io import BytesIO

import pytest
from PIL import Image


@pytest.fixture
def jpeg_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="white").save(buf, format="JPEG")
    return buf.getvalue()
