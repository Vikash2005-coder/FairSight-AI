# FairSight AI — Research-Grade AI Bias Auditor ⚖️🤖

**FairSight AI** is a state-of-the-art AI ethics and bias auditing platform designed for the **Hack2Skill × Google hackathon**. It leverages the reasoning power of **Gemini 2.0 Flash** to detect, explain, and mitigate algorithmic bias in tabular data, text, and ML models.

---

## 🌟 Key Features
- **Multi-Agent Orchestration**: 5 specialized Gemini agents (Profiler, Detector, Analyst, Mitigator, Reporter) work together to provide deep reasoning.
- **Bias Fingerprint™**: Real-time visualization of 8+ industry fairness metrics.
- **Intersectional Analysis**: Detects compounding bias across multiple sensitive attributes (e.g., Gender + Caste).
- **India Bias Atlas**: Interactive mapping of regional outcome disparities across Indian states using Folium.
- **Mitigation Lab**: Automated reweighing and threshold optimization techniques.
- **Gemini Chat Assistant**: A dedicated AI companion to help stakeholders understand audit findings.

---

## 🛠️ Tech Stack
- **AI Core**: Gemini 2.0 Flash (`google-generativeai`)
- **Backend**: FastAPI (Python 3.9+)
- **Analysis**: Scikit-Learn, SHAP, Fairlearn, Pandas
- **Visualization**: Plotly, Folium (India Geo-spatial support)
- **Frontend**: Premium Glassmorphism UI (Vanilla JS/CSS)
- **Reporting**: FPDF2 (Professional PDF Audit Reports)

---

## 🚀 Quick Start
1. **Initialize Environment**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Add API Key**: Create a `.env` file and add your key:
   ```env
   GEMINI_API_KEY=your_key_here
   ```
3. **Run the App**:
   ```bash
   py -3.9 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Access Dashboard**: Open `http://localhost:8000` in your browser.

---

## 📊 Demo Scenarios
- **Hiring Bias**: Analyze gender/age disparity in tech recruitment.
- **Lending Bias**: Identify geographic redlining in Indian loan approvals.
- **Healthcare Bias**: Detect ageism in patient prioritization models.
- **Recidivism (COMPAS)**: Audit racial bias in criminal justice algorithms.

---

## 🗺️ Indian Context
Built specifically with the **India DPDP Act 2023** in mind, FairSight detects bias specific to the Indian subcontinent, including caste proxies, regional language disparities, and state-level outcome variations.

**Developed with ❤️ by FairSight AI Team**
