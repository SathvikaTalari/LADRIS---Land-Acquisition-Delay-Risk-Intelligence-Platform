# LandPulse AI — Limitations & Governance Statement (Phase 7 Updated)

## Mandatory System Declarations

1. **Supervised Delay Model Status**:
   - Supervised delay prediction is **DEFERRED** due to the absence of public planned vs actual milestone completion dates across national portals ($N=10 < 200$ required).
   - The current predictive signal is an **unsupervised IsolationForest structural anomaly score**.

2. **Anomaly Risk vs Delay Probability**:
   - Anomaly risk measures structural statistical divergence from population norms.
   - Anomaly risk is **NOT** a calibrated delay probability or predicted number of delay days.

3. **Risk DNA Composite Profile**:
   - Risk DNA is an aggregated multi-dimensional decision-support profile.
   - It is NOT a new prediction model and does NOT claim causal linkage between any dimension and project delay.

4. **Temporal Risk Intelligence**:
   - Risk history is derived ONLY from real prediction observations logged by the monitoring system.
   - No historical points are fabricated, imputed, or synthetically generated.
   - When no observations exist, the system explicitly returns `temporal_data_available: false`.

5. **Statistical Bottleneck Signals**:
   - Bottleneck signals are observed statistical correlations in project data, NOT causal explanations.
   - Every bottleneck insight displays explicit sample size ($N$), confidence level, and data limitations.
   - Groups with $N < 5$ return `INSUFFICIENT_SAMPLE`.

6. **Comparable Project Benchmarking**:
   - Similarity analysis uses weighted cosine similarity on real structural project attributes.
   - Similarity is STRUCTURAL ATTRIBUTE similarity ONLY — NOT outcome similarity.

7. **Scenario Estimates vs Causal Predictions**:
   - What-If simulation and Greedy Resource Allocation outputs represent **read-only scenario estimates** calculated under hypothetical parameters.
   - They are labeled `OUTPUT TYPE E` and do NOT constitute actual government resource allocations.

8. **Decision-Support Recommendations**:
   - Interventions and priority queue rankings are **decision-support recommendations**.
   - They do not autonomously execute government or legal decisions.

9. **Spatial Accuracy**:
   - Projects lacking verified latitude/longitude coordinates are explicitly flagged as *"Location Unavailable"* and omitted from spatial maps to prevent synthetic positioning.
