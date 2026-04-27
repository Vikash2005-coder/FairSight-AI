"""
FairSight AI - FastAPI Backend
Main application entry point with all API routes
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Import Monitoring Engine
from backend.monitoring import engine

load_dotenv()

# -- Add project root to path ---------------------------------------------------

app = FastAPI(
    title="FairSight AI",
    description="Multi-Agent AI Bias Detection & Auditing System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# ── Request Models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: str = ""

class CounterfactualRequest(BaseModel):
    dataset_summary: dict
    protected_attribute: str
    sample_row: dict

class BenchmarkRequest(BaseModel):
    domain: str
    fairness_score: float
    dataset_size: int = 1000

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the main landing page"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "FairSight AI Backend Running ✅", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_api_key_configured": api_key_set,
        "version": "1.0.0"
    }


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    domain: str = Form("auto"),
    protected_attr: str = Form("")
):
    """
    Main analysis endpoint.
    Accepts: CSV/Excel (tabular), TXT/PDF (text), PKL/JOBLIB (ML model)
    Returns: Full bias analysis with metrics, Gemini reasoning, and recommendations
    """
    try:
        import sys, numpy as np
        sys.path.append(os.path.dirname(__file__))
        from input_handler import handle_input
        result = await handle_input(file, domain, protected_attr)
        
        # ── Numpy-safe JSON serialization ──────────────────────────────────
        # Recursively convert numpy types to Python native types before
        # passing to JSONResponse (which uses stdlib json that can't handle numpy)
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            elif isinstance(obj, (np.integer,)):
                return int(obj)
            elif isinstance(obj, (np.floating,)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, float) and (obj != obj):  # NaN check
                return None
            else:
                return obj

        safe_result = make_serializable(result)
        return JSONResponse(content=safe_result)
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full traceback to server terminal
        raise HTTPException(status_code=500, detail=str(e))


class URLRequest(BaseModel):
    url: str
    domain: str = "auto"

@app.post("/api/analyze/url")
async def analyze_url(req: URLRequest):
    """Analyze a dataset directly from a Kaggle or standard raw URL."""
    try:
        import sys, os
        sys.path.append(os.path.dirname(__file__))
        from input_handler import handle_url_input
        result = await handle_url_input(req.url, req.domain)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to process URL or verify credentials"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Conversational Gemini interface.
    Ask FairSight questions about bias in plain English.
    """
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
        from agents.orchestrator import chat_with_fairsight
        response = await chat_with_fairsight(request.message, request.context)
        return {"reply": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/counterfactual")
async def counterfactual(request: CounterfactualRequest):
    """
    Counterfactual fairness analysis (What-If engine).
    Shows what would happen if a protected attribute were changed.
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from counterfactual import run_counterfactual
        result = run_counterfactual(
            request.dataset_summary,
            request.protected_attribute,
            request.sample_row
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/benchmark")
async def benchmark(request: BenchmarkRequest):
    """
    Compare model fairness score against industry benchmarks.
    Returns percentile ranking, regulatory status, and impact estimate.
    """
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
        from utils.benchmarks_db import get_benchmark_comparison
        result = get_benchmark_comparison(
            request.domain,
            request.fairness_score,
            request.dataset_size
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/intersectional")
async def intersectional(
    file: UploadFile = File(...),
    protected_attrs: str = Form("")  # comma-separated
):
    """
    Intersectional bias analysis — detects bias from multiple combined attributes.
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from intersectional import run_intersectional_analysis
        content = await file.read()
        attrs = [a.strip() for a in protected_attrs.split(",") if a.strip()]
        result = run_intersectional_analysis(content, attrs)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mitigate")
async def mitigate(
    file: UploadFile = File(...),
    technique: str = Form("reweighing"),
    protected_attr: str = Form(""),
    target_col: str = Form("")
):
    """
    Apply bias mitigation to a dataset.
    Techniques: reweighing, disparate_impact_remover, threshold_optimizer
    Returns: original metrics, mitigated metrics, improvement stats
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from mitigator import apply_mitigation
        content = await file.read()
        result = apply_mitigation(content, technique, protected_attr, target_col)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mitigate/tradeoff")
async def mitigate_tradeoff(
    file: UploadFile = File(...),
    protected_attr: str = Form(""),
    target_col: str = Form("")
):
    """
    Generate data for the Fairness-vs-Profit tradeoff curve.
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from mitigator import get_tradeoff_data
        content = await file.read()
        result = get_tradeoff_data(content, protected_attr, target_col)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/redteam")
async def redteam_test(data: dict):
    """
    Adversarial Red-Team Stress Test. 
    Uses Gemini to generate unfair twins and detect decision flips.
    """
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
        from agents.orchestrator import adversarial_redteam_agent
        result = await adversarial_redteam_agent(
            data["sample_row"], 
            data["protected_attr"], 
            data["dataset_summary"]
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compliance")
async def compliance_check(data: dict):
    """
    Evaluate bias metrics against global regulatory standards.
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from compliance_engine import generate_compliance_report
        result = generate_compliance_report(data["metrics"], data.get("domain", "auto"))
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get-atlas")
async def get_atlas():
    """
    Returns the path to the India Bias Atlas map.
    """
    atlas_path = os.path.join(frontend_path, "atlas_map.html")
    if os.path.exists(atlas_path):
        return {"map_url": "/static/atlas_map.html"}
    return {"map_url": None, "message": "Map not yet generated"}


@app.post("/api/report")
async def generate_report(data: dict):
    """
    Generate a professional PDF audit report.
    """
    try:
        import sys
        sys.path.append(os.path.dirname(__file__))
        from report_generator import generate_pdf
        os.makedirs("reports", exist_ok=True)
        pdf_path = generate_pdf(data)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="fairsight_audit_report.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/demo/{sample_id}")
async def get_demo_analysis(sample_id: str):
    """
    Returns a pre-calculated analysis result for the demo.
    sample_id can be 'loan', 'hiring', etc.
    """
    precache_dir = os.path.join(os.path.dirname(__file__), "precache")
    file_map = {
        "loan": "loan_analysis.json",
        "hiring": "hiring_analysis.json",
        "education": "education_analysis.json",
        "ecommerce": "ecommerce_analysis.json"
    }
    
    filename = file_map.get(sample_id.lower())
    if not filename:
        raise HTTPException(status_code=404, detail="Demo project not found")
        
    path = os.path.join(precache_dir, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["ai_source"] = "FairSight Demo"  # Tag it for the UI
            return data
            
    raise HTTPException(status_code=404, detail="Demo data file missing")


@app.get("/api/demo-datasets")
async def list_demo_datasets():
    """List available demo datasets for judges"""
    sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_data")
    datasets = []
    if os.path.exists(sample_dir):
        for f in os.listdir(sample_dir):
            datasets.append({
                "filename": f,
                "description": _get_dataset_description(f)
            })
    return {"datasets": datasets}


def _get_dataset_description(filename: str) -> str:
    descriptions = {
        "hiring_bias.csv": "Tech hiring dataset with gender & age bias (500 rows)",
        "loan_bias.csv": "Bank loan approvals with income proxy & gender bias (600 rows)",
        "healthcare_bias.csv": "Healthcare outcomes with age & gender disparity (400 rows)",
        "compas_sample.csv": "COMPAS criminal recidivism — racial bias (300 rows)",
        "regional_loan_bias.csv": "Geographical bias against female applicant pincodes",
        "national_loan_bias.csv": "Expanded 10-state demographic disparity tracking.",
        "india_banking_bias.csv": "High-fidelity geographical bias (15+ states) for the Atlas.",
        "biased_job_description.txt": "Real-world biased job posting with multiple bias types",
    }
    return descriptions.get(filename, "Sample dataset")


# ── Impact Story API ────────────────────────────────────────────────────────

@app.post("/api/impact-story")
async def impact_story(request: dict):
    """Generate a synthetic victim profile and financial cost of bias"""
    from agents.orchestrator import generate_impact_story
    
    context = request.get("context", "")
    if not context:
        raise HTTPException(status_code=400, detail="Analysis context required")
    
    result = await generate_impact_story(context)
    return result

# ── Monitoring APIs ─────────────────────────────────────────────────────────

@app.post("/api/monitoring/reset")
async def reset_monitoring(request: dict):
    """Reset the monitoring engine with new context"""
    engine.reset(context=request.get("context"))
    return {"status": "Monitoring active"}

@app.get("/api/monitoring/stream")
async def monitoring_stream():
    """SSE endpoint for real-time monitoring pulse"""
    async def event_generator():
        while engine.is_active:
            data = engine.generate_pulse()
            if data:
                yield f"data: {json.dumps(data)}\n\n"
                
                # Check if we should trigger an incident
                if data.get("drift_detected"):
                    incident = await engine.trigger_incident()
                    if incident:
                        yield f"event: incident\ndata: {json.dumps(incident)}\n\n"
            
            await asyncio.sleep(2) # 2s pulse rate

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/monitoring/incidents")
async def get_incidents():
    """Get history of monitoring incidents"""
    return {"incidents": engine.incidents}

@app.post("/api/monitoring/investigate/{incident_id}")
async def investigate_incident(incident_id: str):
    """Use Gemini Guardian to investigate a specific incident"""
    from agents.orchestrator import guardian_audit
    
    # Find incident
    incident = next((i for i in engine.incidents if i["id"] == incident_id), None)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    analysis = await guardian_audit(incident)
    incident["investigation_pending"] = False
    incident["guardian_report"] = analysis
    
    return {"id": incident_id, "report": analysis}

# ── Run Server ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
