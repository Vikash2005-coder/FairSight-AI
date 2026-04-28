import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.report_generator import generate_pdf

data = {
  "success": True,
  "audit": {
    "report": "## FAIRSIGHT AI -- BIAS AUDIT REPORT\n\n### Executive Summary\nThe audit identifies gender bias… — “hello”",
  },
  "benchmarks": {
    "regulatory_status": "High Risk",
    "domain_label": "General AI"
  },
  "metrics": {
    "summary": {},
    "metrics": { "disparate_impact_ratio": 0.655 }
  }
}

try:
    print(generate_pdf(data))
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
