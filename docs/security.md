# LandPulse AI — Security & RBAC Documentation

## 1. Authentication & Session Management
- **OAuth2 Password Flow**: Uses JWT Bearer Tokens with secret key encryption.
- **Refresh Tokens**: Supported via `/api/v1/auth/refresh`.

## 2. Server-Side Role-Based Access Control (RBAC)
LandPulse AI enforces strict backend authorization via FastAPI dependency guards (`require_admin`, `require_officer`):
- `SUPER_ADMIN`: Full system access, threshold configuration, user provisioning.
- `STATE_ADMIN`: State-level project write access and monitoring.
- `DISTRICT_OFFICER`: District-level project updates and intervention execution.
- `PROJECT_OFFICER`: Project-specific record updates.
- `ANALYST`: Read-only access to analytics, predictions, and scenarios.
- `VIEWER`: Read-only access to basic project lists.

## 3. Security Hardening Measures
- SQL Injection protection via SQLAlchemy 2.0 parameterized ORM queries.
- Audit Logging: All state-mutating requests (Create, Update, Delete, Scenario Execute) record user ID, email, role, IP address, and request path to the `audit_logs` table.
- Secret Handling: System configuration loaded securely via environment variables (`.env`).
