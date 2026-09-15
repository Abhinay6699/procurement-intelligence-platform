from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd
import pickle
import os
import json

from ..database import get_db
from ..models import Invoice, PurchaseOrder, Vendor, Payment, Contract, Recommendation
from ml.detectors import LeakageDetectors
from ml.ensemble import LeakageEnsemble

router = APIRouter()

# Load the trained ensemble model on startup
ensemble_path = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "saved_models", "ensemble.pkl")
ensemble_model = None
if os.path.exists(ensemble_path):
    with open(ensemble_path, "rb") as f:
        ensemble_model = pickle.load(f)

@router.post("/run")
def run_analysis(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not ensemble_model:
        return {"status": "error", "message": "ML model not trained yet"}
        
    # Read DB data into pandas
    invoices = pd.read_sql(db.query(Invoice).statement, db.bind)
    pos = pd.read_sql(db.query(PurchaseOrder).statement, db.bind)
    vendors = pd.read_sql(db.query(Vendor).statement, db.bind)
    payments = pd.read_sql(db.query(Payment).statement, db.bind)
    contracts = pd.read_sql(db.query(Contract).statement, db.bind)
    
    if invoices.empty:
        return {"status": "error", "message": "No invoices to analyze"}
        
    detectors = LeakageDetectors(vendors, contracts, pos, invoices, payments)
    
    df_dupes = detectors.detect_duplicate_invoices()
    df_price = detectors.detect_price_leakage()
    df_maverick = detectors.detect_maverick_spend()
    df_split = detectors.detect_split_pos()
    df_payment = detectors.detect_payment_leakage()
    df_vendor = detectors.score_vendor_risk()
    
    all_features = [df_dupes, df_price, df_maverick, df_split, df_payment]
    df_master = pd.concat([df[['id', 'type']] for df in all_features]).drop_duplicates(subset=['id']).reset_index(drop=True)
    
    # ID mapping
    id_to_vendor = {}
    for _, row in invoices.iterrows(): id_to_vendor[row['invoice_id']] = row['vendor_id']
    for _, row in pos.iterrows(): id_to_vendor[row['po_id']] = row['vendor_id']
    for _, row in payments.iterrows():
        inv_id = row['invoice_id']
        v_id = invoices[invoices['id'] == inv_id]['vendor_id'].iloc[0] if not invoices[invoices['id'] == inv_id].empty else None
        if v_id is not None: id_to_vendor[row['payment_id']] = v_id

    df_master['vendor_id'] = df_master['id'].map(id_to_vendor)
    df_master = pd.merge(df_master, df_vendor, on='vendor_id', how='left')
    
    for df_f in all_features:
        df_master = pd.merge(df_master, df_f.drop(columns=['type'], errors='ignore'), on='id', how='left')
        
    df_master.fillna(0, inplace=True)
    df_master = detectors.detect_anomalies(df_master)
    
    predictions = ensemble_model.predict(df_master)
    
    # Process flagged items
    flagged_items = predictions[predictions['flag'] == 'Flagged']
    
    for _, row in flagged_items.iterrows():
        # find invoice id - if row is PO or payment, try to trace to invoice, otherwise just take first matching invoice
        transaction_id = row['id']
        
        # In a real app we'd map back carefully; here we create a recommendation record
        # Let's assume transaction_id matches invoice_id for simplicity, or we look it up.
        inv_record = db.query(Invoice).filter(Invoice.invoice_id == transaction_id).first()
        if not inv_record:
            continue
            
        rec = Recommendation(
            invoice_id=inv_record.id,
            ml_flag="Leakage Detected",
            confidence=row['confidence'],
            justification=row['shap_reason'],
            status="Pending Review"
        )
        db.add(rec)
    
    db.commit()
    return {"status": "success", "flagged_count": len(flagged_items)}

@router.get("/")
def get_analyze_status():
    return {"status": "Analysis module active", "model_loaded": ensemble_model is not None}
