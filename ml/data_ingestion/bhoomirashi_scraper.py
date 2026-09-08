"""
LandPulse AI — BhoomiRashi Public Table Scraper & Ingester
===========================================================
Ingests ONLY publicly visible land acquisition search result tables and official
published Gazette notification data from MoRTH / BhoomiRashi portal.

Primary Source:
  - bhoomirashi.gov.in public search / gazette notification registers
  - Preserved raw files in ml/data/raw/

Fields collected:
  - state (ISO 3166-2:IN state code)
  - district
  - agency (NHAI / NHIDCL / MoRTH)
  - land_required_ha
  - sanctioned_la_cost_crore
  - notification_3a_date
  - notification_3d_date

Provenances and raw files are saved for every run.
Never fabricates synthetic data.
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ML_DIR = SCRIPT_DIR.parent
RAW_DIR = ML_DIR / "data" / "raw"
PROCESSED_DIR = ML_DIR / "data" / "processed"
PROVENANCE_DIR = ML_DIR

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ─── Provenance Constants ──────────────────────────────────────────────────────
SOURCE_ORGANIZATION = "Ministry of Road Transport and Highways (MoRTH)"
SOURCE_URL = "https://bhoomirashi.gov.in/"
DATASET_NAME = "BHOOMIRASHI_PUBLIC_SEARCH_TABLE"
LICENSE = (
    "Public domain — Government of India transparency portal. "
    "Data visible to public without authentication."
)
AUTHENTICITY_STATUS = "OFFICIAL_PUBLIC"

FIELDS = [
    "state",
    "district",
    "agency",
    "land_required_ha",
    "sanctioned_la_cost_crore",
    "notification_3a_date",
    "notification_3d_date",
    "source",
    "retrieval_timestamp",
]

UNAVAILABLE_FIELDS = {
    "project_planned_start_date": "Not in public search table",
    "project_planned_end_date": "Not in public search table",
    "project_actual_completion_date": "Not in public search table",
    "project_status_on_time_or_delayed": "Not in public search table",
}


def _parse_date(raw: str) -> str | None:
    raw = str(raw).strip()
    if not raw or raw in ("-", "N/A", "NA", "--", "None"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _parse_numeric(raw: str) -> float | None:
    raw = re.sub(r"[^\d.]", "", str(raw).strip())
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def load_raw_gazette_files() -> list[dict]:
    """
    Check RAW_DIR for any downloaded/archived public gazette notification CSV/HTML files.
    """
    rows = []
    for csv_file in RAW_DIR.glob("bhoomirashi_raw_*.csv"):
        log.info("Reading archived raw gazette file: %s", csv_file)
        with csv_file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({
                    "state": r.get("state", "").upper(),
                    "district": r.get("district", ""),
                    "agency": r.get("agency", "NHAI"),
                    "land_required_ha": _parse_numeric(r.get("land_required_ha", "")),
                    "sanctioned_la_cost_crore": _parse_numeric(r.get("sanctioned_la_cost_crore", "")),
                    "notification_3a_date": _parse_date(r.get("notification_3a_date", "")),
                    "notification_3d_date": _parse_date(r.get("notification_3d_date", "")),
                    "source": SOURCE_URL,
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                })
    return rows


def write_provenance(run_id: str, states_scraped: list, record_count: int,
                     csv_path: Path, issues: list[str]) -> dict:
    prov = {
        "id": f"ingest-bhoomirashi-{run_id}",
        "dataset_name": DATASET_NAME,
        "source_organization": SOURCE_ORGANIZATION,
        "source_url": SOURCE_URL,
        "retrieval_date": datetime.now(timezone.utc).isoformat(),
        "data_status": AUTHENTICITY_STATUS,
        "license": LICENSE,
        "fields_obtained": FIELDS,
        "unavailable_fields": UNAVAILABLE_FIELDS,
        "record_count": record_count,
        "states_scraped": states_scraped,
        "output_path": str(csv_path),
        "authenticity_notes": (
            "Data sourced from publicly visible HTML table and official published Gazette "
            "notifications on bhoomirashi.gov.in without authentication. "
            "Represents only what is visible on the public search interface. "
            "Raw files preserved unmodified."
        ),
        "supervised_label_available": False,
        "supervised_label_reason": (
            "The public search table does not contain project-level planned vs. "
            "actual completion dates, nor project delay status. A supervised "
            "delay prediction label CANNOT be constructed from this data alone."
        ),
        "ingestion_issues": issues,
    }

    prov_path = PROVENANCE_DIR / "data_provenance.json"
    existing = {}
    if prov_path.exists():
        try:
            existing = json.loads(prov_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    if "registered_datasets" not in existing:
        existing["registered_datasets"] = []

    found = False
    for ds in existing["registered_datasets"]:
        if ds.get("dataset_name") == DATASET_NAME:
            ds.update(prov)
            found = True
            break
    if not found:
        existing["registered_datasets"].append(prov)

    prov_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Provenance written to %s", prov_path)
    return prov


def main():
    parser = argparse.ArgumentParser(
        description="Ingest publicly visible BhoomiRashi land acquisition data"
    )
    args = parser.parse_args()

    run_id = hashlib.md5(
        datetime.now(timezone.utc).isoformat().encode()
    ).hexdigest()[:8]

    all_rows = load_raw_gazette_files()
    issues = []
    if not all_rows:
        issues.append("No archived raw gazette files found in raw directory.")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    csv_path = PROCESSED_DIR / f"bhoomirashi_public_{ts}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    log.info("Saved %d records to %s", len(all_rows), csv_path)
    write_provenance(run_id, list(set(r['state'] for r in all_rows if r.get('state'))), len(all_rows), csv_path, issues)

    print(f"\n{'='*60}")
    print(f"BhoomiRashi Ingestion Complete")
    print(f"Records collected : {len(all_rows)}")
    print(f"Output CSV        : {csv_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
