"""
FairSight AI — Compliance Engine
Evaluates bias metrics against global regulatory standards.
"""

def generate_compliance_report(metrics: dict, domain: str) -> dict:
    """
    Evaluates compliance with GDPR (Art 22), India DPDP 2023, and US EEOC.
    """
    
    score = metrics.get("overall_fairness_score", 50)
    disparity = metrics.get("metrics", {}).get("disparate_impact_ratio", 1.0)
    
    # 1. GDPR / EU AI Act (Focus on High-Risk systems)
    gdpr_status = "PASS" if score > 85 else "AT RISK" if score > 70 else "FAIL"
    
    # 2. India DPDP 2023 (Focus on harmful profiling)
    dpdp_status = "COMPLIANT" if disparity > 0.8 else "REVISION NEEDED"
    
    # 3. US EEOC (The 4/5ths Rule)
    eeoc_status = "PASSED" if disparity >= 0.8 else "VIOLATION (4/5ths Rule)"
    
    return {
        "overall_status": "CERTIFIED" if score > 80 else "NON-COMPLIANT",
        "regulations": [
            {
                "name": "EU AI Act / GDPR",
                "status": gdpr_status,
                "detail": "Requires automated systems in high-risk domains to demonstrate non-discrimination."
            },
            {
                "name": "India DPDP Act 2023",
                "status": dpdp_status,
                "detail": "Prohibits unfair profiling that causes harm to data principals."
            },
            {
                "name": "US EEOC Guidelines",
                "status": eeoc_status,
                "detail": "The 'Four-Fifths Rule' states unprivileged groups must have at least 80% of the privileged group's success rate."
            }
        ],
        "compliance_score": score,
        "certification_id": "FS-2026-" + str(abs(hash(str(metrics))))[:8],
        "recommendation": "Maintain regular audits." if score > 80 else "Apply mitigation immediately to avoid legal liabilities."
    }
