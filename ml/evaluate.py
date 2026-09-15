import pandas as pd
import numpy as np
import os
import pickle
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from detectors import LeakageDetectors
from ensemble import LeakageEnsemble

def evaluate_models():
    print("Loading synthetic data for evaluation...")
    base_dir = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
    
    vendors = pd.read_csv(os.path.join(base_dir, "vendors.csv"))
    contracts = pd.read_csv(os.path.join(base_dir, "contracts.csv"))
    pos = pd.read_csv(os.path.join(base_dir, "purchase_orders.csv"))
    invoices = pd.read_csv(os.path.join(base_dir, "invoices.csv"))
    payments = pd.read_csv(os.path.join(base_dir, "payments.csv"))
    labels = pd.read_csv(os.path.join(base_dir, "ground_truth.csv"))
    labels['leakage_type'] = labels['leakage_type'].fillna('None')
    
    print("Loading trained ensemble...")
    with open(os.path.join(os.path.dirname(__file__), "saved_models", "ensemble.pkl"), "rb") as f:
        ensemble = pickle.load(f)
        
    print("Running features extraction sequentially...")
    detectors = LeakageDetectors(vendors, contracts, pos, invoices, payments)
    
    df_dupes = detectors.detect_duplicate_invoices()
    df_price = detectors.detect_price_leakage()
    df_maverick = detectors.detect_maverick_spend()
    df_split = detectors.detect_split_pos()
    df_payment = detectors.detect_payment_leakage()
    df_vendor = detectors.score_vendor_risk()
    
    all_features = [df_dupes, df_price, df_maverick, df_split, df_payment]
    df_master = pd.concat([df[['id', 'type']] for df in all_features]).drop_duplicates(subset=['id']).reset_index(drop=True)
    
    id_to_vendor = {}
    for _, row in invoices.iterrows(): id_to_vendor[row['invoice_id']] = row['vendor_id']
    for _, row in pos.iterrows(): id_to_vendor[row['po_id']] = row['vendor_id']
    for _, row in payments.iterrows():
        inv_id = row['invoice_id']
        if inv_id in invoices['invoice_id'].values:
            v_id = invoices[invoices['invoice_id'] == inv_id]['vendor_id'].iloc[0]
            id_to_vendor[row['payment_id']] = v_id

    df_master['vendor_id'] = df_master['id'].map(id_to_vendor)
    df_master = pd.merge(df_master, df_vendor, on='vendor_id', how='left')
    
    for df_f in all_features:
        df_master = pd.merge(df_master, df_f.drop(columns=['type'], errors='ignore'), on='id', how='left')
        
    df_master.fillna(0, inplace=True)
    df_master = detectors.detect_anomalies(df_master)
    
    # Merge with ground truth for evaluation
    eval_df = pd.merge(df_master, labels, on='id', how='inner')
    
    X = eval_df[ensemble.feature_names].fillna(0)
    y_true = eval_df['flag']
    
    probs = ensemble.model.predict_proba(X)[:, 1]
    y_pred = (probs > 0.5).astype(int)
    
    print("\n--- ML Detection Engine Evaluation ---")
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, probs)
    cm = confusion_matrix(y_true, y_pred)
    
    print(f"Overall Precision: {precision:.4f}")
    print(f"Overall Recall:    {recall:.4f}")
    print(f"Overall F1-Score:  {f1:.4f}")
    print(f"Overall ROC-AUC:   {roc_auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    
    print("\n--- Category Breakdown (Easy vs Hard) ---")
    print(f"{'Category':<20} | {'Prec (Easy)':<11} | {'Prec (Hard)':<11} | {'Rec (Easy)':<10} | {'Rec (Hard)':<10}")
    print("-" * 75)
    
    cat_flags = {
        'Price Leakage': 'price_leak_flag',
        'Duplicate Invoice': 'duplicate_flag',
        'Maverick Spend': 'maverick_flag',
        'Split PO': 'split_po_flag',
        'Payment Leakage': 'discount_missed_flag'
    }
    
    for cat, flag_col in cat_flags.items():
        if flag_col not in eval_df.columns:
            continue
            
        metrics = {}
        for diff in ['easy', 'hard']:
            subset = eval_df[eval_df['difficulty'] == diff]
            if len(subset) == 0:
                metrics[diff] = {'p': 0.0, 'r': 0.0}
                continue
                
            y_true_sub = (subset['leakage_type'] == cat).astype(int)
            y_pred_sub = ((y_pred[subset.index] == 1) & (subset[flag_col] == 1)).astype(int)
            
            p = precision_score(y_true_sub, y_pred_sub, zero_division=0)
            r = recall_score(y_true_sub, y_pred_sub, zero_division=0)
            metrics[diff] = {'p': p, 'r': r}
            
        m_e = metrics['easy']
        m_h = metrics['hard']
        
        warn = "<-- WARNING: Hard Metric < 0.7" if m_h['p'] < 0.7 or m_h['r'] < 0.7 else ""
        print(f"{cat:<20} | {m_e['p']:.4f}      | {m_h['p']:.4f}      | {m_e['r']:.4f}     | {m_h['r']:.4f}     {warn}")

    # Feature importance table
    print("\n--- XGBoost Feature Importances ---")
    importance = ensemble.model.feature_importances_
    feat_imp = sorted(zip(ensemble.feature_names, importance), key=lambda x: -x[1])
    for fname, imp in feat_imp:
        marker = " <-- NEW" if fname in ('is_approved_vendor', 'is_fuzzy_duplicate') else ""
        print(f"  {fname:<25} {imp:.6f}{marker}")

if __name__ == "__main__":
    evaluate_models()
