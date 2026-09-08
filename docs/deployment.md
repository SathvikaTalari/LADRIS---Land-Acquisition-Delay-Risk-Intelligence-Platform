# LandPulse AI — Production Deployment & Operations Guide

**Document Version:** 1.0.0  
**Target Environment:** Local Development / Docker Containerized Production  

---

## 1. Environment Requirements
- **OS**: Windows / Linux / macOS
- **Python**: Python 3.12+ (or active virtualenv with `backend/requirements.txt`)
- **Node.js**: Node.js 18+ & npm 9+
- **Database**: PostgreSQL 16+ with PostGIS 3.4 extension
- **Docker**: Docker Engine 24+ & Docker Compose v2+

---

## 2. Option A: Local Native Execution

### A. Environment Configuration
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

### B. Backend API Server
```powershell
cd backend
.\venv\Scripts\pytest.exe tests ml\tests   # Run full test suite
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### C. Frontend Web Shell
```powershell
cd frontend
npm install
npm run build
npm run dev
```

---

## 3. Option B: Docker Containerized Deployment

### A. Launch Full Stack with Docker Compose
```bash
docker-compose up -d --build
```

### B. Containers Deployed:
- `landpulse-db`: PostgreSQL 16 + PostGIS 3.4 (Port `5432`)
- `landpulse-backend`: FastAPI Service (Port `8000`)
- `landpulse-frontend`: Vite Production Server (Port `5173`)

---

## 4. Verification & Operations Checks

| Endpoint / Command | URL / Location | Expected Response / Output |
|---|---|---|
| **Health Probe** | `GET http://localhost:8000/health` | `{"status": "healthy", "database": "connected"}` |
| **Readiness Probe** | `GET http://localhost:8000/ready` | `{"status": "ready"}` |
| **OpenAPI Docs** | `http://localhost:8000/docs` | Interactive Swagger UI |
| **Frontend UI** | `http://localhost:5173` | Government Command Center Shell |
| **Pytest Suite** | `pytest backend/tests ml/tests` | `58 passed` |
| **Frontend Build** | `cd frontend && npm run build` | `dist/` bundle created with 0 errors |

---

## 5. Security & Credentials Policy
- Never commit `.env` or production passwords to Git.
- Default Admin: `admin@landpulse.gov.in` (Password set in `.env`).
- Default Officer: `officer@landpulse.gov.in`.
