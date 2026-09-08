# LADRIS
### AI-Powered Land Acquisition Early-Warning & Intervention Intelligence Platform

---

## 📌 Executive Summary

**LADRIS** is an enterprise-grade AI decision-support platform designed for predictive analytics and early detection of land acquisition delays in infrastructure development projects across India.

By analyzing administrative approval timelines, compensation disbursement rates, legal disputes, rehabilitation progress, and geospatial indicators, LADRIS shifts project monitoring from reactive reporting to predictive decision-making.

---

## 🏗️ Monorepo Architecture

```
LADRIS_AI/
├── frontend/          # React + TypeScript + Vite + Tailwind CSS + shadcn/ui
├── backend/           # Python + FastAPI + Async SQLAlchemy + Pydantic + JWT Auth
├── ml/                # ML Pipeline workspace & Data provenance registry
│   ├── data/          # raw/, processed/, features/
│   ├── notebooks/     # EDA & feature engineering notebooks
│   └── models/        # Serialized model artifacts
├── database/          # PostgreSQL + PostGIS schema migrations & index scripts
├── docs/              # System architecture, DB ERD, API specs & data strategy
├── docker-compose.yml # Container orchestration for DB, backend & frontend
└── .env.example       # Environment configuration template
```

---

## 🚀 Comprehensive Local Setup Guide

Follow these instructions to clone, configure, and run **LADRIS** from scratch on your local machine.

---

### 💻 Prerequisites

| Component | Docker Setup (Recommended) | Local / Non-Docker Setup |
| :--- | :--- | :--- |
| **Git** | Installed | Installed |
| **Container Engine** | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose v2+) | Not Required |
| **Node.js** | Not Required | [Node.js (v18+)](https://nodejs.org/) & `npm` |
| **Python** | Not Required | [Python 3.11 / 3.12](https://python.org) |
| **Database** | Handled automatically by Docker | [PostgreSQL 14+](https://www.postgresql.org/) with **PostGIS 3.4+** extension |

---

### 📦 Option A: Quick Launch with Docker Compose (Recommended)

This method sets up the entire application (PostgreSQL + PostGIS database, FastAPI backend, and React Vite frontend) in isolated containers with zero manual configuration.

#### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd LandPulse_AI
```

#### 2. Configure Environment Variables
Copy `.env.example` to create your local `.env` configuration:
```bash
# On Linux / macOS / Git Bash:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```
*(Optional)* Open `.env` in a text editor to customize environment variables (or leave defaults for quick local development).

#### 3. Build & Launch Container Stack
```bash
docker compose up --build -d
```
This command automatically downloads images, builds the backend and frontend containers, and initializes the PostGIS database with all SQL migration scripts in `database/migrations/`.

#### 4. Seed Database with Realistic Infrastructure Data (Optional)
Run the automated database seeders inside the backend container:
```bash
docker compose exec backend python seed_realistic_data.py
docker compose exec backend python seed_risk_snapshots.py
```

#### 5. Verify Running Services
- 🌐 **Frontend App**: `http://localhost:5173`
- ⚙️ **Backend API (Swagger Docs)**: `http://localhost:8000/docs`
- 🗄️ **PostgreSQL / PostGIS**: `localhost:15432`

#### 6. Stop Services
```bash
# Stop containers keeping database volume intact
docker compose down

# Stop containers and wipe database state for a fresh start
docker compose down -v
```

---

### 🛠️ Option B: Local Native Setup (Without Docker)

Use this setup if you want to run Python and Node.js directly on your host operating system.

#### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd LandPulse_AI
```

#### 2. PostgreSQL + PostGIS Database Setup
1. Ensure PostgreSQL is running on your machine.
2. Open `psql` shell or PgAdmin and create the database and user:
   ```sql
   CREATE DATABASE landpulse;
   CREATE USER landpulse_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
   GRANT ALL PRIVILEGES ON DATABASE landpulse TO landpulse_user;
   
   -- Connect to landpulse database and enable PostGIS extension
   \c landpulse
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
3. Run the database migration and initialization scripts:
   ```bash
   psql -U landpulse_user -d landpulse -f database/migrations/001_initial_schema.sql
   psql -U landpulse_user -d landpulse -f database/migrations/002_indexes.sql
   psql -U landpulse_user -d landpulse -f database/migrations/003_seed.sql
   psql -U landpulse_user -d landpulse -f database/migrations/004_phase2_additions.sql
   psql -U landpulse_user -d landpulse -f database/migrations/005_rbac_roles.sql
   ```

#### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update database host to `localhost` and specify your local database password in `.env`:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=landpulse
POSTGRES_USER=landpulse_user
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD

DATABASE_URL=postgresql+asyncpg://landpulse_user:CHANGE_ME_STRONG_PASSWORD@localhost:5432/landpulse
SYNC_DATABASE_URL=postgresql://landpulse_user:CHANGE_ME_STRONG_PASSWORD@localhost:5432/landpulse
JWT_SECRET_KEY=e5999ad77d4411136b6900f8dfb158bb38f87b8d8df7c5885e34771f25b59620
```

#### 4. Backend Setup (FastAPI)
1. Navigate into the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Seed realistic infrastructure data:
   ```bash
   python seed_realistic_data.py
   python seed_risk_snapshots.py
   ```
5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### 5. Frontend Setup (React + Vite)
Open a **new terminal window** and run:
1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```
3. Launch Vite development server:
   ```bash
   npm run dev
   ```
4. Frontend will open at `http://localhost:5173`.

---

### 🔑 Default System Access Credentials

When the backend starts up, default accounts are verified automatically:

| User Role | Email Address | Default Password |
| :--- | :--- | :--- |
| **Super Admin** | `admin@ladris.gov.in` | `admin123` |
| **Project Officer** | `officer@ladris.gov.in` | `admin123` |

---

### 🤖 ML Engine & Pipeline Execution

The ML engine provides **anomaly scoring**, **stage bottleneck detection**, **risk velocity calculation**, and **intervention recommendations** across land acquisition projects.

#### 1. Automatic Real-Time Inference
- **Zero-Config Execution**: The backend (`backend/app/services/anomaly_service.py` & `risk_engine.py`) automatically loads the pre-trained serialized model (`ml/models/isolation_forest_v1.0-anomaly_*.pkl`) on startup.
- In both Docker and Native setups, real-time risk scores and anomaly detection run automatically during API requests.

#### 2. Running Data Ingestion Scrapers (Collecting Real Data)
To ingest official projects from government portals:
```bash
# Docker Setup:
docker compose exec backend python /ml/data_ingestion/bhoomirashi_scraper.py
docker compose exec backend python /ml/data_ingestion/datagov_ingester.py

# Native Setup:
python ml/data_ingestion/bhoomirashi_scraper.py
python ml/data_ingestion/datagov_ingester.py
```

#### 3. Re-Training the ML Anomaly Scorer
To run feature engineering, data leakage checks, and train a new model artifact:
```bash
# Docker Setup:
docker compose exec backend python /ml/training/train.py

# Native Setup:
python ml/training/train.py
```
> The script validates prospective feature leakage, evaluates dataset sizes, trains an Isolation Forest model, normalizes anomaly scores, and updates `ml/models/current_model.json`.

#### 4. Exploratory Data Analysis & Notebooks
For interactive ML research and feature analysis:
```bash
# Install Jupyter inside backend virtual environment
pip install jupyter

# Launch notebook workspace
jupyter notebook ml/notebooks
```

---

## 🔑 Authentication & RBAC

LADRIS uses JWT tokens with standard Role-Based Access Control (RBAC):

| Role | Scope & Permissions |
| :--- | :--- |
| `SUPER_ADMIN` | Full system access, audit logs, dataset provenance management |
| `STATE_ADMIN` | State-wide project CRUD and administrative reporting |
| `DISTRICT_OFFICER` | Revenue district project creation and stage updates |
| `PROJECT_OFFICER` | Single project milestone tracking and event logging |
| `ANALYST` | Read-only analytics, custom query execution, model inspection |
| `VIEWER` | Read-only dashboard view scoped to assigned jurisdiction |

---

## 📜 Real Data Architecture Policy

LADRIS strictly mandates **data authenticity**:
- **No Fabricated Government Data**: Phase 1 includes zero fake government project statistics or dummy projects.
- **Data Provenance**: Every imported dataset is tracked in `ml/data_provenance.json` with source URL, organization, retrieval timestamp, and license.
- **Empty State System**: User interface components display clear, professional empty state indicators until official datasets are registered.

---

## 📖 System Documentation

Detailed technical documentation is available in the [`docs/`](./docs) directory:
- [Master AI Assistant Handoff & Implementation Tracker](./docs/implementation-tracking.md) ⭐
- [Architecture Specifications](./docs/architecture.md)
- [Model Card (v1.0-anomaly)](./docs/model-card.md)
- [Data Gap Report & Target Specification](./docs/data-gap-report.md)
- [ML Methodology & Stage Intelligence](./docs/ml-methodology.md)
- [Database Schema & ERD](./docs/database.md)
- [API Reference Guide](./docs/api.md)
- [Data Strategy & Provenance Standard](./docs/data-strategy.md)
