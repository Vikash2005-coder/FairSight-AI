"""
FairSight AI -- Gemini Multi-Agent Orchestrator
5 specialized agents powered by Gemini 2.0 Flash working together
to deliver comprehensive bias analysis, causal reasoning, and recommendations.
"""

import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# -- Multi-Key Configuration ---------------------------------------------------

GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
# Clean up None values
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

# fallback if new keys not found yet
if not GEMINI_KEYS:
    GEMINI_KEYS = [os.getenv("GEMINI_API_KEY")]

ACTIVE_KEY_INDEX = 0

def get_current_key_source():
    if ACTIVE_KEY_INDEX < len(GEMINI_KEYS):
        return f"Gemini AI (Key #{ACTIVE_KEY_INDEX + 1})"
    return "Demo Cache"

def _rotate_key():
    global ACTIVE_KEY_INDEX, _CACHED_MODEL_NAME
    ACTIVE_KEY_INDEX = (ACTIVE_KEY_INDEX + 1) % len(GEMINI_KEYS)
    genai.configure(api_key=GEMINI_KEYS[ACTIVE_KEY_INDEX])
    _CACHED_MODEL_NAME = None # Reset model cache as new key might have different access
    print(f"[Orchestrator] Rotating to {get_current_key_source()}...")

# Initial config
if GEMINI_KEYS:
    genai.configure(api_key=GEMINI_KEYS[ACTIVE_KEY_INDEX])

GENERATION_CONFIG = genai.GenerationConfig(
    temperature=0.3, 
    top_p=0.85,
    max_output_tokens=4096
)

_CACHED_MODEL_NAME = None

def _get_model():
    global _CACHED_MODEL_NAME
    
    if not _CACHED_MODEL_NAME:
        try:
            # Try to discover the best available model
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # Prioritize 1.5 flash
            for m in available:
                if "gemini-3.1-flash-lite-preview" in m:
                    _CACHED_MODEL_NAME = m
                    break
            if not _CACHED_MODEL_NAME and available:
                _CACHED_MODEL_NAME = available[0]
        except Exception:
            # Fallback to standard name if list fails
            _CACHED_MODEL_NAME = "gemini-3.1-flash-lite-preview"

    return genai.GenerativeModel(
        model_name=_CACHED_MODEL_NAME or "gemini-3.1-flash-lite-preview",
        generation_config=GENERATION_CONFIG
    )

async def _safe_generate(model, prompt, retry_count=0):
    """
    Wrapper for generate_content_async with automatic key rotation on 429 errors.
    """
    try:
        # Use truly asynchronous call with a strict timeout to prevent hangs
        return await model.generate_content_async(
            prompt, 
            request_options={"timeout": 60}
        )
    except Exception as e:
        # Handle Quota / Rate Limits AND Auth / Model availability errors by rotating keys
        error_msg = str(e).lower()
        should_rotate = False
        
        if "429" in error_msg or "resourceexhausted" in error_msg:
            should_rotate = True
        elif "400" in error_msg or "404" in error_msg or "invalid" in error_msg or "permission" in error_msg:
            # Also rotate on invalid keys or when the specific model isn't enabled for a key
            should_rotate = True

        if should_rotate and retry_count < len(GEMINI_KEYS):
            _rotate_key()
            new_model = _get_model()
            return await _safe_generate(new_model, prompt, retry_count + 1)
        
        # Log other errors and propagate
        print(f"[Orchestrator] Generation error: {str(e)}")
        raise e


def _extract_json(text: str) -> dict:
    """Safely extract JSON from Gemini response text"""
    if not text:
        return {"error": "Empty response from Gemini"}
        
    try:
        # Try direct parse first
        return json.loads(text)
    except Exception:
        pass
        
    try:
        # Find JSON block in response using a more robust regex
        # This handles markdown blocks ```json ... ``` which Gemini often adds
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        
        # Try cleaning markdown bits if found
        cleaned = text.strip().strip('`').replace('json\n', '', 1)
        return json.loads(cleaned)
    except Exception:
        pass
        
    # Fallback: return raw text in a dict
    return {"raw_response": text, "error": "Failed to parse JSON"}


# -- Agent 1: Data Profiling Agent --------------------------------------------

async def data_profiling_agent(input_data: dict) -> dict:
    """
    Understands what the data is about.
    Identifies: domain, protected attributes, target column, data quality issues.
    """
    model = _get_model()
    prompt = f"""
You are the Data Profiling Agent for FairSight AI -- an expert in identifying fairness-relevant 
patterns in datasets and AI systems.

Analyze the following dataset information and provide your assessment:

INPUT DATA INFO:
{json.dumps(input_data, indent=2)}

Your task:
1. Identify the most likely DOMAIN (hiring, lending/loan, healthcare, criminal_justice, education, other)
2. List all PROTECTED ATTRIBUTES (gender, age, caste, religion, region, language, race, income_class, etc.)
3. Identify the TARGET/OUTCOME column (what the model predicts or the dataset labels)
4. Note any DATA QUALITY RED FLAGS (missing values in protected cols, highly imbalanced classes, etc.)
5. Write a SHORT SUMMARY (2 sentences) of what this data represents

Respond ONLY with valid JSON in this exact format:
{{
  "domain": "hiring",
  "protected_attributes": ["gender", "age"],
  "target_column": "hired",
  "red_flags": ["Class imbalance: 75% not hired", "Missing values in age column"],
  "summary": "This is a tech hiring dataset from an Indian IT company...",
  "confidence": "high"
}}
"""
    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {
            "domain": "unknown",
            "protected_attributes": [],
            "target_column": "unknown",
            "red_flags": [],
            "summary": f"Analysis unavailable: {str(e)}",
            "confidence": "low"
        }


# -- Agent 2: Bias Detection Agent --------------------------------------------

async def bias_detection_agent(metrics: dict, profile: dict) -> dict:
    """
    Interprets fairness metrics and explains what they mean in plain English.
    Identifies which groups are affected and how severely.
    """
    model = _get_model()
    prompt = f"""
You are the Bias Detection Agent for FairSight AI -- an expert in AI fairness metrics 
and their real-world implications.

DATASET PROFILE:
{json.dumps(profile, indent=2)}

COMPUTED FAIRNESS METRICS:
{json.dumps(metrics, indent=2)}

Your task -- for each metric that indicates bias (threshold > 0.1 for differences, < 0.8 for ratios):
1. Explain what it means in PLAIN ENGLISH (no jargon)
2. Rate SEVERITY: low / medium / high / critical
3. Name the AFFECTED GROUPS specifically
4. Give a REAL-WORLD IMPACT statement (e.g., "Women are 34% less likely to be approved")

Also provide:
- OVERALL SEVERITY (worst of all detected biases)
- OVERALL BIAS SCORE: 0-100 (0=completely biased, 100=perfectly fair)

Respond ONLY with valid JSON:
{{
  "overall_severity": "high",
  "overall_bias_score": 42,
  "biased_metrics": [
    {{
      "metric_name": "Demographic Parity Difference",
      "value": -0.34,
      "severity": "high",
      "plain_explanation": "Women are 34% less likely to be hired than men with equal qualifications",
      "affected_groups": ["Female applicants"],
      "real_world_impact": "For every 3 men hired, only 2 equally qualified women are hired"
    }}
  ],
  "clean_metrics": ["Individual Fairness Score"],
  "most_critical_issue": "Gender bias in hiring decisions",
  "executive_summary": "This model shows significant gender bias..."
}}
"""
    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {
            "overall_severity": "unknown",
            "overall_bias_score": 50,
            "biased_metrics": [],
            "executive_summary": f"Analysis unavailable: {str(e)}"
        }


# -- Agent 3: Causal Analysis Agent -------------------------------------------

async def causal_analysis_agent(metrics: dict, profile: dict) -> dict:
    """
    Goes beyond detecting bias to explain WHY it exists.
    Identifies proxy features, historical causes, and the bias propagation pathway.
    """
    model = _get_model()
    prompt = f"""
You are the Causal Analysis Agent for FairSight AI -- a specialist in causal AI and 
the societal roots of algorithmic discrimination.

DATASET PROFILE:
{json.dumps(profile, indent=2)}

FAIRNESS METRICS:
{json.dumps(metrics, indent=2)}

Your task -- explain WHY this bias exists, not just that it exists:
1. ROOT CAUSES: What in the data or training process caused this bias?
2. PROXY FEATURES: Which features are acting as indirect proxies for protected attributes?
   (e.g., "zip_code" proxies for caste/religion in India; "salary_history" proxies for gender)
3. HISTORICAL CONTEXT: What societal or historical factors created this pattern?
4. BIAS PATHWAY: Step-by-step how bias flows from data -> model -> decision

Focus on the INDIAN CONTEXT where relevant (caste, region, language disparities common in India).

Respond ONLY with valid JSON:
{{
  "root_causes": [
    "Training data reflects historical hiring practices from 2010-2020 where women were systematically underpaid",
    "Performance reviews were conducted predominantly by male managers"
  ],
  "proxy_features": [
    {{"feature": "salary_history", "proxies_for": "gender", "explanation": "Women historically earn less, so this feature encodes gender discrimination"}},
    {{"feature": "zip_code", "proxies_for": "caste/socioeconomic status", "explanation": "Residential segregation in India makes location a caste proxy"}}
  ],
  "historical_context": "India's tech industry historically recruited from elite urban institutions...",
  "bias_pathway": [
    "Step 1: Historical data collected during period of gender inequality",
    "Step 2: Model learns that 'salary_history' correlates with performance",
    "Step 3: Salary history encodes past discrimination",
    "Step 4: Model inherits and amplifies gender bias in predictions"
  ],
  "india_specific_factors": ["Caste-based residential patterns", "Regional language bias in interviews"]
}}
"""
    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {
            "root_causes": [f"Analysis unavailable: {str(e)}"],
            "proxy_features": [],
            "historical_context": "",
            "bias_pathway": []
        }


# -- Agent 4: Mitigation Agent -------------------------------------------------

async def mitigation_agent(metrics: dict, profile: dict) -> dict:
    """
    Recommends the best mitigation strategies and explains the fairness-accuracy tradeoff.
    """
    model = _get_model()
    prompt = f"""
You are the Mitigation Agent for FairSight AI -- an expert in bias mitigation techniques
and their practical implementation.

DATASET PROFILE:
{json.dumps(profile, indent=2)}

FAIRNESS METRICS:
{json.dumps(metrics, indent=2)}

Your task -- recommend the best mitigation strategies:
1. TOP 3 TECHNIQUES with reasoning for why each fits this specific case
2. EXPECTED IMPROVEMENT in fairness score (realistic estimate)
3. ACCURACY TRADEOFF -- what accuracy loss to expect
4. PRIORITY ACTION -- the single most impactful thing to do first
5. IMPLEMENTATION STEPS -- concrete, actionable steps

Available techniques: 
- reweighing (adjust sample weights in training data)
- disparate_impact_remover (transform features to remove proxy bias)  
- threshold_optimizer (adjust decision thresholds per group)
- equalized_odds_postprocessor (balance error rates post-prediction)
- data_augmentation (add more representative samples)

Respond ONLY with valid JSON:
{{
  "recommendations": [
    {{
      "technique": "reweighing",
      "why_this_case": "Best for this dataset because class imbalance is driven by historical bias",
      "expected_fairness_improvement": "20-30 points on bias score",
      "accuracy_loss": "1-3%",
      "implementation": "Apply sample weights based on protected attribute distribution"
    }}
  ],
  "priority_action": "Apply reweighing immediately -- highest impact, lowest risk",
  "expected_overall_improvement": "Bias score likely to improve from 42 to 68-75",
  "cannot_fix_with_data_alone": "Historical proxy features like salary_history need policy-level changes"
}}
"""
    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {
            "recommendations": [],
            "priority_action": f"Analysis unavailable: {str(e)}",
            "expected_overall_improvement": "Unknown"
        }


# -- Agent 5: Report Agent -----------------------------------------------------

async def report_agent(profile: dict, bias_analysis: dict, causal: dict, mitigation: dict) -> str:
    """
    Writes a professional, human-readable audit report.
    """
    model = _get_model()
    prompt = f"""
You are the Report Agent for FairSight AI -- a professional technical writer specializing 
in AI ethics and fairness audits.

Write a PROFESSIONAL BIAS AUDIT REPORT based on the following analysis.
The report should be understandable to BOTH technical and non-technical readers.

DATASET PROFILE:
{json.dumps(profile, indent=2)}

BIAS ANALYSIS:
{json.dumps(bias_analysis, indent=2)}

CAUSAL ANALYSIS:
{json.dumps(causal, indent=2)}

MITIGATION RECOMMENDATIONS:
{json.dumps(mitigation, indent=2)}

Write the report in this EXACT structure:

## FAIRSIGHT AI -- BIAS AUDIT REPORT

### Executive Summary
[2-3 sentences. What was audited, what was found, urgency level]

### Overall Fairness Score: [X/100] -- [HIGH RISK / MODERATE RISK / FAIR]

### Key Findings
[3-5 bullet points with most important discoveries]

### Root Cause Analysis
[2-3 paragraphs explaining WHY bias exists, with Indian context where relevant]

### Affected Groups
[Table or list of who is affected and how severely]

### Recommended Actions
[Numbered list of concrete actions, most impactful first]

### Compliance Status
- India DPDP Act 2023: [COMPLIANT / NON-COMPLIANT / AT RISK]
- EU AI Act (High-Risk AI): [COMPLIANT / NON-COMPLIANT / N/A]
- Suggested timeline for remediation: [X weeks]

Keep the tone professional but empathetic. Emphasize real human impact.
"""
    try:
        response = await _safe_generate(model, prompt)
        return response.text
    except Exception as e:
        return f"Report generation failed: {str(e)}"


# -- Master Orchestrator -------------------------------------------------------

async def master_audit_agent(input_data: dict, metrics: dict) -> dict:
    """
    Compression of all 5 Agent tasks into a single high-efficiency prompt.
    Produces the Profile, Explanation, Causality, Mitigation, and Report.
    """
    model = _get_model()

    # ── Trim payload to prevent Gemini timeout on large datasets ──
    safe_metrics = {
        "overall_fairness_score": metrics.get("overall_fairness_score"),
        "status": metrics.get("status"),
        "summary": {
            "privileged_group": metrics.get("summary", {}).get("privileged_group"),
            "unprivileged_group": metrics.get("summary", {}).get("unprivileged_group"),
            "privileged_rate": metrics.get("summary", {}).get("privileged_rate"),
            "unprivileged_rate": metrics.get("summary", {}).get("unprivileged_rate"),
            "protected_attribute": metrics.get("summary", {}).get("protected_attribute"),
            "group_counts": metrics.get("summary", {}).get("group_counts", {}),
            # Cap all_group_rates to top 10 to avoid huge payloads
            "all_group_rates": dict(list(metrics.get("summary", {}).get("all_group_rates", {}).items())[:10])
        },
        "metrics": metrics.get("metrics", {})
    }

    safe_input = {
        "filename": input_data.get("filename"),
        "rows": input_data.get("rows"),
        "domain": input_data.get("domain"),
        "target_column": input_data.get("target_column"),
        "protected_attribute_analyzed": input_data.get("protected_attribute_analyzed"),
        # Send only first 15 column names, not all 22+
        "columns": input_data.get("columns", [])[:15]
    }

    prompt = f"""
You are FairSight AI, an expert AI fairness auditor. 
Perform a COMPLETE, deep bias audit in a single pass based on the provided data and mathematical metrics.

DATASET INFO:
{json.dumps(safe_input, indent=2)}

FAIRNESS METRICS:
{json.dumps(safe_metrics, indent=2)}

Return ONLY a single valid JSON object containing exactly these nested structures. Do not wrap in markdown or backticks:
{{
  "profile": {{
    "domain": "hiring/lending/etc.",
    "summary": "Short 2 sentence summary of what this dataset is."
  }},
  "bias_analysis": {{
    "overall_severity": "high/medium/low/fair",
    "overall_bias_score": {metrics.get('overall_fairness_score', 50)},
    "executive_summary": "Plain English summary of the bias found (or lack thereof).",
    "biased_metrics": [
      {{
         "metric_name": "Demographic Parity etc.",
         "severity": "high/medium/low",
         "plain_explanation": "Simple explanation.",
         "affected_groups": ["Group A"],
         "real_world_impact": "Impact statement"
      }}
    ]
  }},
  "causal": {{
    "root_cause": "The main societal/historical reason this bias exists in data.",
    "historical_context": "Deep societal context (focus on India if relevant).",
    "proxy_features": [
      "FeatureName -> Why it proxies for the protected attribute"
    ]
  }},
  "mitigation": {{
    "short_term_actions": ["Action 1", "Action 2"],
    "long_term_strategy": "Systemic fixes over time"
  }},
  "report": "## FAIRSIGHT AI -- BIAS AUDIT REPORT\\n\\n### Executive Summary\\n..."
}}
"""
    response = await _safe_generate(model, prompt)
    result = _extract_json(response.text)
    
    # If Gemini returned plain text instead of JSON, we must trigger the fallback
    if "raw_response" in result or "profile" not in result:
        raise ValueError("Gemini returned malformed response or hitting quota limit.")
        
    return result


async def run_full_audit(input_data: dict, metrics: dict) -> dict:
    """
    Runs the complete audit via a single high-efficiency Master Agent.
    """
    print("[Orchestrator] Starting high-efficiency Single-Shot audit...")

    result = await master_audit_agent(input_data, metrics)

    # Fallback missing structures
    profile = result.get("profile", {"domain": "unknown", "summary": "Unavailable"})
    bias_analysis = result.get("bias_analysis", {"overall_bias_score": 50, "overall_severity": "unknown", "executive_summary": "Failed to analyze."})
    causal = result.get("causal", {"root_cause": "N/A", "historical_context": "N/A", "proxy_features": []})
    mitigation_plan = result.get("mitigation", {"short_term_actions": [], "long_term_strategy": "N/A"})
    report = result.get("report", "Report unavailable.")

    print("[Orchestrator] Audit complete! Consumed 1 API Request.")

    return {
        "success": True,
        "profile": profile,
        "bias_analysis": bias_analysis,
        "causal": causal,
        "mitigation": mitigation_plan,
        "report": report,
        "overall_bias_score": bias_analysis.get("overall_bias_score", 50),
        "overall_severity": bias_analysis.get("overall_severity", "unknown"),
        "ai_source": get_current_key_source()
    }


# -- Conversational Interface --------------------------------------------------

async def chat_with_fairsight(message: str, context: str = "") -> str:
    """
    FairSight conversational interface.
    Users can ask questions about bias in plain English.
    """
    model = _get_model()

    system_context = """You are FairSight AI Hub -- a crisp, executive-level AI fairness assistant.
Your goal is to provide brief, high-impact answers to questions about bias analysis.
Never use long introductions or fluff. Just answer the specific question asked.

Communication style:
- Extremely concise and direct.
- 1-3 sentences maximum.
- Use professional but punched-up language.
- Connect findings to human impact only when directly asked.
"""

    prompt = f"""
{system_context}

CONTEXT DATA:
{context if context else "No dataset uploaded yet."}

USER QUESTION:
{message}

Direct answer (1-3 sentences):
"""

    try:
        response = await _safe_generate(model, prompt)
        return response.text
    except Exception as e:
        return f"I'm having trouble connecting right now. Please check your Gemini API key. Error: {str(e)}"


# -- Agent 6: Adversarial Red-Team Agent ---------------------------------------

async def adversarial_redteam_agent(sample_row: dict, protected_attr: str, dataset_summary: dict) -> dict:
    """
    Attempts to 'break' model fairness by generating adversarial variations 
    of a successful profile.
    """
    model = _get_model()
    prompt = f"""
You are the Adversarial Red-Team Agent for FairSight AI. Your goal is to expose hidden bias.

WE HAVE A SUCCESSFUL PROFILE:
{json.dumps(sample_row, indent=2)}

PROTECTED ATTRIBUTE TO ATTACK: {protected_attr}
DATASET DOMAIN: {dataset_summary.get('profile', {}).get('domain', 'unknown')}

YOUR TASK:
1. Generate 3 'Adversarial Twins'. 
2. For each twin, change ONLY the protected attribute values (and closely related proxies) 
   to the most 'UNPRIVILEGED' state found in this domain.
3. Keep all high-value qualifications (education, income, etc.) the same as the original.
4. Predict if the decision would 'FLIP' to REJECTED based on the bias patterns in this domain.

Respond ONLY with valid JSON:
{{
  "original_success_check": "Explain why the original person was likely approved",
  "adversarial_twins": [
    {{
      "name": "Twin A",
      "changes": ["Changed Gender from Male to Female", "Adjusted salary expectation"],
      "predicted_outcome": "REJECTED",
      "risk_reasoning": "In this dataset, females with high income are often flagged as outliers..."
    }}
  ],
  "overall_vulnerability_score": "low/medium/high",
  "vulnerability_summary": "Summary of how easily the model's fairness can be bypassed."
}}
"""
    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {"error": f"Adversarial scan failed: {str(e)}"}
# -- Guardian Agent (Monitoring Awareness) ------------------------------------

async def guardian_audit(incident: dict) -> str:
    """
    Specialized agent for real-time monitoring alerts.
    Provides a crisp, causal explanation for a drop in fairness.
    """
    model = _get_model()

    prompt = f"""You are the FairSight Guardian -- a real-time AI compliance monitor.
An incident has been detected in a live production model:
- Incident ID: {incident['id']}
- Fairness Score Drop: {incident['score']}
- Drift Diagnosis: {incident['diagnosis']}

As the Guardian, providing a brief (2-3 sentences max) expert explanation of why this drift is critical and how the organization should respond immediately. 
Be direct, professional, and actionable.

EXPLANATION:
"""

    try:
        response = await _safe_generate(model, prompt)
        return response.text
    except Exception as e:
        return f"Guardian analysis unavailable. Error: {str(e)}"

# -- Impact Story Agent (Synthetic Victim + Cost Calculator) -------------------

async def generate_impact_story(analysis_context: str) -> dict:
    """
    Generates a synthetic victim profile and financial cost analysis
    based on the bias detected in the dataset.
    """
    model = _get_model()

    prompt = f"""You are FairSight's Impact Storyteller, a specialist in data-evidence-based discrimination analysis.

Below is the ACTUAL bias analysis of a real dataset. You must use the EXACT data provided — do not fabricate generic stories.

DATASET ANALYSIS:
{analysis_context}

TASK 1 — SYNTHETIC VICTIM PROFILE (use the actual data above):
- The "protected_attribute" field tells you WHICH attribute is being discriminated against (e.g., gender, age, race, caste)
- "proxy_features" tells you the REAL COLUMNS in the dataset that are causing the bias (e.g., salary_history, pincode, career_gap) — USE THESE EXACT COLUMN NAMES
- "unprivileged_group" is who is being rejected (e.g., Female, Age>40, SC/ST)
- "unprivileged_approval_rate" vs "privileged_approval_rate" gives you the REAL rejection gap
- The "key_findings" from Gemini's own CAUSAL ANALYSIS must directly inform the victim's story

Create a fictional but realistic Indian person who is a PERFECT VICTIM of this specific bias pattern. Their rejection MUST be explained using the actual proxy features found (NOT just "because they are female" — explain WHICH specific data points in the dataset caused the rejection).

TASK 2 — FINANCIAL COST (use actual numbers from the data):
- Use "affected_count" as the number of unfairly rejected people
- Use "disparate_impact_ratio" to calculate severity
- Reference India DPDP Act 2023 and any relevant sector laws (banking, employment, healthcare)
- Use realistic Indian figures in INR (Crore/Lakh)

IMPORTANT RULES:
- The "if_different" field must name SPECIFIC features from the dataset (the proxy_features), not just gender
- Example: "If her salary_history was above ₹8L and pincode was 400001, approval probability would jump from 34% to 79%"
- The "story" must mention the specific proxy features by name
- Do NOT use generic phrases like "because she is female" — explain the MECHANISM

Respond ONLY in this exact JSON format:
{{
  "victim": {{
    "name": "Indian name matching the unprivileged_group",
    "age": 0,
    "city": "Indian city relevant to the dataset",
    "education": "Specific realistic qualification",
    "experience": "Specific realistic experience matching the dataset domain",
    "model_decision": "Rejected",
    "if_different": "If [specific proxy features from data] were [specific values], approval probability would jump from [real unprivileged rate]% to [real privileged rate]%",
    "story": "2-sentence story naming the EXACT proxy features (e.g., salary_history, pincode) that caused the unfair rejection"
  }},
  "costs": {{
    "lost_revenue": "₹X Crore/year",
    "lost_revenue_detail": "Based on [affected_count] unfairly rejected applicants at average Indian [domain] salary/value of ₹X",
    "legal_risk": "Up to ₹X Crore",
    "legal_risk_detail": "India DPDP Act 2023 Section X — [specific violation description]",
    "reputation_damage": "X% trust erosion",
    "reputation_detail": "Comparable to [real-world Indian or global bias scandal]",
    "total_exposure": "₹X Crore annually"
  }}
}}
"""

    try:
        response = await _safe_generate(model, prompt)
        return _extract_json(response.text)
    except Exception as e:
        return {"error": f"Impact story generation failed: {str(e)}"}
