"""
FairSight AI — Audit Report Generator
Creates a professional PDF report with fairness scores, 
bias findings, and mitigation recommendations.
"""

from fpdf import FPDF
import datetime
import os

class FairSightReport(FPDF):
    def header(self):
        # Logo placeholder or Text logo
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(99, 102, 241) # Indigo
        self.cell(0, 10, 'FairSight AI Audit', border=0, ln=1, align='L')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', border=0, ln=1, align='L')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(169, 169, 169)
        self.cell(0, 10, f'Page {self.page_no()} | CONFIDENTIAL - FairSight AI Bias Audit', 0, 0, 'C')

def generate_pdf(data: dict) -> str:
    """
    Generates a professional PDF audit report.
    Returns the path to the generated file.
    """
    pdf = FairSightReport()
    pdf.add_page()
    
    # ── Executive Summary ──
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 15, '1. Executive Summary', ln=1)
    
    audit_data = data.get("audit", {})
    bench = data.get("benchmarks", {})
    cert_id = bench.get("certification_id", "FS-PENDING")

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 10, f'CERTIFICATION ID: {cert_id}', ln=1)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font('Helvetica', '', 11)
    report_text = audit_data.get("report", "No executive summary text generated.")
    
    # Simple cleanup (Gemini markdown to PDF text)
    clean_report = report_text.replace('**', '').replace('##', '').replace('###', '')
    clean_report = clean_report.replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"').replace("‘", "'")
    try:
        clean_report = clean_report.encode('latin-1', 'replace').decode('latin-1')
    except:
        pass
    
    pdf.multi_cell(0, 7, clean_report)
    pdf.ln(10)

    # ── Regulatory Status ──
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 15, '2. Regulatory Compliance Status', ln=1)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(60, 10, 'Overall Audit Status:', border=0)
    status = bench.get("overall_status", "NON-COMPLIANT")
    if "CERTIFIED" in status or "PASS" in status:
        pdf.set_text_color(16, 185, 129) # green
    else:
        pdf.set_text_color(239, 68, 68) # red
    pdf.cell(0, 10, status, ln=1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Table of regulations
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(80, 10, 'Regulation Framework', border=1, fill=0)
    pdf.cell(40, 10, 'Status', border=1, fill=0)
    pdf.cell(70, 10, 'Compliance Result', border=1, ln=1)

    pdf.set_font('Helvetica', '', 10)
    for reg in bench.get("regulations", []):
        pdf.cell(80, 8, reg['name'], border=1)
        pdf.cell(40, 8, reg['status'], border=1)
        pdf.cell(70, 8, 'Pass' if reg['status'] in ['PASS', 'COMPLIANT', 'PASSED'] else 'Review Needed', border=1, ln=1)

    # ── Fairness Metrics ──
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 15, '3. Detailed Mathematical Findings', ln=1)
    
    metrics = data.get("metrics", {}).get("metrics", {})
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(120, 10, 'Fairness Metric Name', border=1, fill=0)
    pdf.cell(50, 10, 'Value', border=1, ln=1)
    
    pdf.set_font('Helvetica', '', 11)
    for name, val in metrics.items():
        if isinstance(val, (int, float)):
            name_pretty = name.replace('_', ' ').capitalize()
            pdf.cell(120, 8, name_pretty, border=1)
            pdf.cell(50, 8, str(round(val, 4)), border=1, ln=1)

    # Output
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"FairSight_Certification_{timestamp}.pdf"
    output_path = os.path.join("reports", report_name)
    os.makedirs("reports", exist_ok=True)
    pdf.output(output_path)
    
    return output_path
