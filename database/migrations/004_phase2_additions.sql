-- =============================================================================
-- LandPulse AI — Phase 2 Schema Additions
-- Migration: 004_phase2_additions.sql
-- Adds ML model registry, prediction enhancements, data quality snapshots,
-- and extended provenance fields to data_sources.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── Prediction Status Type ───────────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE prediction_status AS ENUM (
        'AVAILABLE',
        'INSUFFICIENT_DATA',
        'ERROR',
        'PENDING'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ─── Model Type ───────────────────────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE ml_model_type AS ENUM (
        'ANOMALY_SCORER',
        'BINARY_CLASSIFIER',
        'REGRESSION'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =============================================================================
-- TABLE: ml_model_registry
-- =============================================================================
CREATE TABLE IF NOT EXISTS ml_model_registry (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name              VARCHAR(255) NOT NULL,
    model_version           VARCHAR(50) NOT NULL UNIQUE,
    model_type              ml_model_type NOT NULL,
    training_date           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dataset_version         VARCHAR(100),
    record_count_used       INTEGER,
    feature_list            JSONB NOT NULL DEFAULT '[]',
    evaluation_metrics      JSONB NOT NULL DEFAULT '{}',
    model_path              TEXT,
    preprocessing_path      TEXT,
    is_current              BOOLEAN NOT NULL DEFAULT FALSE,
    authenticity_statement  TEXT NOT NULL,
    data_sources_used       TEXT[] NOT NULL DEFAULT '{}',
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for current model
CREATE UNIQUE INDEX IF NOT EXISTS idx_ml_model_registry_current
    ON ml_model_registry (model_type) WHERE is_current = TRUE;

-- =============================================================================
-- TABLE: data_quality_snapshots
-- =============================================================================
CREATE TABLE IF NOT EXISTS data_quality_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_source_id          UUID REFERENCES data_sources(id) ON DELETE CASCADE,
    total_records           INTEGER NOT NULL DEFAULT 0,
    valid_records           INTEGER NOT NULL DEFAULT 0,
    invalid_records         INTEGER NOT NULL DEFAULT 0,
    duplicate_records       INTEGER NOT NULL DEFAULT 0,
    missing_value_rate      NUMERIC(5,4),
    prediction_eligible     INTEGER NOT NULL DEFAULT 0,
    quality_issues          JSONB NOT NULL DEFAULT '[]',
    field_null_rates        JSONB NOT NULL DEFAULT '{}',
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Extend: data_sources
-- =============================================================================
ALTER TABLE data_sources
    ADD COLUMN IF NOT EXISTS fields_obtained     TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS authenticity_notes  TEXT,
    ADD COLUMN IF NOT EXISTS ingestion_run_id    UUID,
    ADD COLUMN IF NOT EXISTS transformation_history JSONB DEFAULT '[]';

-- =============================================================================
-- Extend: predictions (if predictions table exists)
-- =============================================================================
DO $$ BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'predictions') THEN
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS prediction_status prediction_status NOT NULL DEFAULT 'PENDING';
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS data_completeness_pct NUMERIC(5,2);
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS dataset_version VARCHAR(100);
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS as_of_date TIMESTAMPTZ;
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS model_registry_id UUID REFERENCES ml_model_registry(id) ON DELETE SET NULL;
        ALTER TABLE predictions ADD COLUMN IF NOT EXISTS error_detail TEXT;
    END IF;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_data_quality_source
    ON data_quality_snapshots (data_source_id, snapshot_date DESC);

-- =============================================================================
-- Initial seed: Register data sources that Phase 2 targets
-- =============================================================================
INSERT INTO data_sources (
    id,
    dataset_name,
    description,
    source_organization,
    source_url,
    data_status,
    file_format,
    license,
    notes,
    fields_obtained,
    authenticity_notes
) VALUES
(
    gen_random_uuid(),
    'BHOOMIRASHI_PUBLIC_SEARCH_TABLE',
    'Publicly visible land acquisition search results table from BhoomiRashi portal. Fields: state, district, agency, land_required_ha, sanctioned_la_cost_crore, 3A notification date, 3D notification date.',
    'Ministry of Road Transport and Highways (MoRTH)',
    'https://bhoomirashi.gov.in/',
    'PENDING_VERIFICATION',
    'HTML_TABLE',
    'Public domain — government transparency portal. No bulk download or API; table rows visible to public without authentication.',
    'Data ingested from publicly visible search result HTML table. No login required. Scraper reads only visible rows. Raw HTML preserved. No private or restricted data accessed.',
    ARRAY['state', 'district', 'agency', 'land_required_ha', 'sanctioned_la_cost_crore', 'notification_3a_date', 'notification_3d_date'],
    'Source is official GoI portal (bhoomirashi.gov.in). Data visible publicly in browser without authentication. Fields are limited to those shown in the public search table.',
    10,
    'OFFICIAL_PUBLIC'
),
(
    gen_random_uuid(),
    'MORTH_ANNUAL_REPORT_AGGREGATE',
    'State-wise aggregate statistics from MoRTH Annual Reports (PDF). Covers total NH length, land acquired, and financial progress by state.',
    'Ministry of Road Transport and Highways (MoRTH)',
    'https://morth.nic.in/annual-report',
    'PENDING_VERIFICATION',
    'PDF',
    'Public domain — official government annual report.',
    'Aggregate state-level statistics only. Does NOT contain per-project planned vs actual milestone dates. Cannot be used for supervised delay label construction.',
    ARRAY['state', 'nh_length_km', 'total_land_acquired_ha', 'financial_year'],
    'Source is official MoRTH Annual Report PDF. Aggregate statistics only — not project-level data.',
    36,
    'OFFICIAL_PUBLIC'
)
ON CONFLICT (dataset_name) DO UPDATE SET 
    record_count = EXCLUDED.record_count,
    data_status = EXCLUDED.data_status;
