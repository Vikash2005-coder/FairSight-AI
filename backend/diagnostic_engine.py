"""
FairSight AI — Deep Diagnostic Engine
Contains logic for "Surgical Data Auditing" (Poison Rows) and "Bias Sensitivity Heatmap".
"""

import pandas as pd
import numpy as np
import io
import sys
import os
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def _is_pos(v):
    v_str = str(v).lower().strip()
    pos_keywords = ['approved', 'yes', 'y', 'admitted', 'paid', 'passed', 'hired', 'true', 'high_risk', 'success', 'eligible', 'good']
    if v_str in pos_keywords or v_str == '1' or v_str == '1.0' or '>' in v_str or '+' in v_str or v_str == 't':
        return 1
    return 0

def _load_data(csv_content: bytes, filename: str) -> pd.DataFrame:
    """Loads a CSV or evaluates a PKL model to return a DataFrame for auditing."""
    if filename.endswith('.pkl'):
        import joblib
        model = joblib.load(io.BytesIO(csv_content))
        
        # We need a test dataset to evaluate the model on
        # Use hiring dataset by default for synthetic_biased_model.pkl
        from generate_samples import generate_hiring_dataset, generate_loan_dataset
        
        # Try to infer if it's loan or hiring based on name, or just try hiring
        if 'india' in filename.lower():
            import sys
            sys.path.append(os.path.dirname(__file__))
            from generate_india_model import generate_india_dataset
            df = generate_india_dataset(200)
            target = "loan_approved"
        elif 'loan' in filename.lower():
            df = generate_loan_dataset(200)
            target = "loan_approved"
        else:
            df = generate_hiring_dataset(200)
            target = "hired"
            
        X = df.drop(columns=[target, 'candidate_id', 'applicant_id'], errors='ignore')
        X_numeric = X.select_dtypes(include=[np.number])
        X_numeric = X_numeric.fillna(X_numeric.mean())
        
        preds = model.predict(X_numeric)
        df['model_prediction'] = preds
        return df
    else:
        return pd.read_csv(io.BytesIO(csv_content))

def find_poison_rows(csv_content: bytes, filename: str, protected_attr: str, target_col: str) -> dict:
    """
    Identifies the rows that are actively driving the bias.
    Calculates a 'Merit Score' using Logistic Regression on legitimate features,
    then finds contradictions.
    """
    try:
        df = _load_data(csv_content, filename)
        
        # If it's a model, target_col is 'model_prediction' regardless of what the UI sent
        if filename.endswith('.pkl'):
            target_col = 'model_prediction'
        
        if not target_col or target_col not in df.columns:
            return {"success": False, "error": "Target column not found"}
            
        # Auto-detect protected attribute if not provided
        if not protected_attr or protected_attr not in df.columns:
            from input_handler import auto_detect_protected_attributes
            detected = auto_detect_protected_attributes(df)
            if detected:
                protected_attr = detected[0]
            else:
                return {"success": False, "error": "Protected attribute not found or not explicitly passed"}

        # Normalize target
        df['__target'] = df[target_col].apply(_is_pos)
        
        # Identify privileged vs unprivileged
        group_rates = df.groupby(protected_attr)['__target'].mean()
        unprivileged = group_rates.idxmin()
        privileged = group_rates.idxmax()

        # Prepare numeric features for Merit Score
        X = df.drop(columns=[target_col, '__target', protected_attr], errors='ignore')
        # Drop likely ID columns
        cols_to_drop = [c for c in X.columns if 'id' in c.lower() or 'name' in c.lower()]
        X = X.drop(columns=cols_to_drop, errors='ignore')
        
        X_numeric = X.select_dtypes(include=[np.number])
        if X_numeric.empty:
            return {"success": False, "error": "No numeric features to calculate merit"}

        # Impute and scale
        X_numeric = X_numeric.fillna(X_numeric.mean())
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_numeric)

        # Train a quick model to estimate "Objective Merit" based on all data
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_scaled, df['__target'])
        
        # Merit Score is the probability of positive outcome based purely on numeric features
        df['merit_score'] = model.predict_proba(X_scaled)[:, 1]

        # Find Poison Rows
        # Type 1: High Merit, Unprivileged, Rejected
        unfair_rejections = df[(df[protected_attr] == unprivileged) & (df['__target'] == 0)]
        unfair_rejections = unfair_rejections.sort_values(by='merit_score', ascending=False).head(5)

        # Type 2: Low Merit, Privileged, Approved
        unfair_approvals = df[(df[protected_attr] == privileged) & (df['__target'] == 1)]
        unfair_approvals = unfair_approvals.sort_values(by='merit_score', ascending=True).head(5)

        def _format_rows(rows_df, reason):
            results = []
            for _, row in rows_df.iterrows():
                # Extract key features for display
                features = {}
                for col in X_numeric.columns[:3]:  # Top 3 features
                    features[col] = round(row[col], 2) if isinstance(row[col], float) else row[col]
                
                results.append({
                    "group": str(row[protected_attr]),
                    "outcome": str(row[target_col]),
                    "merit": f"{round(row['merit_score'] * 100, 1)}%",
                    "reason": reason,
                    "features": features
                })
            return results

        poison_rows = []
        poison_rows.extend(_format_rows(unfair_rejections, f"Highly qualified but rejected (Bias Victim)"))
        poison_rows.extend(_format_rows(unfair_approvals, f"Underqualified but approved (Bias Beneficiary)"))

        return {
            "success": True,
            "unprivileged_group": f"{unprivileged} ({round(group_rates[unprivileged]*100, 1)}% rate)",
            "privileged_group": f"{privileged} ({round(group_rates[privileged]*100, 1)}% rate)",
            "poison_rows": poison_rows
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate_feature_sensitivity(csv_content: bytes, filename: str, protected_attr: str, target_col: str) -> dict:
    """
    Identifies which features are driving the bias by iteratively dropping them 
    and measuring the change in Statistical Parity of a surrogate model.
    """
    try:
        df = _load_data(csv_content, filename)
        
        if filename.endswith('.pkl'):
            target_col = 'model_prediction'
        
        df['__target'] = df[target_col].apply(_is_pos)
        
        # Prepare numeric features
        X = df.drop(columns=[target_col, '__target'], errors='ignore') # Keep protected_attr for evaluation
        cols_to_drop = [c for c in X.columns if 'id' in c.lower() or 'name' in c.lower()]
        X = X.drop(columns=cols_to_drop, errors='ignore')
        
        # Auto-detect protected attribute if not provided
        if not protected_attr or protected_attr not in X.columns:
            from input_handler import auto_detect_protected_attributes
            detected = auto_detect_protected_attributes(X)
            if detected:
                protected_attr = detected[0]
            else:
                return {"success": False, "error": "Protected attribute not in dataset"}

        X_numeric_and_protected = X.select_dtypes(include=[np.number])
        if protected_attr not in X_numeric_and_protected.columns:
            # Temporarily encode protected attribute if it's categorical
            df['__protected_encoded'] = df[protected_attr].astype('category').cat.codes
            X_numeric_and_protected['__protected_encoded'] = df['__protected_encoded']
            eval_attr = '__protected_encoded'
        else:
            eval_attr = protected_attr

        features_to_test = [c for c in X_numeric_and_protected.columns if c != eval_attr]
        if not features_to_test:
            return {"success": False, "error": "Not enough numeric features for sensitivity analysis"}

        X_numeric_and_protected = X_numeric_and_protected.fillna(X_numeric_and_protected.mean())

        # Helper to calculate parity of a model's predictions
        def get_model_parity(features_df):
            scaler = StandardScaler()
            scaled = scaler.fit_transform(features_df)
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(scaled, df['__target'])
            preds = model.predict(scaled)
            
            # Parity = P(pred=1 | group=Privileged) - P(pred=1 | group=Unprivileged)
            # Find groups
            group_rates = pd.Series(preds).groupby(X_numeric_and_protected[eval_attr].values).mean()
            if len(group_rates) < 2: return 0
            return abs(group_rates.max() - group_rates.min())

        # 1. Baseline Parity (using all tested features)
        baseline_parity = get_model_parity(X_numeric_and_protected[features_to_test])
        
        if baseline_parity == 0:
             return {"success": True, "sensitivities": [{"feature": f, "sensitivity": 0} for f in features_to_test]}

        # 2. Iterative Drop
        sensitivities = []
        for feature in features_to_test:
            dropped_features = [f for f in features_to_test if f != feature]
            if not dropped_features:
                continue
                
            new_parity = get_model_parity(X_numeric_and_protected[dropped_features])
            
            # Drop in parity = improvement in fairness
            parity_drop = baseline_parity - new_parity
            
            # If parity drop is positive, the feature CAUSES bias. 
            # If negative, the feature actually helps REDUCE bias. We only care about causes.
            score = max(0, parity_drop)
            sensitivities.append({"feature": feature, "score": score})

        # 3. Normalize to 100%
        total_score = sum(s["score"] for s in sensitivities)
        results = []
        for s in sensitivities:
            pct = round((s["score"] / total_score * 100) if total_score > 0 else 0, 1)
            if pct > 0:  # Don't display 0% sensitivities
                results.append({
                    "feature": s["feature"],
                    "sensitivity": pct
                })

        # Sort descending
        results = sorted(results, key=lambda x: x["sensitivity"], reverse=True)

        return {
            "success": True,
            "sensitivities": results
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}
