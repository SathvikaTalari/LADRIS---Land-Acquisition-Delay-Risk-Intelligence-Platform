# LandPulse AI — Data Provenance & Lineage Documentation (Phase 7 Updated)

This document outlines the provenance tracking system, ingested dataset inventory, output classification standards, and authenticity rules enforced across LandPulse AI.

---

## Ingested Real Public Datasets Inventory

| Dataset Identifier | Source Organization | Source URL / Asset | Ingested Records | Fields Obtained | Supervised Target Usable | Data Status |
|-------------------|---------------------|-------------------|------------------|-----------------|--------------------------|-------------|
| `BHOOMIRASHI_PUBLIC_SEARCH_TABLE` | Ministry of Road Transport and Highways (MoRTH) | `https://bhoomirashi.gov.in/` | 56 projects | state, district, agency, land_ha, cost_crore, 3A date, 3D date | NO (No completion dates) | `OFFICIAL_PUBLIC` |
| `DATAGOV_DELAYED_PROJECTS` | Open Government Data Platform India | `https://data.gov.in/` | 10 projects | project_code, name, state, area_ha, cost_inr, status, delay_months, reason | YES (N=10 too small for model training) | `OFFICIAL_PUBLIC` |
| `MORTH_ANNUAL_REPORT_AGGREGATE` | Ministry of Road Transport and Highways | MoRTH Annual Reports 2021-23 PDFs | 36 state-years | state, nh_length_km, financial_year | NO (Aggregate only) | `OFFICIAL_PUBLIC` |

---

## Phase 7 Output Classification Standards

All outputs across APIs and the frontend UI carry an explicit evidence type classification:

| Output Type | Category | Description | Phase 7 Feature / API Endpoint |
|-------------|----------|-------------|--------------------------------|
| **A** | Official Source Data | Unmodified fields directly from official government sources | Data provenance metadata, real 3A/3D dates, temporal logged observation history |
| **B** | Derived Analytics | Statistical calculations computed from official datasets | Bottleneck discovery distributions, state bottleneck profiles, cosine similarity benchmarks |
| **C** | ML/Model Signals | Inference outputs from trained statistical/ML models | IsolationForest structural anomaly score, Stage Risk Fingerprint, SHAP attributions |
| **D** | Decision Support | Rule-based recommendations & prioritized rankings | Cross-Project Priority Queue, candidate intervention recommendations |
| **E** | Hypothetical Scenario | What-If simulation outputs & resource allocation estimates | What-If simulator, Greedy Resource Allocation Simulation |

---

## Provenance Registry Schema

Each registered dataset entry in `ml/data_provenance.json` records:
- `id`: Unique ingestion run identifier
- `dataset_name`: System dataset name
- `source_organization`: Official publisher (e.g. MoRTH, NIC)
- `source_url`: Portal web link
- `retrieval_date`: Timestamp of retrieval
- `data_status`: `OFFICIAL_PUBLIC` | `DERIVED` | `PENDING_VERIFICATION`
- `record_count`: Total validated rows
- `fields_obtained`: Array of exact column names extracted
- `unavailable_fields`: Object listing missing public fields and reasons
- `authenticity_notes`: Governance statement on source verification
- `supervised_label_available`: Boolean flag for supervised training suitability

---

## Authenticity Enforcement Rules

1. **Zero Synthetic Government Records**: No fake project codes, fake gazette notification numbers, or synthetic delay labels are injected into database tables or training pipelines.
2. **Dual-Signal Labelling**: Every prediction output strictly separates `anomaly_risk` (IsolationForest inference) from `delay_risk` (DEFERRED, null).
3. **No Historical Fabrication**: Temporal risk history reads ONLY real logged prediction timestamps (`monitoring_log.jsonl` / `project_risk_snapshots`). When no observations exist, returns `temporal_data_available: false`.
4. **Traceable Model Lineage**: All predictions include `model_version`, `dataset_version`, and `data_provenance_reference` matching `current_model.json`.
