import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest

class LeakageDetectors:
    def __init__(self, vendors, contracts, pos, invoices, payments):
        self.vendors = vendors
        
        # Ensure dates are datetime
        if 'valid_from' in contracts.columns: contracts['valid_from'] = pd.to_datetime(contracts['valid_from'])
        if 'valid_to' in contracts.columns: contracts['valid_to'] = pd.to_datetime(contracts['valid_to'])
        if 'created_at' in pos.columns: pos['created_at'] = pd.to_datetime(pos['created_at'])
        if 'invoice_date' in invoices.columns: invoices['invoice_date'] = pd.to_datetime(invoices['invoice_date'])
        if 'due_date' in invoices.columns: invoices['due_date'] = pd.to_datetime(invoices['due_date'])
        if 'payment_date' in payments.columns: payments['payment_date'] = pd.to_datetime(payments['payment_date'])

        self.contracts = contracts
        self.pos = pos
        self.invoices = invoices
        self.payments = payments
        self.rf_vendor_risk = None
        self.iso_forest = None
        
    def _fuzzy_match(self, amt1, amt2):
        tolerance = max(5.0, amt1 * 0.03)  # ±$5 or ±3%, whichever is larger
        return abs(amt1 - amt2) <= tolerance

    def detect_duplicate_invoices(self):
        # Exact and fuzzy duplicate invoice detection
        features = []
        invs = self.invoices.sort_values(by=['vendor_id', 'invoice_date']).reset_index(drop=True)
        
        exact_dupes = invs.duplicated(subset=['vendor_id', 'po_id', 'amount', 'invoice_date'], keep='first')
        
        for idx, row in invs.iterrows():
            is_exact = exact_dupes[idx]
            
            # fuzzy check (same vendor, amount diff < 1, within 3 days, same PO)
            recent = invs.iloc[:idx]
            recent = recent[(recent['vendor_id'] == row['vendor_id']) & 
                            (recent['po_id'] == row['po_id']) &
                            (recent['invoice_date'] >= row['invoice_date'] - pd.Timedelta(days=3))]
            
            is_fuzzy = any(self._fuzzy_match(row['amount'], r['amount']) for _, r in recent.iterrows())
            
            features.append({
                'id': row['invoice_id'],
                'type': 'invoice',
                'is_exact_duplicate': int(is_exact),
                'is_fuzzy_duplicate': int(is_fuzzy),
                'duplicate_flag': int(is_exact or is_fuzzy)
            })
            
        return pd.DataFrame(features)

    def detect_price_leakage(self):
        # Invoice amount vs PO amount vs Contract rate
        features = []
        po_dict = self.pos.set_index('po_id').to_dict('index')
        
        for _, row in self.invoices.iterrows():
            po_id = row['po_id']
            inv_amt = row['amount']
            
            price_variance = 0.0
            if po_id in po_dict:
                po_amt = po_dict[po_id]['amount']
                if po_amt > 0:
                    price_variance = (inv_amt - po_amt) / po_amt
                    
            features.append({
                'id': row['invoice_id'],
                'type': 'invoice',
                'price_variance_pct': price_variance,
                'price_leak_flag': int(price_variance > 0.05)
            })
            
        return pd.DataFrame(features)

    def detect_maverick_spend(self):
        # PO without contract or outside valid dates, from an unapproved vendor
        features = []
        
        # Build vendor approval lookup
        vendor_approved = self.vendors.set_index('vendor_id')['is_approved_vendor'].to_dict()
        
        for _, row in self.pos.iterrows():
            v_contracts = self.contracts[self.contracts['vendor_id'] == row['vendor_id']]
            has_contract = False
            if not v_contracts.empty:
                # Check dates
                valid_contracts = v_contracts[(v_contracts['valid_from'] <= row['created_at']) & 
                                              (v_contracts['valid_to'] >= row['created_at'])]
                if not valid_contracts.empty:
                    has_contract = True
            
            is_approved = vendor_approved.get(row['vendor_id'], False)
            # Maverick = no valid contract AND vendor is not approved
            is_maverick = (not has_contract) and (not is_approved)
                    
            features.append({
                'id': row['po_id'],
                'type': 'po',
                'has_contract': int(has_contract),
                'is_approved_vendor': int(is_approved),
                'maverick_flag': int(is_maverick)
            })
        return pd.DataFrame(features)

    def detect_split_pos(self):
        features = []
        THRESHOLD = 10000
        
        pos = self.pos.sort_values(by=['vendor_id', 'created_at'])
        
        for idx, row in pos.iterrows():
            amt = row['amount']
            is_split = False
            cluster_size = 1
            if amt < THRESHOLD:
                # check surrounding 3 days
                near_pos = pos[(pos['vendor_id'] == row['vendor_id']) & 
                               (pos['created_at'] >= row['created_at'] - pd.Timedelta(days=3)) &
                               (pos['created_at'] <= row['created_at'] + pd.Timedelta(days=3)) &
                               (pos['po_id'] != row['po_id']) &
                               (pos['department'] == row['department']) &
                               (pos['amount'] < THRESHOLD)]
                
                sum_near = near_pos['amount'].sum()
                if len(near_pos) > 0 and (amt + sum_near) > THRESHOLD:
                    is_split = True
                    cluster_size = len(near_pos) + 1
                    
            features.append({
                'id': row['po_id'],
                'type': 'po',
                'split_po_cluster_size': cluster_size,
                'split_po_flag': int(is_split)
            })
            
        return pd.DataFrame(features)

    def detect_payment_leakage(self):
        # Paid late or didn't get discount
        features = []
        inv_dict = self.invoices.set_index('invoice_id').to_dict('index')
        
        for _, row in self.payments.iterrows():
            inv_id = row['invoice_id']
            days_late = 0
            if inv_id in inv_dict:
                due = inv_dict[inv_id]['due_date']
                days_late = (row['payment_date'] - due).days
                
            payment_leak_flag = (days_late > 0 and row['discount_taken'] > 0)
            
            features.append({
                'id': row['payment_id'],
                'type': 'payment',
                'days_late': days_late,
                'discount_missed_flag': int(payment_leak_flag)
            })
            
        return pd.DataFrame(features)

    def score_vendor_risk(self):
        v_stats = []
        for v in self.vendors['vendor_id'].unique():
            v_invs = self.invoices[self.invoices['vendor_id'] == v]
            v_pos = self.pos[self.pos['vendor_id'] == v]
            
            total_spend = v_invs['amount'].sum()
            po_count = len(v_pos)
            inv_count = len(v_invs)
            
            v_stats.append({
                'vendor_id': v,
                'total_spend': total_spend,
                'po_count': po_count,
                'inv_count': inv_count
            })
            
        v_df = pd.DataFrame(v_stats).fillna(0)
        
        X = v_df[['total_spend', 'po_count', 'inv_count']]
        
        self.rf_vendor_risk = IsolationForest(contamination=0.1, random_state=42)
        v_df['vendor_risk_score'] = self.rf_vendor_risk.fit_predict(X)
        v_df['vendor_risk_score'] = (v_df['vendor_risk_score'] == -1).astype(int)
        
        return v_df[['vendor_id', 'vendor_risk_score']]

    def detect_anomalies(self, df_combined):
        features_to_use = [col for col in df_combined.columns if col not in ['id', 'type', 'vendor_id', 'category', 'raw_features', 'shap_reason', 'flag', 'leakage_type']]
        X = df_combined[features_to_use].fillna(0)
        
        self.iso_forest = IsolationForest(contamination=0.08, random_state=42)
        preds = self.iso_forest.fit_predict(X)
        
        df_combined['anomaly_score'] = (preds == -1).astype(int)
        return df_combined
