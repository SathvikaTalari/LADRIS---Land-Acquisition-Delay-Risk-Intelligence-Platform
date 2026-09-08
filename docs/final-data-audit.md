# LandPulse AI — Real-Data Integrity Audit

**Document Version:** 1.0.0  
**Audit Status:** PASSED — STRICT DATA INTEGRITY ENFORCED  
**Audit Date:** August 25, 2026  

---

## Executive Summary

This Real-Data Integrity Audit verifies that **LandPulse AI** relies exclusively on verified, authentic public government data sources from the Ministry of Road Transport and Highways (MoRTH), BhoomiRashi portal, and Data.gov.in. 

**Zero synthetic or fabricated project records exist in production database tables.** All production outputs enforce strict data provenance, explicit disclaimers, and clear signal separation.

---

## 1. Registered Data Sources & Provenance

| Dataset Name | Source Organization | Source URL / Asset | Data Period | Record Count | File Format | Provenance Classification |
|---|---|---|---|---|---|---|
| **BHOOMIRASHI_PUBLIC_SEARCH_TABLE** | Ministry of Road Transport and Highways (MoRTH) | [bhoomirashi.gov.in](https://bhoomirashi.gov.in/) | 2018–2026 | 56 records | HTML / CSV | Official Public Government Portal |
| **MORTH_ANNUAL_REPORT_AGGREGATE** | MoRTH, Government of India | [morth.nic.in](https://morth.nic.in/annual-report) | FY 2022–23 | 36 records | PDF / CSV | Official Government Annual Publication |
| **DATAGOV_DELAYED_PROJECTS** | MoSPI / Data.gov.in | [data.gov.in](https://data.gov.in/) | 2020–2025 | 10 records | Open API / CSV | Official Government Transparency Portal |

---

## 2. Fields Extracted & Used in Pipeline

### Extracted Features
- `state_code`: Indian State / Union Territory identifier (e.g., MH, UP, TN, GJ)
- `district_codes`: District administrative units covered by acquisition
- `total_area_ha`: Total land acquisition area required in hectares
- `estimated_compensation_inr`: Sanctioned land acquisition compensation cost (in INR)
- `notification_3a_date`: Gazette publication date under Section 3A (Intention to acquire)
- `notification_3d_date`: Gazette publication date under Section 3D (Declaration of acquisition)
- `executing_agency`: Nodal/Executing agency (NHAI, NHIDCL, MoRTH, PWD)

### Computed Derived Features
- `land_required_ha_log`: `log(1 + total_area_ha)` (log-transformed scale)
- `cost_per_ha`: Compensation cost in Crore INR per hectare
- `notification_interval_days`: Calendar days elapsed between 3A and 3D Gazette notifications

---

## 3. Data Gaps & Known Limitations

> [!WARNING]
> **Supervised Delay Model Deferred**: Public BhoomiRashi search tables do NOT publish project-level planned vs. actual completion dates or operational milestone completion logs.

- **Unavailable Fields in Public Tables:**
  - Project baseline schedule / planned completion date
  - Project actual completion date
  - Section 3G (Award determination) per-landowner timestamps
  - Detailed litigation / court stay status per survey number

- **Supervised Model Eligibility:**
  - Because no defensible ground-truth delay label ($Y_{delay} \in \{0, 1\}$) exists in public search tables, supervised supervised classification/regression is **DEFERRED**.
  - No synthetic delay probabilities or artificial delay days are generated.

---

## 4. Signal Separation Enforcement

LandPulse AI strictly separates ML outputs into two independent signals:

1. **Structural Anomaly Risk (`anomaly_risk`)**:
   - Model: `IsolationForest` unsupervised model trained on BhoomiRashi national population.
   - Output: Structural Anomaly Score ($S_{anomaly} \in [0.0, 1.0]$).
   - Meaning: Relative structural unusualness of land area, cost intensity, or notification interval compared to historical national distribution.
   - Governance Statement: **ANOMALY RISK $\neq$ DELAY PROBABILITY.** High anomaly score does not imply project delay.

2. **Predictive Delay Probability (`delay_risk`)**:
   - Status: `null` with `supervised_training_status: DEFERRED` for general projects.
   - Exception: Explicitly marked `OFFICIAL_OUTCOME_VERIFIED` only for projects matching verified Data.gov.in / MoSPI delayed project records.

---

## 5. Model Eligibility & Quality Gates

Every intelligence endpoint evaluates project completeness before executing inference:

- **Minimum Completeness Requirement:** $\ge 50\%$ required input fields present (`total_area_ha`, `state_code`).
- **Out-of-Distribution (OOD) Gate:** Standardized Z-score distance from training means checked ($Z > 3.0$ triggers `LOW` confidence warning).
- **Controlled Fallback:** If minimum data requirements are not met, API returns status `INSUFFICIENT_DATA` with missing field details. Inventory fallbacks or synthetic numbers are strictly prohibited.

---

## Conclusion & Governance Statement

All project records and intelligence outputs in LandPulse AI are fully traceable to official Government of India public data releases. The platform adheres to the highest standards of data integrity, transparency, and scientific honesty.
