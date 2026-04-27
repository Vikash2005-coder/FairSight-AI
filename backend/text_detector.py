"""
FairSight AI — Text Bias Detector
Uses Gemini 2.0 Flash to analyze documents, job postings, 
and policies for linguistic bias and stereotypes.
"""

import sys
import os
import asyncio
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agents.orchestrator import _get_model, _extract_json

async def detect_text_bias(text: str) -> dict:
    """
    Analyzes raw text for bias using Gemini.
    Detects: gendered language, ageism, regional bias, and stereotypes.
    """
    
    # Pre-check: Basic keyword detection (fast)
    quick_flags = _quick_text_scan(text)
    
    # Deep Analysis: Use Gemini
    model = _get_model()
    prompt = f"""
You are the Text Bias Specialist for FairSight AI — an expert in linguistics, 
D&I (Diversity & Inclusion), and implicit bias.

Analyze the following text for hidden bias, discrimination, or non-inclusive language:

---
TEXT TO ANALYZE:
{text}
---

Your task:
1. Identify specific biased PHRASES or SENTENCES.
2. CATEGORIZE each bias (gender, age, region, caste, religion, education, etc.)
3. Explain WHY it is biased.
4. Provide a NEUTRAL ALTERNATIVE for each biased phrase.
5. Give an OVERALL TEXT FAIRNESS SCORE (0-100).
6. Provide a 2-sentence SUMMARY of the bias profile.

Respond ONLY with valid JSON in this exact format:
{{
  "overall_score": 65,
  "summary": "This document contains several age-related and regional biases...",
  "findings": [
    {{
      "original_text": "young and energetic",
      "category": "age",
      "explanation": "Suggests a preference for younger candidates and may discourage older applicants.",
      "alternative": "highly motivated and dynamic",
      "severity": "medium"
    }},
    {{
      "original_text": "He will lead the team",
      "category": "gender",
      "explanation": "Uses gendered pronouns which assume a male candidate.",
      "alternative": "The candidate will lead the team",
      "severity": "low"
    }}
  ],
  "inclusive_score_factors": {{
    "gender_inclusivity": 80,
    "age_inclusivity": 50,
    "regional_neutrality": 90
  }}
}}
"""
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        gemini_analysis = _extract_json(response.text)
    except Exception as e:
        gemini_analysis = {
            "overall_score": 50,
            "summary": f"Could not complete AI analysis: {str(e)}",
            "findings": []
        }

    return {
        "success": True,
        "overall_score": gemini_analysis.get("overall_score", 50),
        "summary": gemini_analysis.get("summary", ""),
        "findings": gemini_analysis.get("findings", []),
        "quick_flags": quick_flags,
        "score_factors": gemini_analysis.get("inclusive_score_factors", {})
    }


def _quick_text_scan(text: str) -> list:
    """Runs a quick regex-based scan for common biased terms (Fast response)"""
    flags = []
    lower_text = text.lower()
    
    patterns = {
        "gender": [r'\bhe\b', r'\bhim\b', r'\bhis\b', r'\bchairman\b', r'\bmankind\b', r'\bmanpower\b'],
        "age": [r'\byoung\b', r'\bfresh graduate\b', r'\brecently graduated\b', r'\benergetic\b', r'\bdigital native\b'],
        "region/caste": [r'\bnative english\b', r'\btier 1 college\b', r'\biit/nit only\b', r'\bboarding school\b'],
    }
    
    import re
    for category, keywords in patterns.items():
        for pattern in keywords:
            if re.search(pattern, lower_text):
                flags.append({"category": category, "matched_pattern": pattern})
                
    return flags
