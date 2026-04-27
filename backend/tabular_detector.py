"""
FairSight AI — Tabular Bias Detector
Integrates mathematical metrics with Gemini reasoning for CSV/Excel data.
"""

import pandas as pd
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.metrics import compute_fairness_metrics
from utils.benchmarks_db import get_benchmark_comparison
from agents.orchestrator import run_full_audit

def is_positive(val):
    """
    Bulletproof inline: detects success indicators dynamically.
    Sync'd with the latest regulatory standard (v3).
    """
    pos_keywords = ['approved', 'yes', 'y', 'admitted', 'paid', 'passed', 'hired', 'true', 'high_risk', 'success', 'eligible', 'good']
    v_str = str(val).lower().strip()
    return 1 if (v_str in pos_keywords or v_str == '1' or v_str == '1.0' or '>' in v_str or '+' in v_str or v_str == 't') else 0

async def detect_tabular_bias(df: pd.DataFrame, domain: str = "auto", protected_attr: str = "") -> dict:
    """
    Main entry point for tabular bias detection.
    Splits the process into:
    1. Analytical Stage (Math/Geo) - DETERMINISTIC
    2. Reasoning Stage (AI) - PROBABILISTIC / API DEPENDENT
    """
    # -- STAGE 1: ANALYTICAL (Pure Math/Geo) --
    # This part never fails due to API limits.
    analysis = perform_analytical_audit(df, domain, protected_attr)
    if not analysis["success"]:
        return analysis

    # -- STAGE 2: REASONING (Gemini AI) --
    # This part might fail due to quota.
    try:
        input_data_info = {
            "filename": "uploaded_dataset.csv",
            "rows": len(df),
            "columns": list(df.columns),
            "target_column": analysis["target_column"],
            "protected_attribute_analyzed": analysis["protected_attribute"],
            "domain": domain
        }
        
        audit_result = await run_full_audit(input_data_info, analysis["metrics"])
        
        # Merge results
        result = {**analysis, "audit": audit_result}
        return result

    except Exception as ai_err:
        print(f"[TabularDetector] AI Stage skipped/failed: {str(ai_err)}")
        # We raise here to let input_handler handle the formal persona-driven fallback
        raise ai_err


def perform_analytical_audit(df: pd.DataFrame, domain: str = "auto", protected_attr: str = "") -> dict:
    """
    Performs the deterministic parts of the audit:
    - Column normalization
    - Fairness metrics calculation
    - Geographical bias detection
    """
    from input_handler import auto_detect_protected_attributes, infer_target_column
    
    # 1. Normalize column names
    col_map = {c.strip().lower(): c for c in df.columns}
    
    if protected_attr and protected_attr.lower() in col_map:
        protected_attr = col_map[protected_attr.lower()]
    elif not protected_attr:
        detected_attrs = auto_detect_protected_attributes(df)
        if not detected_attrs:
            return {"success": False, "error": "No protected attributes detected."}
        protected_attr = detected_attrs[0]

    target_col = infer_target_column(df)
    
    # 2. Compute fairness metrics
    metrics_result = compute_fairness_metrics(df, protected_attr, target_col)
    if "error" in metrics_result:
        return {"success": False, "error": metrics_result["error"]}

    # 3. Geographical Analysis
    geo_analysis = {"has_geo": False, "regions": []}
    detected_cols = [c for c in df.columns if any(k in str(c).lower() for k in ["region", "state", "city", "location", "pincode"])]
    
    if detected_cols:
        geo_col = detected_cols[0]
        # Prioritize states/cities
        for c in detected_cols:
            if any(k in str(c).lower() for k in ["state", "city"]):
                geo_col = c
                break
        
        for region_name, group_df in df.groupby(geo_col):
            if pd.isna(region_name) or str(region_name).strip() == "": continue
            try:
                reg_metrics = compute_fairness_metrics(group_df, protected_attr, target_col)
                # Extract representative lat/lon from the group (first valid row)
                lat = lon = None
                if "latitude" in df.columns and "longitude" in df.columns:
                    valid = group_df[["latitude", "longitude"]].dropna()
                    if not valid.empty:
                        lat = float(valid["latitude"].iloc[0])
                        lon = float(valid["longitude"].iloc[0])
                geo_analysis["regions"].append({
                    "name": str(region_name),
                    "fairness_score": reg_metrics["overall_fairness_score"],
                    "status": reg_metrics["status"],
                    "sample_size": len(group_df),
                    "lat": lat,
                    "lon": lon
                })
            except Exception:
                # Simple fallback if full metrics fail on small group
                target_vals = group_df[target_col].map(lambda x: 1 if str(x).lower() in ['1', 'true', 'approved', 'yes', 'paid'] else 0)
                rate = target_vals.mean()
                lat = lon = None
                if "latitude" in df.columns and "longitude" in df.columns:
                    valid = group_df[["latitude", "longitude"]].dropna()
                    if not valid.empty:
                        lat = float(valid["latitude"].iloc[0])
                        lon = float(valid["longitude"].iloc[0])
                geo_analysis["regions"].append({
                    "name": str(region_name),
                    "fairness_score": round(rate * 100, 1),
                    "status": "fair" if rate > 0.6 else "caution" if rate > 0.3 else "biased",
                    "sample_size": len(group_df),
                    "is_fallback": True,
                    "lat": lat,
                    "lon": lon
                })
        
        if geo_analysis["regions"]:
            geo_analysis["has_geo"] = True
            geo_analysis["column"] = geo_col
        
        # Add all columns for frontend diagnostics
        geo_analysis["all_columns"] = list(df.columns)

    # 4. Benchmarks
    benchmarks = get_benchmark_comparison(domain, metrics_result["overall_fairness_score"], len(df))

    return {
        "success": True,
        "protected_attribute": protected_attr,
        "target_column": target_col,
        "metrics": metrics_result,
        "benchmarks": benchmarks,
        "geo_analysis": geo_analysis,
        "overall_score": metrics_result["overall_fairness_score"],
        "status": metrics_result["status"]
    }
