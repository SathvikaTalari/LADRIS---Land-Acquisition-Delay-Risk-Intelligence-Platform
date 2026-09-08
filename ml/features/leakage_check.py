"""
LandPulse AI — Data Leakage Prevention Check
=============================================
Validates that no future milestone/outcome information is used as a model feature.

Rules enforced:
1. notification_interval_days uses 3D date — flag if used for project without 3D date
2. No outcome fields (actual completion, delay status) may appear in feature set
3. All date-derived features must precede or equal the as-of prediction date
"""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# Features that are FORBIDDEN in prospective prediction (post-event information)
FORBIDDEN_PROSPECTIVE_FEATURES = {
    "notification_interval_days": (
        "Uses 3D notification date — not available at 3A time. "
        "Only usable in retrospective anomaly scoring."
    ),
    "delay_label": "Outcome variable — never use as a feature.",
    "actual_end_date": "Outcome — not available at prediction time.",
    "actual_completion_days": "Outcome — not available at prediction time.",
    "delay_days": "Outcome — not available at prediction time.",
}

# Features safe for prospective prediction
SAFE_PROSPECTIVE_FEATURES = {
    "land_required_ha",
    "land_required_ha_log",
    "sanctioned_la_cost_crore",
    "cost_per_ha",
    "has_3a_notification",
    "has_3d_notification",
    "state_encoded",
    "agency_encoded",
    "3a_year",
}


def check_feature_set(feature_names: list[str], mode: str = "prospective") -> dict:
    """
    Check a list of feature names for leakage.

    Args:
        feature_names: List of feature column names to check
        mode: 'prospective' = live prediction; 'retrospective' = historical analysis

    Returns:
        dict with 'leakage_detected', 'violations', 'clean_features'
    """
    violations = []
    clean = []

    for f in feature_names:
        if f in FORBIDDEN_PROSPECTIVE_FEATURES and mode == "prospective":
            violations.append({
                "feature": f,
                "reason": FORBIDDEN_PROSPECTIVE_FEATURES[f],
                "severity": "HIGH",
            })
            log.warning("LEAKAGE: Feature '%s' violates prospective prediction. %s", f, FORBIDDEN_PROSPECTIVE_FEATURES[f])
        elif f.startswith("_"):
            # Internal flag columns — not features
            pass
        else:
            clean.append(f)

    return {
        "leakage_detected": len(violations) > 0,
        "violations": violations,
        "clean_features": clean,
        "mode": mode,
    }


def check_temporal_split(
    df: pd.DataFrame,
    date_col: str,
    train_end_date: str,
) -> dict:
    """
    Verify temporal train/test split is respected.
    Training data must only use rows where date_col <= train_end_date.
    """
    if date_col not in df.columns:
        return {"error": f"Column {date_col} not found", "ok": False}

    dates = pd.to_datetime(df[date_col], errors="coerce")
    cutoff = pd.Timestamp(train_end_date)

    train_mask = dates <= cutoff
    test_mask = dates > cutoff

    n_train = train_mask.sum()
    n_test = test_mask.sum()
    n_no_date = dates.isna().sum()

    result = {
        "ok": True,
        "cutoff_date": train_end_date,
        "date_column": date_col,
        "n_train": int(n_train),
        "n_test": int(n_test),
        "n_no_date": int(n_no_date),
        "temporal_split_valid": n_train > 0,
    }

    if n_train < 30:
        log.warning("Only %d training rows before cutoff %s", n_train, train_end_date)
        result["warning"] = "Insufficient training data for temporal split"

    return result


def assert_no_leakage(feature_names: list[str], mode: str = "prospective") -> None:
    """Raise an error if leakage is detected. Use in CI/test pipelines."""
    result = check_feature_set(feature_names, mode)
    if result["leakage_detected"]:
        msg = f"DATA LEAKAGE DETECTED in {mode} feature set:\n"
        for v in result["violations"]:
            msg += f"  - {v['feature']}: {v['reason']}\n"
        raise ValueError(msg)
    log.info("Leakage check passed for %d features (mode=%s)", len(feature_names), mode)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from ml.features.feature_engineering import get_model_features
    features = get_model_features()
    result = check_feature_set(features, mode="prospective")
    print(f"Leakage detected: {result['leakage_detected']}")
    if result["violations"]:
        for v in result["violations"]:
            print(f"  VIOLATION: {v['feature']} — {v['reason']}")
    else:
        print(f"  Clean features: {result['clean_features']}")
