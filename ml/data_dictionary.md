# LandPulse AI — Data Dictionary & Feature Catalog (Phase 2 Real-Data Edition)

This document defines the real fields obtained from verified public government datasets, their transformations, and their availability for ML inference.

---

## 1. BhoomiRashi Public Search Table (`BHOOMIRASHI_PUBLIC_SEARCH_TABLE`)

Source Organization: **Ministry of Road Transport and Highways (MoRTH)**  
Source URL: [bhoomirashi.gov.in](https://bhoomirashi.gov.in/)  
Access Method: Public HTML search table (no API / no bulk export)  
Authenticity: `OFFICIAL_PUBLIC`  

| Field Name | Data Type | Description | Predictor / Feature | Availability at Prediction Time | Leakage Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `state` | Categorical (Str) | ISO State Code (e.g. 'MH', 'UP') | `state_encoded` | **Yes** (At 3A issuance) | None |
| `district` | Categorical (Str) | Revenue District Name | Categorical filter | **Yes** (At 3A issuance) | None |
| `agency` | Categorical (Str) | Executing Agency (NHAI, NHIDCL, PWD) | `agency_encoded` | **Yes** (At 3A issuance) | None |
| `land_required_ha` | Continuous (Float) | Sanctioned land area in hectares | `land_required_ha_log` | **Yes** (At 3A issuance) | None |
| `sanctioned_la_cost_crore` | Continuous (Float) | Land acquisition budget (₹ Crore) | `cost_per_ha` | **Yes** (At 3A issuance) | None |
| `notification_3a_date` | Date (YYYY-MM-DD) | Section 3A notification date | `3a_year`, `has_3a_notification` | **Yes** (Prediction Anchor) | None |
| `notification_3d_date` | Date (YYYY-MM-DD) | Section 3D declaration date | `notification_interval_days`, `has_3d_notification` | **No** (Only post-3D) | Medium (Retrospective only) |

---

## 2. Derived ML Features (Anomaly Scorer Engine)

Model: **Unsupervised IsolationForest Anomaly Scorer** (`v1.0-anomaly`)  
Target: **Anomaly Score** \(\in [0.0, 1.0]\) (Measures structural unusualness relative to population baseline)  

| Feature Name | Type | Derived From | Transformation / Formula | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `land_required_ha_log` | Numerical | `land_required_ha` | \(\ln(1 + \text{land\_required\_ha})\) | Log-scaled area to handle heavy skewness |
| `cost_per_ha` | Numerical | `sanctioned_la_cost_crore`, `land_required_ha` | \(\frac{\text{sanctioned\_la\_cost\_crore}}{\text{land\_required\_ha}}\) | Cost intensity (high cost/ha signals peri-urban/complex land) |
| `notification_interval_days` | Numerical | `notification_3d_date`, `notification_3a_date` | \(\text{Date}_{3D} - \text{Date}_{3A}\) | Days between preliminary 3A and declaration 3D |
| `state_encoded` | Categorical | `state` | Ordinal Label Encoding | State geographical grouping |
| `agency_encoded` | Categorical | `agency` | Ordinal Label Encoding | Implementing agency baseline risk profile |
| `has_3a_notification` | Binary | `notification_3a_date` | \(1\) if present, else \(0\) | Baseline milestone flag |
| `has_3d_notification` | Binary | `notification_3d_date` | \(1\) if present, else \(0\) | Advanced milestone flag |

---

## 3. Documented Data Gaps (Unavailable Fields)

The following fields are **NOT available** from any accessible official public dataset as of Phase 2:

| Unavailable Field | Intended Purpose | Reason for Absence | Resulting System Action |
| :--- | :--- | :--- | :--- |
| `planned_completion_date` | Supervised delay label | Not published in public BhoomiRashi table | Supervised delay target **cannot** be derived |
| `actual_completion_date` | Supervised delay label | Not published in public BhoomiRashi table | Supervised delay target **cannot** be derived |
| `compensation_disbursement_date` | Financial progress feature | Gated behind CALA portal authentication | Documented as data gap |
| `legal_dispute_case_number` | Legal risk factor | Not linked to BhoomiRashi public views | Documented as data gap |
| `rr_family_relocation_count` | R&R milestone tracking | Gated behind internal portal logins | Documented as data gap |

---

## 4. Model Output Classification & Risk Tiers

Because supervised delay labels are unavailable, the model produces an **Unsupervised Anomaly Score**:

- **HIGH_ANOMALY**: Anomaly Score \(\ge 0.75\) — Project features significantly deviate from typical acquisition profiles.
- **MODERATE_ANOMALY**: \(0.50 \le \text{Score} < 0.75\)
- **LOW_ANOMALY**: \(0.25 \le \text{Score} < 0.50\)
- **TYPICAL**: Score \(< 0.25\) — Acquisition parameters match standard national distribution.
