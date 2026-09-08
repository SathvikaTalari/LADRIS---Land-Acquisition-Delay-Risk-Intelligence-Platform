-- =============================================================================
-- LandPulse AI — Roles & System Seed Data
-- Migration: 003_seed.sql
-- NOTE: Only system-level seed data (no fabricated project data)
-- =============================================================================

-- This file seeds only the minimum structural data required for the system
-- to function. No government project records are inserted here.
-- All SUPER_ADMIN credentials must be set via environment variables.

-- Insert default data_source entry to track that no real datasets are loaded yet
INSERT INTO data_sources (
    dataset_name,
    description,
    source_organization,
    source_url,
    data_status,
    notes
) VALUES (
    'SYSTEM_PLACEHOLDER',
    'Placeholder data source record. No real government datasets have been loaded. Connect an approved dataset through the Data Sources admin panel to begin analysis.',
    'LandPulse AI System',
    NULL,
    'PENDING_VERIFICATION',
    'Phase 1: No real data loaded. Awaiting Phase 2 data pipeline setup.'
) ON CONFLICT (dataset_name) DO NOTHING;
