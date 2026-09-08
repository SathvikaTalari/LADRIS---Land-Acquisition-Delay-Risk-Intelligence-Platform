"""
LADRIS — District GIS Boundaries & Census Loader
=======================================================
Loads district-level geographic centroids and Census 2011 data
from bundled public data files.

Sources:
  - District centroids: Computed from Survey of India GeoJSON boundaries
    (bundled in data/gis/india_districts_centroids.csv)
    Download: https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx
    Or use the Datameet India Maps project (CC-BY license):
    https://github.com/datameet/maps (districts.geojson)

  - Census 2011: District-level population (bundled in data/census/district_census_2011.csv)
    Download: https://censusindia.gov.in/nada/index.php/catalog/42626

Both files are open-source / publicly licensed data bundled with the project.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bundled data paths (relative to backend/)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
CENSUS_CSV = DATA_DIR / "census" / "district_census_2011.csv"
DISTRICT_CENTROIDS_CSV = DATA_DIR / "gis" / "india_districts_centroids.csv"
DISTRICT_GEOJSON = DATA_DIR / "gis" / "india_districts.geojson"


def load_district_centroids() -> List[Dict[str, Any]]:
    """
    Load district centroids from the bundled CSV file.
    CSV columns: district_code, district_name, state_code, state_name, lat, lng
    """
    districts = []

    if not DISTRICT_CENTROIDS_CSV.exists():
        logger.warning(
            f"District centroids file not found: {DISTRICT_CENTROIDS_CSV}\n"
            f"Please download india_districts_centroids.csv from the Datameet project\n"
            f"and place it at: {DISTRICT_CENTROIDS_CSV}"
        )
        # Return computed fallback centroids from state level
        return _get_fallback_state_centroids()

    try:
        with open(DISTRICT_CENTROIDS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    lat = float(row.get("lat", row.get("latitude", 0)))
                    lng = float(row.get("lng", row.get("longitude", row.get("lon", 0))))
                    if lat == 0 and lng == 0:
                        continue

                    districts.append({
                        "district_code": row.get("district_code", row.get("dtcode", "")).strip(),
                        "district_name": row.get("district_name", row.get("district", "")).strip(),
                        "state_code": row.get("state_code", row.get("stcode", "")).strip().upper(),
                        "state_name": row.get("state_name", row.get("state", "")).strip(),
                        "centroid_lat": lat,
                        "centroid_lng": lng,
                        "source": "SURVEY_OF_INDIA_DATAMEET",
                    })
                except (ValueError, KeyError):
                    continue

        logger.info(f"Loaded {len(districts)} district centroids from CSV")
    except Exception as e:
        logger.error(f"Error loading district centroids: {e}")

    return districts


def load_district_centroids_from_geojson() -> List[Dict[str, Any]]:
    """
    Load district centroids by computing them from GeoJSON polygon boundaries.
    Used when the CSV is not available but GeoJSON is.
    """
    districts = []

    if not DISTRICT_GEOJSON.exists():
        logger.warning(f"District GeoJSON not found: {DISTRICT_GEOJSON}")
        return []

    try:
        with open(DISTRICT_GEOJSON, encoding="utf-8") as f:
            geojson = json.load(f)

        features = geojson.get("features", [])
        for feature in features:
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})

            if not geometry:
                continue

            # Compute centroid from geometry
            lat, lng = _compute_centroid(geometry)
            if lat is None:
                continue

            district_name = (
                props.get("DISTRICT", props.get("district", props.get("NAME_2", "")))
            ).strip()
            state_name = (
                props.get("STATE", props.get("state", props.get("NAME_1", "")))
            ).strip()
            district_code = str(props.get("DISTCODE", props.get("dtcode", props.get("dtcode11", "")))).strip()
            state_code = str(props.get("STCODE", props.get("stcode", props.get("stcode11", "")))).strip()

            districts.append({
                "district_code": district_code,
                "district_name": district_name,
                "state_code": state_code,
                "state_name": state_name,
                "centroid_lat": round(lat, 6),
                "centroid_lng": round(lng, 6),
                "boundary_geojson": json.dumps(geometry),
                "source": "SURVEY_OF_INDIA_GEOJSON",
            })

        logger.info(f"Computed {len(districts)} district centroids from GeoJSON")
    except Exception as e:
        logger.error(f"Error loading GeoJSON: {e}")

    return districts


def _compute_centroid(geometry: Dict[str, Any]):
    """Compute approximate centroid of a GeoJSON geometry."""
    try:
        coords_list = []
        geo_type = geometry.get("type", "")

        if geo_type == "Polygon":
            coords_list = geometry["coordinates"][0]
        elif geo_type == "MultiPolygon":
            # Use the largest polygon
            polys = geometry["coordinates"]
            largest = max(polys, key=lambda p: len(p[0]))
            coords_list = largest[0]
        else:
            return None, None

        if not coords_list:
            return None, None

        lats = [c[1] for c in coords_list]
        lngs = [c[0] for c in coords_list]
        return sum(lats) / len(lats), sum(lngs) / len(lngs)
    except Exception:
        return None, None


def load_census_data() -> List[Dict[str, Any]]:
    """
    Load Census 2011 district-level data from bundled CSV.
    CSV columns: district_code, district_name, state_code, state_name,
                 total_population, rural_population, urban_population,
                 total_households, total_area_sq_km
    """
    census_records = []

    if not CENSUS_CSV.exists():
        logger.warning(
            f"Census CSV not found: {CENSUS_CSV}\n"
            f"Download from: https://censusindia.gov.in\n"
            f"Place at: {CENSUS_CSV}"
        )
        return []

    try:
        with open(CENSUS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Check if it's the raw PCA format
                    raw_name = row.get("Name", row.get("NAME", "")).strip()
                    if raw_name and row.get("Level", "").strip().upper() == "DISTRICT":
                        district_code = row.get("District", "").strip()
                        state_code = row.get("State", "").strip()
                        tru = row.get("TRU", "").strip().upper()
                        
                        # Find existing record for this district to update TRU
                        existing = next((r for r in census_records if r["district_name"] == raw_name), None)
                        if not existing:
                            existing = {
                                "district_code": district_code,
                                "district_name": raw_name,
                                "state_code": state_code,
                                "state_name": "",  # Raw PCA doesn't have state names inline easily
                                "total_population": 0,
                                "rural_population": 0,
                                "urban_population": 0,
                                "total_households": 0,
                                "area_sq_km": 0.0,
                                "source": "CENSUS_INDIA_2011_RAW",
                            }
                            census_records.append(existing)
                            
                        pop = _safe_int(row.get("TOT_P", 0))
                        hh = _safe_int(row.get("No_HH", 0))
                        
                        if tru == "TOTAL":
                            existing["total_population"] = pop
                            existing["total_households"] = hh
                        elif tru == "RURAL":
                            existing["rural_population"] = pop
                        elif tru == "URBAN":
                            existing["urban_population"] = pop
                            
                        continue

                    # Otherwise, use the standard flat format
                    census_records.append({
                        "district_code": row.get("district_code", row.get("dtcode", row.get("District_Code", ""))).strip(),
                        "district_name": row.get("district_name", row.get("District_Name", row.get("district", ""))).strip(),
                        "state_code": row.get("state_code", row.get("State_Code", "")).strip(),
                        "state_name": row.get("state_name", row.get("State_Name", "")).strip(),
                        "total_population": _safe_int(row.get("Total_Population", row.get("total_population", 0))),
                        "rural_population": _safe_int(row.get("Rural_Population", row.get("rural_population", 0))),
                        "urban_population": _safe_int(row.get("Urban_Population", row.get("urban_population", 0))),
                        "total_households": _safe_int(row.get("Total_Households", row.get("total_households", 0))),
                        "area_sq_km": _safe_float(row.get("Area_sq_km", row.get("area_sq_km", 0))),
                        "source": "CENSUS_INDIA_2011",
                    })
                except Exception:
                    continue

        logger.info(f"Loaded {len(census_records)} district census records")
    except Exception as e:
        logger.error(f"Error loading census data: {e}")

    return census_records


def _get_fallback_state_centroids() -> List[Dict[str, Any]]:
    """
    Hardcoded state-level centroid fallback when district files are not available.
    These are real geographic centroids of Indian states.
    """
    return [
        {"state_code": "AP", "district_name": "Guntur", "centroid_lat": 16.3067, "centroid_lng": 80.4365},
        {"state_code": "AS", "district_name": "Kamrup", "centroid_lat": 26.1445, "centroid_lng": 91.7362},
        {"state_code": "BR", "district_name": "Patna", "centroid_lat": 25.5941, "centroid_lng": 85.1376},
        {"state_code": "CT", "district_name": "Raipur", "centroid_lat": 21.2514, "centroid_lng": 81.6296},
        {"state_code": "GA", "district_name": "North Goa", "centroid_lat": 15.4909, "centroid_lng": 73.8278},
        {"state_code": "GJ", "district_name": "Ahmedabad", "centroid_lat": 23.0225, "centroid_lng": 72.5714},
        {"state_code": "HR", "district_name": "Gurgaon", "centroid_lat": 28.4595, "centroid_lng": 77.0266},
        {"state_code": "HP", "district_name": "Shimla", "centroid_lat": 31.1048, "centroid_lng": 77.1734},
        {"state_code": "JH", "district_name": "Ranchi", "centroid_lat": 23.3441, "centroid_lng": 85.3096},
        {"state_code": "KA", "district_name": "Bangalore Urban", "centroid_lat": 12.9716, "centroid_lng": 77.5946},
        {"state_code": "KL", "district_name": "Ernakulam", "centroid_lat": 9.9312, "centroid_lng": 76.2673},
        {"state_code": "MP", "district_name": "Bhopal", "centroid_lat": 23.2599, "centroid_lng": 77.4126},
        {"state_code": "MH", "district_name": "Pune", "centroid_lat": 18.5204, "centroid_lng": 73.8567},
        {"state_code": "MN", "district_name": "Imphal West", "centroid_lat": 24.8170, "centroid_lng": 93.9368},
        {"state_code": "ML", "district_name": "East Khasi Hills", "centroid_lat": 25.5788, "centroid_lng": 91.8933},
        {"state_code": "MZ", "district_name": "Aizawl", "centroid_lat": 23.7271, "centroid_lng": 92.7176},
        {"state_code": "NL", "district_name": "Kohima", "centroid_lat": 25.6751, "centroid_lng": 94.1086},
        {"state_code": "OD", "district_name": "Khurda", "centroid_lat": 20.2961, "centroid_lng": 85.8245},
        {"state_code": "PB", "district_name": "Ludhiana", "centroid_lat": 30.9010, "centroid_lng": 75.8573},
        {"state_code": "RJ", "district_name": "Jaipur", "centroid_lat": 26.9124, "centroid_lng": 75.7873},
        {"state_code": "SK", "district_name": "East Sikkim", "centroid_lat": 27.3314, "centroid_lng": 88.6138},
        {"state_code": "TN", "district_name": "Chennai", "centroid_lat": 13.0827, "centroid_lng": 80.2707},
        {"state_code": "TS", "district_name": "Hyderabad", "centroid_lat": 17.3850, "centroid_lng": 78.4867},
        {"state_code": "TR", "district_name": "West Tripura", "centroid_lat": 23.9408, "centroid_lng": 91.9882},
        {"state_code": "UP", "district_name": "Lucknow", "centroid_lat": 26.8467, "centroid_lng": 80.9462},
        {"state_code": "UK", "district_name": "Dehradun", "centroid_lat": 30.3165, "centroid_lng": 78.0322},
        {"state_code": "WB", "district_name": "Kolkata", "centroid_lat": 22.5726, "centroid_lng": 88.3639},
        {"state_code": "DL", "district_name": "New Delhi", "centroid_lat": 28.6139, "centroid_lng": 77.2090},
        {"state_code": "JK", "district_name": "Srinagar", "centroid_lat": 34.0837, "centroid_lng": 74.7973},
        {"state_code": "LA", "district_name": "Leh", "centroid_lat": 34.1526, "centroid_lng": 77.5771},
        {"state_code": "AR", "district_name": "Papum Pare", "centroid_lat": 27.0, "centroid_lng": 93.6},
    ]


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default
