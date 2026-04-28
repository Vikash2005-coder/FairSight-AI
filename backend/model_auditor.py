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
from utils.benchmarks_db import get_benchmark_comparison
from agents.orchestrator import run_full_audit

async def audit_model(model, domain: str = "auto", protected_attr: str = "", test_df: pd.DataFrame = None, filename: str = "") -> dict:
    """
    Audits a trained ML model for bias.
    1. Runs model on test data.
    2. Computes fairness metrics on predictions.
    3. Runs SHAP to identify feature importance (bias drivers).
    4. Runs Gemini audit.
    """
    
    # 1. Use sample data if no test data provided
    if test_df is None:
        if 'india' in filename.lower():
            import sys
            sys.path.append(os.path.dirname(__file__))
            from generate_india_model import generate_india_dataset
            test_df = generate_india_dataset(200)
            target_col = "loan_approved"
        elif 'loan' in filename.lower() or domain == "lending":
            from generate_samples import generate_loan_dataset
            test_df = generate_loan_dataset(200)
            target_col = "loan_approved"
        else:
            from generate_samples import generate_hiring_dataset
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

    # 6. Geographical Analysis
    geo_analysis = {"has_geo": False, "regions": []}
    detected_cols = [c for c in test_df.columns if any(k in str(c).lower() for k in ["region", "state", "city", "location", "pincode"])]
    
    if detected_cols:
        geo_col = detected_cols[0]
        for c in detected_cols:
            if any(k in str(c).lower() for k in ["state", "city"]):
                geo_col = c
                break
        
        for region_name, group_df in test_df.groupby(geo_col):
            if pd.isna(region_name) or str(region_name).strip() == "": continue
            try:
                reg_metrics = compute_fairness_metrics(group_df, protected_attr, 'model_prediction')
                geo_analysis["regions"].append({
                    "name": str(region_name),
                    "fairness_score": reg_metrics["overall_fairness_score"],
                    "status": reg_metrics["status"],
                    "sample_size": len(group_df),
                    "lat": None,
                    "lon": None
                })
            except Exception:
                # Simple fallback
                rate = group_df['model_prediction'].mean()
                geo_analysis["regions"].append({
                    "name": str(region_name),
                    "fairness_score": round(rate * 100, 1),
                    "status": "fair" if rate > 0.6 else "caution" if rate > 0.3 else "biased",
                    "sample_size": len(group_df),
                    "is_fallback": True,
                    "lat": None,
                    "lon": None
                })
        
        if geo_analysis["regions"]:
            geo_analysis["has_geo"] = True
            geo_analysis["column"] = geo_col
        geo_analysis["all_columns"] = list(test_df.columns)

    # 7. Run Gemini Multi-Agent Audit
    input_data_info = {
        "model_type": type(model).__name__,
        "protected_attribute": protected_attr,
        "shap_importance": shap_summary,
        "metrics": metrics_result["metrics"],
        "domain": domain
    }
    
    audit_result = await run_full_audit(input_data_info, metrics_result)

    # 8. Generate Benchmarks for Human Impact
    benchmarks = get_benchmark_comparison(domain, metrics_result["overall_fairness_score"], len(test_df))

    return {
        "success": True,
        "model_type": type(model).__name__,
        "protected_attribute": protected_attr,
        "target_column": target_col,
        "metrics": metrics_result,
        "shap_summary": shap_summary,
        "geo_analysis": geo_analysis,
        "audit": audit_result,
        "benchmarks": benchmarks,
        "overall_score": metrics_result["overall_fairness_score"],
        "status": metrics_result.get("status", "UNKNOWN")
    }
