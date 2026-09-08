# LandPulse AI — Recommendation Policy & Governance Standard

## Purpose
This document establishes strict governance and labeling standards for all outputs produced by the LandPulse AI Intervention Intelligence Engine.

---

## 1. Non-Legal-Order Directive
- **Rule**: No output produced by LandPulse AI may be framed as a directive, binding legal order, or administrative instruction to an officer or collector.
- **Implementation**:
  - Recommendations use advisory vocabulary: *"Review status of pending Section 3D publication..."*, *"Prioritize unresolved payment records..."*, *"Escalate to State NHAI liaison..."*.
  - Every recommendation includes the `non_causal_note` field stating: *"This is a rule-based decision-support suggestion. It does not constitute a legal directive or guarantee delay reduction."*

---

## 2. Distinction Between Model Signals, Rules, and Scenarios
LandPulse AI strictly separates three distinct data concepts across all APIs and UIs:

| Category | System Source | UI Label | Disclaimer / Note |
| :--- | :--- | :--- | :--- |
| **Model-Supported Risk Contributor** | IsolationForest SHAP values (`ml/training/shap_explainer.py`) | *Model-supported risk contributor* | Describes mathematical feature importance relative to anomaly score, NOT a causal delay cause. |
| **Rule-Based Recommendation** | Explicit Python Rule Engine (`ml/interventions/rule_engine.py`) | *Rule-based recommendation* | Advisory suggestion mapped from risk signals using catalog rules. |
| **Scenario Estimate** | What-If Simulator (`ml/scenario/engine.py`) | *Scenario estimate* | Hypothetical risk signal delta recomputed on user inputs. |

---

## 3. Sample Size Safeguard Policy
- **Rule**: District and regional intelligence metrics must NEVER be used to make broad policy claims from small sample sizes.
- **Implementation**:
  - All district analytics displays `sample_size` prominently alongside metrics.
  - Districts with fewer than 3 projects display the notice: *"Small Sample (< 3 projects). Patterns may not be statistically robust."*
  - Policy claim warnings are hardcoded into all district analytics endpoints and UI components.

---

## 4. No Fabrication Policy
- **Rule**: The system must NEVER invent fake government records, historical outcomes, delay probabilities, or intervention success rates.
- **Data Provenance**:
  - All evidence references are tied directly to official public sources: BhoomiRashi (MoRTH), Data.gov.in delayed project records, or MoRTH Annual Reports.
  - Supervised delay prediction remains explicitly `DEFERRED` (`delay_risk.score = None`) until a real, publicly verifiable delay dataset is published.
