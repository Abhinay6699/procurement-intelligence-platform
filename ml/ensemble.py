import xgboost as xgb
import shap
import pandas as pd
import numpy as np
import json

class LeakageEnsemble:
    def __init__(self):
        self.model = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
        self.explainer = None
        self.feature_names = None
        
    def train(self, df_features, df_labels):
        # Merge features and labels on 'id'
        df = pd.merge(df_features, df_labels, on='id', how='inner')
        
        # Determine feature columns (only numeric)
        exclude_cols = ['id', 'type', 'leakage_type', 'flag', 'vendor_id', 'category', 'difficulty']
        self.feature_names = [c for c in df.columns if c not in exclude_cols and not c.startswith('type_') and df[c].dtype in ['int64', 'float64', 'int32', 'float32', 'bool']]
        
        X = df[self.feature_names].fillna(0)
        y = df['flag']
        
        self.model.fit(X, y)
        self.explainer = shap.TreeExplainer(self.model)
        
        return self
        
    def predict(self, df_features):
        X = df_features[self.feature_names].fillna(0)
        probs = self.model.predict_proba(X)[:, 1]
        
        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X)
        
        results = []
        for i, row in df_features.iterrows():
            prob = float(probs[i])
            flag = "Flagged" if prob > 0.5 else "OK"
            
            # Generate SHAP reason
            shap_row = shap_values[i]
            # Handle if shap_values is a list (multiclass) or 2D array
            if isinstance(shap_row, list):
                shap_row = shap_row[1] # For binary classification, typically index 1 is positive class
                
            # Get top 2 features driving the prediction positively
            top_indices = np.argsort(shap_row)[-2:][::-1]
            reasons = []
            for idx in top_indices:
                if shap_row[idx] > 0:
                    feat_name = self.feature_names[idx]
                    feat_val = X.iloc[i][feat_name]
                    reasons.append(f"{feat_name} ({feat_val:.2f})")
            
            shap_reason = "No significant leakage risk factors found."
            if flag == "Flagged" and reasons:
                shap_reason = f"High risk driven by: {', '.join(reasons)}"
                
            raw_features = X.iloc[i].to_dict()
            
            results.append({
                "id": row["id"],
                "flag": flag,
                "confidence": prob,
                "shap_reason": shap_reason,
                "raw_features": json.dumps(raw_features)
            })
            
        return pd.DataFrame(results)
