/**
 * FairSight AI — Mitigation Lab Logic
 * Handles interactive simulations, tradeoff curves, and adversarial stress-tests.
 */

let tradeoffCurveData = null;

function initMitigationLab() {
    console.log("Initializing Mitigation Lab...");
    
    if (!window.currentState || !window.currentState.analysisResult) {
        showLabError("Please upload a dataset in the Audit Dashboard first.");
        return;
    }

    const res = window.currentState.analysisResult;
    
    // Defensive extraction: Results can be in res.audit or res directly
    const audit = res.audit || res;
    const profile = audit.profile || res.profile || {};
    const metrics = res.metrics || audit.metrics;
    
    if (!metrics) {
        showLabError("Could not find fairness metrics for this dataset. Please ensure the analysis is complete.");
        return;
    }

    const domain = profile.domain || res.domain || "auto";
    const overallScore = res.overall_score || res.overall_fairness_score || (audit.bias_analysis ? audit.bias_analysis.overall_bias_score : 50);
    
    document.getElementById('lab-fairness-score').innerText = overallScore;
    
    // Load Tradeoff Data
    fetchTradeoffData();
    
    // Load initial compliance status
    fetchComplianceReport();
}

async function fetchTradeoffData() {
    const { file, analysisResult } = window.currentState;
    if (!file) return;

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('protected_attr', analysisResult.protected_attribute || '');
        formData.append('target_col', analysisResult.target_column || '');

        const response = await fetch('/api/mitigate/tradeoff', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.success) {
            tradeoffCurveData = data.curve;
            const optimalIndex = data.best_balance_index || 0;
            const optimalLevel = data.curve[optimalIndex];
            
            // Render the Chart
            renderTradeoffChart(data.curve, optimalIndex);
            
            // Populate Reasoning Dialogue
            populateReasoning(data.curve, optimalIndex, data.reason);

            // Set dynamic slider value
            const slider = document.getElementById('intensity-slider');
            if (slider) {
                slider.value = optimalLevel.intensity * 100;
                updateIntensity(slider.value);
            }
        }
    } catch (err) {
        console.error("Tradeoff fetch failed:", err);
    }
}

function renderTradeoffChart(curve, optimalIndex) {
    const x = curve.map(d => d.intensity * 100);
    const fairness = curve.map(d => d.fairness_score);
    const profit = curve.map(d => d.profit_index);
    const optX = x[optimalIndex];

    const trace1 = {
        x: x,
        y: fairness,
        name: 'Fairness Score',
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#10b981', width: 3, shape: 'spline' },
        marker: { size: 8 }
    };

    const trace2 = {
        x: x,
        y: profit,
        name: 'Profit/Accuracy Index',
        yaxis: 'y2',
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#f43f5e', width: 2, dash: 'dot' },
        marker: { symbol: 'diamond' }
    };

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#ffffff', family: 'Inter' },
        margin: { t: 50, b: 40, l: 40, r: 40 },
        showlegend: true,
        legend: { orientation: 'h', y: -0.25 },
        xaxis: { title: 'Mitigation Intensity (%)', gridcolor: 'rgba(255,255,255,0.05)' },
        yaxis: { title: 'Fairness', gridcolor: 'rgba(255,255,255,0.05)', range: [0, 105] },
        yaxis2: {
            title: 'Profit',
            overlaying: 'y',
            side: 'right',
            range: [80, 100]
        },
        shapes: [
            {
                type: 'line',
                x0: optX,
                y0: 0,
                x1: optX,
                y1: 1,
                yref: 'paper',
                line: {
                    color: 'rgba(99, 102, 241, 0.4)',
                    width: 2,
                    dash: 'dash'
                }
            }
        ],
        annotations: [
            {
                x: optX,
                y: 1,
                yref: 'paper',
                text: 'OPTIMAL POINT',
                showarrow: false,
                font: { size: 10, color: '#818cf8', weight: 'bold' },
                bgcolor: 'rgba(15, 23, 42, 0.7)',
                bordercolor: '#818cf8',
                borderwidth: 1,
                borderpad: 4,
                opacity: 0.8
            }
        ]
    };

    Plotly.newPlot('tradeoff-chart', [trace1, trace2], layout, { displayModeBar: false, responsive: true });
}

function populateReasoning(curve, index, backendReason = null) {
    const point = curve[index];
    const initialProfit = curve[0].profit_index;
    const profitLoss = (initialProfit - point.profit_index).toFixed(1);
    
    let reasoning = backendReason || `System identifies <strong>${point.intensity * 100}% Intensity</strong> as optimal. It achieves a high Fairness Score of <strong>${point.fairness_score}</strong> while limiting accuracy degradation to just <strong>-${profitLoss}%</strong>. Further mitigation exhibits Diminishing Marginal Returns.`;
    
    const box = document.getElementById('optimal-reasoning-box');
    const text = document.getElementById('optimal-reasoning-text');
    
    if (box && text) {
        text.innerHTML = reasoning;
        box.style.display = 'block';
    }
}

function updateIntensity(value) {
    document.getElementById('intensity-val').innerText = value + "%";
    
    if (!tradeoffCurveData) return;
    
    // Find closest index
    const index = Math.min(Math.floor(value / 20), 5);
    const point = tradeoffCurveData[index];
    
    const fairEl = document.getElementById('lab-fairness-score');
    const accEl = document.getElementById('lab-accuracy-impact');
    
    fairEl.innerText = point.fairness_score;
    const impact = (point.profit_index - tradeoffCurveData[0].profit_index).toFixed(1);
    accEl.innerText = (impact > 0 ? "+" : "") + impact + "%";
    accEl.style.color = impact < -3 ? "#f43f5e" : "#f59e0b";
}

async function runRedTeamTest() {
    const { analysisResult } = window.currentState;
    const resultsContainer = document.getElementById('red-team-results');
    
    resultsContainer.innerHTML = '<div class="placeholder-text"><i class="fas fa-spinner fa-spin"></i> Gemini is simulating persona attacks...</div>';

    try {
        // Find a 'good' sample from the analysis summary or metadata if possible
        // For MVP, we pass the first row profile mentioned in audit or a generic high-quality row
        const sampleRow = analysisResult.metrics.privileged_sample || { "age": 32, "education": "Master's", "experience": 8, "income": 85000 };
        
        const response = await fetch('/api/redteam', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sample_row: sampleRow,
                protected_attr: analysisResult.protected_attribute,
                dataset_summary: analysisResult
            })
        });

        const data = await response.json();
        
        if (data.error) throw new Error(data.error);

        renderRedTeamCards(data);
    } catch (err) {
        resultsContainer.innerHTML = `<div class="placeholder-text" style="color: #f43f5e;">Red-Team engine failed: ${err.message}</div>`;
    }
}

function renderRedTeamCards(data) {
    const container = document.getElementById('red-team-results');
    container.innerHTML = `
        <div style="margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem;">
            <p style="font-size: 0.8rem; color: var(--text-muted);">${data.original_success_check}</p>
        </div>
    `;

    data.adversarial_twins.forEach(twin => {
        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.padding = '1rem';
        card.style.marginBottom = '0.8rem';
        card.style.borderLeft = `4px solid ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e' : '#10b981'}`;
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <span style="font-weight: 700; font-size: 0.9rem;">${twin.name}</span>
                <span class="badge" style="font-size: 0.7rem; background: ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e20' : '#10b98120'}; color: ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e' : '#10b981'}; padding: 2px 8px; border-radius: 4px;">
                    ${twin.predicted_outcome}
                </span>
            </div>
            <p style="font-size: 0.75rem; margin: 0.5rem 0; color: var(--text-muted); line-height: 1.4;">${twin.risk_reasoning}</p>
            <div style="font-size: 0.7rem; color: var(--accent); opacity: 0.8;">
                <i class="fas fa-microchip"></i> Changes: ${twin.changes.join(', ')}
            </div>
        `;
        container.appendChild(card);
    });
}

async function fetchComplianceReport() {
    const { analysisResult } = window.currentState;
    try {
        const response = await fetch('/api/compliance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                metrics: analysisResult.metrics,
                domain: analysisResult.profile.domain
            })
        });

        const data = await response.json();
        renderComplianceList(data);
    } catch (err) {
        console.error("Compliance fetch failed:", err);
    }
}

function renderComplianceList(data) {
    // Cache for PDF generation
    window.lastComplianceData = data;
    
    const list = document.getElementById('compliance-status-list');
    list.innerHTML = '';
    
    data.regulations.forEach(reg => {
        const item = document.createElement('div');
        item.style.marginBottom = '0.8rem';
        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
                <span title="${reg.detail}">${reg.name}</span>
                <span class="badge" style="background: ${getStatusColor(reg.status)}20; color: ${getStatusColor(reg.status)}; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 0.7rem;">
                    ${reg.status}
                </span>
            </div>
        `;
        list.appendChild(item);
    });
}

function getStatusColor(status) {
    if (status === 'PASS' || status === 'PASSED' || status === 'COMPLIANT') return '#10b981';
    if (status === 'AT RISK' || status === 'REVISION NEEDED') return '#f59e0b';
    return '#f43f5e';
}

async function downloadCertificate() {
    const { analysisResult } = window.currentState;
    if (!analysisResult) {
        alert("No analysis data available to generate a report.");
        return;
    }

    const btn = document.querySelector('.certification-card .btn-outline');
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Legal PDF...';
    btn.disabled = true;

    try {
        // We pack the audit data and metrics for the PDF generator
        const auditData = analysisResult.audit || analysisResult;
        
        const payload = {
            audit: auditData,
            metrics: analysisResult.metrics || auditData.metrics,
            benchmarks: window.lastComplianceData || { domain_label: "Global", regulatory_status: "At Risk" }
        };

        const response = await fetch('/api/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("Server failed to generate PDF");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `FairSight_Compliance_Report_${new Date().getTime()}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        // Success notification
        btn.innerHTML = '<i class="fas fa-check"></i> Certificate Downloaded';
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
        }, 3000);

    } catch (err) {
        console.error("PDF Download failed:", err);
        alert("Failed to generate certificate: " + err.message);
        btn.innerHTML = originalHtml;
        btn.disabled = false;
    }
}

function showLabError(msg) {
    const container = document.getElementById('view-mitigation');
    container.innerHTML = `
        <div class="placeholder-text" style="margin-top: 10rem;">
            <i class="fas fa-exclamation-triangle" style="font-size: 4rem; color: var(--accent); margin-bottom: 2rem; display: block;"></i>
            <h2>Action Required</h2>
            <p>${msg}</p>
            <button class="btn btn-primary" style="margin-top: 2rem;" onclick="switchView('audit')">Return to Audit Dashboard</button>
        </div>
    `;
}

// Global Exports
window.updateIntensity = updateIntensity;
window.runRedTeamTest = runRedTeamTest;
window.downloadCertificate = downloadCertificate;
window.initMitigationLab = initMitigationLab;
