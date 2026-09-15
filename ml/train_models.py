import pandas as pd
import pickle
import os
from detectors import LeakageDetectors
from ensemble import LeakageEnsemble

def train_and_save():
    print("Loading synthetic data...")
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
    
    vendors = pd.read_csv(os.path.join(base_dir, "vendors.csv"))
    contracts = pd.read_csv(os.path.join(base_dir, "contracts.csv"))
    pos = pd.read_csv(os.path.join(base_dir, "purchase_orders.csv"))
    invoices = pd.read_csv(os.path.join(base_dir, "invoices.csv"))
    payments = pd.read_csv(os.path.join(base_dir, "payments.csv"))
    labels = pd.read_csv(os.path.join(base_dir, "ground_truth.csv"))
    labels['leakage_type'] = labels['leakage_type'].fillna('None')
    
    print("Initializing Leakage Detectors...")
    detectors = LeakageDetectors(vendors, contracts, pos, invoices, payments)
    
    # 1. Duplicate Invoice Detection
    print("Running Module 1: Duplicate Invoices...")
    df_dupes = detectors.detect_duplicate_invoices()
    
    # 2. Contract Price Leakage
    print("Running Module 2: Contract Price Leakage...")
    df_price = detectors.detect_price_leakage()
    
    # 3. Maverick Spend
    print("Running Module 3: Maverick Spend...")
    df_maverick = detectors.detect_maverick_spend()
    
    # 4. Split POs
    print("Running Module 4: Split POs...")
    df_split = detectors.detect_split_pos()
    
    # 5. Payment Leakage
    print("Running Module 5: Payment Leakage...")
    df_payment = detectors.detect_payment_leakage()
    
    # 6. Vendor Risk
    print("Running Module 6: Vendor Risk Scoring...")
    df_vendor = detectors.score_vendor_risk()
    
    print("Aggregating features...")
    # Aggregate features onto a master transaction ID list (we can union all IDs)
    all_features = [df_dupes, df_price, df_maverick, df_split, df_payment]
    
    # Start with a list of all IDs
    df_master = pd.concat([df[['id', 'type']] for df in all_features]).drop_duplicates(subset=['id']).reset_index(drop=True)
    
    # Map vendor_id to each transaction ID
    id_to_vendor = {}
    for _, row in invoices.iterrows(): id_to_vendor[row['invoice_id']] = row['vendor_id']
    for _, row in pos.iterrows(): id_to_vendor[row['po_id']] = row['vendor_id']
    for _, row in payments.iterrows():
        inv_id = row['invoice_id']
        if inv_id in invoices['invoice_id'].values:
            v_id = invoices[invoices['invoice_id'] == inv_id]['vendor_id'].iloc[0]
            id_to_vendor[row['payment_id']] = v_id

    df_master['vendor_id'] = df_master['id'].map(id_to_vendor)
    
    # Join Vendor Risk
    df_master = pd.merge(df_master, df_vendor, on='vendor_id', how='left')
    
    # Join individual detector features
    for df_f in all_features:
        df_master = pd.merge(df_master, df_f.drop(columns=['type'], errors='ignore'), on='id', how='left')
        
    df_master.fillna(0, inplace=True)
    
    # 7. Anomaly Detection
    print("Running Module 7: Anomaly Detection...")
    df_master = detectors.detect_anomalies(df_master)
    
    # Ensemble
    print("Training XGBoost Ensemble...")
    ensemble = LeakageEnsemble()
    ensemble.train(df_master, labels)
    
    # Save models
    os.makedirs(os.path.join(os.path.dirname(__file__), "saved_models"), exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), "saved_models", "ensemble.pkl"), "wb") as f:
        pickle.dump(ensemble, f)
        
    print("Training complete. Models saved.")

if __name__ == "__main__":
    train_and_save()
