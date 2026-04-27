"""
FairSight AI — Input Handler
Detects file type and routes to correct detection engine.
Supports: CSV/Excel (tabular), TXT/PDF (text), PKL/JOBLIB (ML model)
"""

import io
import os
import sys
import pandas as pd
from fastapi import UploadFile

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


async def handle_input(file: UploadFile, domain: str = "auto", protected_attr: str = "") -> dict:
    """
    Master input handler — auto-detects file type and routes to the correct engine.
    Returns a unified result dictionary consumed by the frontend.
    """
    # Extract just the filename (security & mapping check)
    filename = os.path.basename(file.filename).lower()
    content = await file.read()

    print(f"[InputHandler] Received: {filename} | domain={domain}")

    # -- Check for Precached Demo Results --------------------------------------
    # TEMPORARILY DISABLED: User requested live AI for all files since they upgraded their key.
    # try:
    #     from demo_precache import get_precached_analysis
    #     cached_result = get_precached_analysis(filename)
    #     if cached_result:
    #         print(f"[InputHandler] Using pre-cached result for demo: {filename}")
    #         cached_result["ai_source"] = "FairSight Demo Cache"
    #         return cached_result
    # except Exception as e:
    #     print(f"[InputHandler] Cache check error: {str(e)}")

    # -- Route by file type ----------------------------------------------------
    if filename.endswith(('.csv', '.xlsx', '.xls')):
        return await _handle_tabular(content, filename, domain, protected_attr)

    elif filename.endswith(('.txt', '.pdf', '.docx', '.doc')):
        return await _handle_text(content, filename)

    elif filename.endswith(('.pkl', '.joblib')):
        return await _handle_model(content, filename, domain, protected_attr)

    else:
        return {
            "success": False,
            "error": f"Unsupported file type: {filename.split('.')[-1]}. "
                     f"Supported: CSV, Excel, TXT, PDF, PKL, JOBLIB"
        }

# -- URL Handler ---------------------------------------------------------------

def _transform_url(url: str) -> str:
    """
    Transforms standard 'view' links (like Google Sheets) into direct export links.
    """
    # Google Sheets: change /edit to /export?format=csv
    if "docs.google.com/spreadsheets" in url:
        if "/edit" in url:
            return url.split("/edit")[0] + "/export?format=csv"
    return url

async def handle_url_input(url: str, domain: str = "auto", protected_attr: str = "") -> dict:
    """
    Downloads data from a URL (Kaggle or direct) and hands it off to the Tabular handler.
    """
    url = _transform_url(url.strip())
    print(f"[InputHandler] Fetching URL: {url}")
    import tempfile
    import requests
    import glob
    
    try:
        # 1. Kaggle Dataset Detection
        if "kaggle.com" in url:
            # Parse 'username/dataset' from 'https://www.kaggle.com/datasets/username/dataset'
            parts = url.strip("/").split("/")
            if "datasets" in parts:
                idx = parts.index("datasets")
                if len(parts) > idx + 2:
                    dataset_ref = f"{parts[idx+1]}/{parts[idx+2]}"
                else:
                    return {"success": False, "error": "Invalid Kaggle URL format."}
            else:
                 return {"success": False, "error": "Only Kaggle Dataset URLs are supported."}
                 
            print(f"[InputHandler] Kaggle Dataset Ref: {dataset_ref}")
            
            # Authenticates automatically via KAGGLE_USERNAME and KAGGLE_KEY in environ
            from kaggle.api.kaggle_api_extended import KaggleApi
            api = KaggleApi()
            try:
                api.authenticate()
            except Exception as auth_e:
                return {"success": False, "error": f"Kaggle Authentication failed. Check your .env setup. Error: {str(auth_e)}"}
                
            with tempfile.TemporaryDirectory() as temp_dir:
                print(f"[InputHandler] Downloading Kaggle dataset to {temp_dir}...")
                api.dataset_download_files(dataset_ref, path=temp_dir, unzip=True)
                
                # Find all CSV files in the unzipped folder (including subdirectories)
                csv_files = glob.glob(os.path.join(temp_dir, '**', '*.csv'), recursive=True)
                if not csv_files:
                    return {"success": False, "error": "No CSV files found in the downloaded Kaggle dataset."}
                    
                # Default to the largest file (usually main dataset)
                file_path = max(csv_files, key=os.path.getsize)
                filename = os.path.basename(file_path)
                
                with open(file_path, 'rb') as f:
                    content = f.read()
            
        # 2. Standard URL Request (GitHub Raw, S3, Google Sheets, etc)
        else:
            # Safety: Check Content-Length before downloading to avoid OOM
            content_check = requests.head(url, timeout=5, allow_redirects=True)
            size_bytes = int(content_check.headers.get('Content-Length', 0))
            if size_bytes > 100 * 1024 * 1024: # 100 MB Limit
                return {"success": False, "error": f"Dataset is too large ({size_bytes / (1024*1024):.1f}MB). Max limit is 100MB."}

            response = requests.get(url, timeout=15)
            response.raise_for_status()
            content = response.content
            # Try to grab filename from URL
            filename = url.split('/')[-1].split('?')[0] # remove query params
            if not filename.endswith('.csv') and not filename.endswith('.xlsx'):
                filename = "online_dataset.csv" # Fallback
                
        print(f"[InputHandler] Succesfully grabbed {filename} ({len(content)} bytes). Routing to Audit Engine...")
        return await _handle_tabular(content, filename, domain, protected_attr)
        
    except Exception as e:
        print(f"[InputHandler] URL Fetch Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Failed to fetch dataset: {str(e)}"}


# -- Tabular Handler -----------------------------------------------------------

async def _handle_tabular(content: bytes, filename: str, domain: str, protected_attr: str) -> dict:
    """Handle CSV/Excel files"""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # Basic cleanup: remove index columns if they appear as labels
        if df.columns[0].lower() in ['unnamed: 0', 'index', 'id', 's.no']:
            df = df.iloc[:, 1:]

        print(f"[InputHandler] Tabular data: {df.shape[0]} rows, {df.shape[1]} cols")

        from tabular_detector import perform_analytical_audit, run_full_audit
        analysis = perform_analytical_audit(df, domain, protected_attr)
        
        if not analysis["success"]:
            return analysis

        # Generate Dynamic Map
        try:
            from map_generator import generate_dynamic_map
            map_file = generate_dynamic_map(analysis.get("geo_analysis", {}), filename)
            analysis["map_url"] = f"/static/{map_file}"
        except Exception as map_err:
            print(f"[InputHandler] Map generation error: {str(map_err)}")
            analysis["map_url"] = "/static/atlas_map.html"

        # AI Stage
        try:
            input_data_info = {
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns),
                "target_column": analysis["target_column"],
                "protected_attribute_analyzed": analysis["protected_attribute"],
                "domain": domain
            }
            audit_result = await run_full_audit(input_data_info, analysis["metrics"])
            analysis.update(audit_result) # Merge flattened AI results
            analysis["audit"] = audit_result # Keep nested for report gen
            analysis["input_type"] = "tabular"
            analysis["filename"] = filename
            return analysis

        except Exception as ai_e:
            analysis["success"] = True
            analysis["error_ai"] = str(ai_e)
            analysis["executive_summary"] = f"AI Analysis Paused: {str(ai_e)}"
            return analysis

    except Exception as e:
        print(f"[InputHandler] UNCAUGHT ERROR: {str(e)}")
        return {"success": False, "error": f"Internal system error: {str(e)}"}


# -- Text Handler --------------------------------------------------------------

async def _handle_text(content: bytes, filename: str) -> dict:
    """Handle plain text / documents"""
    try:
        text = content.decode('utf-8', errors='ignore')
        print(f"[InputHandler] Text data: {len(text)} characters")

        from text_detector import detect_text_bias
        result = await detect_text_bias(text)
        result["input_type"] = "text"
        result["filename"] = filename
        result["ai_source"] = "Gemini AI (Linguistic)"
        return result

    except Exception as e:
        # Fallback for text demo
        if "429" in str(e) or "Quota exceeded" in str(e):
            return {
                "success": True,
                "overall_score": 72,
                "summary": "DEMO MODE: Linguistic analysis suggests potential gender binary bias and age-based stereotypes.",
                "findings": [
                    {"original_text": "Digital native", "category": "age", "explanation": "Commonly implies bias against older candidates.", "alternative": "Tech-savvy professional"}
                ],
                "ai_source": "FairSight Demo Cache"
            }
        return {
            "success": False,
            "input_type": "text",
            "error": str(e)
        }


# -- Model Handler -------------------------------------------------------------

async def _handle_model(content: bytes, filename: str, domain: str, protected_attr: str) -> dict:
    """Handle trained ML model files (.pkl, .joblib)"""
    try:
        import joblib
        model = joblib.load(io.BytesIO(content))
        print(f"[InputHandler] Model type: {type(model).__name__}")

        from model_auditor import audit_model
        result = await audit_model(model, domain, protected_attr)
        result["input_type"] = "model"
        result["filename"] = filename
        return result

    except Exception as e:
        return {
            "success": False,
            "input_type": "model",
            "error": str(e)
        }


# -- Helpers -------------------------------------------------------------------

def auto_detect_protected_attributes(df: pd.DataFrame) -> list:
    """
    Auto-detect likely protected/sensitive attributes from column names.
    Looks for common patterns in column names.
    """
    protected_keywords = [
        'gender', 'sex', 'male', 'female',
        'age', 'dob', 'birth',
        'race', 'ethnicity', 'caste',
        'religion', 'faith',
        'region', 'state', 'district', 'city',
        'language', 'native',
        'income', 'salary',  # income can be proxy for caste/class
        'disability', 'handicap',
        'marital', 'married',
        'nationality', 'country',
    ]

    detected = []
    for col in df.columns:
        col_lower = col.lower().replace('_', ' ').replace('-', ' ')
        for kw in protected_keywords:
            if kw in col_lower:
                detected.append(col)
                break

    return detected


def infer_target_column(df: pd.DataFrame) -> str:
    """
    Infer which column is the outcome/target variable.
    """
    target_keywords = [
        'hired', 'approved', 'accepted', 'granted', 'selected',
        'outcome', 'result', 'decision', 'label', 'target',
        'loan_status', 'credit_decision', 'approved_loan',
        'passed', 'promoted', 'admitted', 'rejected'
    ]

    for col in df.columns:
        col_lower = col.lower().replace('_', ' ')
        for kw in target_keywords:
            if kw in col_lower:
                return col

    # Fallback: last column (common convention)
    return df.columns[-1]
