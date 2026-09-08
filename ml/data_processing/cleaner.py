"""
LandPulse AI — Data Cleaner
============================
Produces a clean dataset from validated raw ingested data.
NEVER modifies raw source files.
Flags rows that fail validation; does not silently drop them.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def clean_bhoomirashi(input_csv: Path) -> pd.DataFrame:
    """
    Clean BhoomiRashi public table CSV.

    Rules:
    - Coerce numeric columns; mark invalid as NaN
    - Parse date columns; mark invalid as NaT
    - Flag rows with date-ordering violation
    - Derive: notification_interval_days (3D - 3A)
    - Mark rows as valid/invalid — do not drop
    - Return clean DataFrame with _row_valid flag
    """
    df = pd.read_csv(input_csv, dtype=str)
    log.info("Loaded %d rows from %s", len(df), input_csv)

    # ── Numeric coercion ──────────────────────────────────────────────────────
    df["land_required_ha"] = pd.to_numeric(
        df["land_required_ha"].str.replace(",", "", regex=False),
        errors="coerce",
    )
    df["sanctioned_la_cost_crore"] = pd.to_numeric(
        df["sanctioned_la_cost_crore"].str.replace(",", "", regex=False),
        errors="coerce",
    )

    # ── Date coercion ─────────────────────────────────────────────────────────
    df["notification_3a_date"] = pd.to_datetime(
        df["notification_3a_date"], errors="coerce", format="%Y-%m-%d"
    )
    df["notification_3d_date"] = pd.to_datetime(
        df["notification_3d_date"], errors="coerce", format="%Y-%m-%d"
    )

    # ── Date ordering validation ───────────────────────────────────────────────
    both_dates = df["notification_3a_date"].notna() & df["notification_3d_date"].notna()
    df["_date_order_ok"] = True
    df.loc[
        both_dates & (df["notification_3d_date"] < df["notification_3a_date"]),
        "_date_order_ok",
    ] = False
    violations = (~df["_date_order_ok"]).sum()
    if violations:
        log.warning("%d rows have 3D date before 3A date — flagged, not dropped", violations)

    # ── Derived feature: notification interval days ───────────────────────────
    df["notification_interval_days"] = None
    mask = both_dates & df["_date_order_ok"]
    df.loc[mask, "notification_interval_days"] = (
        df.loc[mask, "notification_3d_date"] - df.loc[mask, "notification_3a_date"]
    ).dt.days

    # ── Range validation flags ─────────────────────────────────────────────────
    df["_land_ha_valid"] = df["land_required_ha"].between(0.001, 100000.0, inclusive="both") | df["land_required_ha"].isna()
    df["_cost_valid"] = df["sanctioned_la_cost_crore"].between(0.0, 500000.0, inclusive="both") | df["sanctioned_la_cost_crore"].isna()

    # ── Overall row validity ───────────────────────────────────────────────────
    df["_row_valid"] = (
        df["state"].notna()
        & df["_date_order_ok"]
        & df["_land_ha_valid"]
        & df["_cost_valid"]
    )

    # ── State code normalisation ───────────────────────────────────────────────
    df["state"] = df["state"].str.upper().str.strip()

    # ── Agency normalisation ───────────────────────────────────────────────────
    df["agency"] = df["agency"].str.strip().str.upper().where(df["agency"].notna())

    log.info(
        "Clean result: %d valid, %d invalid of %d total",
        df["_row_valid"].sum(),
        (~df["_row_valid"]).sum(),
        len(df),
    )
    return df


def save_clean(df: pd.DataFrame, name: str) -> Path:
    """Save clean DataFrame to processed directory."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = PROCESSED_DIR / f"{name}_clean_{ts}.csv"
    df.to_csv(out, index=False)
    log.info("Saved clean CSV to %s", out)
    return out


def get_latest_bhoomirashi_csv() -> Path | None:
    csvs = sorted(PROCESSED_DIR.glob("bhoomirashi_public_*.csv"), reverse=True)
    return csvs[0] if csvs else None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    src = get_latest_bhoomirashi_csv()
    if not src:
        print("No processed BhoomiRashi CSV found. Run bhoomirashi_scraper.py first.")
        sys.exit(1)
    df = clean_bhoomirashi(src)
    out = save_clean(df, "bhoomirashi")
    print(f"Clean file: {out}")
    print(df[["state", "district", "land_required_ha",
              "notification_interval_days", "_row_valid"]].head(10).to_string())
