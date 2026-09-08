"""
LandPulse AI — Data Validator
==============================
Validates raw ingested data for schema, types, duplicates,
missing values, date ordering, and impossible numeric values.
Produces a data_quality_report.json.

Never modifies raw source files.
"""

import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ─── Schema Definitions ───────────────────────────────────────────────────────

BHOOMIRASHI_SCHEMA = {
    "state":                        {"type": "str",   "required": True,  "min_len": 2, "max_len": 3},
    "district":                     {"type": "str",   "required": False},
    "agency":                       {"type": "str",   "required": False},
    "land_required_ha":             {"type": "float", "required": False, "min": 0.001, "max": 100000.0},
    "sanctioned_la_cost_crore":     {"type": "float", "required": False, "min": 0.0,   "max": 500000.0},
    "notification_3a_date":         {"type": "date",  "required": False},
    "notification_3d_date":         {"type": "date",  "required": False},
    "source":                       {"type": "str",   "required": True},
    "retrieval_timestamp":          {"type": "str",   "required": True},
}

MORTH_AGGREGATE_SCHEMA = {
    "state":            {"type": "str",   "required": True},
    "state_name":       {"type": "str",   "required": True},
    "nh_length_km":     {"type": "float", "required": True, "min": 0.0, "max": 50000.0},
    "financial_year":   {"type": "str",   "required": True,
                         "pattern": r"^\d{4}-\d{2}$"},
    "source":           {"type": "str",   "required": True},
}

VALID_AGENCIES = {
    "NHAI", "NHIDCL", "MoRTH", "PWD", "BRO", "IRCON",
    "STATE_PWD", "OTHER", "MORTH",
}


# ─── Validation Logic ─────────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.invalid = 0
        self.duplicate = 0
        self.issues: list[dict] = []
        self.field_null_counts: dict[str, int] = {}
        self.field_null_rates: dict[str, float] = {}

    def add_issue(self, row_idx: int, field: str, issue: str, value: Any = None):
        self.issues.append({
            "row": row_idx,
            "field": field,
            "issue": issue,
            "value": str(value)[:100] if value is not None else None,
        })

    def compute_null_rates(self, fields: list[str]):
        if self.total == 0:
            return
        for f in fields:
            count = self.field_null_counts.get(f, 0)
            self.field_null_rates[f] = round(count / self.total, 4)

    @property
    def missing_value_rate(self) -> float:
        if not self.field_null_rates:
            return 0.0
        return round(sum(self.field_null_rates.values()) / len(self.field_null_rates), 4)

    def to_dict(self) -> dict:
        return {
            "total_records": self.total,
            "valid_records": self.valid,
            "invalid_records": self.invalid,
            "duplicate_records": self.duplicate,
            "missing_value_rate": self.missing_value_rate,
            "field_null_rates": self.field_null_rates,
            "issue_count": len(self.issues),
            "issues_sample": self.issues[:50],  # First 50 issues
        }


def _parse_date_safe(val: str) -> datetime | None:
    if not val or val.strip() in ("-", "N/A", ""):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def validate_row_bhoomirashi(
    row: dict,
    row_idx: int,
    result: ValidationResult,
) -> bool:
    """Validate one BhoomiRashi row. Returns True if valid."""
    is_valid = True

    for field, spec in BHOOMIRASHI_SCHEMA.items():
        val = row.get(field)
        # Track nulls
        if val is None or str(val).strip() == "":
            result.field_null_counts[field] = result.field_null_counts.get(field, 0) + 1
            if spec.get("required"):
                result.add_issue(row_idx, field, "REQUIRED_FIELD_MISSING")
                is_valid = False
            continue

        val_str = str(val).strip()

        if spec["type"] == "float":
            try:
                fval = float(val_str)
            except (ValueError, TypeError):
                result.add_issue(row_idx, field, "INVALID_NUMERIC", val)
                is_valid = False
                continue
            if "min" in spec and fval < spec["min"]:
                result.add_issue(row_idx, field, f"BELOW_MIN ({spec['min']})", fval)
                is_valid = False
            if "max" in spec and fval > spec["max"]:
                result.add_issue(row_idx, field, f"ABOVE_MAX ({spec['max']})", fval)
                is_valid = False

        elif spec["type"] == "date":
            dt = _parse_date_safe(val_str)
            if dt is None:
                result.add_issue(row_idx, field, "INVALID_DATE_FORMAT", val)
                is_valid = False
            elif dt.year < 2014:
                result.add_issue(
                    row_idx, field,
                    "DATE_BEFORE_BHOOMIRASHI_PORTAL_LAUNCH_2018",
                    val,
                )
                # Not marking invalid — data may be older
            elif dt.year > 2030:
                result.add_issue(row_idx, field, "DATE_IMPLAUSIBLY_FUTURE", val)
                is_valid = False

        elif spec["type"] == "str":
            if "min_len" in spec and len(val_str) < spec["min_len"]:
                result.add_issue(row_idx, field, f"STRING_TOO_SHORT (min={spec['min_len']})", val)
            if "max_len" in spec and len(val_str) > spec["max_len"]:
                result.add_issue(row_idx, field, f"STRING_TOO_LONG (max={spec['max_len']})", val)

    # Date ordering: 3A must precede 3D
    date_3a_str = row.get("notification_3a_date")
    date_3d_str = row.get("notification_3d_date")
    if date_3a_str and date_3d_str:
        dt_3a = _parse_date_safe(str(date_3a_str))
        dt_3d = _parse_date_safe(str(date_3d_str))
        if dt_3a and dt_3d and dt_3d < dt_3a:
            result.add_issue(
                row_idx, "notification_3d_date",
                "DATE_ORDER_VIOLATION: 3D before 3A",
                f"3A={date_3a_str}, 3D={date_3d_str}",
            )
            is_valid = False

    return is_valid


def validate_csv(
    csv_path: Path,
    schema: str = "bhoomirashi",
) -> ValidationResult:
    """Validate a processed CSV file. Returns ValidationResult."""
    result = ValidationResult()
    seen_keys: set[str] = set()

    log.info("Validating %s (schema=%s)", csv_path, schema)

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    result.total = len(rows)
    fields = list(rows[0].keys()) if rows else []

    for i, row in enumerate(rows):
        # Duplicate detection key
        dup_key = f"{row.get('state','')}-{row.get('district','')}-{row.get('agency','')}-{row.get('land_required_ha','')}-{row.get('notification_3a_date','')}"
        if dup_key in seen_keys:
            result.duplicate += 1
            result.add_issue(i, "ROW", "DUPLICATE_ROW", dup_key)
        else:
            seen_keys.add(dup_key)

        if schema == "bhoomirashi":
            valid = validate_row_bhoomirashi(row, i, result)
        else:
            valid = True  # Future: add other schemas

        if valid:
            result.valid += 1
        else:
            result.invalid += 1

    result.compute_null_rates(fields)
    log.info(
        "Validation complete: %d total, %d valid, %d invalid, %d duplicates",
        result.total, result.valid, result.invalid, result.duplicate,
    )
    return result


def generate_quality_report(
    results: dict[str, ValidationResult],
    output_path: Path,
) -> dict:
    """Generate and save a data quality report JSON."""
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "datasets": {
            name: res.to_dict()
            for name, res in results.items()
        },
        "summary": {
            "total_records": sum(r.total for r in results.values()),
            "total_valid": sum(r.valid for r in results.values()),
            "total_invalid": sum(r.invalid for r in results.values()),
            "total_duplicates": sum(r.duplicate for r in results.values()),
            "prediction_eligible": sum(
                r.valid - r.duplicate
                for r in results.values()
            ),
        },
    }

    # Determine prediction eligibility
    total_eligible = report["summary"]["prediction_eligible"]
    report["summary"]["anomaly_model_trainable"] = total_eligible >= 50
    report["summary"]["supervised_trainable"] = False
    report["summary"]["supervised_not_trainable_reason"] = (
        "No project-level planned vs. actual milestone dates available "
        "from any public source. Supervised delay label cannot be constructed."
    )

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Quality report written to %s", output_path)
    return report


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    PROCESSED = Path(__file__).parent.parent / "data" / "processed"
    csvs = sorted(PROCESSED.glob("bhoomirashi_public_*.csv"))
    if not csvs:
        print("No processed BhoomiRashi CSV found. Run bhoomirashi_scraper.py first.")
        sys.exit(1)

    results = {}
    for csv_path in csvs:
        results[csv_path.stem] = validate_csv(csv_path, schema="bhoomirashi")

    report = generate_quality_report(
        results,
        Path(__file__).parent.parent / "data" / "processed" / "data_quality_report.json",
    )
    print(json.dumps(report["summary"], indent=2))
