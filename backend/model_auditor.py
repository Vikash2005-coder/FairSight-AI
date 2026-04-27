"""
FairSight AI — Model Auditor
Audits trained ML models for bias using SHAP explainability 
and group-wise performance metrics.
"""

import pandas as pd
import numpy as np
import shap
import sys
import os
import joblib
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.metrics import compute_fairness_metrics
from agents.orchestrator import run_full_audit

async def audit_model(model, domain: str = "auto", protected_attr: str = "", test_df: pd.DataFrame = None) -> dict:
    """
    Audits a trained ML model for bias.
    1. Runs model on test data.
    2. Computes fairness metrics on predictions.
    3. Runs SHAP to identify feature importance (bias drivers).
    4. Runs Gemini audit.
    """
    
    # 1. Use sample data if no test data provided
    if test_df is None:
        from generate_samples import generate_hiring_dataset
        # Default to hiring if auto/unknown
        if domain == "lending":
            from generate_samples import generate_loan_dataset
            test_df = generate_loan_dataset(200)
            target_col = "loan_approved"
        else:
            test_df = generate_hiring_dataset(200)
            target_col = "hired"
    else:
        from input_handler import infer_target_column
        target_col = infer_target_column(test_df)

    # 2. Get protected attribute
    if not protected_attr:
        from input_handler import auto_detect_protected_attributes
        detected = auto_detect_protected_attributes(test_df)
        protected_attr = detected[0] if detected else test_df.columns[0]

    print(f"[ModelAuditor] Auditing model: {type(model).__name__} | Attribute: {protected_attr}")

    # 3. Generate Predictions
    # We assume 'model' has a .predict() or .predict_proba() method (scikit-learn style)
    try:
        # Prepare features (drop target and id)
        X = test_df.drop(columns=[target_col], errors='ignore')
        if 'candidate_id' in X.columns: X = X.drop(columns=['candidate_id'])
        if 'applicant_id' in X.columns: X = X.drop(columns=['applicant_id'])
        if 'patient_id' in X.columns: X = X.drop(columns=['patient_id'])
        
        # Ensure only numeric/original features are used if model was trained on them
        # (Simplified for MVP: we use numeric cols)
        X_numeric = X.select_dtypes(include=[np.number])
        
        y_pred = model.predict(X_numeric)
        test_df['model_prediction'] = y_pred
    except Exception as e:
        return {"success": False, "error": f"Model prediction failed: {str(e)}"}

    # 4. Compute Fairness Metrics on predictions
    metrics_result = compute_fairness_metrics(test_df, protected_attr, 'model_prediction')

    # 5. SHAP Explainability (Detect Bias Drivers)
    shap_summary = {}
    try:
        # Simplified SHAP for common models
        explainer = shap.Explainer(model, X_numeric)
        shap_values = explainer(X_numeric)
        
        # Get mean absolute SHAP values per feature
        feature_importance = pd.DataFrame({
            'feature': X_numeric.columns,
            'importance': np.abs(shap_values.values).mean(axis=0)
        }).sort_values(by='importance', ascending=False)
        
        shap_summary = {
            "top_features": feature_importance.head(10).to_dict(orient='records'),
            "is_protected_attr_used": protected_attr in X_numeric.columns
        }
    except Exception as e:
        shap_summary = {"error": f"SHAP analysis failed: {str(e)}"}

    # 6. Run Gemini Multi-Agent Audit
    input_data_info = {
        "model_type": type(model).__name__,
        "protected_attribute": protected_attr,
        "shap_importance": shap_summary,
        "metrics": metrics_result["metrics"],
        "domain": domain
    }
    
    audit_result = await run_full_audit(input_data_info, metrics_result)

    return {
        "success": True,
        "model_type": type(model).__name__,
        "metrics": metrics_result,
        "shap_summary": shap_summary,
        "audit": audit_result,
        "overall_score": metrics_result["overall_fairness_score"]
    }
