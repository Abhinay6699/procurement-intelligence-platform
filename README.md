# Procurement Intelligence Platform (MVP)

An AI-driven platform for detecting and explaining procurement leakage (maverick spend, duplicate invoices, contract price variances, split POs, and payment leakage).

## Current Status

We have just completed **Phase 3** of the MVP development. The ML Detection Engine is fully implemented and tested against a rigorous synthetic dataset containing both "easy" and "hard" edge cases.

### Achievements to Date
- **Synthetic Data Generator**: Created a robust data pipeline that simulates legitimate procurement data alongside hard-to-detect leakage scenarios (e.g., small rounding errors in duplicates, legitimate small off-contract purchases vs actual maverick spend).
- **Leakage Detectors**: Implemented 5 specialized rule-based heuristics that successfully identify leakage candidates.
- **XGBoost Ensemble**: Built and trained an XGBoost model that acts as a meta-classifier over the heuristics and an Isolation Forest anomaly detector. The model successfully learns complex feature combinations and provides SHAP-based explainability.
- **Evaluation & Hardening**: Identified and fixed critical bugs in the Duplicate Invoice (fuzzy matching tolerance) and Maverick Spend (vendor approval status) detectors. The overall pipeline now achieves high precision and recall (0.84 - 1.00) even on difficult edge cases.

### Next Steps (Phase 4)
We are now moving into **Phase 4: Agent Integration**. The next phase will involve:
1. Wrapping the XGBoost predictions into the backend FastAPI endpoints.
2. Building an AI agent capable of interacting with these endpoints, reading the SHAP reason codes, and communicating findings to the end-user.

## Architecture

* **Backend**: FastAPI
* **Machine Learning**: XGBoost, scikit-learn (IsolationForest), SHAP for explainability
* **Data**: Synthetic procurement data (vendors, contracts, POs, invoices, payments)
