-- =============================================================================
-- LandPulse AI — Database Indexes & Performance Optimization
-- Migration: 002_indexes.sql
-- =============================================================================

-- ─── users ───────────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_state ON users (state_code) WHERE state_code IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users (is_active) WHERE is_active = TRUE;

-- ─── projects ────────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_code ON projects (project_code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_status ON projects (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_risk ON projects (risk_level);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_state ON projects (state_code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_type ON projects (project_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_deleted ON projects (deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_created ON projects (created_at DESC);
-- Full-text search on project name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_name_trgm ON projects USING GIN (name gin_trgm_ops);
-- Spatial index on project geometry
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_geom ON projects USING GIST (geom) WHERE geom IS NOT NULL;
-- Composite: list filtered by state + status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_state_status ON projects (state_code, status) WHERE deleted_at IS NULL;

-- ─── project_stages ──────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stages_project ON project_stages (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stages_status ON project_stages (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stages_risk ON project_stages (stage_risk_level);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stages_delayed ON project_stages (project_id, status) WHERE status = 'DELAYED';

-- ─── project_events ──────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_project ON project_events (project_id, event_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_stage ON project_events (stage_id);

-- ─── land_parcels ────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parcels_project ON land_parcels (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parcels_geom ON land_parcels USING GIST (geom) WHERE geom IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parcels_district ON land_parcels (district, state_code);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_parcels_disputed ON land_parcels (project_id) WHERE has_legal_dispute = TRUE;

-- ─── compensation_records ────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comp_project ON compensation_records (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comp_parcel ON compensation_records (land_parcel_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comp_disputed ON compensation_records (project_id) WHERE is_disputed = TRUE;

-- ─── legal_cases ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_legal_project ON legal_cases (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_legal_status ON legal_cases (case_status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_legal_stay ON legal_cases (project_id) WHERE stay_on_acquisition = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_legal_hearing ON legal_cases (next_hearing_date) WHERE case_status NOT IN ('DISMISSED', 'RESOLVED');

-- ─── rr_records ──────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rr_project ON rr_records (project_id);

-- ─── approvals ───────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_approvals_project ON approvals (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_approvals_pending ON approvals (project_id, expected_date) WHERE is_pending = TRUE;

-- ─── possessions ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessions_project ON possessions (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessions_taken ON possessions (project_id) WHERE is_taken = FALSE;

-- ─── predictions ─────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pred_project ON predictions (project_id, prediction_date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pred_risk ON predictions (risk_level);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pred_model ON predictions (model_version);

-- ─── stage_predictions ───────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stage_pred_project ON stage_predictions (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stage_pred_stage ON stage_predictions (stage_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stage_pred_pred ON stage_predictions (prediction_id);

-- ─── risk_factors ────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rf_prediction ON risk_factors (prediction_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rf_category ON risk_factors (factor_category);

-- ─── recommendations ─────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recs_project ON recommendations (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_recs_priority ON recommendations (project_id, priority DESC);

-- ─── intervention_scenarios ──────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scenarios_project ON intervention_scenarios (project_id);

-- ─── alerts ──────────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_project ON alerts (project_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_status ON alerts (status) WHERE status = 'ACTIVE';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_severity ON alerts (severity, triggered_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_alerts_triggered ON alerts (triggered_at DESC);

-- ─── audit_logs ──────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user ON audit_logs (user_id, timestamp DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_action ON audit_logs (action);

-- ─── data_sources ────────────────────────────────────────────────────────────
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ds_status ON data_sources (data_status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ds_active ON data_sources (is_active) WHERE is_active = TRUE;
