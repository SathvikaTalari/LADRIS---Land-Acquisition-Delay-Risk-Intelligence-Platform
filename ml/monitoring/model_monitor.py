"""
LandPulse AI — Model Monitoring Service
=========================================
Records prediction statistics, feature distribution snapshots, and
anomaly rate tracking. Does NOT trigger automatic retraining.

Monitoring data is written to ml/models/monitoring_log.jsonl
and a rolling summary at ml/models/monitoring_summary.json.

Metrics recorded:
  - prediction_count (total, eligible, ineligible)
  - missing_data_rate
  - anomaly_rate (fraction scoring > 0.60)
  - feature_distribution snapshot (mean, std per feature)
  - model_version at time of recording
  - timestamp
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"
MONITORING_LOG = MODELS_DIR / "monitoring_log.jsonl"
MONITORING_SUMMARY = MODELS_DIR / "monitoring_summary.json"

# Max entries to keep in summary (rolling window)
ROLLING_WINDOW = 1000


def record_prediction(
    project_id: str,
    model_version: str,
    anomaly_score: Optional[float],
    stage_fingerprint_risk: Optional[float],
    data_completeness_pct: float,
    prediction_eligible: bool,
    feature_values: Optional[Dict[str, float]] = None,
    missing_fields: Optional[List[str]] = None,
) -> None:
    """
    Record a single prediction event to the monitoring log.
    Non-blocking — failures are logged but do not propagate.
    """
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": str(project_id),
            "model_version": model_version,
            "anomaly_score": round(float(anomaly_score), 4) if anomaly_score is not None else None,
            "stage_fingerprint_risk": round(float(stage_fingerprint_risk), 4) if stage_fingerprint_risk is not None else None,
            "data_completeness_pct": round(float(data_completeness_pct), 1),
            "prediction_eligible": bool(prediction_eligible),
            "missing_fields": missing_fields or [],
            "feature_values": {k: round(float(v), 4) for k, v in (feature_values or {}).items() if v is not None},
        }
        MODELS_DIR.mkdir(exist_ok=True)
        with MONITORING_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning("Failed to record prediction to monitoring log: %s", e)


def compute_monitoring_summary() -> Dict[str, Any]:
    """
    Compute rolling monitoring summary from the prediction log.
    Returns summary dict suitable for the /api/v1/monitoring/summary endpoint.
    """
    if not MONITORING_LOG.exists():
        return _empty_summary()

    try:
        entries = []
        with MONITORING_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        if not entries:
            return _empty_summary()

        # Use rolling window
        entries = entries[-ROLLING_WINDOW:]

        total = len(entries)
        eligible = sum(1 for e in entries if e.get("prediction_eligible"))
        ineligible = total - eligible

        scores = [e["anomaly_score"] for e in entries if e.get("anomaly_score") is not None]
        anomaly_rate = round(float(sum(1 for s in scores if s >= 0.60) / max(len(scores), 1)), 4)
        mean_score = round(float(np.mean(scores)), 4) if scores else None

        missing_rates = [len(e.get("missing_fields", [])) > 0 for e in entries]
        missing_data_rate = round(float(sum(missing_rates) / max(total, 1)), 4)

        # Feature distribution from last 100 entries with features
        feat_entries = [e for e in entries[-100:] if e.get("feature_values")]
        feature_stats = {}
        if feat_entries:
            all_feats = set()
            for e in feat_entries:
                all_feats.update(e["feature_values"].keys())
            for feat in all_feats:
                vals = [e["feature_values"][feat] for e in feat_entries if feat in e["feature_values"]]
                if vals:
                    feature_stats[feat] = {
                        "mean": round(float(np.mean(vals)), 4),
                        "std": round(float(np.std(vals)), 4),
                        "min": round(float(np.min(vals)), 4),
                        "max": round(float(np.max(vals)), 4),
                        "n": len(vals),
                    }

        # Model version distribution
        model_versions = {}
        for e in entries:
            mv = e.get("model_version", "unknown")
            model_versions[mv] = model_versions.get(mv, 0) + 1

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_size": total,
            "prediction_count": total,
            "eligible_prediction_count": eligible,
            "ineligible_prediction_count": ineligible,
            "eligibility_rate": round(eligible / max(total, 1), 4),
            "missing_data_rate": missing_data_rate,
            "anomaly_rate_above_60pct": anomaly_rate,
            "mean_anomaly_score": mean_score,
            "model_version_distribution": model_versions,
            "feature_distribution_snapshot": feature_stats,
            "monitoring_note": (
                "This monitoring summary covers the last {} prediction events. "
                "Automatic retraining is NOT triggered by this service.".format(total)
            ),
        }

        # Write to summary file
        MONITORING_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        return summary

    except Exception as e:
        log.error("Failed to compute monitoring summary: %s", e)
        return _empty_summary()


def _empty_summary() -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_size": 0,
        "prediction_count": 0,
        "eligible_prediction_count": 0,
        "ineligible_prediction_count": 0,
        "eligibility_rate": 0.0,
        "missing_data_rate": 0.0,
        "anomaly_rate_above_60pct": 0.0,
        "mean_anomaly_score": None,
        "model_version_distribution": {},
        "feature_distribution_snapshot": {},
        "monitoring_note": "No prediction events recorded yet.",
    }


def get_monitoring_summary() -> Dict[str, Any]:
    """
    Return cached monitoring summary if recent, else recompute.
    """
    if MONITORING_SUMMARY.exists():
        try:
            summary = json.loads(MONITORING_SUMMARY.read_text(encoding="utf-8"))
            # If summary is less than 5 minutes old, return cached
            generated_at = summary.get("generated_at", "")
            if generated_at:
                age_s = (datetime.now(timezone.utc) - datetime.fromisoformat(generated_at)).total_seconds()
                if age_s < 300:
                    return summary
        except Exception:
            pass
    return compute_monitoring_summary()
