# LandPulse AI — Intervention Intelligence Engine Architecture

## Overview
The **LandPulse Intervention Intelligence Engine** forms Phase 4 of LandPulse AI. It transforms the system from **Risk Detection + Explanation** into a complete decision-support workflow:

$$\text{Detect} \longrightarrow \text{Explain} \longrightarrow \text{Prioritize} \longrightarrow \text{Simulate} \longrightarrow \text{Recommend}$$

## Architectural Principles
1. **No Redesign of Base Architecture**: Extends the Phase 3 ML pipeline without modifying core schemas.
2. **Transparent, Auditable Rules**: Every candidate intervention is mapped via explicit python rules in `ml/interventions/rule_engine.py`.
3. **Traceable Data Provenance**: Every intervention references real public data signals from BhoomiRashi (MoRTH), Data.gov.in, or MoRTH Annual Reports. No evidence is fabricated.
4. **Non-Causal Decision-Support Framing**: All recommendations are labeled as **Rule-Based Decision-Support Suggestions** — NOT causal predictions and NOT legal orders.

---

## Intervention Catalog
The catalog (`ml/interventions/catalog.py`) defines structured candidate interventions mapped to the 6 acquisition stages (NH Act 1956 / RFCTLARR 2013):

| ID | Stage | Display Name | Provenance / Data Basis | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `NOTIF-001` | NOTIFICATION | Expedite 3D Notification Publication | BhoomiRashi public search table (56 records, median=194d) | HIGH (Real date signal) |
| `NOTIF-002` | NOTIFICATION | Review Pending 3A Notification Milestones | BhoomiRashi public search table | HIGH |
| `COMP-001` | COMPENSATION | Prioritize Pending Compensation Case Review | DataGov.in delayed projects (10 records, 2023–2025) | MEDIUM (Proxy) |
| `COMP-002` | COMPENSATION | Resolve High-Value Compensation Disputes | BhoomiRashi cost data (p75 = 1.2 Cr/ha) | MEDIUM (Proxy) |
| `LEGAL-001` | OBJECTION | Escalate Unresolved Ownership/Objection Cases | DataGov.in delayed project records | MEDIUM (Proxy) |
| `DOC-001` | AWARD | Resolve Incomplete Award Documentation | BhoomiRashi land area data (p75 = 185 ha) | MEDIUM (Proxy) |
| `RR-001` | RR | Prioritize Pending R&R Cases | DataGov.in R&R delay records (WB, BR, MH) | MEDIUM (Proxy) |
| `RR-002` | RR | Accelerate Resettlement Colony Allotment | DataGov.in large displacement records | LOW (Proxy) |

---

## Decision-Support Priority Scorer Formula
The Priority Scorer (`ml/interventions/priority_scorer.py`) produces a transparent 0–100 **Decision-Support Priority Score** for each candidate intervention using explicit weights:

$$\text{Raw} = 0.30 \cdot \text{RiskSeverity} + 0.25 \cdot \text{Urgency} + 0.20 \cdot \text{PotentialImpact} + 0.15 \cdot \text{Feasibility} + 0.10 \cdot \text{DataConfidence}$$

$$\text{PriorityScore} = \text{clip}\left(\text{Raw} \times 100, 0, 100\right)$$

### Component Weights & Definitions:
- **Risk Severity ($w = 0.30$)**: Combined risk signal $\max(\text{AnomalyScore}, \text{StageRisk})$.
- **Urgency ($w = 0.25$)**: Catalog-defined urgency weight $[0, 1]$.
- **Potential Impact ($w = 0.20$)**: Scope of affected families, land area, and cost intensity.
- **Implementation Feasibility ($w = 0.15$)**: Catalog-defined actionability weight $[0, 1]$.
- **Data Confidence ($w = 0.10$)**: Data basis quality ($\text{HIGH}=0.90$, $\text{MEDIUM}=0.65$, $\text{LOW}=0.40$).

*Data Completeness Penalty*: If project data completeness is below 75%, a scaling factor factor $= 0.80 + 0.20 \cdot \left(\frac{\text{Completeness}}{75}\right)$ is applied.

---

## Database Audit Models
All generated recommendations are saved with mandatory non-government-action record types:

1. **`InterventionRecommendation`**
   - `record_type`: `'RECOMMENDATION — NOT GOVERNMENT ACTION'`
   - Stores priority score, score components, triggering rules, and connected SHAP risk contributors.

2. **`InterventionScenario`**
   - `record_type`: `'SCENARIO — NOT ACTUAL GOVERNMENT ACTION'`
   - Stores audit trail of read-only what-if simulations.
