# Procurement Intelligence Platform (MVP)

An AI-driven procurement leakage detection platform designed to identify, flag, and explain anomalies and non-compliant purchasing behavior. The platform processes purchase orders, contracts, invoices, and payments to detect five specific categories of procurement leakage.

## Core Leakage Categories Detected

1. **Maverick Spend**: Purchases made without an active contract or from unapproved vendors, exposing the organization to un-negotiated rates and supplier risk.
2. **Contract Price Leakage**: Discrepancies where the invoiced amount exceeds the contract's negotiated rate.
3. **Duplicate Invoices**: Identical or near-identical invoices (handling fuzzy tax/rounding differences) submitted for the same purchase.
4. **Split Purchase Orders (Split POs)**: Instances where a single large purchase is artificially split into smaller consecutive POs to bypass managerial approval thresholds.
5. **Payment Leakage (Missed Discounts)**: Invoices that are paid late, resulting in the forfeiture of early-payment discounts.

## System Architecture & Machine Learning Methodology

The platform operates on a robust, multi-stage detection pipeline:

### 1. Synthetic Data Generation (`ml/generate_data.py`)
To rigorously test the system, we generate realistic procurement data containing both "Easy" and "Hard" leakage cases. 
- **Hard Cases** force the model to distinguish between legitimate edge-cases (e.g., a legitimate $90 one-off purchase from an approved vendor without a contract) and actual leakage (e.g., a $200 purchase from an unapproved vendor).
- The generator creates deterministic relationships across Vendors, Contracts, POs, Invoices, and Payments.

### 2. Rule-Based Heuristic Detectors (`ml/detectors.py`)
Each leakage category has a dedicated heuristic detector that parses the raw transactional data and extracts highly engineered features (e.g., `price_variance_pct`, `is_fuzzy_duplicate`, `split_po_cluster_size`, `is_approved_vendor`). It also includes an `IsolationForest` to generate a global `anomaly_score`.

### 3. XGBoost Meta-Classifier Ensemble (`ml/ensemble.py`)
Rather than relying purely on static rules, an XGBoost ensemble model ingest the features extracted by the heuristics. 
- **Explainability**: The model leverages **SHAP (SHapley Additive exPlanations)** to generate reason codes for every flagged transaction. Instead of a black-box "Anomaly Detected," the system can explicitly state: *"Flagged due to a 5.6% price variance above negotiated contract rate."*

## Current Project Status: Phase 3 Complete

We have successfully completed **Phase 3: ML Detection Engine & Evaluation**. 
- The pipeline was rigorously evaluated against a synthetic dataset of ~2,000 transactions.
- We achieved an overall F1-Score of **0.98+**.
- Hard edge cases for Maverick Spend and Split POs maintain high precision (0.84 - 0.93), proving the detectors successfully isolate leakage without being fooled by legitimate but similar-looking transactions.

## Next Steps: Phase 4 (Agent Integration)

We are actively transitioning into **Phase 4**. The immediate next steps are:
1. **API Layer**: Wrap the trained XGBoost model and heuristic logic into FastAPI endpoints (`backend/routers/analyze.py`).
2. **AI Agent**: Build a conversational agent (utilizing LLMs) that can query these endpoints, read the SHAP reason codes, and summarize the findings to a procurement officer in natural language.
3. **Dashboard UI**: Develop the frontend interface for end-users to interact with the platform.

## Project Structure

```text
├── backend/                  # FastAPI backend server
│   ├── routers/              # API Endpoints (auth, analyze, dashboard, reports, etc.)
│   ├── database.py           # Database connection and session management
│   ├── models.py             # SQLAlchemy ORM models
│   ├── schemas.py            # Pydantic schemas for data validation
│   └── main.py               # Application entry point
├── ml/                       # Machine Learning Pipeline
│   ├── generate_data.py      # Synthetic data generator
│   ├── detectors.py          # Rule-based heuristics and IsolationForest
│   ├── ensemble.py           # XGBoost classifier and SHAP integration
│   ├── train_models.py       # Orchestration script to run pipeline and train
│   ├── evaluate.py           # Evaluation script generating Precision/Recall metrics
│   └── saved_models/         # Serialized pickle files of the trained ensemble
├── data/                     
│   └── synthetic/            # Generated CSVs (Vendors, Contracts, POs, Invoices, Payments)
├── tests/                    # Pytest test suite
├── .gitignore                
├── requirements.txt          
└── README.md                 
```
