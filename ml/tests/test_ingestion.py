import sys
from pathlib import Path

# Ensure ML package is importable
TESTS_DIR = Path(__file__).parent
ML_DIR = TESTS_DIR.parent
for p in (str(ML_DIR.parent), "/ml", "/"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

from ml.data_ingestion.bhoomirashi_scraper import (
    _parse_date,
    _parse_numeric,
    load_raw_gazette_files,
    write_provenance,
)


def test_parse_date():
    assert _parse_date("15/08/2022") == "2022-08-15"
    assert _parse_date("2023-01-30") == "2023-01-30"
    assert _parse_date("-") is None
    assert _parse_date("N/A") is None


def test_parse_numeric():
    assert _parse_numeric("1,234.56") == 1234.56
    assert _parse_numeric(" 45.0 ha ") == 45.0
    assert _parse_numeric("-") is None


def test_load_raw_gazette_files():
    rows = load_raw_gazette_files()
    assert isinstance(rows, list)
    if rows:
        r = rows[0]
        assert "state" in r
        assert "land_required_ha" in r


def test_write_provenance():
    prov = write_provenance("test-run", ["MH"], 10, Path("test.csv"), [])
    assert prov["id"] == "ingest-bhoomirashi-test-run"
    assert prov["record_count"] == 10
    assert prov["data_status"] == "OFFICIAL_PUBLIC"
