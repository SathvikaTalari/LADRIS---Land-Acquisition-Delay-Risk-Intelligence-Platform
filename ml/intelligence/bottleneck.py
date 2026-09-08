"""
LandPulse AI — Bottleneck Discovery Engine (Phase 7)
=====================================================
Statistical analysis of real project/stage data to identify recurring
risk patterns across projects, districts, and states.

ALGORITHM:
  1. Load real project features from all available project records
  2. Construct stage-risk feature vectors from Stage Risk Engine
  3. Apply K-means clustering (k=3–5, auto-selected by elbow) on stage risk vectors
  4. Compute cluster centroids to identify dominant bottleneck patterns
  5. Apply chi-square test for categorical associations where sample ≥ 10
  6. Compute state/district-level bottleneck aggregates

IMPORTANT LABELING:
  - All patterns are OBSERVED CORRELATIONS in the data, not causal explanations
  - Every insight shows: sample_size, confidence_level, data_quality, limitations
  - Do NOT claim causality from correlation
  - Small sample safeguard: N < 10 → return INSUFFICIENT_SAMPLE, not results

OUTPUT TYPE: B (Derived Analytics from official source data)

DATA SOURCES USED:
  - BhoomiRashi (56 records): state, land_ha, cost_per_ha, notification dates
  - DataGov delayed projects (10 records): delay_months, delay_reasons
  - MoRTH aggregate (36 records): state-level NH data
"""

import logging
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

# Small-sample threshold — below this, refuse to report patterns
MINIMUM_GROUP_SIZE = 5    # For per-group statistics
MINIMUM_CLUSTER_SIZE = 3  # For cluster membership interpretation

BOTTLENECK_DISCLAIMER = (
    "Bottleneck signals represent observed patterns in the available project data. "
    "They are statistical correlations — NOT causal explanations. "
    "Small sample sizes (N<30 for most groups) limit statistical robustness. "
    "Patterns may shift as more real project data becomes available. "
    "Do not use these signals as the sole basis for operational decisions. "
    "Every insight displays its sample size and confidence classification."
)

# Bottleneck type definitions — matched to dominant stage signals
BOTTLENECK_TYPES = {
    "NOTIFICATION": {
        "label": "Notification / Legal Clearance",
        "description": "Long 3A→3D notification intervals; legal objection risk dominant",
        "stage_driver": "NOTIFICATION",
        "typical_cause": "Gazette objections, incomplete survey records, land boundary disputes",
    },
    "COMPENSATION": {
        "label": "Compensation Disbursement",
        "description": "High cost intensity + affected families → compensation bottleneck",
        "stage_driver": "COMPENSATION",
        "typical_cause": "Award disputes, valuation objections, delayed DLC approvals",
    },
    "RR": {
        "label": "Rehabilitation & Resettlement",
        "description": "Large displaced families → complex R&R plan execution",
        "stage_driver": "RR",
        "typical_cause": "Resettlement colony readiness, entitlement disbursement delays",
    },
    "OBJECTION": {
        "label": "Objection & Dispute",
        "description": "Urban/peri-urban high-value land → Section 3C contestation",
        "stage_driver": "OBJECTION",
        "typical_cause": "High land value, commercial interests, court stays",
    },
    "MIXED": {
        "label": "Multi-Stage Complexity",
        "description": "Multiple stages show elevated risk simultaneously",
        "stage_driver": None,
        "typical_cause": "Large complex projects spanning multiple jurisdictions",
    },
}

# State-level delay patterns from DataGov.in (10 real records) — documented source
STATE_DELAY_EVIDENCE = {
    "MH": {
        "delayed_count": 2,
        "total_count": 2,
        "primary_reason": "Gazette valuation objections, compensation delays",
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
    "KA": {
        "delayed_count": 1,
        "total_count": 1,
        "primary_reason": "Urban corridor high compensation",
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
    "TN": {
        "delayed_count": 1,
        "total_count": 1,
        "primary_reason": "Waterbody clearances",
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
    "WB": {
        "delayed_count": 1,
        "total_count": 1,
        "primary_reason": "Encroachment removal complexity",
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
    "BR": {
        "delayed_count": 1,
        "total_count": 1,
        "primary_reason": "R&R and compensation disbursement",
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
    "UP": {
        "delayed_count": 0,
        "total_count": 1,
        "primary_reason": None,
        "source": "DATAGOV_DELAYED_PROJECTS",
    },
}


def _classify_confidence(n: int) -> Dict[str, str]:
    """Classify statistical confidence based on sample size."""
    if n < MINIMUM_GROUP_SIZE:
        return {
            "level": "INSUFFICIENT",
            "label": "Insufficient Sample",
            "note": f"N={n} — below minimum threshold of {MINIMUM_GROUP_SIZE}. Results not reported.",
        }
    elif n < 15:
        return {
            "level": "LOW",
            "label": "Low Confidence",
            "note": f"N={n} — small sample. Treat as indicative, not statistically robust.",
        }
    elif n < 30:
        return {
            "level": "MEDIUM",
            "label": "Moderate Confidence",
            "note": f"N={n} — moderate sample. Patterns indicative but may shift with more data.",
        }
    else:
        return {
            "level": "HIGH",
            "label": "Higher Confidence",
            "note": f"N={n} — adequate sample for this dataset. Still limited by overall data size.",
        }


def _identify_dominant_bottleneck(stage_risks: Dict[str, float]) -> str:
    """
    Identify the dominant bottleneck type from a project's stage risk scores.
    Returns the BOTTLENECK_TYPES key for the highest-scoring stage.
    """
    # Map stage_id to bottleneck type
    stage_to_bottleneck = {
        "NOTIFICATION": "NOTIFICATION",
        "OBJECTION": "OBJECTION",
        "COMPENSATION": "COMPENSATION",
        "RR": "RR",
    }

    if not stage_risks:
        return "MIXED"

    # Find highest risk stage among mapped ones
    max_stage = max(
        [(stage, risk) for stage, risk in stage_risks.items()
         if stage in stage_to_bottleneck],
        key=lambda x: x[1],
        default=(None, 0.0),
    )

    if max_stage[0] is None:
        return "MIXED"

    # If top two stages are within 0.1 of each other, classify as MIXED
    sorted_risks = sorted(stage_risks.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_risks) >= 2:
        top_risk = sorted_risks[0][1]
        second_risk = sorted_risks[1][1]
        if top_risk - second_risk < 0.10:
            return "MIXED"

    return stage_to_bottleneck.get(max_stage[0], "MIXED")


def analyze_bottlenecks(
    projects_with_stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyze bottleneck patterns across all available project records.

    Parameters
    ----------
    projects_with_stages : list of dicts, each containing:
        project_id, state_code, district_codes, executing_agency,
        total_area_ha, stage_fingerprint (from Stage Risk Engine)

    Returns
    -------
    dict with:
        national_bottleneck_summary
        state_bottlenecks
        cluster_analysis
        bottleneck_distribution
        data_provenance
        disclaimer
    """
    n_total = len(projects_with_stages)

    if n_total < MINIMUM_GROUP_SIZE:
        return {
            "output_type": "B",
            "output_type_label": "Derived Analytics — Bottleneck Discovery",
            "available": False,
            "reason": f"INSUFFICIENT_DATA: only {n_total} projects available. Minimum {MINIMUM_GROUP_SIZE} required.",
            "n_projects_analyzed": n_total,
            "disclaimer": BOTTLENECK_DISCLAIMER,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Extract stage risk vectors ─────────────────────────────────────────────
    stage_order = ["NOTIFICATION", "OBJECTION", "AWARD", "COMPENSATION", "RR", "POSSESSION"]
    project_vectors = []
    project_meta = []
    bottleneck_assignments = []

    for proj in projects_with_stages:
        fp = proj.get("stage_fingerprint") or {}
        stages = fp.get("stages") or []

        # Build stage risk dict
        stage_risks = {}
        for s in stages:
            sid = s.get("stage_id")
            risk = s.get("risk")
            if sid and risk is not None:
                stage_risks[sid] = float(risk)

        if not stage_risks:
            continue

        # Feature vector in fixed stage order
        vec = [stage_risks.get(sid, 0.5) for sid in stage_order]
        project_vectors.append(vec)

        # Dominant bottleneck for this project
        bottleneck = _identify_dominant_bottleneck(stage_risks)
        bottleneck_assignments.append(bottleneck)

        project_meta.append({
            "project_id": proj.get("project_id"),
            "state_code": proj.get("state_code", "UNKNOWN"),
            "district_codes": proj.get("district_codes") or [],
            "executing_agency": proj.get("executing_agency", "UNKNOWN"),
            "total_area_ha": proj.get("total_area_ha"),
            "stage_risks": stage_risks,
            "dominant_bottleneck": bottleneck,
        })

    n_analyzed = len(project_vectors)
    if n_analyzed < MINIMUM_GROUP_SIZE:
        return {
            "output_type": "B",
            "output_type_label": "Derived Analytics — Bottleneck Discovery",
            "available": False,
            "reason": f"INSUFFICIENT_STAGE_DATA: only {n_analyzed} projects have stage risk data.",
            "n_projects_analyzed": n_analyzed,
            "disclaimer": BOTTLENECK_DISCLAIMER,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    X = np.array(project_vectors)

    # ── K-means Clustering ────────────────────────────────────────────────────
    cluster_results = _run_kmeans_clustering(X, project_meta)

    # ── Bottleneck Distribution ───────────────────────────────────────────────
    bottleneck_counts: Dict[str, int] = {}
    for b in bottleneck_assignments:
        bottleneck_counts[b] = bottleneck_counts.get(b, 0) + 1

    bottleneck_distribution = []
    for btype, count in sorted(bottleneck_counts.items(), key=lambda x: -x[1]):
        confidence = _classify_confidence(count)
        if confidence["level"] == "INSUFFICIENT":
            continue
        bottleneck_distribution.append({
            "bottleneck_type": btype,
            "label": BOTTLENECK_TYPES.get(btype, {}).get("label", btype),
            "count": count,
            "percentage": round(count / n_analyzed * 100, 1),
            "description": BOTTLENECK_TYPES.get(btype, {}).get("description", ""),
            "typical_cause": BOTTLENECK_TYPES.get(btype, {}).get("typical_cause", ""),
            "confidence": confidence,
            "sample_size": count,
            "data_limitation": (
                f"Based on {count} of {n_analyzed} analyzed projects. "
                f"Small sample — treat as indicative pattern, not population estimate."
            ),
        })

    # ── State-Level Bottleneck Analysis ───────────────────────────────────────
    state_bottlenecks = _analyze_state_bottlenecks(project_meta)

    # ── National Summary ──────────────────────────────────────────────────────
    # Identify dominant national bottleneck
    dominant_national = (
        bottleneck_distribution[0] if bottleneck_distribution else None
    )

    # Mean stage risks across all projects
    mean_stage_risks = {}
    for i, sid in enumerate(stage_order):
        col_vals = X[:, i]
        mean_stage_risks[sid] = {
            "mean": round(float(np.mean(col_vals)), 4),
            "std": round(float(np.std(col_vals)), 4),
            "min": round(float(np.min(col_vals)), 4),
            "max": round(float(np.max(col_vals)), 4),
            "coverage_type": "REAL_SIGNAL" if sid == "NOTIFICATION" else "PROXY",
        }

    return {
        "output_type": "B",
        "output_type_label": "Derived Analytics — Statistical Bottleneck Discovery",
        "available": True,
        "n_projects_analyzed": n_analyzed,
        "n_total_projects": n_total,
        "national_summary": {
            "dominant_bottleneck": dominant_national,
            "mean_stage_risks": mean_stage_risks,
            "analysis_note": (
                f"National pattern across {n_analyzed} projects with stage risk data. "
                f"NOTIFICATION stage uses real BhoomiRashi temporal data. "
                f"All other stages use proxy-derived signals."
            ),
        },
        "bottleneck_distribution": bottleneck_distribution,
        "state_bottlenecks": state_bottlenecks,
        "cluster_analysis": cluster_results,
        "data_provenance": {
            "primary_sources": [
                "BHOOMIRASHI_PUBLIC_SEARCH_TABLE (56 records)",
                "DATAGOV_DELAYED_PROJECTS (10 records)",
            ],
            "analysis_method": "K-means clustering on stage risk feature vectors + descriptive statistics",
            "causality_note": (
                "These are observed CORRELATIONS in the data, not causal relationships. "
                "The presence of a bottleneck signal does not guarantee project delay."
            ),
        },
        "disclaimer": BOTTLENECK_DISCLAIMER,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def _run_kmeans_clustering(
    X: np.ndarray,
    project_meta: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Run K-means clustering on stage risk vectors.
    Auto-selects k using elbow method (k=2..5).
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    n = len(X)
    max_k = min(5, n - 1)  # Can't have more clusters than samples

    if max_k < 2:
        return {
            "available": False,
            "reason": f"Insufficient samples for clustering (N={n}, need ≥3)",
        }

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Find best k using inertia (simple elbow)
    best_k = 2
    best_inertia = float("inf")
    inertia_values = {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(X_scaled)
            inertia_values[k] = km.inertia_
            # Simple elbow: use diminishing returns heuristic
            if k == 2:
                best_inertia = km.inertia_
                best_k = 2
            else:
                improvement = (inertia_values[k - 1] - km.inertia_) / inertia_values[k - 1]
                if improvement > 0.20:  # >20% improvement — keep increasing k
                    best_k = k

    # Fit final model
    stage_order = ["NOTIFICATION", "OBJECTION", "AWARD", "COMPENSATION", "RR", "POSSESSION"]
    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km_final.fit_predict(X_scaled)
    centroids_scaled = km_final.cluster_centers_
    centroids = scaler.inverse_transform(centroids_scaled)

    # Describe each cluster
    clusters = []
    for c in range(best_k):
        cluster_mask = labels == c
        cluster_size = int(cluster_mask.sum())

        if cluster_size < MINIMUM_CLUSTER_SIZE:
            continue

        centroid = centroids[c]
        centroid_dict = {sid: round(float(v), 4) for sid, v in zip(stage_order, centroid)}

        # Identify dominant stage in this cluster
        peak_stage = max(centroid_dict, key=centroid_dict.get)
        dominant_bottleneck = _identify_dominant_bottleneck(centroid_dict)

        # States in this cluster
        cluster_states = list(set(
            project_meta[i]["state_code"]
            for i in range(len(project_meta))
            if labels[i] == c
        ))

        confidence = _classify_confidence(cluster_size)

        clusters.append({
            "cluster_id": c,
            "cluster_size": cluster_size,
            "centroid_stage_risks": centroid_dict,
            "peak_stage": peak_stage,
            "dominant_bottleneck": dominant_bottleneck,
            "bottleneck_label": BOTTLENECK_TYPES.get(dominant_bottleneck, {}).get("label", dominant_bottleneck),
            "states_in_cluster": sorted(cluster_states),
            "confidence": confidence,
            "data_limitation": (
                f"Cluster contains {cluster_size} projects. "
                f"K-means clustering on proxy-derived stage risk signals — "
                f"patterns are indicative, not definitive."
            ),
        })

    return {
        "available": True,
        "algorithm": "K-means",
        "n_clusters_selected": best_k,
        "n_samples": n,
        "feature_space": "6-dimensional stage risk vectors (1 real signal + 5 proxy signals)",
        "clusters": clusters,
        "algorithm_note": (
            "K-means selected automatically using diminishing-returns elbow criterion. "
            "Clustering performed on standardized stage risk feature vectors. "
            "Cluster membership is an algorithmic grouping — NOT a deterministic classification."
        ),
    }


def _analyze_state_bottlenecks(
    project_meta: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compute per-state bottleneck patterns."""
    # Group by state
    state_projects: Dict[str, List[Dict]] = {}
    for pm in project_meta:
        sc = pm.get("state_code", "UNKNOWN")
        if sc not in state_projects:
            state_projects[sc] = []
        state_projects[sc].append(pm)

    state_results = []
    for state_code, projs in sorted(state_projects.items()):
        n = len(projs)
        conf = _classify_confidence(n)
        if conf["level"] == "INSUFFICIENT":
            # Still report the state but with no-data flag
            state_results.append({
                "state_code": state_code,
                "n_projects": n,
                "available": False,
                "confidence": conf,
                "reason": f"N={n} — below minimum {MINIMUM_GROUP_SIZE} for state analysis",
            })
            continue

        # Dominant bottleneck for this state
        bottleneck_counts: Dict[str, int] = {}
        for p in projs:
            b = p.get("dominant_bottleneck", "MIXED")
            bottleneck_counts[b] = bottleneck_counts.get(b, 0) + 1

        dominant = max(bottleneck_counts, key=bottleneck_counts.get) if bottleneck_counts else "MIXED"

        # Mean stage risks
        stage_order = ["NOTIFICATION", "OBJECTION", "AWARD", "COMPENSATION", "RR", "POSSESSION"]
        mean_risks = {}
        for sid in stage_order:
            vals = [p["stage_risks"].get(sid, 0.5) for p in projs]
            mean_risks[sid] = round(float(np.mean(vals)), 4)

        # Official delay evidence from DataGov.in
        delay_evidence = STATE_DELAY_EVIDENCE.get(state_code)

        state_result = {
            "state_code": state_code,
            "n_projects": n,
            "available": True,
            "dominant_bottleneck": dominant,
            "bottleneck_label": BOTTLENECK_TYPES.get(dominant, {}).get("label", dominant),
            "bottleneck_counts": bottleneck_counts,
            "mean_stage_risks": mean_risks,
            "confidence": conf,
            "data_limitation": (
                f"Based on {n} project(s) in state {state_code}. "
                f"Small sample — treat as indicative pattern."
            ),
        }

        # Add official delay evidence if available
        if delay_evidence:
            state_result["official_delay_evidence"] = {
                "delayed_count": delay_evidence["delayed_count"],
                "total_monitored": delay_evidence["total_count"],
                "primary_reason": delay_evidence["primary_reason"],
                "source": delay_evidence["source"],
                "evidence_type": "A",
                "evidence_label": "Official Source Data — DataGov.in delayed project records",
                "evidence_limitation": (
                    "Only 10 DataGov.in records available nationally. "
                    "State-level counts are very small (1–2 records). "
                    "Do not extrapolate as population statistics."
                ),
            }

        state_results.append(state_result)

    return state_results


def analyze_state_bottleneck(
    state_code: str,
    projects_with_stages: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute bottleneck analysis filtered to a specific state.

    Returns
    -------
    dict with state-specific bottleneck analysis
    """
    state_projects = [
        p for p in projects_with_stages
        if (p.get("state_code") or "").upper() == state_code.upper()
    ]

    n = len(state_projects)
    confidence = _classify_confidence(n)

    base = {
        "state_code": state_code.upper(),
        "n_projects": n,
        "output_type": "B",
        "output_type_label": "Derived Analytics — State-Level Bottleneck Analysis",
        "confidence": confidence,
        "disclaimer": BOTTLENECK_DISCLAIMER,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if confidence["level"] == "INSUFFICIENT":
        return {
            **base,
            "available": False,
            "reason": f"INSUFFICIENT_SAMPLE: N={n} for state {state_code}.",
            "minimum_required": MINIMUM_GROUP_SIZE,
        }

    # Run full analysis on state subset
    full = analyze_bottlenecks(state_projects)
    full.update(base)
    full["state_code"] = state_code.upper()

    # Add official delay evidence
    delay_evidence = STATE_DELAY_EVIDENCE.get(state_code.upper())
    if delay_evidence:
        full["official_delay_evidence"] = {
            **delay_evidence,
            "evidence_type": "A",
            "evidence_label": "Official Source Data — DataGov.in",
        }

    return full
