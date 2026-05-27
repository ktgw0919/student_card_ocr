import json
from pathlib import Path

import pytest

from ocr.postprocess import process_raw_data

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "anonymized"
EXPECTED_PATH = FIXTURE_DIR / "expected.json"


@pytest.fixture(scope="module")
def expected() -> dict:
    with EXPECTED_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def load_raw():
    def _load(name: str) -> dict:
        path = FIXTURE_DIR / f"{name}.raw.json"
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    return _load


@pytest.mark.parametrize(
    "fixture_name",
    ["test_student_card_01", "test_student_card_02"],
)
def test_student_card_extraction(load_raw, expected: dict, fixture_name: str):
    result = process_raw_data(load_raw(fixture_name))

    assert result["document_type"] == "student_card"
    assert result["schema_id"] == "student_card_jp"

    fields = result["fields"]
    assert fields["student_id"]["value"] == expected["student_id"]
    assert fields["student_id"]["status"] == "found"

    assert fields["name"]["value"] == expected["name"]
    assert fields["name"]["status"] == "found"

    assert fields["expiry_date"]["normalized_value"] == expected["expiry_date"]
    assert fields["expiry_date"]["status"] == "found"


def test_driver_license_routing(load_raw):
    result = process_raw_data(load_raw("driver_license_anonymized"))

    assert result["document_type"] == "driver_license"
    assert result["schema_id"] == "driver_license_jp"
    assert "student_id" not in result["fields"]


def test_empty_raw_data():
    result = process_raw_data({})

    assert result["document_type"] == "unknown"
    assert "empty_raw_data" in result["warnings"]
