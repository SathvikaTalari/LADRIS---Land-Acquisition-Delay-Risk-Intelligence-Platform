# LandPulse AI — Demo Project Selection Guide

**Document Version:** 1.0.0  
**Purpose:** Select authentic, verified production project records for hackathon demo walkthroughs.  
**Policy:** Zero synthetic demo records. All demo flows run exclusively on real ingested government project data.

---

## Recommended Demo Project 1: Pune Peripheral Ring Road Acquisition

### Project Details & Metadata
- **Project Code:** `MH-NH-PUNE-01`
- **Project Name:** Pune Peripheral Ring Road Land Acquisition Corridor
- **State Code:** `MH` (Maharashtra)
- **District:** Pune District
- **Executing Agency:** NHAI (National Highways Authority of India)
- **Acquisition Act:** RFCTLARR 2013 / NH Act 1956

### Why Selected for Demo
- **Maximum Intelligence Coverage:** Contains 100% complete field data (`total_area_ha: 145.2`, `estimated_compensation_inr: 62.5 Cr`, `total_affected_families: 450`).
- **High Anomaly Risk Signal:** Exhibits structural cost intensity ($4.30\text{ Cr/ha}$) and large population impact, triggering a High Anomaly Risk score ($0.78$) and firing 3 intervention candidate rules.
- **Complete Stage Lifecycle:** Demonstrates all 6 lifecycle stages with proxy risk signals and Section 3A/3D notification timestamps.
- **Full What-If Simulation Support:** Eligible for all 4 simulatable parameters (`cost_per_ha`, `compensation_completion_pct`, `area_acquired_pct`, `total_affected_families`).

---

## Recommended Demo Project 2: Varanasi Ring Road Phase II (UP)

### Project Details & Metadata
- **Project Code:** `UP-NH-VNS-02`
- **Project Name:** Varanasi Ring Road Phase II Acquisition
- **State Code:** `UP` (Uttar Pradesh)
- **District:** Varanasi District
- **Executing Agency:** NHAI / MoRTH

### Why Selected for Demo
- **Cross-State Comparison:** Demonstrates multi-state geographic coverage (Uttar Pradesh vs. Maharashtra).
- **Moderate Anomaly Risk:** Scores in the Medium Risk tier ($0.58$), showing contrast against Pune Ring Road in the Priority Intelligence Queue.

---

## Demonstration Feature Matrix

| Feature / Screen | Pune Ring Road (`MH-NH-PUNE-01`) | Varanasi Ring Road (`UP-NH-VNS-02`) | Unmonitored Project |
|---|---|---|---|
| **Identity & Status** | Available | Available | Available |
| **Structural Anomaly Score** | 0.78 (High) | 0.58 (Medium) | Insufficient Data (Controlled) |
| **Supervised Delay Prob.** | Null (Deferred) | Null (Deferred) | Null (Deferred) |
| **Stage Risk Fingerprint** | 6 Stages Available | 6 Stages Available | Available |
| **SHAP Feature Explanation** | Top 4 Contributors | Top 3 Contributors | N/A |
| **Intervention Priority** | Priority 84.5 / 100 | Priority 62.0 / 100 | Low Priority |
| **What-If Scenario Simulation**| Eligible (4 Fields) | Eligible (4 Fields) | Ineligible (<50% Completeness) |
| **GIS Map Marker** | Georeferenced (MH Centroid) | Georeferenced (UP Centroid) | Location Unavailable |
| **CSV Report Export** | Fully Exported | Fully Exported | Fully Exported |

---

## Legitimate Unavailable States

When demonstrating features where data is incomplete or unavailable:
1. **Supervised Delay Probability:** Clearly displays `PREDICTION UNAVAILABLE — Supervised Model Deferred` with link to `data-gap-report.md`.
2. **Missing Coordinates:** Clearly displays `Location unavailable` with state centroid fallback label.
3. **Low-Completeness Projects:** Displays `PREDICTION UNAVAILABLE — Insufficient Data (Completeness < 50%)`.
