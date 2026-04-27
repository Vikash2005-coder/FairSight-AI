/**
 * FairSight AI — Intersectional Bias UI Component
 * Renders a Treemap or Heatmap showing compounding bias 
 * between multiple protected attributes.
 */

window.renderIntersectional = function(data) {
    const interData = data.intersectional || {};
    if (!interData.combinations) return;

    // We filter for combinations with high disparity
    const criticalCombs = interData.combinations.filter(c => c.disparity_index < 0.7);
    
    // For simplicity, we'll render these as a specialized list in a new pane
    const container = document.getElementById('pane-explanation'); // Using explanation tab for this
    container.innerHTML = `
        <h3><i class="fas fa-layer-group accent"></i> Intersectional Bias Analysis</h3>
        <p style="color: var(--text-muted); margin-bottom: 2rem;">
            Analyzing compounding effects of multiple attributes (e.g., Gender + Religion).
        </p>
        <div id="intersectional-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;">
        </div>
    `;

    const grid = document.getElementById('intersectional-grid');

    interData.combinations.slice(0, 12).forEach(comb => {
        const severity = comb.disparity_index < 0.6 ? 'critical' : comb.disparity_index < 0.8 ? 'high' : 'medium';
        const groupLabel = Object.entries(comb.group).map(([k, v]) => `${k}:${v}`).join(' + ');

        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.padding = '1.5rem';
        card.innerHTML = `
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Combination</div>
            <div style="font-weight: 700; margin: 0.5rem 0; color: var(--text-main);">${groupLabel}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                <span class="badge ${severity}">${(comb.disparity_index * 100).toFixed(0)}% Parity</span>
                <span style="font-size: 0.8rem; color: var(--text-muted);">Impact: ${comb.impact_score.toFixed(2)}</span>
            </div>
            <div class="progress-container" style="height: 4px; margin-top: 1rem; background: rgba(255,255,255,0.05);">
                <div style="width: ${comb.disparity_index * 100}%; height: 100%; background: var(--primary);"></div>
            </div>
        `;
        grid.appendChild(card);
    });
};
