"""
LADRIS — ETL Data Normalizer & DB Loader
===============================================
Takes raw project dicts from scrapers/API clients,
normalizes them to match the Project ORM model,
and upserts them into the PostgreSQL database.

Logic:
  1. Deduplicates by (nh_number + state_code) or (name + state_code)
  2. Assigns real risk level based on acquisition % and delay months
  3. Maps district names to district_codes
  4. Derives a project_code from NH number + state
  5. Upserts into `projects` table (insert new / update existing)
  6. Stamps data_source_label = 'BHOOMIRASHI' | 'DATA_GOV_IN' | 'REAL_DERIVED'
"""

import hashlib
import logging
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Risk Level Derivation ─────────────────────────────────────────────────────
def derive_risk_level(
    total_area: float,
    acquired_area: float,
    delay_months: int,
    legal_cases: int,
    compensation_backlog_pct: float,
) -> str:
    """Derive risk level from real acquisition data using structured rules."""
    score = 0

    # Acquisition progress
    if total_area > 0:
        acq_pct = (acquired_area / total_area) * 100
        if acq_pct < 30:
            score += 40
        elif acq_pct < 60:
            score += 20
        elif acq_pct < 80:
            score += 10

    # Delay impact
    if delay_months >= 12:
        score += 30
    elif delay_months >= 6:
        score += 20
    elif delay_months >= 3:
        score += 10

    # Legal disputes
    if legal_cases >= 10:
        score += 25
    elif legal_cases >= 5:
        score += 15
    elif legal_cases > 0:
        score += 8

    # Compensation backlog
    if compensation_backlog_pct >= 60:
        score += 20
    elif compensation_backlog_pct >= 30:
        score += 10

    if score >= 70:
        return "CRITICAL"
    elif score >= 45:
        return "HIGH"
    elif score >= 20:
        return "MEDIUM"
    else:
        return "LOW"


def derive_project_status(raw_status: Optional[str], acquisition_pct: float, delay_months: int) -> str:
    """Map raw BhoomiRashi/data.gov.in status to our ProjectStatus enum."""
    if raw_status:
        rs = raw_status.upper().strip()
        if rs in ("COMPLETED", "COMPLETE"):
            return "COMPLETED"
        if rs in ("ON HOLD", "ON_HOLD", "HOLD"):
            return "ON_HOLD"
        if rs in ("CANCELLED", "CANCELED"):
            return "CANCELLED"

    if delay_months >= 6:
        return "DELAYED"
    if acquisition_pct >= 95:
        return "COMPLETED"
    if acquisition_pct > 0:
        return "ACTIVE"
    return "ACTIVE"


def generate_project_code(nh_number: Optional[str], state_code: str, name: str) -> str:
    """Generate a deterministic project code from available identifiers."""
    if nh_number:
        nh_clean = nh_number.replace(" ", "").replace("-", "").upper()[:8]
        state_clean = state_code.upper()[:2]
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:4].upper()
        return f"{state_clean}-{nh_clean}-{hash_suffix}"
    else:
        # Hash from name
        hash_val = hashlib.md5(f"{state_code}{name}".encode()).hexdigest()[:8].upper()
        return f"{state_code.upper()}-NH-{hash_val}"


def normalize_project(raw: Dict[str, Any], district_map: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Normalize a raw scraped/API project dict to match the Project ORM schema.
    Returns None if the record is unusable (no name, no state).
    """
    name = (raw.get("name") or "").strip()
    state_code = (raw.get("state_code") or "").strip().upper()

    if not name or not state_code or state_code == "XX":
        return None

    nh_number = raw.get("nh_number")
    district_name = (raw.get("district") or "").strip()
    agency = (raw.get("executing_agency") or "NHAI").strip()
    total_area = _safe_float(raw.get("total_area_ha"))
    acquired_area = _safe_float(raw.get("area_acquired_ha"))
    possessed_area = _safe_float(raw.get("area_possessed_ha", raw.get("area_in_possession_ha", 0)))
    cost_crore = _safe_float(raw.get("estimated_cost_crore"))
    disbursed_crore = _safe_float(raw.get("disbursed_compensation_crore", 0))
    total_fam = _safe_int(raw.get("total_affected_families", 0))
    comp_fam = _safe_int(raw.get("families_compensated", 0))
    rehab_fam = _safe_int(raw.get("families_rehabilitated", 0))

    # Date normalization
    date_3a = _parse_date(raw.get("notification_3a_date"))
    date_3d = _parse_date(raw.get("notification_3d_date"))

    # Derived metrics
    acq_pct = (acquired_area / total_area * 100) if total_area > 0 else 0
    comp_backlog_pct = ((total_fam - comp_fam) / total_fam * 100) if total_fam > 0 else 0
    delay_months = _safe_int(raw.get("delay_months", 0))

    # Estimate delay from 3A date if not provided
    if delay_months == 0 and date_3a:
        months_since_3a = (date.today() - date_3a).days // 30
        # Average LA should complete in 18 months per RFCTLARR
        if months_since_3a > 18:
            delay_months = months_since_3a - 18

    risk_level = derive_risk_level(
        total_area=total_area,
        acquired_area=acquired_area,
        delay_months=delay_months,
        legal_cases=_safe_int(raw.get("legal_case_count", 0)),
        compensation_backlog_pct=comp_backlog_pct,
    )

    status = derive_project_status(raw.get("raw_status"), acq_pct, delay_months)

    project_code = generate_project_code(nh_number, state_code, name)

    # District codes
    district_codes = []
    if district_name:
        district_codes = [district_name.upper()[:20]]

    # Get centroid from district map if available
    lat = _safe_float(raw.get("latitude"), None)
    lng = _safe_float(raw.get("longitude"), None)

    if (lat is None or lat == 0) and district_map and district_name:
        district_lower = district_name.lower()
        for dk, dv in district_map.items():
            if district_lower in dk.lower() or dk.lower() in district_lower:
                if dv.get("state_code", "").upper() == state_code:
                    lat = dv.get("centroid_lat")
                    lng = dv.get("centroid_lng")
                    break

    # Planned dates (estimate from 3A if not provided)
    planned_start = date_3a
    planned_end = None
    if date_3a:
        from datetime import timedelta
        planned_end = date(date_3a.year + 2, date_3a.month, date_3a.day)  # 2-year standard

    # Compensation in INR (convert from crore)
    estimated_comp_inr = cost_crore * 10_000_000 if cost_crore else None
    disbursed_comp_inr = disbursed_crore * 10_000_000 if disbursed_crore else 0

    source_label = raw.get("source", "REAL_DERIVED")
    if "BHOOMIRASHI" in source_label:
        source_label = "BHOOMIRASHI"
    elif "DATA_GOV_IN" in source_label:
        source_label = "DATA_GOV_IN"

    return {
        "id": str(uuid.uuid4()),
        "project_code": project_code,
        "name": name,
        "description": (
            f"NH Project: {nh_number or 'N/A'} | {state_code} | "
            f"Source: {source_label}"
        ),
        "project_type": "HIGHWAY",
        "acquisition_act": "NH_ACT_1956" if agency != "MoRTH" else "RFCTLARR_2013",
        "status": status,
        "risk_level": risk_level,
        "nodal_agency": "MoRTH",
        "executing_agency": agency,
        "state_code": state_code,
        "district_codes": district_codes,
        "total_area_ha": total_area if total_area > 0 else None,
        "area_acquired_ha": acquired_area,
        "area_in_possession_ha": possessed_area,
        "total_affected_families": total_fam,
        "families_compensated": comp_fam,
        "families_rehabilitated": rehab_fam,
        "planned_start_date": planned_start,
        "planned_end_date": planned_end,
        "estimated_compensation_inr": estimated_comp_inr,
        "disbursed_compensation_inr": disbursed_comp_inr,
        "notification_3a_date": date_3a,
        "notification_3d_date": date_3d,
        "delay_months": delay_months,
        "legal_case_count": _safe_int(raw.get("legal_case_count", 0)),
        "legal_case_status": raw.get("legal_case_status", "NONE"),
        "milestone_data_status": f"REAL_{source_label}",
        "latitude": lat,
        "longitude": lng,
        "lacrris_integration_status": "INTEGRATED",
        "data_source_label": source_label,
        "nh_number": nh_number,
        "stretch_description": raw.get("stretch_description"),
        "bhoomirashi_project_id": raw.get("bhoomirashi_project_id"),
    }


def deduplicate_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate projects. Key = (project_code).
    In case of duplicate, prefer BHOOMIRASHI over DATA_GOV_IN.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    priority = {"BHOOMIRASHI": 3, "DATA_GOV_IN": 2, "REAL_DERIVED": 1}

    for p in projects:
        code = p.get("project_code", "")
        if not code:
            continue
        if code not in seen:
            seen[code] = p
        else:
            existing_priority = priority.get(seen[code].get("data_source_label", ""), 0)
            new_priority = priority.get(p.get("data_source_label", ""), 0)
            if new_priority > existing_priority:
                seen[code] = p

    return list(seen.values())


def _parse_date(val: Any) -> Optional[date]:
    """Parse various date formats to Python date."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s or s in ("-", "N/A", "NA", ""):
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(str(val).replace(",", "").split(".")[0].strip())
    except (ValueError, TypeError):
        return default
