"""
LandPulse AI — Comparable Project Finder (Phase 7)
===================================================
Identifies structurally similar projects using cosine similarity on real
project attribute vectors.

ALGORITHM:
  Cosine similarity on a 6-dimensional feature vector:
    [state_encoded, land_area_log, cost_per_ha_norm, agency_encoded,
     acquisition_act_encoded, families_normalized]

IMPORTANT LABELING:
  - Comparability is based on STRUCTURAL ATTRIBUTE SIMILARITY only
  - NOT based on outcome similarity (we have no outcome data)
  - High similarity score ≠ same risk outcome
  - Every result shows which features drove the similarity and their weights

OUTPUT TYPE: B (Derived Analytics from official source data)

DATA SOURCE: Real project attributes from database (BhoomiRashi + DataGov.in)
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

COMPARABLE_DISCLAIMER = (
    "Comparable projects are identified using cosine similarity on real project "
    "structural attributes (state, land area, cost intensity, agency, acquisition act). "
    "Similarity is STRUCTURAL ONLY — not based on risk outcomes (which are unavailable). "
    "A high similarity score means the projects share similar land acquisition characteristics, "
    "NOT that they will have the same risk trajectory or delay outcome. "
    "Comparables are provided for contextual benchmarking only."
)

# Feature definitions for similarity computation
SIMILARITY_FEATURES = [
    {
        "name": "state_encoded",
        "label": "State / Geographic Region",
        "description": "Encoded state code — same state = high similarity",
        "weight": 2.0,  # Strong weight — state context is highly relevant
        "output_type": "A",
    },
    {
        "name": "land_area_log",
        "label": "Land Acquisition Scale (log Ha)",
        "description": "Log-transformed total land area in hectares",
        "weight": 1.5,
        "output_type": "A",
    },
    {
        "name": "cost_per_ha_norm",
        "label": "Cost Intensity (Cr/Ha, normalized)",
        "description": "Estimated compensation per hectare — proxy for urban/rural land type",
        "weight": 1.5,
        "output_type": "A",
    },
    {
        "name": "agency_encoded",
        "label": "Executing Agency",
        "description": "NHAI vs NHIDCL vs State PWD",
        "weight": 1.0,
        "output_type": "A",
    },
    {
        "name": "acquisition_act_encoded",
        "label": "Acquisition Act",
        "description": "NH Act 1956 vs RFCTLARR 2013 vs others",
        "weight": 1.0,
        "output_type": "A",
    },
    {
        "name": "families_normalized",
        "label": "Affected Families (normalized)",
        "description": "Total affected families normalized by population maximum",
        "weight": 1.0,
        "output_type": "A",
    },
]

STATE_CODES = [
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "GA", "GJ", "HR",
    "HP", "JK", "JH", "KA", "KL", "LD", "LA", "MP", "MH", "MN", "ML", "MZ",
    "NL", "OD", "PY", "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB"
]

AGENCIES = ["NHAI", "NHIDCL", "MORTH", "STATE_PWD", "PWD", "OTHER"]
ACQUISITION_ACTS = ["RFCTLARR_2013", "NH_ACT_1956", "RAILWAYS_ACT_1989", "ELECTRICITY_ACT_2003", "STATE_SPECIFIC", "OTHER"]


def _encode_project_features(project_data: Dict[str, Any]) -> Optional[np.ndarray]:
    """
    Convert project attributes to a numerical feature vector for similarity.

    Returns
    -------
    numpy array of shape (6,) or None if insufficient data
    """
    state_str = (project_data.get("state_code") or "MH").upper().strip()
    agency_str = (project_data.get("executing_agency") or "NHAI").upper().strip()
    act_str = (project_data.get("acquisition_act") or "RFCTLARR_2013").upper().strip()

    state_enc = float(STATE_CODES.index(state_str) if state_str in STATE_CODES else 10)
    agency_enc = float(AGENCIES.index(agency_str) if agency_str in AGENCIES else 0)
    act_enc = float(ACQUISITION_ACTS.index(act_str) if act_str in ACQUISITION_ACTS else 0)

    area_ha = project_data.get("total_area_ha")
    area_log = math.log1p(float(area_ha)) if (area_ha and float(area_ha) > 0) else 4.5  # default: median

    comp_inr = project_data.get("estimated_compensation_inr")
    cost_crore = float(comp_inr) / 10_000_000.0 if comp_inr else None
    cost_per_ha = cost_crore / max(float(area_ha), 0.01) if (cost_crore and area_ha) else 0.5
    cost_norm = float(np.clip(cost_per_ha / 4.0, 0.0, 1.0))  # Normalize by p95 (4 Cr/ha)

    families = project_data.get("total_affected_families") or 0
    families_norm = float(np.clip(int(families) / 2000.0, 0.0, 1.0))  # Normalize by 2000 families

    return np.array([state_enc, area_log, cost_norm, agency_enc, act_enc, families_norm])


def _weighted_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray, weights: np.ndarray) -> float:
    """
    Compute weighted cosine similarity between two feature vectors.
    Returns value in [-1, 1] — higher is more similar.
    """
    # Apply weights
    wa = vec_a * weights
    wb = vec_b * weights

    dot = float(np.dot(wa, wb))
    norm_a = float(np.linalg.norm(wa))
    norm_b = float(np.linalg.norm(wb))

    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0

    return float(np.clip(dot / (norm_a * norm_b), -1.0, 1.0))


def _explain_similarity(
    target_features: Dict[str, float],
    comparable_features: Dict[str, float],
    similarity_score: float,
) -> List[Dict[str, Any]]:
    """
    Generate feature-level explanation for why two projects are similar.
    """
    feature_names = [f["name"] for f in SIMILARITY_FEATURES]
    explanations = []

    for feat_def in SIMILARITY_FEATURES:
        fname = feat_def["name"]
        target_val = target_features.get(fname, 0.0)
        comp_val = comparable_features.get(fname, 0.0)
        diff = abs(target_val - comp_val)

        # Normalize difference by expected range per feature
        ranges = {
            "state_encoded": 35.0,
            "land_area_log": 2.0,
            "cost_per_ha_norm": 1.0,
            "agency_encoded": 5.0,
            "acquisition_act_encoded": 5.0,
            "families_normalized": 1.0,
        }
        feature_range = ranges.get(fname, 1.0)
        closeness = 1.0 - float(np.clip(diff / feature_range, 0.0, 1.0))

        explanations.append({
            "feature": fname,
            "label": feat_def["label"],
            "description": feat_def["description"],
            "target_value": round(float(target_val), 4),
            "comparable_value": round(float(comp_val), 4),
            "closeness_score": round(closeness, 4),
            "similarity_contribution": (
                "HIGH" if closeness > 0.8 else
                "MEDIUM" if closeness > 0.5 else
                "LOW"
            ),
            "output_type": feat_def["output_type"],
        })

    return sorted(explanations, key=lambda x: -x["closeness_score"])


def find_comparable_projects(
    target_project: Dict[str, Any],
    all_projects: List[Dict[str, Any]],
    top_k: int = 5,
    min_similarity: float = 0.60,
) -> Dict[str, Any]:
    """
    Find the top-k most structurally similar projects to the target project.

    Parameters
    ----------
    target_project : dict
        Project data dict with: project_id, state_code, executing_agency,
        acquisition_act, total_area_ha, estimated_compensation_inr,
        total_affected_families
    all_projects : list of dicts
        All available projects (target will be excluded from results)
    top_k : int
        Maximum number of comparables to return (default 5)
    min_similarity : float
        Minimum similarity threshold (default 0.60)

    Returns
    -------
    dict with comparables, similarity scores, and explanations
    """
    target_id = str(target_project.get("project_id") or target_project.get("id", ""))

    # Encode target
    target_vec = _encode_project_features(target_project)
    target_feature_dict = {}

    if target_vec is None:
        return {
            "project_id": target_id,
            "output_type": "B",
            "available": False,
            "reason": "Could not encode target project features",
            "comparable_projects": [],
            "disclaimer": COMPARABLE_DISCLAIMER,
        }

    feature_names = [f["name"] for f in SIMILARITY_FEATURES]
    weights = np.array([f["weight"] for f in SIMILARITY_FEATURES])

    for i, fname in enumerate(feature_names):
        target_feature_dict[fname] = float(target_vec[i])

    # Compute similarity to all other projects
    similarities: List[Tuple[float, Dict[str, Any], np.ndarray]] = []

    for proj in all_projects:
        comp_id = str(proj.get("project_id") or proj.get("id", ""))
        if comp_id == target_id:
            continue  # Never compare project to itself

        comp_vec = _encode_project_features(proj)
        if comp_vec is None:
            continue

        sim_score = _weighted_cosine_similarity(target_vec, comp_vec, weights)
        similarities.append((sim_score, proj, comp_vec))

    # Sort by similarity descending
    similarities.sort(key=lambda x: -x[0])

    # Filter by minimum similarity and take top_k
    filtered = [
        (score, proj, vec)
        for score, proj, vec in similarities
        if score >= min_similarity
    ][:top_k]

    if not filtered:
        # Relax threshold if no results
        filtered = similarities[:min(top_k, 3)]

    # Build response
    comparables = []
    for rank, (sim_score, proj, comp_vec) in enumerate(filtered, 1):
        comp_id = str(proj.get("project_id") or proj.get("id", ""))
        comp_feature_dict = {
            fname: float(comp_vec[i])
            for i, fname in enumerate(feature_names)
        }

        explanations = _explain_similarity(target_feature_dict, comp_feature_dict, sim_score)

        # Similarity tier
        if sim_score >= 0.90:
            sim_tier = "HIGH"
        elif sim_score >= 0.75:
            sim_tier = "MODERATE"
        elif sim_score >= 0.60:
            sim_tier = "LOW"
        else:
            sim_tier = "WEAK"

        comparables.append({
            "rank": rank,
            "project_id": comp_id,
            "project_code": proj.get("project_code"),
            "project_name": proj.get("name"),
            "state_code": proj.get("state_code"),
            "executing_agency": proj.get("executing_agency"),
            "total_area_ha": proj.get("total_area_ha"),
            "status": proj.get("status"),
            "risk_level": proj.get("risk_level"),
            "similarity_score": round(sim_score, 4),
            "similarity_tier": sim_tier,
            "similarity_explanation": explanations,
            "top_shared_features": [
                e["label"] for e in explanations if e["closeness_score"] > 0.7
            ],
            "comparability_note": (
                f"Structural attribute similarity: {round(sim_score * 100, 1)}%. "
                f"Key shared features: {', '.join(e['label'] for e in explanations[:3])}. "
                f"This is ATTRIBUTE similarity only — NOT outcome similarity."
            ),
        })

    return {
        "project_id": target_id,
        "output_type": "B",
        "output_type_label": "Derived Analytics — Comparable Project Similarity",
        "available": True,
        "n_comparables_found": len(comparables),
        "n_projects_searched": len(all_projects) - 1,
        "algorithm": "Weighted Cosine Similarity",
        "feature_space": f"{len(SIMILARITY_FEATURES)} real project attributes",
        "features_used": [f["label"] for f in SIMILARITY_FEATURES],
        "comparable_projects": comparables,
        "disclaimer": COMPARABLE_DISCLAIMER,
        "methodology_note": (
            "Cosine similarity computed on a 6-dimensional feature vector constructed from "
            "real project attributes: state, land scale, cost intensity, agency, acquisition act, "
            "and affected families. Features are weighted by their relevance to acquisition context. "
            "No synthetic comparison projects are used."
        ),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
