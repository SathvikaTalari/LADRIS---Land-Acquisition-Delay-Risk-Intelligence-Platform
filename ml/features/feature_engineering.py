"""
LandPulse AI — Feature Engineering
=====================================
Builds ML-ready feature vectors from real ingested data.

Features are derived ONLY from fields genuinely available in the
public BhoomiRashi search table. No synthetic or fabricated values.

Prediction-as-of-date logic:
  All features represent information that would have been available
  at or before the 3A notification date — no future information leaks.

Documented feature catalog is written to feature_catalog.json.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

log = logging.getLogger(__name__)

FEATURES_DIR = Path(__file__).parent
ML_DIR = FEATURES_DIR.parent
PROCESSED_DIR = ML_DIR / "data" / "processed"


# ─── Feature Definitions ──────────────────────────────────────────────────────
# Each entry: name, source_field, transformation, meaning, availability_date,
#             usable_at_prediction_time, leakage_risk

FEATURE_CATALOG = [
    {
        "feature_name": "land_required_ha",
        "source_field": "land_required_ha",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "None (raw value from public table)",
        "meaning": "Total land area required for NH project (hectares)",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
        "notes": "Available in BhoomiRashi public table",
    },
    {
        "feature_name": "land_required_ha_log",
        "source_field": "land_required_ha",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "log1p(land_required_ha)",
        "meaning": "Log-transformed land area — reduces skewness",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "sanctioned_la_cost_crore",
        "source_field": "sanctioned_la_cost_crore",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "None (raw value from public table)",
        "meaning": "Total sanctioned land acquisition cost (₹ crore)",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "cost_per_ha",
        "source_field": "sanctioned_la_cost_crore / land_required_ha",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "sanctioned_la_cost_crore / land_required_ha (₹ crore per ha)",
        "meaning": "Land acquisition cost intensity. High values may indicate complex urban/peri-urban acquisition.",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "notification_interval_days",
        "source_field": "notification_3d_date - notification_3a_date",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "Days between 3A and 3D notifications",
        "meaning": "Time elapsed between section 3A (preliminary) and 3D (final declaration) NH Act notifications. Longer intervals may indicate acquisition complexity.",
        "availability_date": "After 3D notification date (NOT available at 3A time)",
        "usable_at_prediction_time": False,
        "leakage_risk": "MEDIUM — only available after 3D notification issued; cannot use before that event",
        "notes": "Include only as historical pattern feature in anomaly scorer, not for prospective prediction.",
    },
    {
        "feature_name": "state_encoded",
        "source_field": "state",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "Label encoding (ordinal integer per state code)",
        "meaning": "State where NH project land is being acquired",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "agency_encoded",
        "source_field": "agency",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "Label encoding (ordinal integer per agency)",
        "meaning": "Implementing agency (NHAI, NHIDCL, State PWD, etc.)",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "has_3a_notification",
        "source_field": "notification_3a_date",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "1 if 3A date is not null, else 0",
        "meaning": "Binary flag: whether preliminary notification has been issued",
        "availability_date": "At prediction time",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "has_3d_notification",
        "source_field": "notification_3d_date",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "1 if 3D date is not null, else 0",
        "meaning": "Binary flag: whether final declaration has been issued",
        "availability_date": "At prediction time",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
    {
        "feature_name": "3a_year",
        "source_field": "notification_3a_date",
        "source_dataset": "BHOOMIRASHI_PUBLIC_SEARCH_TABLE",
        "transformation": "Year extracted from 3A notification date",
        "meaning": "Year of 3A notification — captures macro policy/budget cycles",
        "availability_date": "At 3A notification date",
        "usable_at_prediction_time": True,
        "leakage_risk": "NONE",
    },
]

# Features NOT available from real data (documented gaps)
UNAVAILABLE_FEATURES = [
    {
        "feature_name": "planned_acquisition_duration_days",
        "reason": "Not in BhoomiRashi public table",
        "required_for": "Supervised delay target",
    },
    {
        "feature_name": "actual_acquisition_duration_days",
        "reason": "Not in BhoomiRashi public table",
        "required_for": "Supervised delay target",
    },
    {
        "feature_name": "delay_label",
        "reason": "Cannot be derived — no actual vs planned completion dates available",
        "required_for": "Supervised classifier training",
    },
    {
        "feature_name": "compensation_disbursement_pct",
        "reason": "Not in BhoomiRashi public table",
        "required_for": "Compensation progress feature",
    },
    {
        "feature_name": "legal_dispute_count",
        "reason": "Not in BhoomiRashi public table",
        "required_for": "Legal risk feature",
    },
    {
        "feature_name": "rr_grievance_rate",
        "reason": "Not in BhoomiRashi public table",
        "required_for": "R&R risk feature",
    },
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build ML feature matrix from cleaned BhoomiRashi DataFrame.
    Returns a new DataFrame with only feature columns + metadata.
    """
    feat = pd.DataFrame()

    # ── Numeric features ──────────────────────────────────────────────────────
    feat["land_required_ha"] = pd.to_numeric(df.get("land_required_ha"), errors="coerce")
    feat["land_required_ha_log"] = feat["land_required_ha"].apply(
        lambda x: math.log1p(x) if x and x > 0 else np.nan
    )
    feat["sanctioned_la_cost_crore"] = pd.to_numeric(
        df.get("sanctioned_la_cost_crore"), errors="coerce"
    )
    feat["cost_per_ha"] = np.where(
        feat["land_required_ha"] > 0,
        feat["sanctioned_la_cost_crore"] / feat["land_required_ha"],
        np.nan,
    )

    # ── Date-derived features ─────────────────────────────────────────────────
    date_3a = pd.to_datetime(df.get("notification_3a_date"), errors="coerce")
    date_3d = pd.to_datetime(df.get("notification_3d_date"), errors="coerce")

    feat["has_3a_notification"] = date_3a.notna().astype(int)
    feat["has_3d_notification"] = date_3d.notna().astype(int)

    feat["3a_year"] = date_3a.dt.year.astype("Int64")

    # Notification interval — only set when BOTH dates available and 3D >= 3A
    interval = (date_3d - date_3a).dt.days
    interval[interval < 0] = np.nan  # Flag violated ordering
    feat["notification_interval_days"] = interval

    # ── Categorical encoding ───────────────────────────────────────────────────
    le_state = LabelEncoder()
    state_vals = df.get("state", pd.Series()).fillna("UNKNOWN").str.upper().str.strip()
    feat["state_encoded"] = le_state.fit_transform(state_vals)
    feat["state"] = state_vals.values  # Keep raw for traceability

    le_agency = LabelEncoder()
    agency_vals = df.get("agency", pd.Series()).fillna("UNKNOWN").str.upper().str.strip()
    feat["agency_encoded"] = le_agency.fit_transform(agency_vals)
    feat["agency"] = agency_vals.values

    # ── Metadata passthrough ───────────────────────────────────────────────────
    if "district" in df.columns:
        feat["district"] = df["district"].values
    if "_row_valid" in df.columns:
        feat["_row_valid"] = df["_row_valid"].values

    # ── Prediction-as-of-date: filter only rows with 3A notification date ─────
    # Without 3A date, we have no temporal anchor for prediction.
    feat["_prediction_eligible"] = feat["has_3a_notification"].astype(bool)

    log.info(
        "Feature engineering complete: %d rows, %d prediction-eligible",
        len(feat),
        feat["_prediction_eligible"].sum(),
    )
    return feat


def get_model_features(mode: str = "prospective") -> list[str]:
    """Return the ordered list of feature column names for the ML model."""
    if mode == "prospective":
        return [
            "land_required_ha_log",
            "cost_per_ha",
            "has_3a_notification",
            "has_3d_notification",
            "state_encoded",
            "agency_encoded",
        ]
    return [
        "land_required_ha_log",
        "cost_per_ha",
        "has_3a_notification",
        "has_3d_notification",
        "state_encoded",
        "agency_encoded",
        "notification_interval_days",
    ]


def write_feature_catalog(output_path: Path) -> None:
    """Write feature catalog JSON."""
    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available_features": FEATURE_CATALOG,
        "unavailable_features": UNAVAILABLE_FEATURES,
        "model_features": get_model_features(),
        "notes": (
            "Features marked usable_at_prediction_time=False must NOT be used "
            "in prospective predictions. notification_interval_days is available "
            "only after 3D notification — it is used only in the anomaly scorer "
            "which is trained on historical patterns, not deployed for live prediction "
            "on projects without a 3D date."
        ),
    }
    output_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Feature catalog written to %s", output_path)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    from ml.data_processing.cleaner import get_latest_bhoomirashi_csv, clean_bhoomirashi

    src = get_latest_bhoomirashi_csv()
    if not src:
        print("No processed BhoomiRashi CSV. Run ingestion first.")
        sys.exit(1)

    df_clean = clean_bhoomirashi(src)
    feat_df = engineer_features(df_clean)
    print(feat_df[get_model_features() + ["_prediction_eligible"]].describe())

    write_feature_catalog(FEATURES_DIR / "feature_catalog.json")
    print("Feature catalog written.")
