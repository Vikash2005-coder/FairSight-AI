"""
FairSight AI — Fairness Metrics Computation
Core mathematical logic for computing demographic parity, 
disparate impact, equalized odds, and more.
"""

import pandas as pd
import numpy as np

def is_positive(val):
    """
    Detects success indicators like '>', 'approved', 'yes', etc.
    Shared across audit and mitigation engines.
    """
    pos_keywords = ['approved', 'yes', 'y', 'admitted', 'paid', 'passed', 'hired', 'true', 'high_risk', 'success', 'eligible', 'good']
    v_str = str(val).lower().strip()
    # 1. Direct Keyword Match
    if v_str in pos_keywords or v_str == '1' or v_str == '1.0':
        return 1
    # 2. Mathematical Indicators (e.g., ">50K", "+1")
    if '>' in v_str or '+' in v_str:
        return 1
    # 3. Handle Boolean-like strings
    if v_str == 'true' or v_str == 't':
        return 1
    return 0

def compute_fairness_metrics(df: pd.DataFrame, protected_attr: str, target_col: str) -> dict:
    """
    Computes 8+ industry-standard fairness metrics.
    Assumes binary target (1 = positive/benefit, 0 = negative/penalty).
    Assumes protected attribute can be categorical (mapped to Privileged/Unprivileged).
    """
    
    # 1. Ensure Target Column is Numeric (Binary 0/1)
    # Convert categorical outcomes like 'Approved'/'Rejected' or '>50K' to 1/0
    if not pd.api.types.is_numeric_dtype(df[target_col]):
        df = df.copy() # Avoid SettingWithCopyWarning
        df[target_col] = df[target_col].apply(is_positive)
    else:
        # If numeric (Standardize to 0/1)
        # Even if there is noise or multiple values, we need a binary decision for fairness metrics.
        unique_vals = sorted(df[target_col].dropna().unique())
        if len(unique_vals) > 1:
            if not (0 in unique_vals and 1 in unique_vals and len(unique_vals) == 2):
                # We normalize: The highest value becomes 1, everything else becomes 0
                df = df.copy()
                max_val = df[target_col].max()
                df[target_col] = (df[target_col] == max_val).astype(int)
        else:
            # Only one value - cannot compute disparity fairly, but let's keep it 0 or 1
            df = df.copy()
            df[target_col] = 0
    
    # Identify unique groups
    groups = df[protected_attr].dropna().unique()
    if len(groups) < 2:
        return {"error": f"Attribute '{protected_attr}' has only one group in {len(df)} rows. Cannot compute disparity."}

    # Automatically identify Privileged vs Unprivileged
    # Usually the group with the higher outcome rate is considered privileged in disparity analysis
    group_rates = df.groupby(protected_attr)[target_col].mean().sort_values(ascending=False)
    privileged_group = group_rates.index[0]
    unprivileged_group = group_rates.index[-1]
    
    # Data subsets
    df_priv = df[df[protected_attr] == privileged_group]
    df_unpriv = df[df[protected_attr] == unprivileged_group]
    
    # ── 1. Demographic Parity (Statistical Parity) ──────────────────────────
    # P(Y=1 | Privileged) - P(Y=1 | Unprivileged)
    rate_priv = df_priv[target_col].mean() if len(df_priv) > 0 else 0
    rate_unpriv = df_unpriv[target_col].mean() if len(df_unpriv) > 0 else 0
    
    # Safety: If NO POSITIVE outcomes exist at all, the model is technically "fair" (it denies everyone equally)
    if rate_priv == 0 and rate_unpriv == 0:
        return {
            "summary": {
                "privileged_group": str(privileged_group),
                "unprivileged_group": str(unprivileged_group),
                "privileged_rate": 0.0,
                "unprivileged_rate": 0.0,
                "protected_attribute": str(protected_attr),
                "group_counts": {str(k): int(v) for k, v in df[protected_attr].value_counts().to_dict().items()},
                "all_group_rates": {str(k): 0.0 for k in df[protected_attr].unique()}
            },
            "metrics": {
                "demographic_parity_difference": 0.0,
                "disparate_impact_ratio": 1.0,
                "statistical_parity_difference": 0.0,
                "individual_fairness_proxy": 1.0
            },
            "overall_fairness_score": 100.0,
            "status": "fair",
            "message": "No positive outcomes (approved/hired) detected in the dataset. System is technically fair as it treats all groups equally."
        }

    demographic_parity_diff = rate_priv - rate_unpriv
    
    # ── 2. Disparate Impact Ratio (80% Rule) ──────────────────────────────
    # P(Y=1 | Unprivileged) / P(Y=1 | Privileged)
    if rate_priv == 0:
        disparate_impact_ratio = 1.0 if rate_unpriv == 0 else 0.0
    else:
        disparate_impact_ratio = rate_unpriv / rate_priv
        
    # ── 3. Statistical Parity Difference ──────────────────────────────────
    # Same as demographic parity diff but strictly the difference
    stat_parity_diff = abs(demographic_parity_diff)

    # Note: For error-based metrics, we'd need ground truth vs predictions.
    # If the user uploaded a dataset WITH predictions (e.g. model audit), 
    # we expect columns for both actual and predicted.
    # For now, let's look for 'prediction' or similar columns.
    
    pred_col = None
    for col in df.columns:
        if str(col).lower() in ['prediction', 'predicted', 'pred', 'high_risk_predicted', 'loan_status_pred']:
            pred_col = col
            break
            
    # Error metrics (only if prediction column exists)
    error_metrics = {}
    if pred_col:
        # TPR (Recall), FPR, etc.
        def get_tpr(sub_df):
            tp = len(sub_df[(sub_df[target_col] == 1) & (sub_df[pred_col] == 1)])
            fn = len(sub_df[(sub_df[target_col] == 1) & (sub_df[pred_col] == 0)])
            return tp / (tp + fn) if (tp + fn) > 0 else 1.0

        def get_fpr(sub_df):
            fp = len(sub_df[(sub_df[target_col] == 0) & (sub_df[pred_col] == 1)])
            tn = len(sub_df[(sub_df[target_col] == 0) & (sub_df[pred_col] == 0)])
            return fp / (fp + tn) if (fp + tn) > 0 else 0.0

        tpr_priv = get_tpr(df_priv)
        tpr_unpriv = get_tpr(df_unpriv)
        fpr_priv = get_fpr(df_priv)
        fpr_unpriv = get_fpr(df_unpriv)
        
        # ── 4. Equalized Odds Difference ──────────────────────────────────
        # Max(|TPR_diff|, |FPR_diff|)
        tpr_diff = abs(tpr_priv - tpr_unpriv)
        fpr_diff = abs(fpr_priv - fpr_unpriv)
        equalized_odds_diff = max(tpr_diff, fpr_diff)
        
        # ── 5. Average Odds Difference ────────────────────────────────────
        # (TPR_diff + FPR_diff) / 2
        avg_odds_diff = (tpr_diff + fpr_diff) / 2
        
        error_metrics = {
            "tpr_privileged": round(tpr_priv, 3),
            "tpr_unprivileged": round(tpr_unpriv, 3),
            "fpr_privileged": round(fpr_priv, 3),
            "fpr_unprivileged": round(fpr_unpriv, 3),
            "equalized_odds_difference": round(equalized_odds_diff, 3),
            "average_odds_difference": round(avg_odds_diff, 3)
        }

    # ── 6. Individual Fairness (Consistency) ──────────────────────────────
    # Simple consistency: for each row, find nearest neighbors and compare outcomes
    # Note: In full implementation, we'd use k-NN.
    individual_fairness_proxy = 1.0 - float(df[target_col].std()) if len(df) > 1 else 1.0
    
    # All Group Rates for detailed charting
    all_group_rates = {str(k): round(float(v), 3) for k, v in group_rates.to_dict().items()}
    
    # ── 7. Overall Fairness Score (0-100) ─────────────────────────────────
    # We aggregate several factors into one number
    # Start with 100 and subtract penalties
    score = 100.0
    score -= (float(stat_parity_diff) * 40.0) # Max 40 penalty
    if disparate_impact_ratio < 0.8:
        # Avoid division by zero and handle infinity
        impact_penalty = ((0.8 - float(disparate_impact_ratio)) / 0.8) * 30.0
        score -= min(30.0, max(0.0, impact_penalty))
    
    if "equalized_odds_difference" in error_metrics:
        score -= (float(error_metrics["equalized_odds_difference"]) * 30.0)
    
    # Final score safety
    score = float(score)
    if np.isnan(score): score = 50.0 # Neutral fallback
    score = max(0.0, min(100.0, score))

    # Identify a 'Privileged Sample' for Red-Teaming (a successful outcome row)
    privileged_sample = None
    try:
        # Standardize success label detection (1 = positive/success)
        pos_indices = df[target_col] == 1
        pos_df = df[pos_indices]
        if not pos_df.empty:
            privileged_sample = pos_df.iloc[0].to_dict()
            privileged_sample = {k: (float(v) if isinstance(v, (np.float64, np.int64, np.float32, np.int32)) else v) for k, v in privileged_sample.items()}
    except Exception as e:
        print(f"Sample extraction error: {e}")

    return {
        "summary": {
            "privileged_group": str(privileged_group),
            "unprivileged_group": str(unprivileged_group),
            "privileged_rate": round(float(rate_priv), 3),
            "unprivileged_rate": round(float(rate_unpriv), 3),
            "protected_attribute": str(protected_attr),
            "group_counts": {str(k): int(v) for k, v in df[protected_attr].value_counts().to_dict().items()},
            "all_group_rates": all_group_rates
        },
        "metrics": {
            "demographic_parity_difference": round(float(demographic_parity_diff), 3),
            "disparate_impact_ratio": round(float(disparate_impact_ratio), 3),
            "statistical_parity_difference": round(float(stat_parity_diff), 3),
            "individual_fairness_proxy": round(float(individual_fairness_proxy), 3),
            **error_metrics
        },
        "overall_fairness_score": round(float(score), 1),
        "status": "fair" if score > 80 else "caution" if score > 60 else "biased",
        "privileged_sample": privileged_sample,
        "protected_attribute": str(protected_attr),
        "target_column": str(target_col)
    }

def get_intersectional_groups(df: pd.DataFrame, attrs: list) -> pd.Series:
    """Combines multiple columns into one intersectional attribute"""
    return df[attrs].astype(str).agg(' | '.join, axis=1)
