-- =============================================================================
-- LandPulse AI — Migration: 005_rbac_roles.sql
-- Expand user_role ENUM and add scope columns to users table
-- =============================================================================

ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'CENTRAL_ADMIN';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'LA_OFFICER';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'PROJECT_AGENCY';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'POLICY_ANALYST';

ALTER TABLE users ADD COLUMN IF NOT EXISTS agency_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_project_ids VARCHAR(1024);
