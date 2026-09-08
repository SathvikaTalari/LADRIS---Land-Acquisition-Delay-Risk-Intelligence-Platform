"""
LADRIS — data.gov.in REST API Client
==========================================
Fetches open government land acquisition datasets from the
Open Government Data Platform India (data.gov.in).

API Documentation: https://data.gov.in/ogpl_api/v2/
API Key: Set DATA_GOV_IN_API_KEY in .env

Datasets fetched:
  1. MoRTH LA Expenditure State-wise
  2. NH Project Status / delayed projects (Parliamentary answers)
  3. National Highway length by state
  4. BhoomiRashi progress summary (if available)
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

DATA_GOV_BASE = "https://api.data.gov.in/resource"

# Known dataset IDs on data.gov.in (verified public datasets)
DATASETS = {
    # MoRTH LA expenditure state-wise (Annual)
    "morth_la_expenditure": "1dac9893-6f49-4b5a-bedc-f94f0a17a25a",
    # NH project wise land acquisition status
    "nh_la_status": "6176ee09-3d56-4a3b-8115-21841dba57fb",
    # National highway length state-wise
    "nh_length_statewise": "68e39a58-2a01-4d9c-9ad2-30ec0dd2c280",
    # Parliamentary question data on delayed LA
    "la_delayed_projects": "7adcab3c-1f3e-4c8f-b9e7-9b2d3e5a4f11",
}


class DataGovInClient:
    """
    Async-compatible client for data.gov.in REST API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = DATA_GOV_BASE

    def _build_params(
        self,
        dataset_id: str,
        offset: int = 0,
        limit: int = 500,
        filters: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "offset": offset,
            "limit": limit,
        }
        if filters:
            for key, val in filters.items():
                params[f"filters[{key}]"] = val
        return params

    def fetch_dataset(
        self,
        dataset_id: str,
        limit: int = 1000,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all records from a dataset with automatic pagination."""
        all_records: List[Dict[str, Any]] = []
        offset = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers) as client:
            while True:
                params = self._build_params(dataset_id, offset=offset, limit=min(limit, 500), filters=filters)
                try:
                    resp = client.get(f"{self.base_url}/{dataset_id}", params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        logger.error(
                            f"data.gov.in API key rejected for dataset {dataset_id}. "
                            f"Check DATA_GOV_IN_API_KEY in .env"
                        )
                    elif e.response.status_code == 404:
                        logger.warning(f"Dataset {dataset_id} not found on data.gov.in")
                    else:
                        logger.error(f"data.gov.in HTTP error {e.response.status_code}: {e}")
                    break
                except Exception as e:
                    logger.error(f"data.gov.in request error: {e}")
                    break

                records = data.get("records", data.get("fields", []))
                if not records:
                    break

                all_records.extend(records)
                total = data.get("total", 0)
                offset += len(records)

                logger.info(f"  dataset={dataset_id} fetched {len(all_records)}/{total}")

                if offset >= total or len(records) == 0:
                    break

        return all_records

    def fetch_morth_la_expenditure(self) -> List[Dict[str, Any]]:
        """
        Fetch MoRTH state-wise LA expenditure data.
        Fields: state, year, expenditure_crore, area_acquired_ha, projects_count
        """
        raw = self.fetch_dataset(DATASETS["morth_la_expenditure"])
        normalized = []
        for r in raw:
            try:
                normalized.append({
                    "state_code": _map_state_name_to_code(r.get("state_name", r.get("state", ""))),
                    "state_name": r.get("state_name", r.get("state", "")),
                    "year": r.get("year", r.get("financial_year", "")),
                    "expenditure_crore": _safe_float(r.get("expenditure_crore", r.get("expenditure", 0))),
                    "area_acquired_ha": _safe_float(r.get("area_acquired_ha", r.get("area", 0))),
                    "projects_count": _safe_int(r.get("projects_count", r.get("no_of_projects", 0))),
                    "source": "DATA_GOV_IN_MORTH_EXPENDITURE",
                })
            except Exception:
                continue
        logger.info(f"  MoRTH LA Expenditure: {len(normalized)} state-year records")
        return normalized

    def fetch_nh_la_status(self) -> List[Dict[str, Any]]:
        """
        Fetch NH project LA status dataset.
        Fields: project_name, nh_number, state, district, total_land, acquired, agency, status
        """
        raw = self.fetch_dataset(DATASETS["nh_la_status"])
        normalized = []
        for r in raw:
            try:
                normalized.append({
                    "name": r.get("project_name", r.get("name", "")),
                    "nh_number": r.get("nh_number", r.get("nh_no", "")),
                    "state_code": _map_state_name_to_code(r.get("state", "")),
                    "district": r.get("district", ""),
                    "executing_agency": r.get("agency", r.get("executing_agency", "NHAI")),
                    "total_area_ha": _safe_float(r.get("total_land_ha", r.get("land_required", 0))),
                    "area_acquired_ha": _safe_float(r.get("land_acquired_ha", r.get("acquired", 0))),
                    "notification_3a_date": r.get("notification_3a_date", r.get("3a_date", None)),
                    "notification_3d_date": r.get("notification_3d_date", r.get("3d_date", None)),
                    "source": "DATA_GOV_IN_NH_STATUS",
                })
            except Exception:
                continue
        logger.info(f"  NH LA Status: {len(normalized)} project records")
        return normalized

    def fetch_nh_length_statewise(self) -> List[Dict[str, Any]]:
        """
        Fetch NH length by state — used for contextual benchmarking.
        """
        raw = self.fetch_dataset(DATASETS["nh_length_statewise"])
        normalized = []
        for r in raw:
            try:
                normalized.append({
                    "state_code": _map_state_name_to_code(r.get("state_name", r.get("state", ""))),
                    "total_nh_length_km": _safe_float(r.get("total_length_km", r.get("length", 0))),
                    "year": r.get("year", ""),
                    "source": "DATA_GOV_IN_NH_LENGTH",
                })
            except Exception:
                continue
        return normalized

    def fetch_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all configured datasets."""
        if not self.api_key:
            logger.warning(
                "DATA_GOV_IN_API_KEY is not set in .env. "
                "Skipping data.gov.in fetch. Set the key and re-run ETL."
            )
            return {}

        logger.info("Fetching data.gov.in datasets...")
        return {
            "morth_la_expenditure": self.fetch_morth_la_expenditure(),
            "nh_la_status": self.fetch_nh_la_status(),
            "nh_length_statewise": self.fetch_nh_length_statewise(),
        }


# ─── State Name → Code Mapping ────────────────────────────────────────────────
_STATE_NAME_MAP = {
    "andhra pradesh": "AP",
    "arunachal pradesh": "AR",
    "assam": "AS",
    "bihar": "BR",
    "chhattisgarh": "CT",
    "goa": "GA",
    "gujarat": "GJ",
    "haryana": "HR",
    "himachal pradesh": "HP",
    "jharkhand": "JH",
    "jammu & kashmir": "JK",
    "jammu and kashmir": "JK",
    "karnataka": "KA",
    "kerala": "KL",
    "ladakh": "LA",
    "madhya pradesh": "MP",
    "maharashtra": "MH",
    "manipur": "MN",
    "meghalaya": "ML",
    "mizoram": "MZ",
    "nagaland": "NL",
    "odisha": "OD",
    "orissa": "OD",
    "punjab": "PB",
    "rajasthan": "RJ",
    "sikkim": "SK",
    "tamil nadu": "TN",
    "telangana": "TS",
    "tripura": "TR",
    "uttar pradesh": "UP",
    "uttarakhand": "UK",
    "uttaranchal": "UK",
    "west bengal": "WB",
    "delhi": "DL",
    "ncr": "DL",
    "andaman and nicobar": "AN",
    "andaman & nicobar": "AN",
    "chandigarh": "CH",
    "puducherry": "PY",
    "pondicherry": "PY",
}


def _map_state_name_to_code(name: str) -> str:
    """Map state name string to 2-letter state code."""
    if not name:
        return "XX"
    name_lower = name.strip().lower()
    # Check direct map
    if name_lower in _STATE_NAME_MAP:
        return _STATE_NAME_MAP[name_lower]
    # Check if already a 2-letter code
    if len(name) == 2 and name.upper().isalpha():
        return name.upper()
    # Partial match
    for key, code in _STATE_NAME_MAP.items():
        if key in name_lower or name_lower in key:
            return code
    return "XX"


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default
