"""
FairSight AI — Intersectional Bias Engine
Detects bias arising from the combination of multiple 
protected attributes (e.g., Gender + Caste + Region).
"""

import pandas as pd
import numpy as np
import sys
import os
import io

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.metrics import compute_fairness_metrics, get_intersectional_groups

def run_intersectional_analysis(csv_content: bytes, protected_attrs: list) -> dict:
    """
    Computes bias for each combination of protected attributes.
    Detects if combined bias > individual bias (intersectional amplification).
    """
    try:
        df = pd.read_csv(io.BytesIO(csv_content))
        from input_handler import infer_target_column
        target_col = infer_target_column(df)
        
        if not protected_attrs or len(protected_attrs) < 2:
            return {"success": False, "error": "Require at least 2 protected attributes for intersectional analysis."}

        # 1. Compute Individual Baselines
        individual_results = []
        for attr in protected_attrs:
            res = compute_fairness_metrics(df, attr, target_col)
            individual_results.append({
                "attribute": attr,
                "disparity": res["metrics"]["statistical_parity_difference"],
                "overall_score": res["overall_fairness_score"]
            })

        # 2. Create Intersectional Attribute
        # e.g., "Male | Rural"
        df['intersectional_attr'] = get_intersectional_groups(df, protected_attrs)
        
        # 3. Compute Intersectional Metrics
        inter_res = compute_fairness_metrics(df, 'intersectional_attr', target_col)
        
        # 4. Detect Amplification
        # If intersectional disparity > max of individual disparities
        max_individual_disp = max(r["disparity"] for r in individual_results)
        inter_disp = inter_res["metrics"]["statistical_parity_difference"]
        amplification_factor = inter_disp / max_individual_disp if max_individual_disp > 0 else 1.0

        # 5. Extract Subgroup Scores for Bubble Chart
        # Calculate rates for each unique combination
        group_stats = df.groupby('intersectional_attr')[target_col].agg(['mean', 'count']).reset_index()
        subgroups = []
        for _, row in group_stats.iterrows():
            subgroups.append({
                "name": row['intersectional_attr'],
                "outcome_rate": round(row['mean'], 3),
                "count": int(row['count']),
                "disparity_from_avg": round(row['mean'] - df[target_col].mean(), 3)
            })

        return {
            "success": True,
            "attributes_analyzed": protected_attrs,
            "individual_results": individual_results,
            "intersectional_summary": {
                "max_disparity": round(inter_disp, 3),
                "amplification_factor": round(amplification_factor, 2),
                "most_vulnerable_group": inter_res["summary"]["unprivileged_group"],
                "overall_intersectional_score": inter_res["overall_fairness_score"]
            },
            "subgroups": subgroups,
            "risk_level": "critical" if amplification_factor > 2.0 else "high" if amplification_factor > 1.5 else "moderate"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
