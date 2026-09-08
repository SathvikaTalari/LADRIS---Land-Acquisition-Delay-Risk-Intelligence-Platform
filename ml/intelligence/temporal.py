"""
LandPulse AI — Temporal Risk Intelligence (Phase 7)
=====================================================
Reads real timestamped prediction observations from the monitoring log.
Detects genuine risk escalation/de-escalation from available observations.

CRITICAL RULES:
  - NEVER fabricate historical data points
  - NEVER infer exact future delay dates
  - NEVER use synthetic observations
  - When no observations exist: return temporal_data_available = false
  - All timestamps come from real prediction log entries

DATA SOURCE:
  ml/models/monitoring_log.jsonl — appended by model_monitor.py on each
  real prediction API call. Entries contain: project_id, timestamp,
  anomaly_score, data_completeness_pct.

OUTPUT TYPE: A (Official Source Data — real logged timestamps)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# Monitoring log location
MONITORING_LOG_PATH = Path(__file__).parent.parent / "models" / "monitoring_log.jsonl"

TEMPORAL_DISCLAIMER = (
    "Risk history is derived ONLY from real prediction observations logged by the "
    "LandPulse monitoring system (ml/models/monitoring_log.jsonl). "
    "Each observation is created when a project is assessed via the API. "
    "No historical data points are fabricated, imputed, or synthetically generated. "
    "Trend labels (ESCALATING/DE_ESCALATING/STABLE) are simple arithmetic deltas "
    "between real observations — NOT forecasts of future risk."
)

NO_DATA_DISCLAIMER = (
    "No temporal observation history is available for this project. "
    "The monitoring system begins logging predictions from first API access onwards. "
    "Temporal data will accumulate as the project continues to be assessed. "
    "This is NOT a limitation of data quality — it reflects honest tracking of "
    "only real system observations."
)

MINIMUM_OBSERVATIONS_FOR_TREND = 2


def _load_monitoring_log() -> List[Dict[str, Any]]:
    """Load all entries from the monitoring log. Returns empty list if unavailable."""
    if not MONITORING_LOG_PATH.exists():
        log.debug("Monitoring log not found at %s", MONITORING_LOG_PATH)
        return []

    entries = []
    try:
        with MONITORING_LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log.warning("Failed to read monitoring log: %s", e)

    return entries


def get_project_observations(project_id: str) -> List[Dict[str, Any]]:
    """
    Get all real timestamped observations for a project from the monitoring log.

    Returns
    -------
    list of dicts with keys: timestamp, anomaly_score, data_completeness_pct
    Empty list if no observations exist.
    """
    all_entries = _load_monitoring_log()

    project_entries = [
        e for e in all_entries
        if str(e.get("project_id", "")) == str(project_id)
    ]

    # Sort ascending by timestamp
    project_entries.sort(key=lambda x: x.get("timestamp", ""))

    # Return cleaned observation objects
    observations = []
    for e in project_entries:
        ts = e.get("timestamp") or e.get("logged_at")
        score = e.get("anomaly_score")
        if ts is not None and score is not None:
            observations.append({
                "timestamp": ts,
                "anomaly_score": round(float(score), 4),
                "data_completeness_pct": e.get("data_completeness_pct"),
                "stage_fingerprint_risk": e.get("stage_fingerprint_risk"),
                "model_version": e.get("model_version"),
                "source": "monitoring_log.jsonl",
            })

    return observations


def analyze_temporal_risk(project_id: str) -> Dict[str, Any]:
    """
    Analyze temporal risk observations for a project.

    Returns
    -------
    dict with:
        temporal_data_available (bool)
        observation_count (int)
        observations (list of real observations)
        risk_trend (float or None) — delta between first and last observation
        risk_trend_label (str) — ESCALATING / DE_ESCALATING / STABLE / INSUFFICIENT_DATA
        escalation_events (list) — observation pairs where score increased > threshold
        deescalation_events (list) — observation pairs where score decreased > threshold
        temporal_disclaimer (str)
        output_type (str)
    """
    observations = get_project_observations(project_id)
    n = len(observations)

    base = {
        "project_id": project_id,
        "output_type": "A",
        "output_type_label": "Official Source Data — real logged prediction observations",
    }

    if n == 0:
        return {
            **base,
            "temporal_data_available": False,
            "observation_count": 0,
            "observations": [],
            "risk_trend": None,
            "risk_trend_label": "NO_DATA",
            "escalation_events": [],
            "deescalation_events": [],
            "first_observation_date": None,
            "last_observation_date": None,
            "temporal_disclaimer": NO_DATA_DISCLAIMER,
        }

    if n == 1:
        obs = observations[0]
        return {
            **base,
            "temporal_data_available": True,
            "observation_count": 1,
            "observations": observations,
            "risk_trend": None,
            "risk_trend_label": "INSUFFICIENT_DATA",
            "escalation_events": [],
            "deescalation_events": [],
            "first_observation_date": obs["timestamp"],
            "last_observation_date": obs["timestamp"],
            "temporal_disclaimer": (
                f"Only 1 observation available (logged at {obs['timestamp']}). "
                f"At least {MINIMUM_OBSERVATIONS_FOR_TREND} observations are required "
                f"to detect risk trends. Check back after another assessment is performed."
            ),
        }

    # Multiple observations — compute trend
    first_score = observations[0]["anomaly_score"]
    last_score = observations[-1]["anomaly_score"]
    delta = round(last_score - first_score, 4)

    # Threshold for meaningful change
    ESCALATION_THRESHOLD = 0.05
    DEESCALATION_THRESHOLD = -0.05

    if delta > ESCALATION_THRESHOLD:
        trend_label = "ESCALATING"
    elif delta < DEESCALATION_THRESHOLD:
        trend_label = "DE_ESCALATING"
    else:
        trend_label = "STABLE"

    # Identify individual escalation/de-escalation events between consecutive observations
    escalation_events = []
    deescalation_events = []

    for i in range(1, n):
        prev = observations[i - 1]
        curr = observations[i]
        step_delta = curr["anomaly_score"] - prev["anomaly_score"]

        if step_delta > ESCALATION_THRESHOLD:
            escalation_events.append({
                "from_timestamp": prev["timestamp"],
                "to_timestamp": curr["timestamp"],
                "from_score": prev["anomaly_score"],
                "to_score": curr["anomaly_score"],
                "delta": round(step_delta, 4),
                "event_type": "ESCALATION",
            })
        elif step_delta < DEESCALATION_THRESHOLD:
            deescalation_events.append({
                "from_timestamp": prev["timestamp"],
                "to_timestamp": curr["timestamp"],
                "from_score": prev["anomaly_score"],
                "to_score": curr["anomaly_score"],
                "delta": round(step_delta, 4),
                "event_type": "DE_ESCALATION",
            })

    # Score statistics
    scores = [o["anomaly_score"] for o in observations]

    return {
        **base,
        "temporal_data_available": True,
        "observation_count": n,
        "observations": observations,
        "risk_trend": delta,
        "risk_trend_label": trend_label,
        "escalation_events": escalation_events,
        "deescalation_events": deescalation_events,
        "first_observation_date": observations[0]["timestamp"],
        "last_observation_date": observations[-1]["timestamp"],
        "score_statistics": {
            "min": round(min(scores), 4),
            "max": round(max(scores), 4),
            "mean": round(float(sum(scores) / len(scores)), 4),
            "range": round(max(scores) - min(scores), 4),
        },
        "temporal_disclaimer": TEMPORAL_DISCLAIMER,
        "trend_note": (
            "ESCALATING: anomaly score increased >5% between first and most recent observation. "
            "DE_ESCALATING: anomaly score decreased >5%. "
            "STABLE: change within ±5%. "
            "These are arithmetic deltas between REAL observations — NOT forecasts."
        ),
    }


def get_all_project_temporal_summary() -> Dict[str, Any]:
    """
    Get a summary of temporal observations across all projects.
    Used by bottleneck engine to understand data density.
    """
    all_entries = _load_monitoring_log()

    project_counts: Dict[str, int] = {}
    for e in all_entries:
        pid = str(e.get("project_id", ""))
        if pid:
            project_counts[pid] = project_counts.get(pid, 0) + 1

    return {
        "total_logged_entries": len(all_entries),
        "projects_with_history": len(project_counts),
        "projects_with_multiple_observations": sum(
            1 for c in project_counts.values() if c >= MINIMUM_OBSERVATIONS_FOR_TREND
        ),
        "max_observations_single_project": max(project_counts.values()) if project_counts else 0,
        "log_path": str(MONITORING_LOG_PATH),
        "log_exists": MONITORING_LOG_PATH.exists(),
    }
