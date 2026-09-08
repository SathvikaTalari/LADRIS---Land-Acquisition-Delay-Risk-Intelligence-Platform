import sys
from pathlib import Path

# Ensure ML package is importable
TESTS_DIR = Path(__file__).parent
ML_DIR = TESTS_DIR.parent
for p in (str(ML_DIR.parent), "/ml", "/"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

import pandas as pd
import pytest
from ml.features.feature_engineering import engineer_features, get_model_features
from ml.features.leakage_check import check_feature_set, assert_no_leakage


def test_engineer_features():
    df = pd.DataFrame([
        {
            "state": "MH",
            "district": "Pune",
            "agency": "NHAI",
            "land_required_ha": "100.0",
            "sanctioned_la_cost_crore": "50.0",
            "notification_3a_date": "2021-01-01",
            "notification_3d_date": "2021-07-01",
            "_row_valid": True,
        },
        {
            "state": "UP",
            "district": "Lucknow",
            "agency": "NHAI",
            "land_required_ha": "200.0",
            "sanctioned_la_cost_crore": "80.0",
            "notification_3a_date": "2022-03-15",
            "notification_3d_date": None,
            "_row_valid": True,
        },
    ])

    feats = engineer_features(df)
    assert len(feats) == 2
    assert feats.loc[0, "cost_per_ha"] == 0.5  # 50 / 100
    assert feats.loc[0, "has_3a_notification"] == 1
    assert feats.loc[0, "has_3d_notification"] == 1
    assert feats.loc[0, "notification_interval_days"] == 181
    assert feats.loc[1, "has_3d_notification"] == 0
    assert pd.isna(feats.loc[1, "notification_interval_days"])


def test_leakage_check_prospective():
    model_features = get_model_features()
    # Prospective features should not raise an exception unless post-event features are included
    # notification_interval_days is flagged in prospective mode
    res = check_feature_set(["land_required_ha_log", "cost_per_ha", "state_encoded"], mode="prospective")
    assert res["leakage_detected"] is False
    assert len(res["clean_features"]) == 3

    res_leaked = check_feature_set(["notification_interval_days", "delay_label"], mode="prospective")
    assert res_leaked["leakage_detected"] is True
    assert len(res_leaked["violations"]) == 2


def test_assert_no_leakage_raises():
    with pytest.raises(ValueError, match="DATA LEAKAGE DETECTED"):
        assert_no_leakage(["delay_label"], mode="prospective")
