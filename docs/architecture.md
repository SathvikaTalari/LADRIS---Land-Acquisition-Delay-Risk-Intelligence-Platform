# LandPulse AI — System Architecture Document (Phase 7 Updated)

## 1. High-Level System Architecture

```
Government/Public Sources (MoRTH, BhoomiRashi, Data.gov.in)
        │
        ▼
Data Ingestion (BeautifulSoup, Gazette Parser, PDF Extractors)
        │
        ▼
Validation + Provenance (data_provenance.json, Data Quality Gates)
        │
        ▼
PostgreSQL / PostGIS (Async SQLAlchemy 2.0 + Spatial Indexes)
        │
        ▼
Feature Engineering (Log Ha, Cost/Ha, 3A/3D Notification Intervals)
        │
        ▼
ML / Risk Intelligence (IsolationForest Unsupervised Anomaly Model)
        │
        ▼
SHAP / Explainability (Model-supported Risk Contributor Explanations)
        │
        ▼
Stage Intelligence (6-Stage Lifecycle Proxy Risk Fingerprint Engine)
        │
        ▼
Phase 7 Decision Intelligence Layer
 ├── Risk DNA Composer (Composite 5-dimensional risk profile)
 ├── Temporal Risk Engine (Logged prediction observations & trend analysis)
 ├── Bottleneck Discovery Engine (K-means clustering on stage risk vectors)
 ├── Comparable Project Finder (Weighted Cosine Similarity on structural attributes)
 └── Cross-Project Priority Queue & Greedy Resource Simulator
        │
        ▼
FastAPI Backend (/api/v1/intelligence/ + REST API v1 + JWT Auth + RBAC)
        │
        ▼
React Government Command Center UI (Intelligence Platform View)
        │
        ▼
GIS Map / Alerts / Reports / Audit Trail / Risk Snapshots
```

---

## 2. Technical Stack Breakdown

### Frontend Layer
- **Framework**: React 18 + TypeScript (Strict Mode)
- **Build Tool**: Vite
- **Styling**: Vanilla CSS Design System ("Government Command Center" visual theme)
- **Visualization**: Apache ECharts (`echarts-for-react`) + Framer Motion
- **API Client**: Typed Axios client with JWT request interceptor & 401 token refresh

### Backend API Layer
- **Framework**: FastAPI (Python 3.12)
- **ORM**: Async SQLAlchemy 2.0 (`asyncpg` driver)
- **Phase 7 Intelligence Endpoints**:
  - `GET /api/v1/intelligence/risk-dna/{id}` (Project Risk DNA profile)
  - `GET /api/v1/intelligence/risk-history/{id}` (Real temporal risk observations)
  - `GET /api/v1/intelligence/bottlenecks` (National bottleneck analysis)
  - `GET /api/v1/intelligence/bottlenecks/{state_code}` (State-level bottleneck analysis)
  - `GET /api/v1/intelligence/comparable-projects/{id}` (Cosine similarity comparables)
  - `GET /api/v1/intelligence/priority-queue` (Cross-project priority queue)
  - `POST /api/v1/intelligence/resource-scenario` (Greedy resource allocation simulator)

### ML & Decision Intelligence Layer
- **Anomaly Model**: Scikit-Learn IsolationForest Pipeline (`v1.0-anomaly`)
- **Explainability**: SHAP TreeExplainer with human-readable feature descriptions
- **Stage Intelligence**: 6-stage lifecycle risk calculator (Notification, Objection, Award, Compensation, R&R, Possession)
- **Risk DNA**: 5-dimensional composite profile (Anomaly, Stage Risk, Data Completeness, SHAP Driver, Reliability)
- **Temporal Engine**: Real observation history reader (`monitoring_log.jsonl` + DB snapshots)
- **Bottleneck Engine**: K-means clustering (k=3–5) on stage risk feature vectors + confidence badges
- **Comparable Engine**: Weighted Cosine Similarity on structural attribute vectors
- **Priority Queue**: Extended Phase 4 priority scorer + greedy resource simulation

### Database Layer
- **Database**: PostgreSQL 16 with PostGIS 3.4
- **Tables**: `projects`, `project_stages`, `users`, `ml_model_registry`, `data_quality_snapshots`, `prediction_logs`, `intervention_recommendations`, `intervention_scenarios`, `project_risk_snapshots` (Phase 7)
