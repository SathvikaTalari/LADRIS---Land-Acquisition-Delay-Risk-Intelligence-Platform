# LandPulse AI — Database Schema Documentation

## 1. Relational Schema Summary

The LandPulse AI database model consists of **18 PostgreSQL/PostGIS tables** designed for tracking the complete land acquisition lifecycle, legal disputes, compensation disbursement, and ML predictions.

---

## 2. Core Tables Description

### `users`
Tracks system users, hashed credentials, assigned roles, and spatial jurisdiction constraints.

### `projects`
Central entity representing infrastructure project acquisitions.
- Spatial column: `geom` (`MultiPolygon`, EPSG:4326)
- Foreign keys: `created_by`, `updated_by`, `data_source_id`

### `project_stages`
Tracks 12 standard land acquisition stages (Section 11 Notification, SIA, Section 19 Declaration, Award, Disbursement, Possession, etc.). Contains auto-generated `delay_days` generated column.

### `land_parcels`
Individual survey/khasra land plots. Contains parcel geometry (`Polygon`, EPSG:4326), ownership counts, dispute flags, and possession status.

### `compensation_records`
Beneficiary-level compensation disbursement records tracking awarded amount vs disbursed amount, payment mode, and escrow dispute reference.

### `legal_cases`
Court disputes, writ petitions, civil suits, and arbitration cases affecting acquisition plots. Tracks stay orders (`stay_on_acquisition = TRUE`) and hearing schedules.

### `rr_records`
Rehabilitation and Resettlement (R&R) monitoring, housing relocation counts, livelihood support disbursement, and grievance counts.

### `approvals`
Inter-departmental approvals (Environmental clearance, Forest clearance, Defence clearance, Railway crossing approvals) with expected vs actual approval timelines.

### `possessions`
Physical possession handover tracking, obstruction type (encroachment, physical protest, legal stay), and resolution dates.

### `predictions` & `stage_predictions` (Phase 2 Schema Ready)
Stores ML delay risk probability scores, overall project risk score, predicted delay days, and JSONB SHAP explainability outputs.

### `risk_factors` & `recommendations`
Stores explainable AI key delay drivers (e.g. pending Forest clearance) and recommended administrative interventions.

### `intervention_scenarios`
Simulated "What-If" intervention scenarios (e.g., accelerating compensation disbursement by 30 days) and simulated risk score outputs.

### `alerts`
Automated risk escalation alerts for project managers and district officers.

### `audit_logs`
Security and forensic audit records tracking user action, request path, IP address, and payload parameters.

### `data_sources`
Data provenance and dataset registry tracking dataset status (`OFFICIAL_PUBLIC`, `DERIVED`, `SYNTHETIC`), source URL, and license.

---

## 3. Spatial Indexes
- `idx_projects_geom`: GIST index on `projects.geom`
- `idx_parcels_geom`: GIST index on `land_parcels.geom`
