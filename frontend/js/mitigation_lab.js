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
    
    // Load Diagnostic Data (Poison Rows & Sensitivity)
    fetchDiagnosticsData();
    
    // Load initial compliance status
    fetchComplianceReport();
}

async function fetchDiagnosticsData() {
    const { file, analysisResult } = window.currentState;
    if (!file) return;

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('protected_attr', analysisResult.protected_attribute || '');
        formData.append('target_col', analysisResult.target_column || '');

        // 1. Fetch Sensitivity
        fetch('/api/diagnostic/sensitivity', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderSensitivityChart(data.sensitivities);
                } else {
                    document.getElementById('sensitivity-chart').innerHTML = `<div class="placeholder-text" style="color: #f43f5e;"><i class="fas fa-exclamation-triangle"></i> Analysis Failed: ${data.error}</div>`;
                }
            })
            .catch(err => {
                console.error("Sensitivity fetch failed:", err);
                document.getElementById('sensitivity-chart').innerHTML = '<div class="placeholder-text" style="color: #f43f5e;">Network or server error.</div>';
            });

        // 2. Fetch Poison Rows
        fetch('/api/diagnostic/poison_rows', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderPoisonRows(data.poison_rows);
                } else {
                    document.getElementById('poison-rows-body').innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #f43f5e;"><i class="fas fa-exclamation-triangle"></i> Error: ${data.error}</td></tr>`;
                }
            })
            .catch(err => {
                console.error("Poison rows fetch failed:", err);
                document.getElementById('poison-rows-body').innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #f43f5e;">Network or server error.</td></tr>';
            });

    } catch (err) {
        console.error("Diagnostic fetch failed:", err);
    }
}

function renderSensitivityChart(sensitivities) {
    if (!sensitivities || sensitivities.length === 0) {
        document.getElementById('sensitivity-chart').innerHTML = '<div class="placeholder-text">Insufficient numeric features for sensitivity analysis.</div>';
        return;
    }

    // Sort to have highest at top
    const sorted = [...sensitivities].reverse();
    const x = sorted.map(d => d.sensitivity);
    const y = sorted.map(d => d.feature.replace(/_/g, ' ').toUpperCase());

    const trace1 = {
        x: x,
        y: y,
        type: 'bar',
        orientation: 'h',
        marker: {
            color: x.map(val => val > 30 ? '#f43f5e' : (val > 10 ? '#f59e0b' : '#10b981')),
            opacity: 0.8
        }
    };

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#ffffff', family: 'Inter', size: 10 },
        margin: { t: 20, b: 40, l: 100, r: 20 },
        xaxis: { title: 'Bias Sensitivity (%)', gridcolor: 'rgba(255,255,255,0.05)', range: [0, 100] },
        yaxis: { gridcolor: 'rgba(255,255,255,0.05)' },
        annotations: sorted.map((d, i) => ({
            x: d.sensitivity + 2,
            y: i,
            text: d.sensitivity + '%',
            showarrow: false,
            font: { color: '#ffffff', size: 10 },
            xanchor: 'left'
        }))
    };

    // Clear the loading text before rendering the chart
    document.getElementById('sensitivity-chart').innerHTML = '';

    Plotly.newPlot('sensitivity-chart', [trace1], layout, { displayModeBar: false, responsive: true });
}

function renderPoisonRows(rows) {
    const tbody = document.getElementById('poison-rows-body');
    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">No contradictory rows found. Data aligns well with merit.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        
        let featString = '';
        for (const [k, v] of Object.entries(row.features)) {
            featString += `<span class="badge" style="background: rgba(255,255,255,0.05); font-size: 0.7rem; margin-right: 4px;">${k}: ${v}</span>`;
        }

        const isVictim = row.reason.includes('Victim');
        const reasonColor = isVictim ? '#f43f5e' : '#10b981';

        tr.innerHTML = `
            <td style="padding: 0.8rem; font-weight: 600;">${row.group}</td>
            <td style="padding: 0.8rem;">
                <span style="color: ${row.outcome === '0' || row.outcome === '0.0' ? '#f43f5e' : '#10b981'}">
                    ${row.outcome === '0' || row.outcome === '0.0' ? 'Negative (0)' : 'Positive (1)'}
                </span>
            </td>
            <td style="padding: 0.8rem; font-family: monospace;">${row.merit}</td>
            <td style="padding: 0.8rem; font-size: 0.75rem; color: ${reasonColor};">${row.reason}</td>
            <td style="padding: 0.8rem;">${featString}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function runRedTeamTest() {
    const { analysisResult } = window.currentState;
    const resultsContainer = document.getElementById('red-team-results');
    
    resultsContainer.innerHTML = '<div class="placeholder-text"><i class="fas fa-spinner fa-spin"></i> Gemini is simulating persona attacks...</div>';

    try {
        // Find a 'good' sample dynamically from the poison rows if available
        let sampleRow = { "age": 32, "education": "Master's", "experience": 8, "income": 85000 };
        if (window.currentState.poisonRows && window.currentState.poisonRows.length > 0) {
            sampleRow = window.currentState.poisonRows[0].features;
        } else if (analysisResult.metrics && analysisResult.metrics.privileged_sample) {
            sampleRow = analysisResult.metrics.privileged_sample;
        }
        
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

    if (!data.adversarial_twins || !Array.isArray(data.adversarial_twins)) {
        container.innerHTML += `<div class="placeholder-text" style="color: #f59e0b;">Gemini returned an unexpected response format. Please try running the Stress Test again.</div>`;
        return;
    }

    data.adversarial_twins.forEach(twin => {
        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.padding = '1rem';
        card.style.marginBottom = '0.8rem';
        card.style.borderLeft = `4px solid ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e' : '#10b981'}`;
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <span style="font-weight: 700; font-size: 0.9rem;">${twin.name || 'Adversarial Profile'}</span>
                <span class="badge" style="font-size: 0.7rem; background: ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e20' : '#10b98120'}; color: ${twin.predicted_outcome === 'REJECTED' ? '#f43f5e' : '#10b981'}; padding: 2px 8px; border-radius: 4px;">
                    ${twin.predicted_outcome || 'UNKNOWN'}
                </span>
            </div>
            <p style="font-size: 0.75rem; margin: 0.5rem 0; color: var(--text-muted); line-height: 1.4;">${twin.risk_reasoning || 'No reasoning provided.'}</p>
            <div style="font-size: 0.7rem; color: var(--accent); opacity: 0.8;">
                <i class="fas fa-microchip"></i> Changes: ${twin.changes ? twin.changes.join(', ') : 'None'}
            </div>
        `;
        container.appendChild(card);
    });
}

async function fetchComplianceReport() {
    const { analysisResult } = window.currentState;
    
    // Safely extract domain (handling both CSV and PKL structures)
    const audit = analysisResult.audit || analysisResult;
    const profile = audit.profile || analysisResult.profile || {};
    const domain = profile.domain || "auto";

    try {
        const response = await fetch('/api/compliance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                metrics: analysisResult.metrics || audit.metrics,
                domain: domain
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
window.runRedTeamTest = runRedTeamTest;
window.downloadCertificate = downloadCertificate;
window.initMitigationLab = initMitigationLab;
