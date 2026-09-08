# LandPulse AI — Hackathon & Presentation Demonstration Script (Phase 7 Updated)

## Step-by-Step Demo Flow

1. **Login & Authenticate**
   - Access `http://localhost:5173/login`.
   - Log in using `admin@landpulse.gov.in` / `admin123`.

2. **Executive Command Center & Transparency Banner**
   - Land on the **Executive Command Center** (`/dashboard`).
   - Review verified data statistics (56 BhoomiRashi projects, 10 DataGov delayed records).
   - Review judge-critical transparency banner: *ANOMALY RISK ≠ DELAY PROBABILITY*.

3. **Government Decision Intelligence Platform**
   - Click **Decision Intelligence** in the sidebar (`/intelligence`).
   - **Tab 1: Cross-Project Priority Queue**:
     - View all projects ranked by multi-factor Priority Score (0–100).
     - Toggle **Simulate Constrained Capacity** button.
     - Adjust Legal (3), Compensation (2), and R&R (1) capacity sliders.
     - Click **Run Simulation** to demonstrate greedy allocation into *Assigned* vs *Deferred* queues (`OUTPUT TYPE E`).
   - **Tab 2: Bottleneck Discovery Engine**:
     - Review dominant national bottleneck distribution.
     - Inspect K-means cluster profiles and state-by-state breakdown.
     - Highlight explicit sample size badges ($N=56$) and statistical limitation warnings.
   - **Tab 3: Project Risk DNA & Benchmarking**:
     - Select target project **Pune Peripheral Ring Road (`MH-NH-PUNE-01`)**.
     - Inspect 5-dimensional **Risk DNA Profile** (Anomaly, Stage Fingerprint, Completeness, SHAP Driver, Reliability).
     - Review **Real Temporal Risk Observation History** (shows real logged prediction timestamps; `NO_DATA` when unassessed).
     - Review **Structurally Comparable Projects** (cosine similarity benchmarking on real project attributes).

4. **Project Intelligence Workspace**
   - Navigate to `/projects` and select `MH-NH-PUNE-01`.
   - Click **Inspect Risk DNA** button in the header.
   - View **Stage Risk Fingerprint** chart (NOTIFICATION stage uses real 3A→3D BhoomiRashi temporal data).
   - Open **Intervention Intelligence** and run the **What-If Simulator**.

5. **GIS, Data Quality & Provenance**
   - Navigate to **GIS Map** to inspect georeferenced spatial circles and *"Location Unavailable"* fallback handling.
   - Open **Data Sources** and **Data Quality** to demonstrate zero-synthetic-data standards and public provenance registry.
