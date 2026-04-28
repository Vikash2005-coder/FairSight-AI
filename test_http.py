import requests

data = {
  "success": True,
  "audit": {
    "report": "## FAIRSIGHT AI -- BIAS AUDIT REPORT\n\n### Executive Summary\nThe audit identifies gender bias...",
  },
  "benchmarks": {
    "domain": "auto",
    "domain_label": "General AI System"
  },
  "metrics": {
    "summary": {},
    "metrics": { "disparate_impact_ratio": 0.655 }
  }
}

try:
    res = requests.post("http://localhost:8000/api/report", json=data)
    print(res.status_code)
    print(res.text)
except Exception as e:
    print(e)
