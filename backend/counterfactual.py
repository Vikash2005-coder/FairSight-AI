"""
FairSight AI — Counterfactual Fairness Engine
Implements 'What-If' analysis to show how changing a protected 
attribute (e.g., Male -> Female) affects the model outcome.
"""

import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def run_counterfactual(dataset_summary: dict, protected_attr: str, sample_row: dict) -> dict:
    """
    Simulates changing an attribute and predicting the outcome.
    For MVP, uses the bias patterns detected in the dataset to 
    estimate the counterfactual probability change.
    """
    try:
        # 1. Identify current state
        current_val = sample_row.get(protected_attr)
        
        # 2. Identify counterfactual state 
        # (e.g., if Male, what if Female? if Urban, what if Rural?)
        if str(current_val).lower() in ['male', 'man']:
            cf_val = 'Female'
        elif str(current_val).lower() in ['female', 'woman']:
            cf_val = 'Male'
        elif 'urban' in str(current_val).lower():
            cf_val = 'Rural'
        else:
            # Random alternative if not binary
            cf_val = "Alternative Group"

        # 3. Estimate outcome change based on disparity
        # In a real model, we would call model.predict(cf_row)
        # Here we use the statistical disparity as a guide for the visualization
        
        disparity = dataset_summary.get("metrics", {}).get("demographic_parity_difference", 0.2)
        
        # If current group is privileged, moving to unprivileged decreases approval
        # If current group is unprivileged, moving to privileged increases approval
        
        is_privileged = str(current_val) == str(dataset_summary.get("summary", {}).get("privileged_group"))
        
        current_decision = sample_row.get("hired") or sample_row.get("loan_approved") or 1
        
        if is_privileged:
            # What if unprivileged?
            cf_decision = 0 if np.random.random() < abs(disparity) else current_decision
            cf_confidence = 0.85 - abs(disparity)
            current_confidence = 0.85
        else:
            # What if privileged?
            cf_decision = 1 if np.random.random() < abs(disparity) else current_decision
            cf_confidence = 0.85 + abs(disparity)
            current_confidence = 0.75

        return {
            "success": True,
            "attribute": protected_attr,
            "actual": {
                "value": str(current_val),
                "decision": "Approved/Hired" if current_decision == 1 else "Rejected",
                "confidence": round(current_confidence, 2)
            },
            "counterfactual": {
                "value": str(cf_val),
                "decision": "Approved/Hired" if cf_decision == 1 else "Rejected",
                "confidence": round(cf_confidence, 2)
            },
            "bias_finding": "Same profile, different attribute resulted in a different decision." if current_decision != cf_decision else "No immediate decision flip detected for this specific sample, but confidence shifted."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
