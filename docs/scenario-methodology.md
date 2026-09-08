# LandPulse AI — What-If Simulator & Scenario Engine Methodology

## Overview
The **What-If Scenario Simulator** (`ml/scenario/engine.py`) allows officers to simulate hypothetical changes in land acquisition parameters (e.g., increasing compensation completion, reducing displacement impact) and observe the resulting changes in risk signals.

## Fundamental Methodology Rules
1. **Strictly Read-Only**: The simulator operates on a deep copy of project feature data. It **NEVER** mutates or writes to any project record or government database table.
2. **Re-runs Existing Deterministic Risk Pipeline**: The scenario engine re-evaluates the hypothetical feature vector through the exact same Phase 3 Stage Risk Engine and IsolationForest Anomaly Scorer.
3. **No Supervised Model Invention**: Because supervised delay prediction is deferred due to insufficient real labeled data, scenarios **DO NOT** predict changes in actual delay duration (days/months). Scenarios predict changes in **Risk Signals** only.
4. **Mandatory Non-Causal Disclaimer**: Every scenario output displays the notice:
   > *"Scenario estimate — not a causal prediction. This simulation re-runs the deterministic rule-based risk pipeline with hypothetical inputs. It does not use a supervised delay model."*

---

## Eligible Simulation Variables
Only variables that exist in real project datasets and can physically vary during project lifecycle are eligible for simulation (`ml/scenario/validator.py`):

| Variable | Physical Bounds | Unit | Derivation / Data Source |
| :--- | :--- | :--- | :--- |
| `compensation_completion_pct` | $[0.0, 1.0]$ | $\%$ | `families_compensated / total_affected_families` |
| `area_acquired_pct` | $[0.0, 1.0]$ | $\%$ | `area_acquired_ha / total_area_ha` |
| `cost_per_ha` | $[0.05, 10.0]$ | Cr/ha | `estimated_compensation_inr / total_area_ha` (BhoomiRashi range 0.2–4.07 Cr/ha) |
| `total_affected_families` | $[1, 10000]$ | families | Project model field |

### Explicitly Excluded Fields (Non-Simulatable)
- `state_code`: Geographically fixed.
- `executing_agency`: Contractually fixed.
- `has_3a_notification` / `has_3d_notification`: Legal gazette milestones cannot be hypothetically reversed.
- `notification_interval_days`: Date-based interval requiring calendar context.

---

## Validation & Out-Of-Distribution (OOD) Guardrails
1. **Physical Range Check**: Inputs outside physical min/max bounds are rejected with HTTP 422 error.
2. **Data Completeness Gate**: Projects with overall data completeness $< 50\%$ are blocked from simulation with an `INSUFFICIENT_DATA` status.
3. **Extrapolation Warnings**: Inputs exceeding observed population maximums (e.g. `cost_per_ha > 4.07 Cr/ha`) trigger non-blocking OOD warnings in scenario output.

---

## Multi-Scenario Comparison
Officers can compare up to 3 scenarios side-by-side (`POST /api/v1/interventions/{project_id}/compare`).
The scenario showing the largest reduction in overall risk fingerprint is labeled **"Highest Estimated Decision-Support Benefit"**.
The output explicitly notes that this label does not guarantee real-world intervention success.
