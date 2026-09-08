# LandPulse AI — Canonical Data Gap Report & Supervised Target Specification

## Executive Summary
Supervised delay prediction training is **DEFERRED**. The available public data does not contain a sufficient volume of project-level planned vs. actual milestone dates necessary to derive a statistically defensible delay label. This document records the scientific justification, dataset audit results, canonical target specification, and the alternative unsupervised architecture implemented in LandPulse AI Phase 3.

---

## 1. Datasets Audited

### 1.1 BhoomiRashi Portal (`bhoomirashi.gov.in`)
- **Status**: 56 project records ingested
- **Fields Available**: State, district, executing agency, land required (ha), sanctioned cost (Cr), Section 3A date, Section 3D date.
- **Fields Missing**: Planned project start date, planned project end date, actual project completion date, stage completion dates, delay status.
- **Conclusion**: Excellent for structural feature engineering and notification duration analysis; lacks target labels.

### 1.2 Open Government Data Platform (`data.gov.in`)
- **Status**: 10 delayed project records ingested (2023–2025)
- **Fields Available**: Project code, name, state, area (ha), compensation (INR), planned start, target completion, status (`DELAYED`, `ACTIVE`, `APPROVED`), `delay_months`, delay reason.
- **Fields Missing**: Large-sample historical time-series across all states.
- **Conclusion**: Provides authentic real delay outcome definitions, but $N = 10$ is far below the required $N \ge 200$ threshold for supervised classifier training.

### 1.3 MoRTH Annual Reports (PDFs)
- **Status**: 36 state-year aggregate records parsed
- **Conclusion**: State-level highway construction aggregates only — no per-project data.

---

## 2. Canonical Supervised Target Specification

When a sufficient dataset ($N \ge 200$) is acquired, the supervised target formula is defined as:

$$\text{delay\_event}_i = \begin{cases} 1 & \text{if } \text{delay\_months}_i \ge 6 \text{ or } (\text{actual\_completion}_i - \text{planned\_completion}_i) > 90 \text{ days} \\ 0 & \text{otherwise} \end{cases}$$

### Domain Justification
MoRTH infrastructure project monitoring rules classify schedule slippage exceeding 1 quarter (90 days / 6 months) as material contract delay requiring intervention.

---

## 3. Implemented Alternative: Phase 3 Dual-Signal Engine

In accordance with Phase 3 rules, LandPulse AI implements two distinct signals:

1. **Structural Anomaly Risk (IsolationForest Model)**:
   - Trained on 56 real BhoomiRashi project records.
   - Outputs a score between $0.0$ and $1.0$ measuring structural divergence from national norms.
   - Labeled clearly as **"Structural Anomaly Score"** — NOT delay probability.

2. **Stage Risk Fingerprint**:
   - Calculates proxy risk signals across 6 acquisition stages (Notification, Objection, Award, Compensation, R&R, Possession).
   - NOTIFICATION stage uses real 3A$\rightarrow$3D interval signal; other stages use structural proxies.

3. **Supervised Delay Risk**:
   - Explicitly marked **`DEFERRED`** (`score: null`).
   - No fake numbers or synthetic probability scores are generated.

---

## 4. Pathway to Enabling Supervised Training

Supervised classification (Logistic Regression, Random Forest, XGBoost, LightGBM) will activate automatically when any of the following data sources provide $N \ge 200$ labeled records:
1. RTI (Right to Information) project milestone request to MoRTH / NHAI.
2. NIC (National Informatics Centre) government-to-government data access.
3. State CALA (Competent Authority for Land Acquisition) district-level acquisition completion registers.
