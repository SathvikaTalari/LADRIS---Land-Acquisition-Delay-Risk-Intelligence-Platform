import sys
from pathlib import Path

# Ensure ML package is importable
TESTS_DIR = Path(__file__).parent
ML_DIR = TESTS_DIR.parent
for p in (str(ML_DIR.parent), "/ml", "/"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

from ml.data_processing.validator import ValidationResult, validate_row_bhoomirashi


def test_validation_result():
    res = ValidationResult()
    res.total = 10
    res.valid = 8
    res.invalid = 2
    res.duplicate = 1
    res.field_null_counts = {"district": 2, "agency": 0}
    res.compute_null_rates(["district", "agency"])

    d = res.to_dict()
    assert d["total_records"] == 10
    assert d["valid_records"] == 8
    assert d["field_null_rates"]["district"] == 0.2
    assert d["field_null_rates"]["agency"] == 0.0


def test_validate_row_bhoomirashi_valid():
    res = ValidationResult()
    row = {
        "state": "MH",
        "district": "Thane",
        "agency": "NHAI",
        "land_required_ha": "50.5",
        "sanctioned_la_cost_crore": "12.0",
        "notification_3a_date": "2021-05-10",
        "notification_3d_date": "2021-11-15",
        "source": "https://bhoomirashi.gov.in/",
        "retrieval_timestamp": "2026-08-23T22:00:00Z",
    }
    is_valid = validate_row_bhoomirashi(row, 0, res)
    assert is_valid is True
    assert len(res.issues) == 0


def test_validate_row_bhoomirashi_date_order_violation():
    res = ValidationResult()
    row = {
        "state": "MH",
        "district": "Thane",
        "agency": "NHAI",
        "land_required_ha": "50.5",
        "sanctioned_la_cost_crore": "12.0",
        "notification_3a_date": "2022-05-10",
        "notification_3d_date": "2021-11-15",  # 3D before 3A!
        "source": "https://bhoomirashi.gov.in/",
        "retrieval_timestamp": "2026-08-23T22:00:00Z",
    }
    is_valid = validate_row_bhoomirashi(row, 0, res)
    assert is_valid is False
    assert any("DATE_ORDER_VIOLATION" in issue["issue"] for issue in res.issues)
