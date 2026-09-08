-- =============================================================================
-- LandPulse AI — Migration: 006_project_extended_fields.sql
-- Adds extended real data, provenance, and geospatial columns to projects table
-- =============================================================================

ALTER TABLE projects 
    ADD COLUMN IF NOT EXISTS notification_3a_date DATE,
    ADD COLUMN IF NOT EXISTS notification_3d_date DATE,
    ADD COLUMN IF NOT EXISTS delay_months INTEGER,
    ADD COLUMN IF NOT EXISTS delay_reason TEXT,
    ADD COLUMN IF NOT EXISTS legal_case_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS legal_case_status VARCHAR(50) DEFAULT 'NONE',
    ADD COLUMN IF NOT EXISTS milestone_data_status VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO',
    ADD COLUMN IF NOT EXISTS latitude NUMERIC(9, 6),
    ADD COLUMN IF NOT EXISTS longitude NUMERIC(9, 6),
    ADD COLUMN IF NOT EXISTS lacrris_integration_status VARCHAR(50) DEFAULT 'PLANNED';

ALTER TABLE projects ALTER COLUMN district_codes TYPE TEXT[];

ALTER TABLE users ADD COLUMN IF NOT EXISTS agency_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_project_ids VARCHAR(1024);
