# LandPulse AI — Data Strategy & Real Data Policy (Phase 2 Edition)

## 1. Core Principles

1. **Zero Synthetic Government Data Misrepresentation**: Synthetic or dummy project datasets generated for testing must NEVER be presented as authentic government infrastructure records.
2. **Traceable Data Lineage**: Every dataset ingested into LandPulse AI maintains a data provenance record tracking:
   - Source Organization (e.g. Ministry of Road Transport & Highways, State Revenue Dept)
   - Source URL / Open Data Portal endpoint
   - Ingestion Date & Retrieval Timestamp
   - Covered Time Period
   - Classification (`OFFICIAL_PUBLIC`, `DERIVED`)
   - Fields obtained and explicit list of unavailable fields
3. **Data-Gap Honesty Standard**: If official public sources do not contain fields necessary for a supervised machine learning target, the system MUST stop supervised model training and produce a formal Data Gap Report rather than inventing labels or synthetic dates.

---

## 2. Ingested Datasets

### A. BhoomiRashi Public Search Table (`BHOOMIRASHI_PUBLIC_SEARCH_TABLE`)
- **Source**: Ministry of Road Transport and Highways (MoRTH) / bhoomirashi.gov.in
- **Access**: Public search interface (HTML table view)
- **Authenticity**: `OFFICIAL_PUBLIC`
- **Fields Obtained**: `state`, `district`, `agency`, `land_required_ha`, `sanctioned_la_cost_crore`, `notification_3a_date`, `notification_3d_date`
- **Unavailable Fields**: `project_planned_start_date`, `project_planned_end_date`, `project_actual_completion_date`, `project_delay_status`

### B. MoRTH Annual Report Aggregate (`MORTH_ANNUAL_REPORT_AGGREGATE`)
- **Source**: MoRTH Annual Reports (2021-22, 2022-23)
- **Access**: Official PDF reports on morth.nic.in
- **Authenticity**: `OFFICIAL_PUBLIC`
- **Fields Obtained**: `state`, `state_name`, `nh_length_km`, `financial_year`
- **Limitations**: Aggregate state-level data only; no per-project milestone timing.

---

## 3. Data Pipeline & Quality Controls

1. **Raw Preservation**: Raw PDF and HTML/CSV files are stored unmodified in `ml/data/raw/`.
2. **Validation**: `ml/data_processing/validator.py` checks schema, dtypes, duplicate records, numeric bounds, and date ordering.
3. **Quality Report**: Generated automatically as `data_quality_report.json` and served via `/api/v1/data-quality`.
4. **Data Cleaning**: Coerces types and flags bad records in `ml/data/processed/` without altering raw files.
