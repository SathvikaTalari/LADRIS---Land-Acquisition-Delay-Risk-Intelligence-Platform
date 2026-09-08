# LandPulse AI — System User Guide

## 1. Introduction
LandPulse AI is an AI-powered land acquisition early-warning and intervention decision-support platform built for Indian National Highway projects (under the NH Act 1956 and RFCTLARR Act 2013).

## 2. Navigation & Key Interfaces

### A. Executive Command Center (`/dashboard`)
- **KPI Metrics**: Displays total verified projects, high anomaly-risk count, and real data coverage.
- **LandPulse Priority Queue**: Ranks projects dynamically based on the Phase 4 Decision-Support Priority Score.

### B. Priority Intelligence Center (`/priority-intelligence`)
- Dedicated ranking engine allowing multi-parameter filtering across risk levels, target stages, states, and districts.
- Explains *"Why this project is prioritized"* using explicit rule components.

### C. Project Intelligence Workspace (`/projects/:id`)
- Persistent project intelligence header tracking identity, acquisition stage, anomaly signal, data status, and supervised delay status.
- Workflow tabs: Overview -> Risk Fingerprint -> Intervention Intelligence -> Acquisition Stages.

### D. GIS Intelligence Map (`/gis`)
- Interactive spatial map displaying project markers with verified PostGIS coordinates.
- Projects without coordinates are explicitly listed under *"Location Unavailable"* to prevent fake spatial rendering.

### E. District Intelligence Analytics (`/analytics`)
- Aggregates state and district-level project distributions.
- Implements minimum sample-size safeguards to avoid drawing broad policy claims from small sample sizes.

### F. Alerts & Warning System (`/alerts`)
- Rules-based early-warning signals flagging high anomaly risk, priority interventions, and data quality degradation.

## 3. Governance & Non-Causal Standard
- Recommendations are **decision-support suggestions** and do not constitute government legal orders.
- What-If simulations are **scenario estimates**, not causal predictions.
- Supervised delay prediction is formally **DEFERRED** until N >= 200 project completion records are verified.
