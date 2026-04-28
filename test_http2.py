import json
import requests

with open('backend/precache/loan_analysis.json', 'r') as f:
    data = json.load(f)

res = requests.post("http://localhost:8000/api/report", json=data)
if res.status_code == 500:
    print(res.json())
else:
    print(res.status_code)
