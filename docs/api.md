# LandPulse AI — REST API Documentation

FastAPI provides dynamic interactive OpenAPI docs at `/docs` and ReDoc documentation at `/redoc`.

---

## 1. Authentication Endpoints (`/api/v1/auth`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Public | Register new user (restricted for SUPER_ADMIN) |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & receive access/refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Public | Exchange refresh token for new access token |
| `GET`  | `/api/v1/auth/me` | Authenticated | Fetch active user profile & role |

---

## 2. Project Endpoints (`/api/v1/projects`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET`    | `/api/v1/projects/` | Authenticated | List projects with page, status, and state filters |
| `POST`   | `/api/v1/projects/` | Officer/Admin | Create a new land acquisition project |
| `GET`    | `/api/v1/projects/{id}` | Authenticated | Retrieve detailed project record |
| `PUT`    | `/api/v1/projects/{id}` | Officer/Admin | Update project details and stage progress |
| `DELETE` | `/api/v1/projects/{id}` | Officer/Admin | Soft-delete project |

---

## 3. Analytics & System Endpoints

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | System health status & DB connectivity |
| `GET` | `/api/v1/analytics/overview` | Authenticated | Dashboard KPI summary (Empty state if no data) |
| `GET` | `/api/v1/alerts/` | Authenticated | Retrieve active system risk warnings |
| `GET` | `/api/v1/gis/projects` | Authenticated | Spatial GeoJSON features (Phase 2 ready) |
