"""
FairSight AI — Pre-cached Demo Mode
Provides instant analysis results for the sample datasets 
to ensure a smooth, fast-loading demo for judges.
"""

import os
import json

DEMO_DATA_MAP = {
    "hiring_bias.csv": "hiring_analysis.json",
    "loan_bias.csv": "loan_analysis.json",
    "healthcare_bias.csv": "healthcare_analysis.json",
    "compas_sample.csv": "compas_analysis.json",
    "education_bias.csv": "education_analysis.json",
    "ecommerce_bias.csv": "ecommerce_analysis.json"
}

PRECACHE_DIR = os.path.join(os.path.dirname(__file__), "precache")

def get_precached_analysis(filename: str) -> dict:
    """
    Returns a pre-generated analysis JSON if available for the filename.
    """
    cache_file_name = DEMO_DATA_MAP.get(filename)
    if not cache_file_name:
        return None
        
    cache_path = os.path.join(PRECACHE_DIR, cache_file_name)
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    return None

def save_to_precache(filename: str, result: dict):
    """
    Saves a result to precache for future instant loading.
    """
    os.makedirs(PRECACHE_DIR, exist_ok=True)
    cache_file_name = DEMO_DATA_MAP.get(filename)
    if cache_file_name:
        cache_path = os.path.join(PRECACHE_DIR, cache_file_name)
        with open(cache_path, 'w') as f:
            json.dump(result, f, indent=2)
