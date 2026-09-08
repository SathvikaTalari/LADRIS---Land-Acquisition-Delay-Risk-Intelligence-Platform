"""
LADRIS — Phase 7 Intelligence API Schemas (Pydantic v2)
=============================================================
Request and response schemas for /api/v1/intelligence/ endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Shared ───────────────────────────────────────────────────────────────────

class OutputLabel(BaseModel):
    output_type: str = Field(description="A/B/C/D/E classification")
    output_type_label: str = Field(description="Human-readable output type description")


class ConfidenceLevel(BaseModel):
    level: str
    label: str
    note: str


# ─── Risk DNA ─────────────────────────────────────────────────────────────────

class DNADimension(BaseModel):
    score: float
    weight: float
    contribution: Optional[float] = None
    available: bool = True
    output_type: str
    output_type_label: str
    description: str


class AnomályDimension(DNADimension):
    risk_level: Optional[str] = None


class StageDimension(DNADimension):
    peak_stage: Optional[str] = None
    peak_stage_value: Optional[float] = None
    stage_details: Optional[List[Dict[str, Any]]] = None


class CompletnessDimension(BaseModel):
    score: float
    completeness_pct: float
    risk_contribution: float
    weight: float
    output_type: str
    output_type_label: str
    description: str


class ShapDimension(DNADimension):
    top_driver_name: Optional[str] = None
    top_driver_contribution: Optional[float] = None


class ReliabilityDimension(BaseModel):
    score: float
    confidence_assessment: str
    is_out_of_distribution: bool
    ood_details: Optional[Dict[str, Any]] = None
    weight: float
    risk_contribution: float
    output_type: str
    output_type_label: str
    description: str


class TemporalObservation(BaseModel):
    timestamp: str
    anomaly_score: float
    data_completeness_pct: Optional[float] = None
    stage_fingerprint_risk: Optional[float] = None
    model_version: Optional[str] = None
    source: str = "monitoring_log.jsonl"


class TemporalInfo(BaseModel):
    observations_available: bool
    observation_count: int
    observations: List[TemporalObservation] = []
    risk_trend: Optional[float] = None
    risk_trend_label: str
    temporal_disclaimer: str
    output_type: str
    output_type_label: str


class RiskDNAResponse(BaseModel):
    project_id: str
    output_type: str = "RISK_DNA"
    output_label: str
    dna_composite_score: float
    dna_tier: str  # CRITICAL / HIGH / MEDIUM / LOW
    disclaimer: str
    dimensions: Dict[str, Any]
    temporal: TemporalInfo
    weights: Dict[str, float]
    computed_at: str
    provenance: Dict[str, str]


# ─── Risk History ─────────────────────────────────────────────────────────────

class EscalationEvent(BaseModel):
    from_timestamp: str
    to_timestamp: str
    from_score: float
    to_score: float
    delta: float
    event_type: str


class ScoreStats(BaseModel):
    min: float
    max: float
    mean: float
    range: float


class RiskHistoryResponse(BaseModel):
    project_id: str
    output_type: str
    output_type_label: str
    temporal_data_available: bool
    observation_count: int
    observations: List[TemporalObservation] = []
    risk_trend: Optional[float] = None
    risk_trend_label: str
    escalation_events: List[EscalationEvent] = []
    deescalation_events: List[EscalationEvent] = []
    first_observation_date: Optional[str] = None
    last_observation_date: Optional[str] = None
    score_statistics: Optional[ScoreStats] = None
    temporal_disclaimer: str
    trend_note: Optional[str] = None


# ─── Bottleneck Discovery ─────────────────────────────────────────────────────

class BottleneckTypeEntry(BaseModel):
    bottleneck_type: str
    label: str
    count: int
    percentage: float
    description: str
    typical_cause: str
    confidence: ConfidenceLevel
    sample_size: int
    data_limitation: str


class StateBottleneck(BaseModel):
    state_code: str
    n_projects: int
    available: bool
    confidence: ConfidenceLevel
    dominant_bottleneck: Optional[str] = None
    bottleneck_label: Optional[str] = None
    bottleneck_counts: Optional[Dict[str, int]] = None
    mean_stage_risks: Optional[Dict[str, float]] = None
    official_delay_evidence: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    data_limitation: Optional[str] = None


class ClusterEntry(BaseModel):
    cluster_id: int
    cluster_size: int
    centroid_stage_risks: Dict[str, float]
    peak_stage: str
    dominant_bottleneck: str
    bottleneck_label: str
    states_in_cluster: List[str]
    confidence: ConfidenceLevel
    data_limitation: str


class ClusterAnalysis(BaseModel):
    available: bool
    algorithm: Optional[str] = None
    n_clusters_selected: Optional[int] = None
    n_samples: Optional[int] = None
    feature_space: Optional[str] = None
    clusters: Optional[List[ClusterEntry]] = None
    algorithm_note: Optional[str] = None
    reason: Optional[str] = None


class BottleneckResponse(BaseModel):
    output_type: str
    output_type_label: str
    available: bool
    n_projects_analyzed: int
    n_total_projects: Optional[int] = None
    national_summary: Optional[Dict[str, Any]] = None
    bottleneck_distribution: Optional[List[BottleneckTypeEntry]] = None
    state_bottlenecks: Optional[List[StateBottleneck]] = None
    cluster_analysis: Optional[ClusterAnalysis] = None
    data_provenance: Optional[Dict[str, Any]] = None
    disclaimer: str
    computed_at: str
    reason: Optional[str] = None


# ─── Comparable Projects ──────────────────────────────────────────────────────

class FeatureSimilarityEntry(BaseModel):
    feature: str
    label: str
    description: str
    target_value: float
    comparable_value: float
    closeness_score: float
    similarity_contribution: str  # HIGH / MEDIUM / LOW
    output_type: str


class ComparableProject(BaseModel):
    rank: int
    project_id: str
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    state_code: Optional[str] = None
    executing_agency: Optional[str] = None
    total_area_ha: Optional[float] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    similarity_score: float
    similarity_tier: str  # HIGH / MODERATE / LOW / WEAK
    similarity_explanation: List[FeatureSimilarityEntry]
    top_shared_features: List[str]
    comparability_note: str


class ComparableProjectsResponse(BaseModel):
    project_id: str
    output_type: str
    output_type_label: str
    available: bool
    n_comparables_found: int
    n_projects_searched: int
    algorithm: str
    feature_space: str
    features_used: List[str]
    comparable_projects: List[ComparableProject]
    disclaimer: str
    methodology_note: str
    computed_at: str
    reason: Optional[str] = None


# ─── Priority Queue ───────────────────────────────────────────────────────────

class QueueEntry(BaseModel):
    rank: int
    project_id: str
    project_code: Optional[str] = None
    project_name: Optional[str] = None
    state_code: Optional[str] = None
    executing_agency: Optional[str] = None
    status: Optional[str] = None
    composite_priority_score: float
    queue_tier: str  # CRITICAL / HIGH / MEDIUM / LOW
    score_breakdown: Dict[str, Any]
    risk_signals: Dict[str, Any]
    bottleneck_type: Optional[str] = None
    recommended_resource: Optional[Dict[str, str]] = None
    data_completeness_pct: float
    output_type: str
    output_type_label: str
    scoring_note: Optional[str] = None


class TierSummary(BaseModel):
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0


class PriorityQueueResponse(BaseModel):
    output_type: str
    output_type_label: str
    total_projects: int
    tier_summary: Dict[str, int]
    active_filters: Dict[str, Optional[str]]
    queue: List[QueueEntry]
    queue_disclaimer: str
    computed_at: str


# ─── Resource Scenario ────────────────────────────────────────────────────────

class ResourceScenarioRequest(BaseModel):
    capacity_constraints: Dict[str, int] = Field(
        description="Resource type → available capacity. Keys: LEGAL, COMPENSATION, RR, FIELD",
        example={"LEGAL": 3, "COMPENSATION": 2, "RR": 1},
    )
    filter_state: Optional[str] = Field(
        default=None,
        description="Optional: limit scenario to projects in this state",
    )
    filter_agency: Optional[str] = Field(
        default=None,
        description="Optional: limit scenario to projects by this agency",
    )


class ResourceScenarioResponse(BaseModel):
    output_type: str = "E"
    output_type_label: str = "Hypothetical Scenario Estimate — Decision-Support Simulation"
    simulation_type: str
    disclaimer: str
    input_constraints: Dict[str, int]
    total_projects: int
    assigned_count: int
    deferred_count: int
    remaining_capacity: Dict[str, int]
    assigned_projects: List[Dict[str, Any]]
    deferred_projects: List[Dict[str, Any]]
    simulation_note: str
    computed_at: str
    available: bool = True
    reason: Optional[str] = None
