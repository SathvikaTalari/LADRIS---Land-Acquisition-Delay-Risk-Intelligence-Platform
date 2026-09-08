# LandPulse AI — Model Card: Risk Anomaly Scorer & Intelligence Platform (v1.0-anomaly / Phase 7)

## 1. Model Details
- **Model Name**: LandPulse IsolationForest Risk Anomaly Scorer & Decision Intelligence Platform
- **Model Version**: `v1.0-anomaly` (Phase 7 upgrade)
- **Model Type**: Unsupervised IsolationForest (scikit-learn Pipeline with SimpleImputer + StandardScaler) + Phase 7 Decision Intelligence Layer
- **Developer**: LandPulse AI Team
- **Release Date**: August 2026
- **License**: Government Open Data License (India) / Internal Operations Use
- **Mandatory Governance Statement**: "IsolationForest provides a structural anomaly signal and is not a supervised prediction of delay probability."

---

## 2. Intended Use
- **Primary Use**: Identifying national highway infrastructure land acquisition projects whose structural parameters diverge significantly from national baseline, composing 5-dimensional Risk DNA, analyzing statistical bottlenecks, ranking project priority, and simulating constrained resource allocation.
- **Intended Users**: MoRTH, NHAI, state CALA (Competent Authority for Land Acquisition) officers, district collectors, project analysts.
- **Decision Support Role**: High anomaly risk scores and bottleneck signals trigger investigative review by project officers — NOT automated decisions or sanction cancellations.

---

## 3. Prohibited Use
- **Prohibited**: Claiming the anomaly score or Risk DNA represents a probabilistic delay prediction.
- **Prohibited**: Automated penalty imposition, contractor blacklisting, or land compensation reduction based on model scores.
- **Prohibited**: Use on non-infrastructure private land acquisition without model re-calibration.

---

## 4. Training Data & Data Coverage
- **Primary Source**: BhoomiRashi Public Search Table (`bhoomirashi.gov.in`)
- **Secondary Source**: DataGov.in Delayed Projects Register (2023–2025)
- **Record Count**: 56 valid prediction-eligible BhoomiRashi project records
- **Geographic Coverage**: 20 States (MH, UP, KA, GJ, RJ, TN, AP, MP, TS, PB, HR, JH, BR, WB, CG, OD, KL, UK, HP, AS, GA)
- **Training Date**: August 2026
- **Data Period**: Projects notified 2020–2024

---

## 5. Model Features
1. `land_required_ha_log`: $\ln(1 + \text{land\_required\_ha})$ — reduces area skewness
2. `cost_per_ha`: $\frac{\text{sanctioned\_la\_cost\_crore}}{\text{land\_required\_ha}}$ — land acquisition cost intensity (Cr/ha)
3. `has_3a_notification`: Binary flag (1 if Section 3A preliminary notification date present)
4. `has_3d_notification`: Binary flag (1 if Section 3D final declaration date present)
5. `state_encoded`: Ordinal label encoding of state code
6. `agency_encoded`: Ordinal label encoding of executing agency (NHAI, NHIDCL, State PWD)

---

## 6. Supervised Target Specification & Deferral Status
- **Target Definition**: $\text{delay\_event} = 1$ if $\text{delay\_months} \ge 6$ or $\text{actual\_duration} - \text{planned\_duration} > 90 \text{ days}$.
- **Status**: **DEFERRED**
- **Reason**: Current public datasets contain only 10 project records with real delay outcomes — below the 200-record statistical threshold.
- **Pluggable Architecture**: Supervised models (Logistic Regression, Random Forest, XGBoost, LightGBM) will activate automatically when $N \ge 200$.

---

## 7. Validation Strategy & Evaluation Metrics
- **Anomaly Scorer Metrics**:
  - Contamination parameter: $0.10$ (assumes ~10% outliers in national baseline)
  - Anomaly rate in training population: $10.7\%$ (6 of 56 records tagged anomalous)
  - Score range: $[0.0, 1.0]$ after min-max scaling relative to population
  - Out-of-distribution threshold: $Z_{\text{max}} > 3.0$
- **Phase 7 Intelligence Validation**:
  - Risk DNA: 5-dimensional weighted composition (weights sum = 1.0)
  - Bottleneck Discovery: K-means clustering ($k \in [3, 5]$) on stage risk feature vectors
  - Comparable Projects: Weighted Cosine Similarity on structural attributes ($S \ge 0.60$)
  - Priority Queue: Extended scoring formula + greedy resource simulation

---

## 8. Limitations & Known Biases
1. **Sample Size**: Trained on 56 real project records; statistical representation will improve as more state CALA records are ingested.
2. **State Selection Bias**: High-activity highway construction states (MH, UP, KA, GJ) are over-represented relative to North-Eastern states.
3. **Uncalibrated Scores**: IsolationForest outputs relative unusualness scores — NOT calibrated probabilities.
4. **Proxy Stage Signals**: Stage risk signals for 5 of 6 stages are proxy-derived due to lack of per-stage completion logs in public tables.

---

## 9. Phase 7: Government Decision Intelligence Platform
- **Risk DNA**: Assembles IsolationForest anomaly score, 6-stage risk fingerprint, SHAP top contributor, data completeness, and prediction reliability into a structured composite profile.
- **Temporal Risk Intelligence**: Reads real logged prediction observations (`monitoring_log.jsonl`). Detects escalation/de-escalation deltas. Clearly labels unavailable temporal data (`NO_DATA`). Never fabricates historical points or future dates.
- **Bottleneck Discovery Engine**: Statistical K-means clustering on stage risk vectors. Displays explicit `sample_size`, `confidence_level`, and `data_limitation` for every insight. Non-causal standard enforced.
- **Comparable Project Finder**: Cosine similarity benchmarking on real structural features (state, land scale, cost intensity, agency, act, families). Shows feature-level closeness explanations.
- **Cross-Project Priority Queue & Simulator**: Extended priority scoring across all projects. Includes greedy resource allocation simulation under capacity constraints (labeled `OUTPUT TYPE E`).
