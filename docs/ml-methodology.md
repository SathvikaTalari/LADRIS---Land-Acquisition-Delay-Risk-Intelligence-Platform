# LandPulse AI — ML Methodology & Risk Engine Architecture (Phase 7 Updated)

## 1. Problem Formulation & Dual-Signal Architecture

### Dual-Signal Separation
LandPulse AI maintains strict separation between structural anomaly detection and supervised delay prediction:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LandPulse AI API                                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌──────────────────────────────┐                      ┌──────────────────────┐
│   Signal 1: Anomaly Risk     │                      │ Signal 2: Delay Risk │
│   (IsolationForest Model)    │                      │ (Supervised Model)   │
├──────────────────────────────┤                      ├──────────────────────┤
│ - Model: IsolationForest     │                      │ - Status: DEFERRED   │
│ - Output: Score ∈ [0.0, 1.0] │                      │ - Score: null        │
│ - Trained on: BhoomiRashi    │                      │ - Reason: No public  │
│   56 real NH project records │                      │   planned vs actual  │
│ - Measures: Structural       │                      │   milestone dates    │
│   unusualness relative to    │                      │ - Target threshold:  │
│   national baseline          │                      │   N ≥ 200 required   │
└──────────────────────────────┘                      └──────────────────────┘
```

> **CRITICAL RULE**: Structural Anomaly Risk $\neq$ Delay Probability. Anomaly scores measure structural divergence from population norms, NOT probability of delay.

---

## 2. Supervised Target Specification & Deferral Rationale

### Target Definition
When sufficient labeled outcome data exists ($N \ge 200$), the target is defined as:

$$\text{delay\_event}_i = \begin{cases} 1 & \text{if } \text{delay\_months}_i \ge 6 \text{ or } (\text{actual\_end}_i - \text{planned\_end}_i) > 90 \text{ days} \\ 0 & \text{otherwise} \end{cases}$$

### Current Data Availability & Gap
- **DataGov.in Ingested**: 10 real delayed project records (2023–2025) with `delay_months` (range 3–24 months).
- **Gap**: $N = 10 < 200$ minimum requirement.
- **Decision**: Supervised classification models (Logistic Regression, Random Forest, XGBoost, LightGBM) are **DEFERRED**. The architecture is pluggable for future training when $N \ge 200$.

---

## 3. Phase 7 Government Decision Intelligence Algorithms

### A. Risk DNA Composer
Combines 5 independent intelligence dimensions into a single multi-dimensional profile:

$$\text{Risk\_DNA\_Score} = w_1 S_{\text{anomaly}} + w_2 S_{\text{stage}} + w_3 (1 - S_{\text{completeness}}) + w_4 S_{\text{shap}} + w_5 (1 - S_{\text{reliability}})$$

Where:
- $w_1 = 0.30$ (IsolationForest Anomaly Score)
- $w_2 = 0.30$ (Stage Fingerprint Peak Risk)
- $w_3 = 0.15$ (Data Incompleteness Penalty)
- $w_4 = 0.15$ (SHAP Dominant Driver Severity)
- $w_5 = 0.10$ (Out-of-Distribution Reliability Penalty)

### B. Statistical Bottleneck Discovery Engine
Applies K-means clustering ($k \in [3, 5]$) on 6-dimensional stage risk feature vectors $V_i = [r_{\text{NOTIFICATION}}, r_{\text{OBJECTION}}, r_{\text{AWARD}}, r_{\text{COMPENSATION}}, r_{\text{RR}}, r_{\text{POSSESSION}}]$:
- Standardized scaling via `StandardScaler`
- Centroid analysis to identify dominant bottleneck profiles
- Small-sample safeguard: Groups with $N < 5$ return `INSUFFICIENT_SAMPLE`
- Every insight displays explicit `sample_size`, `confidence_level`, and `data_limitation`
- Non-causal rule: Patterns represent observed correlations, NOT causal proofs of delay

### C. Comparable Project Finder (Cosine Similarity Benchmarking)
Calculates structural attribute similarity between a target project $A$ and candidate projects $B$:

$$\text{CosineSim}(A, B) = \frac{\sum_{k=1}^6 w_k A_k B_k}{\sqrt{\sum_{k=1}^6 w_k A_k^2} \sqrt{\sum_{k=1}^6 w_k B_k^2}}$$

Feature space:
1. `state_encoded` (weight = 2.0)
2. `land_area_log` (weight = 1.5)
3. `cost_per_ha_norm` (weight = 1.5)
4. `agency_encoded` (weight = 1.0)
5. `acquisition_act_encoded` (weight = 1.0)
6. `families_normalized` (weight = 1.0)

Returns top $k$ comparables ($S \ge 0.60$) with feature-level closeness explanations. Explicitly labeled as attribute similarity, NOT outcome similarity.

### D. Cross-Project Priority Queue & Resource Allocation Simulation
Extends Phase 4 priority scorer to rank all projects:

$$\text{Composite\_Priority} = 0.70 \cdot \text{Base\_Priority} + 0.15 \cdot \text{Bottleneck\_Modifier} + 0.10 \cdot \text{Comparable\_Context} + 0.05 \cdot \text{Freshness}$$

**Greedy Resource Scenario Simulation**:
Given capacity constraints $C = \{C_{\text{LEGAL}}, C_{\text{COMPENSATION}}, C_{\text{RR}}, C_{\text{FIELD}}\}$, projects are assigned sequentially in priority order. Outputs labeled `OUTPUT TYPE E (Hypothetical Scenario Estimate)` — NOT actual government allocation.

---

## 4. Evidence Classification Standard (Government Transparency)

Every output in LandPulse AI is classified into one of 5 categories:
- **A — Official Source Data**: Unmodified attributes from BhoomiRashi/DataGov/MoRTH
- **B — Derived Analytics**: Statistical metrics, bottleneck distributions, cosine similarity
- **C — ML/Model Signals**: IsolationForest anomaly score, stage fingerprint, SHAP
- **D — Decision-Support Recommendations**: Priority queue ranking, catalog interventions
- **E — Hypothetical Scenario Estimates**: What-If simulation outputs, greedy resource allocation
