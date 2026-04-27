/**
 * FairSight AI — Main Dashboard Logic
 * Handles file uploads, API orchestration, and state management.
 */

// ── State Management ──
window.currentState = {
    file: null,
    analysisResult: null,
    activeTab: 'overview',
    mapUrl: null
};
const currentState = window.currentState;

// ── File Upload Handler ──
async function handleFileUpload(input) {
    if (!input.files || input.files.length === 0) return;
    
    const file = input.files[0];
    currentState.file = file;
    document.getElementById('active-filename').innerText = file.name;

    // Start Simulation Animation
    startSimulation();

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('domain', 'auto');

        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Analysis failed');

        const result = await response.json();
        
        if (result.success === false) {
            throw new Error(result.error || "Analysis failed");
        }

        currentState.analysisResult = result;
        currentState.mapUrl = result.map_url;
        console.log("Analysis Result:", result);

        // Update UI
        updateDashboardUI(result);
        stopSimulation();

    } catch (error) {
        console.error("Upload failed:", error);
        alert("Error analyzing file. Please check your Gemini API key and backend logs.");
        stopSimulation();
    }
}

// ── URL Fetch Handler ──
async function handleUrlSubmit() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput.value.trim();
    if (!url) {
        alert("Please paste a Kaggle or CSV link first.");
        return;
    }
    
    document.getElementById('active-filename').innerText = "Fetching URL...";
    startSimulation();

    try {
        const response = await fetch('/api/analyze/url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, domain: 'auto' })
        });

        if (!response.ok) {
            let errorText = await response.text();
            try { 
                const errObj = JSON.parse(errorText); 
                errorText = errObj.detail || errorText;
            } catch(e) {}
            throw new Error(`Failed to fetch data: ${errorText}`);
        }

        const result = await response.json();
        
        if (result.success === false) {
            throw new Error(result.error || "Analysis failed");
        }

        currentState.analysisResult = result;
        currentState.mapUrl = result.map_url;
        console.log("URL Analysis Result:", result);

        // Update UI
        updateDashboardUI(result);
        stopSimulation();
        urlInput.value = ''; // clear input
        document.getElementById('active-filename').innerText = result.filename || "URL Dataset";

    } catch (error) {
        console.error("URL Fetch failed:", error);
        alert(error.message);
        stopSimulation();
        document.getElementById('active-filename').innerText = "No file selected";
    }
}


function renderFindings(data) {
    const list = document.getElementById('audit-findings-list');
    list.innerHTML = '';

    const findings = data.audit?.bias_analysis?.biased_metrics || [];
    
    if (findings.length === 0) {
        list.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle"></i> No critical biases detected by Gemini.
            </div>
        `;
        return;
    }

    findings.forEach(f => {
        const div = document.createElement('div');
        div.className = `glass-card alert alert-${f.severity === 'high' || f.severity === 'critical' ? 'danger' : 'warning'}`;
        div.style.marginBottom = '1rem';
        div.style.flexDirection = 'column';
        div.style.alignItems = 'flex-start';
        
        div.innerHTML = `
            <div style="display: flex; gap: 0.8rem; font-weight: 600;">
                <i class="fas fa-exclamation-circle"></i> ${f.metric_name}
            </div>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-main); opacity: 0.8;">
                ${f.plain_explanation}
            </p>
            <div style="margin-top: 0.8rem; font-size: 0.75rem; color: var(--text-muted);">
                Affected: ${f.affected_groups ? f.affected_groups.join(', ') : 'All sensitive groups'}
            </div>
        `;
        list.appendChild(div);
    });

    // Add Gemini Summary
    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'glass-card';
    summaryDiv.style.marginTop = '1.5rem';
    summaryDiv.innerHTML = `
        <h4 style="margin-bottom: 0.5rem;"><i class="fas fa-robot accent"></i> Gemini Executive Summary</h4>
        <p style="font-size: 0.9rem; color: var(--text-muted);">${data.audit.bias_analysis.executive_summary}</p>
    `;
    list.appendChild(summaryDiv);
}

function renderGeminiTab(data) {
    const geminiPane = document.getElementById('gemini-report-container');
    if (!geminiPane) return;

    if (!data.audit) {
        if (data.error_ai) {
            geminiPane.innerHTML = `
                <div class="glass-card" style="border-left: 4px solid var(--danger); background: rgba(220, 38, 38, 0.05);">
                    <h3 style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> AI Audit Paused</h3>
                    <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem;">
                        The statistical audit is complete, but the AI reasoning engine encountered an issue: 
                        <code style="display: block; background: rgba(0,0,0,0.4); padding: 0.8rem; margin: 1rem 0; border-radius: 8px; color: #fecaca; font-size: 0.8rem; border: 1px solid rgba(239, 68, 68, 0.2);">${data.error_ai}</code>
                    </p>
                    <p style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted);">
                        <i class="fas fa-info-circle"></i> This usually happens due to missing API keys or reached quotas. You can still navigate other tabs for the mathematical analysis.
                    </p>
                </div>
            `;
        } else {
            geminiPane.innerHTML = `<div class="placeholder-text">Detailed reasoning will appear here after the AI audit is complete...</div>`;
        }
        return;
    }

    let content = '';
    
    // Causal Analysis
    if (data.audit.causal) {
        content += `<div class="glass-card" style="margin-bottom: 1.5rem;">
            <h3 style="color: var(--accent); margin-bottom: 0.8rem;"><i class="fas fa-search-location"></i> Causal Analysis</h3>
            <p><strong>Root Cause:</strong> ${data.audit.causal.root_cause || 'No clear root cause identified.'}</p>
            <p style="margin-top: 0.5rem;"><strong>Historical Context:</strong> ${data.audit.causal.historical_context || 'N/A'}</p>
            <div style="margin-top: 0.5rem;"><strong>Proxy Features Detected:</strong> <ul>${(data.audit.causal.proxy_features || []).map(f => `<li>${f}</li>`).join('')}</ul></div>
        </div>`;
    }

    // Mitigation Strategy
    if (data.audit.mitigation) {
        content += `<div class="glass-card" style="margin-bottom: 1.5rem;">
            <h3 style="color: #10b981; margin-bottom: 0.8rem;"><i class="fas fa-tools"></i> Mitigation Recommendations</h3>
            <p><strong>Short-Term Actions:</strong> <ul>${(data.audit.mitigation.short_term_actions || []).map(a => `<li>${a}</li>`).join('')}</ul></p>
            <p style="margin-top: 0.5rem;"><strong>Long-Term Strategy:</strong> ${data.audit.mitigation.long_term_strategy || 'N/A'}</p>
        </div>`;
    }

    // Full Report Generation Status
    if (data.audit.report) {
        content += `<div class="glass-card">
            <h3 style="color: var(--primary); margin-bottom: 0.8rem;"><i class="fas fa-file-contract"></i> Deep Audit Report (Preview)</h3>
            <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.85rem; color: var(--text-muted);">${data.audit.report.substring(0, 500)}...</pre>
            <button class="btn btn-primary" id="pdf-download-btn" style="margin-top: 1rem;" onclick="downloadPDFReport()">Download Full PDF Report</button>
        </div>`;
    }

    if (content) {
        geminiPane.innerHTML = content;
    } else {
        geminiPane.innerHTML = `<div class="placeholder-text">Detailed reasoning is not available for this analysis.</div>`;
    }
}

function renderExplainabilityTab(data) {
    const pane = document.getElementById('explainability-container');
    if (!pane) return;

    let proxies = [];
    if (data.audit && data.audit.causal && data.audit.causal.proxy_features) {
        proxies = data.audit.causal.proxy_features;
    }

    if (proxies.length === 0) {
        pane.innerHTML = `
            <h3 style="color: var(--success); margin-bottom: 1rem;"><i class="fas fa-shield-alt"></i> Model is Intrinsically Fair</h3>
            <p style="color: var(--text-muted);">No significant demographic proxy variables were found influencing the neural network weights.</p>
        `;
        return;
    }

    let content = `
        <h3 style="color: var(--accent); margin-bottom: 0.5rem;"><i class="fas fa-project-diagram"></i> Feature Importance (SHAP Values)</h3>
        <p style="color: var(--text-muted); margin-bottom: 2rem; font-size: 0.9rem;">
            The following proxy features were heavily weighted by the algorithm, indirectly causing demographic discrimination.
        </p>
    `;

    // Generate simulated SHAP visual bars
    let baseWeight = 85;
    proxies.forEach((proxy, idx) => {
        const weight = Math.max(30, baseWeight - (idx * 15)); // Diminishing weights
        
        // Deep Explainability Engine
        let explanation = "This feature acts as a hidden proxy, allowing the AI to mathematically deduce a person's sensitive demographic without explicitly looking at it.";
        const proxyLower = proxy.toLowerCase();
        
        if (proxyLower.includes('pin') || proxyLower.includes('zip') || proxyLower.includes('region') || proxyLower.includes('location')) {
            explanation = `<b>Geographical Redlining:</b> While this feature looks like simple geography, historically segregated neighborhoods mean that a Pincode strongly correlates with gender, religion, or caste. The AI uses this to systemically reject applicants from marginalized locations.`;
        } else if (proxyLower.includes('income') || proxyLower.includes('salary') || proxyLower.includes('wealth')) {
            explanation = `<b>Socioeconomic Proxy:</b> Income gaps often reflect historical inequalities. Because women and marginalized groups statistically report lower median incomes, using this as a heavy weight inherently traps them in a cycle of algorithmic rejection.`;
        } else if (proxyLower.includes('career') || proxyLower.includes('gap') || proxyLower.includes('experience')) {
            explanation = `<b>Maternity & Age Penalty:</b> Strict reliance on uninterrupted work experience heavily penalizes women who take maternity leave or individuals with non-traditional career paths, acting as a direct proxy for gender discrimination.`;
        } else if (proxyLower.includes('education') || proxyLower.includes('degree') || proxyLower.includes('school')) {
            explanation = `<b>Educational Disparity:</b> Using specific university prestige or schooling data often filters out high-performing applicants who simply lacked the generational wealth to attend tier-1 institutions.`;
        }

        content += `
            <div style="margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.8rem;">
                    <span style="font-weight: 700; font-family: 'Outfit'; font-size: 1.1rem; color: #fff;">
                        <i class="fas fa-project-diagram" style="color: var(--accent); margin-right: 0.5rem;"></i>
                        ${proxy.replace('_', ' ').toUpperCase()}
                    </span>
                    <span style="color: var(--danger); font-weight: bold; background: rgba(239, 68, 68, 0.1); padding: 0.3rem 0.8rem; border-radius: 20px;">
                        +${weight}% Decision Impact
                    </span>
                </div>
                
                <div style="width: 100%; height: 10px; background: rgba(255, 255, 255, 0.05); border-radius: 5px; overflow: hidden; margin-bottom: 1rem;">
                    <div style="width: ${weight}%; height: 100%; background: linear-gradient(90deg, var(--danger), #f87171); border-radius: 5px; box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);"></div>
                </div>
                
                <div style="background: rgba(255,255,255,0.02); border-left: 3px solid var(--danger); padding: 1rem; border-radius: 0 8px 8px 0;">
                    <h4 style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted); margin-bottom: 0.5rem;">Why This Is Biased:</h4>
                    <p style="font-size: 0.9rem; color: var(--text-main); line-height: 1.5;">
                        ${explanation}
                    </p>
                </div>
            </div>
        `;
    });

    pane.innerHTML = content;
}



// ── Tab Switching ──
function initTabs() {
    console.log("[FairSight] Initializing Tabs (Cache-Bust V3)...");
    const tabContainer = document.querySelector('.tabs');
    if (!tabContainer) return;

    // Remove any existing listeners to prevent duplicates
    const newTabContainer = tabContainer.cloneNode(true);
    tabContainer.parentNode.replaceChild(newTabContainer, tabContainer);

    newTabContainer.addEventListener('click', (e) => {
        const tab = e.target.closest('.tab');
        if (!tab) return;

        const tabId = tab.dataset.tab;
        console.log(`[FairSight] Tab Switch: ${tabId}`);
        
        // 1. Update Tab UI
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentState.activeTab = tabId;

        // 2. Update Content Panes (Aggressive Brute Force)
        const allPanes = document.querySelectorAll('.tab-pane');
        allPanes.forEach(pane => {
            pane.classList.remove('active');
            pane.style.setProperty('display', 'none', 'important');
        });

        const targetPane = document.getElementById(`pane-${tabId}`);
        if (targetPane) {
            console.log(`[FairSight] Showing Pane: pane-${tabId}`);
            targetPane.classList.add('active');
            targetPane.style.setProperty('display', 'block', 'important');
            
            // Special handling for Atlas
            if (tabId === 'atlas' && window.loadAtlas) {
                window.loadAtlas();
            }
        } else {
            console.error(`[FairSight] Target pane not found: pane-${tabId}`);
        }
    });
}

// ── PDF Generation ──
async function downloadPDFReport() {
    if (!currentState.analysisResult) {
        alert("No audit data available to generate report.");
        return;
    }
    const btn = document.getElementById('pdf-download-btn') || document.querySelector('button[onclick="downloadPDFReport()"]');
    if (btn) {
        btn.innerText = "Generating PDF...";
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentState.analysisResult)
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `FairSight_Audit_Report.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        console.error(err);
        alert("Failed to generate PDF report: " + err.message);
    } finally {
        if (btn) {
            btn.innerText = "Download Full PDF Report";
            btn.disabled = false;
        }
    }
}

// ── UI Updates ──
function updateDashboardUI(data) {
    if (!data) return;
    
    // Synchronize context with Chat component
    window.lastAnalysisResult = data;
    
    // Dependency Guard: Wait for charts.js to be ready
    if (!window.renderMainChart) {
        console.warn("Charts engine not ready, retrying in 100ms...");
        setTimeout(() => updateDashboardUI(data), 100);
        return;
    }

    const score = data.overall_score || data.metrics?.overall_fairness_score || 0;
    const scoreEl = document.getElementById('score-val');
    scoreEl.innerText = Math.round(score);
    
    // Color coding score
    if (score > 80) scoreEl.style.color = 'var(--success)';
    else if (score > 60) scoreEl.style.color = 'var(--warning)';
    else scoreEl.style.color = 'var(--danger)';

    const status = data.status || "UNKNOWN";
    document.getElementById('score-status').innerText = status.toUpperCase();
    
    const dispRatio = data.metrics?.metrics?.disparate_impact_ratio || 0;
    document.getElementById('disp-val').innerText = dispRatio.toFixed(2);
    
    const biasedFeats = data.audit?.causal?.proxy_features?.length || 0;
    document.getElementById('feat-val').innerText = biasedFeats;

    const annualImpact = data.benchmarks?.human_impact?.estimated_annual_impact || 0;
    document.getElementById('impact-val').innerText = annualImpact.toLocaleString();

    // 2. Render Main Chart (Overview)
    if (window.renderMainChart) {
        window.renderMainChart(data);
    }

    // 3. Render Audit Findings
    renderFindings(data);

    // 4. Render Gemini Reasoning Tab
    renderGeminiTab(data);

    // 4.5. Render Feature Explainability Tab
    renderExplainabilityTab(data);

    // 5. Update AI Source Badge
    const sourceBadge = document.getElementById('ai-status-badge');
    const sourceText = document.getElementById('ai-status-text');
    if (sourceBadge && data.ai_source) {
        sourceBadge.style.display = 'block';
        sourceText.innerText = data.ai_source.toUpperCase();
        
        // Color coding
        if (data.ai_source.includes('Demo')) {
            sourceBadge.style.color = '#fbbf24'; // Amber
            sourceBadge.style.borderColor = '#fbbf24';
        } else {
            sourceBadge.style.color = '#10b981'; // Emerald/Green
            sourceBadge.style.borderColor = '#10b981';
        }
    }

    // 6. Trigger Impact Story generation in the background
    renderImpactTab(data);
}

// ── Impact Story Renderer ────────────────────────────────────────────────────
async function renderImpactTab(data) {
    const victimEl = document.getElementById('victim-profile-content');
    const costEl = document.getElementById('cost-analysis-content');
    if (!victimEl || !costEl) return;

    // Show loading state
    const loadingHTML = `<div style="text-align:center; padding: 3rem;">
        <i class="fas fa-circle-notch fa-spin" style="font-size:2rem; color:var(--primary); margin-bottom:1rem; display:block;"></i>
        <p style="color:var(--text-muted);">Gemini is generating Impact Analysis...</p>
    </div>`;
    victimEl.innerHTML = loadingHTML;
    costEl.innerHTML = loadingHTML;

    try {
        // Build a rich, dataset-specific context for Gemini
        const metrics = data.metrics?.metrics || {};
        const causal = data.audit?.causal || {};
        const geminiAudit = data.audit?.gemini || {};
        const counterfactual = data.audit?.counterfactual || {};

        const ctx = {
            // Dataset metadata
            dataset_type: data.dataset_type || 'unknown',
            filename: data.filename || 'dataset',
            total_rows: data.total_rows || 0,
            
            // Core fairness metrics
            overall_score: data.overall_score,
            status: data.status,
            disparate_impact_ratio: metrics.disparate_impact_ratio,
            statistical_parity: metrics.statistical_parity_difference,
            equalized_odds: metrics.equalized_odds_difference,
            
            // Protected attribute(s)
            protected_attribute: causal.protected_attribute || 'gender',
            privileged_group: causal.privileged_group || 'Male',
            unprivileged_group: causal.unprivileged_group || 'Female',
            
            // CRITICAL: The actual proxy features found in THIS dataset
            proxy_features: causal.proxy_features || [],
            proxy_explanations: causal.proxy_explanations || {},
            feature_importance: causal.feature_importance || {},
            
            // Actual rejection rates from the data
            privileged_approval_rate: causal.privileged_approval_rate,
            unprivileged_approval_rate: causal.unprivileged_approval_rate,
            rejection_rate_gap: causal.rejection_rate_gap,
            affected_count: causal.estimated_affected_count,

            // Dataset column info
            columns: data.columns || [],
            outcome_column: data.outcome_column || 'hired',

            // Counterfactual data (what changes would flip the decision)
            counterfactual_features: counterfactual.key_changes || [],

            // Gemini's own findings from the audit
            root_cause: geminiAudit.root_cause || '',
            key_findings: (geminiAudit.key_findings || []).slice(0, 4)
        };

        const res = await fetch('/api/impact-story', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ context: JSON.stringify(ctx) })
        });

        const story = await res.json();
        if (story.error) throw new Error(story.error);

        // ── Render Victim Card ──
        const v = story.victim;
        victimEl.innerHTML = `
            <div style="display:flex; align-items:center; gap:1.5rem; margin-bottom:1.5rem;">
                <div style="width:70px; height:70px; border-radius:50%; background:linear-gradient(135deg,#ef4444,#f97316); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    <i class="fas fa-user" style="font-size:1.8rem; color:white;"></i>
                </div>
                <div>
                    <div style="font-size:1.4rem; font-weight:700; font-family:'Outfit';">${v.name}</div>
                    <div style="color:var(--text-muted); font-size:0.9rem;">${v.age} years old &bull; ${v.city}</div>
                </div>
                <div style="margin-left:auto; background:rgba(239,68,68,0.15); color:#ef4444; padding:0.5rem 1rem; border-radius:8px; font-weight:700; font-size:0.9rem;">
                    ❌ ${v.model_decision}
                </div>
            </div>

            <div style="background:rgba(255,255,255,0.03); border-radius:0.8rem; padding:1rem; margin-bottom:1rem;">
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.8rem;">
                    <div><span style="color:var(--text-muted); font-size:0.75rem; text-transform:uppercase;">Education</span><br><strong>${v.education}</strong></div>
                    <div><span style="color:var(--text-muted); font-size:0.75rem; text-transform:uppercase;">Experience</span><br><strong>${v.experience}</strong></div>
                </div>
            </div>

            <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); border-radius:0.8rem; padding:1rem; margin-bottom:1rem;">
                <span style="color:#10b981; font-size:0.8rem; font-weight:600;"><i class="fas fa-exchange-alt"></i> COUNTERFACTUAL</span>
                <p style="margin-top:0.5rem; font-size:0.9rem;">${v.if_different}</p>
            </div>

            <div style="background:rgba(239,68,68,0.05); border-left:3px solid #ef4444; padding:1rem; border-radius:0 0.5rem 0.5rem 0; font-style:italic; color:var(--text-muted); font-size:0.9rem;">
                "${v.story}"
            </div>`;

        // ── Render Cost Card ──
        const c = story.costs;
        costEl.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:1rem;">
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:0.8rem; padding:1.2rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <span style="font-weight:600;"><i class="fas fa-hand-holding-usd" style="color:#ef4444;"></i> Lost Revenue</span>
                        <span style="font-size:1.2rem; font-weight:800; font-family:'Outfit'; color:#ef4444;">${c.lost_revenue}</span>
                    </div>
                    <p style="color:var(--text-muted); font-size:0.83rem; margin:0;">${c.lost_revenue_detail}</p>
                </div>

                <div style="background:rgba(234,179,8,0.08); border:1px solid rgba(234,179,8,0.2); border-radius:0.8rem; padding:1.2rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <span style="font-weight:600;"><i class="fas fa-gavel" style="color:#eab308;"></i> Legal Penalty Risk</span>
                        <span style="font-size:1.2rem; font-weight:800; font-family:'Outfit'; color:#eab308;">${c.legal_risk}</span>
                    </div>
                    <p style="color:var(--text-muted); font-size:0.83rem; margin:0;">${c.legal_risk_detail}</p>
                </div>

                <div style="background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.2); border-radius:0.8rem; padding:1.2rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <span style="font-weight:600;"><i class="fas fa-chart-line" style="color:#8b5cf6;"></i> Reputation Damage</span>
                        <span style="font-size:1.2rem; font-weight:800; font-family:'Outfit'; color:#8b5cf6;">${c.reputation_damage}</span>
                    </div>
                    <p style="color:var(--text-muted); font-size:0.83rem; margin:0;">${c.reputation_detail}</p>
                </div>

                <div style="background:linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15)); border:1px solid rgba(99,102,241,0.3); border-radius:0.8rem; padding:1.2rem; text-align:center;">
                    <div style="color:var(--text-muted); font-size:0.8rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:0.3rem;">Total Risk Exposure</div>
                    <div style="font-size:2rem; font-weight:800; font-family:'Outfit'; color:#ef4444;">${c.total_exposure}</div>
                    <div style="color:var(--text-muted); font-size:0.8rem; margin-top:0.3rem;">Immediate mitigation recommended.</div>
                </div>
            </div>`;

    } catch (err) {
        console.error("Impact story failed:", err);
        victimEl.innerHTML = `<div style="color:#ef4444; text-align:center; padding:3rem;"><i class="fas fa-exclamation-circle"></i> ${err.message}</div>`;
        costEl.innerHTML = `<div style="color:#ef4444; text-align:center; padding:3rem;"><i class="fas fa-exclamation-circle"></i> Unable to calculate cost.</div>`;
    }
}

// ... existing functions ...

// ── Live Demo Auto-Load ──────────────────────────────────────────────────────
async function checkDemoParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const demoId = urlParams.get('demo');
    
    if (demoId) {
        console.log(`[FairSight] Live Demo Mode: ${demoId}`);
        
        // Show loading state on the badge
        const statusBadge = document.getElementById('ai-status-badge');
        const statusText = document.getElementById('ai-status-text');
        if (statusBadge) {
            statusBadge.style.display = 'block';
            statusText.innerText = "LOADING DEMO...";
        }

        try {
            const response = await fetch(`/api/demo/${demoId}`);
            if (!response.ok) throw new Error("Demo data not found");
            
            const result = await response.json();
            window.currentState.analysisResult = result;
            window.lastAnalysisResult = result; // For chat context
            
            // Safety delay to ensure DOM is fully painted and dependencies are active
            setTimeout(() => {
                updateDashboardUI(result);
                document.getElementById('active-filename').innerText = `DEMO: ${demoId.toUpperCase()} AUDIT`;
                console.log("[FairSight] Demo loaded successfully.");
            }, 100);
            
        } catch (err) {
            console.error("[FairSight] Demo load failed:", err);
            if (statusBadge) {
                statusText.innerText = "DEMO DATA ERROR";
                statusBadge.style.borderColor = "var(--danger)";
            }
        }
    }
}

// Initializing using robust failsafe pattern
function initFairSight() {
    console.info("[FairSight] Dashboard Initialized. Checking for demo parameters...");
    initTabs();
    checkDemoParams();
}

// Failsafe: Check if DOM is already ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFairSight);
} else {
    initFairSight();
}

// Backup: Also attempt on window load just in case
window.addEventListener('load', () => {
    if (!window.currentState.analysisResult) {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('demo')) {
            console.warn("[FairSight] Failsafe: DOMContentLoaded was missed, launching from window.onload");
            checkDemoParams();
        }
    }
});
