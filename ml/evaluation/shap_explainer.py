"""
LandPulse AI — SHAP Explainability (Phase 3 Upgrade)
=======================================================
Generates SHAP feature contributions for trained IsolationForest model.

Phase 3 Upgrades:
  - Human-readable feature descriptions
  - Positive (risk-increasing) / negative (risk-decreasing) contributor split
  - Clearer language: "model-supported risk contributor" — NOT "causal factor"
  - Calibration-aware output labeling

Output clearly labeled as "feature contribution to anomaly score"
NOT as "causal factor of project delay."
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

SHAP_DISCLAIMER = (
    "SHAP values represent each feature's mathematical contribution to the "
    "model's anomaly score for this specific record. They describe model "
    "behaviour — NOT causal reasons for project delay. A high SHAP contribution "
    "from a feature means the model found that feature's value structurally unusual, "
    "not that the feature causes delays. Correlation ≠ causation. "
    "These are model-supported risk contributors, not confirmed delay drivers."
)

# Human-readable descriptions for each feature
FEATURE_DESCRIPTIONS = {
    "land_required_ha_log": {
        "display_name": "Land Area (log-transformed)",
        "unit": "log(ha)",
        "high_risk_interpretation": "Project requires unusually large land area relative to the national BhoomiRashi population.",
        "low_risk_interpretation": "Land area is within the typical range for NH projects.",
    },
    "cost_per_ha": {
        "display_name": "Acquisition Cost Intensity",
        "unit": "₹ Cr / ha",
        "high_risk_interpretation": "High cost per hectare signals peri-urban or urban land — often more contested and time-consuming to acquire.",
        "low_risk_interpretation": "Cost intensity is within normal range for this project type.",
    },
    "has_3a_notification": {
        "display_name": "3A Notification Issued",
        "unit": "binary (0/1)",
        "high_risk_interpretation": "Notification stage not yet reached — acquisition is in early planning.",
        "low_risk_interpretation": "Preliminary 3A notification has been issued.",
    },
    "has_3d_notification": {
        "display_name": "3D Final Declaration Issued",
        "unit": "binary (0/1)",
        "high_risk_interpretation": "Final 3D declaration not yet issued — acquisition is pending declaration.",
        "low_risk_interpretation": "Final 3D declaration has been issued.",
    },
    "state_encoded": {
        "display_name": "State",
        "unit": "encoded integer",
        "high_risk_interpretation": "This state has structural characteristics associated with unusual acquisition patterns.",
        "low_risk_interpretation": "State characteristics are typical of the training population.",
    },
    "agency_encoded": {
        "display_name": "Executing Agency",
        "unit": "encoded integer",
        "high_risk_interpretation": "This agency's acquisition profile is structurally unusual relative to the population.",
        "low_risk_interpretation": "Executing agency profile is typical.",
    },
    "notification_interval_days": {
        "display_name": "Notification Interval (3A → 3D)",
        "unit": "days",
        "high_risk_interpretation": "Long gap between 3A and 3D notifications — indicates a protracted preliminary phase.",
        "low_risk_interpretation": "Notification interval is within the typical range for NH projects.",
    },
}


def _get_feature_description(feature_name: str, is_high_risk: bool) -> str:
    """Return human-readable description for a feature and direction."""
    info = FEATURE_DESCRIPTIONS.get(feature_name)
    if not info:
        # Generic fallback
        direction = "unusually high" if is_high_risk else "within typical range"
        return f"Feature value is {direction} relative to the training population."
    if is_high_risk:
        return info["high_risk_interpretation"]
    return info["low_risk_interpretation"]


_EXPLAINER_CACHE: Dict[int, Any] = {}


def compute_shap_values(
    pipeline: Any,
    feature_values: dict,
    feature_cols: list,
) -> Optional[Dict]:
    """
    Compute SHAP values for a single prediction.

    Uses TreeExplainer for IsolationForest.
    Returns structured explanation JSON with human-readable descriptions.
    """
    try:
        import shap
    except ImportError:
        log.warning("SHAP not installed — skipping explanation. pip install shap")
        return None

    try:
        X = np.array([[feature_values.get(f, 0.0) for f in feature_cols]])

        model = pipeline.named_steps["model"]
        scaler = pipeline.named_steps["scaler"]
        imputer = pipeline.named_steps["imputer"]

        X_imputed = imputer.transform(X)
        X_scaled = scaler.transform(X_imputed)

        model_id = id(model)
        if model_id not in _EXPLAINER_CACHE:
            _EXPLAINER_CACHE[model_id] = shap.TreeExplainer(model)
        explainer = _EXPLAINER_CACHE[model_id]

        shap_values = explainer.shap_values(X_scaled)


        if hasattr(shap_values, "__iter__") and not isinstance(shap_values, np.ndarray):
            shap_values = np.array(shap_values[0])
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim > 1:
            shap_values = shap_values[0]

        contributions = []
        for i, feat in enumerate(feature_cols):
            val = float(shap_values[i]) if i < len(shap_values) else 0.0
            feat_val = float(feature_values.get(feat, 0.0))
            is_high_risk = val > 0
            feat_info = FEATURE_DESCRIPTIONS.get(feat, {})

            contributions.append({
                "feature": feat,
                "display_name": feat_info.get("display_name", feat.replace("_", " ").title()),
                "feature_value": round(feat_val, 4),
                "feature_unit": feat_info.get("unit", ""),
                "shap_contribution": round(val, 6),
                "direction": "INCREASES_ANOMALY_RISK" if is_high_risk else "DECREASES_ANOMALY_RISK",
                "absolute_importance": round(abs(val), 6),
                "interpretation": _get_feature_description(feat, is_high_risk),
                "contributor_label": (
                    "Model-supported risk contributor"
                    if is_high_risk
                    else "Model-supported risk reducer"
                ),
            })

        # Sort by absolute importance
        contributions.sort(key=lambda x: x["absolute_importance"], reverse=True)

        # Split into positive and negative contributors
        positive_contributors = [c for c in contributions if c["shap_contribution"] > 0]
        negative_contributors = [c for c in contributions if c["shap_contribution"] <= 0]

        base_val = None
        if hasattr(explainer, "expected_value") and explainer.expected_value is not None:
            try:
                base_val = float(np.ravel(explainer.expected_value)[0])
            except Exception:
                base_val = None

        return {
            "feature_contributions": contributions,
            "top_contributors": contributions[:5],
            "top_positive_contributors": positive_contributors[:3],
            "top_negative_contributors": negative_contributors[:3],
            "base_value": base_val,
            "disclaimer": SHAP_DISCLAIMER,
            "output_type": "ANOMALY_SCORE_CONTRIBUTIONS",
            "causal_warning": (
                "DO NOT interpret these as causal explanations. "
                "SHAP contributions describe model feature importance only."
            ),
        }

    except Exception as e:
        log.warning("SHAP computation failed: %s", e)
        return {
            "feature_contributions": [],
            "top_contributors": [],
            "top_positive_contributors": [],
            "top_negative_contributors": [],
            "disclaimer": SHAP_DISCLAIMER,
            "error": str(e),
            "output_type": "ANOMALY_SCORE_CONTRIBUTIONS",
        }


def format_explanation(shap_result: dict, anomaly_score: float) -> dict:
    """Format SHAP output for API response."""
    if not shap_result:
        return {
            "available": False,
            "reason": "SHAP library not available or model explanation failed.",
        }

    return {
        "available": True,
        "anomaly_score": round(anomaly_score, 4),
        "model_output_type": "ANOMALY_SCORE",
        "disclaimer": SHAP_DISCLAIMER,
        "causal_warning": (
            "SHAP values are model-supported risk contributors — "
            "NOT causal explanations of project delay."
        ),
        "top_positive_contributors": [
            {
                "factor": c["display_name"],
                "raw_feature": c["feature"],
                "contribution": c["shap_contribution"],
                "direction": c["direction"],
                "feature_value": c["feature_value"],
                "feature_unit": c.get("feature_unit", ""),
                "interpretation": c.get("interpretation", ""),
                "contributor_label": c.get("contributor_label", "Model-supported risk contributor"),
            }
            for c in shap_result.get("top_positive_contributors", [])[:3]
        ],
        "top_negative_contributors": [
            {
                "factor": c["display_name"],
                "raw_feature": c["feature"],
                "contribution": c["shap_contribution"],
                "direction": c["direction"],
                "feature_value": c["feature_value"],
                "feature_unit": c.get("feature_unit", ""),
                "interpretation": c.get("interpretation", ""),
                "contributor_label": c.get("contributor_label", "Model-supported risk reducer"),
            }
            for c in shap_result.get("top_negative_contributors", [])[:3]
        ],
        "all_contributions": shap_result.get("feature_contributions", []),
    }
