"""
LADRIS — BhoomiRashi Public Portal Scraper
=================================================
Scrapes the publicly accessible Highway Register on bhoomirashi.gov.in.

What it collects (no login required):
  - NH project name, number, corridor description
  - State, District
  - Executing agency (NHAI / NHIDCL / MoRTH)
  - Total land required (Ha)
  - Notification dates (3A / 3D)
  - LA stage status
  - Cost of land acquisition (₹ Crore)

Strategy:
  - Uses BhoomiRashi's public /PublicSearch endpoints
  - Iterates state-by-state using known state codes
  - Parses HTML tables with BeautifulSoup
  - Returns list of normalized project dicts
"""

import time
import logging
from typing import Any, Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# BhoomiRashi public base URL
BHOOMIRASHI_BASE = "https://bhoomirashi.gov.in"

# All India state codes used by BhoomiRashi portal
BHOOMIRASHI_STATE_CODES = {
    "AN": "Andaman & Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CH": "Chandigarh",
    "CT": "Chhattisgarh",
    "DN": "Dadra & Nagar Haveli",
    "DD": "Daman & Diu",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu & Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OD": "Odisha",
    "PY": "Puducherry",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TS": "Telangana",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UK": "Uttarakhand",
    "WB": "West Bengal",
}

# Agencies on BhoomiRashi
AGENCIES = ["NHAI", "NHIDCL", "MoRTH"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": BHOOMIRASHI_BASE,
}


def _normalize_area(raw: str) -> Optional[float]:
    """Convert area string like '45.23 Ha' or '45,234' to float hectares."""
    if not raw:
        return None
    cleaned = raw.replace(",", "").replace("Ha", "").replace("ha", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_date(raw: str) -> Optional[str]:
    """Convert date strings like '25/08/2023' to 'YYYY-MM-DD'."""
    if not raw or raw.strip() in ("", "-", "N/A", "NA"):
        return None
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y"):
        try:
            from datetime import datetime
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _normalize_cost(raw: str) -> Optional[float]:
    """Convert cost string '₹ 1,234.56 Cr' to float crore."""
    if not raw:
        return None
    cleaned = raw.replace("₹", "").replace("Cr", "").replace(",", "").replace("crore", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def scrape_highway_register(
    state_code: str,
    agency: str = "NHAI",
    delay_seconds: float = 1.5,
    timeout: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Scrape BhoomiRashi Highway Register for a given state and agency.
    Returns list of project dicts.
    """
    projects = []

    try:
        with httpx.Client(headers=HEADERS, timeout=timeout, follow_redirects=True) as client:
            # Step 1: Get CSRF token / session cookie from homepage
            resp = client.get(BHOOMIRASHI_BASE)
            resp.raise_for_status()

            # Step 2: Try the public highway register endpoint
            register_url = f"{BHOOMIRASHI_BASE}/PublicSearch/HighwayRegister"
            payload = {
                "stateCode": state_code,
                "agency": agency,
            }

            resp = client.post(register_url, data=payload)
            if resp.status_code != 200:
                logger.warning(
                    f"BhoomiRashi register returned {resp.status_code} "
                    f"for state={state_code}, agency={agency}"
                )
                return projects

            soup = BeautifulSoup(resp.text, "lxml")
            table = soup.find("table", {"id": "tblHighwayRegister"}) or soup.find("table")

            if not table:
                logger.info(f"No table found for {state_code}/{agency}")
                return projects

            rows = table.find_all("tr")[1:]  # skip header
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if len(cells) < 5:
                    continue

                # Best-effort column mapping (BhoomiRashi table structure)
                # Columns vary slightly by query type; we handle flexible mapping
                project_data = _parse_register_row(cells, state_code, agency)
                if project_data:
                    projects.append(project_data)

    except httpx.RequestError as e:
        logger.error(f"HTTP error scraping BhoomiRashi {state_code}/{agency}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scraping BhoomiRashi {state_code}/{agency}: {e}")

    time.sleep(delay_seconds)
    return projects


def _parse_register_row(
    cells: List[str], state_code: str, agency: str
) -> Optional[Dict[str, Any]]:
    """
    Parse a table row from BhoomiRashi Highway Register.
    Column order (best-effort): Sr | NH No | Project Name | District | LA Area | 3A Date | 3D Date | Cost | Status
    """
    try:
        # Flexible parsing — detect which column is which by content type
        nh_number = None
        project_name = None
        district = None
        area_ha = None
        date_3a = None
        date_3d = None
        cost_crore = None
        status = None

        for i, cell in enumerate(cells):
            cell = cell.strip()
            if not cell or cell in ("Sr", "S.No", "#"):
                continue

            # NH Number detection
            if cell.upper().startswith("NH") or cell.upper().startswith("SH"):
                nh_number = cell

            # Date detection
            elif "/" in cell and len(cell) == 10:
                if date_3a is None:
                    date_3a = _normalize_date(cell)
                elif date_3d is None:
                    date_3d = _normalize_date(cell)

            # Area detection (contains decimal or "Ha")
            elif ("." in cell or "ha" in cell.lower()) and any(c.isdigit() for c in cell):
                if area_ha is None:
                    area_ha = _normalize_area(cell)

            # Cost detection (₹ or Cr)
            elif "₹" in cell or "cr" in cell.lower() or ("." in cell and len(cell) < 15 and any(c.isdigit() for c in cell)):
                if cost_crore is None and area_ha is not None:
                    cost_crore = _normalize_cost(cell)

            # Status detection
            elif cell in ("COMPLETED", "IN PROGRESS", "DELAYED", "NOT STARTED", "UNDER PROCESS"):
                status = cell

            # Project name detection (longest remaining text field)
            elif len(cell) > 10 and project_name is None and not any(c in cell for c in ["₹", "/", "%"]):
                project_name = cell

            # District detection (shorter text after project name)
            elif len(cell) > 2 and len(cell) < 40 and district is None and project_name is not None:
                district = cell

        if not project_name:
            return None

        return {
            "nh_number": nh_number,
            "name": project_name,
            "state_code": state_code,
            "district": district,
            "executing_agency": agency,
            "total_area_ha": area_ha,
            "notification_3a_date": date_3a,
            "notification_3d_date": date_3d,
            "estimated_cost_crore": cost_crore,
            "raw_status": status,
            "source": "BHOOMIRASHI",
            "source_url": f"{BHOOMIRASHI_BASE}/PublicSearch/HighwayRegister",
        }
    except Exception as e:
        logger.debug(f"Row parse error: {e}")
        return None


def scrape_project_details(nh_number: str, state_code: str) -> Dict[str, Any]:
    """
    Scrape detailed project page on BhoomiRashi for a specific NH number and state.
    Returns additional fields: stretch_km, notification_details, awarded_area, etc.
    """
    details = {}
    try:
        with httpx.Client(headers=HEADERS, timeout=30.0, follow_redirects=True) as client:
            url = f"{BHOOMIRASHI_BASE}/PublicSearch/ProjectDetail"
            resp = client.post(url, data={"nhNumber": nh_number, "stateCode": state_code})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                # Extract additional details from detail page
                for row in soup.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).lower()
                        val = cells[1].get_text(strip=True)
                        if "stretch" in key or "section" in key:
                            details["stretch_description"] = val
                        elif "award" in key and "area" in key:
                            details["area_awarded_ha"] = _normalize_area(val)
                        elif "possession" in key:
                            details["area_possessed_ha"] = _normalize_area(val)
                        elif "family" in key or "families" in key:
                            try:
                                details["total_affected_families"] = int(val.replace(",", ""))
                            except ValueError:
                                pass
                        elif "compensat" in key and "disburs" in key:
                            details["disbursed_compensation_crore"] = _normalize_cost(val)
    except Exception as e:
        logger.debug(f"Project detail scrape error for {nh_number}: {e}")

    return details


def run_all_states(
    agencies: List[str] = None,
    delay_seconds: float = 2.0,
    max_projects_per_state: int = 500,
) -> List[Dict[str, Any]]:
    """
    Main entry point: scrape BhoomiRashi for ALL states and agencies.
    Returns consolidated list of project dicts.
    """
    if agencies is None:
        agencies = AGENCIES

    all_projects = []
    total_states = len(BHOOMIRASHI_STATE_CODES)

    for idx, (state_code, state_name) in enumerate(BHOOMIRASHI_STATE_CODES.items()):
        logger.info(f"[{idx+1}/{total_states}] Scraping {state_name} ({state_code})...")
        state_projects = []

        for agency in agencies:
            projects = scrape_highway_register(
                state_code=state_code,
                agency=agency,
                delay_seconds=delay_seconds,
            )
            logger.info(f"  {agency}: {len(projects)} projects found")
            state_projects.extend(projects)

        # Deduplicate by project name within state
        seen_names = set()
        deduped = []
        for p in state_projects:
            key = (p.get("name", ""), p.get("nh_number", ""))
            if key not in seen_names:
                seen_names.add(key)
                deduped.append(p)

        all_projects.extend(deduped[:max_projects_per_state])
        logger.info(f"  State total: {len(deduped)} unique projects")

    logger.info(f"BhoomiRashi scrape complete: {len(all_projects)} total projects")
    return all_projects
