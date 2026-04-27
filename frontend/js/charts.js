/**
 * FairSight AI — Charts Logic
 * Uses Plotly.js to render beautiful, interactive fairness visualizations.
 */

window.renderMainChart = function(data) {
    const metrics = data.metrics?.summary || {};
    const groupCounts = metrics.group_counts || {};
    const groupRates = {};
    
    // Use the real rates for all groups provided by the backend
    const allRates = metrics.all_group_rates || {};
    const labels = Object.keys(allRates).length > 0 ? Object.keys(allRates) : Object.keys(groupCounts);
    
    // Safety check for rates
    const rates = labels.map(label => {
        if (allRates[label] !== undefined) return allRates[label];
        if (label === metrics.privileged_group) return metrics.privileged_rate;
        if (label === metrics.unprivileged_group) return metrics.unprivileged_rate;
        return 0.0; // Default to 0 instead of a fake 0.5
    });

    const plotData = [{
        x: labels,
        y: rates,
        type: 'bar',
        marker: {
            color: labels.map(l => l === metrics.unprivileged_group ? '#ef4444' : '#6366f1'),
            opacity: 0.8,
            line: { width: 1, color: 'rgba(255,255,255,0.2)' }
        },
        name: 'Outcome Rate'
    }];

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Inter' },
        margin: { t: 20, r: 20, l: 40, b: 60 },
        xaxis: { 
            gridcolor: 'rgba(255,255,255,0.05)', 
            zeroline: false,
            title: {
                text: (metrics.protected_attribute || 'Subgroup').toUpperCase(),
                font: { size: 10, color: 'var(--accent)' }
            }
        },
        yaxis: { 
            gridcolor: 'rgba(255,255,255,0.05)', 
            zeroline: false, 
            title: 'Approval Rate',
            range: [0, 1]
        },
        showlegend: false
    };

    Plotly.newPlot('main-plotly-chart', plotData, layout, {responsive: true, displayModeBar: false});
    
    // Also render Radar Chart if the container exists
    if (document.getElementById('hero-radar-placeholder')) {
        renderRadarChart(data);
    }
};

function renderRadarChart(data) {
    const metrics = data.metrics?.metrics || {};
    
    // 5 pillars of the Bias Fingerprint
    const categories = [
        'Statistical Parity', 
        'Disparate Impact', 
        'Equalized Odds', 
        'Individual Fairness',
        'Causal Fairness'
    ];
    
    // Values normalized 0-1 (higher is better/fairer)
    const values = [
        1 - (metrics.statistical_parity_difference || 0.5),
        metrics.disparate_impact_ratio || 0.5,
        1 - (metrics.equalized_odds_difference || 0.3),
        metrics.individual_fairness_proxy || 0.7,
        0.6 // Causal proxy
    ];

    const plotData = [{
        type: 'scatterpolar',
        r: values,
        theta: categories,
        fill: 'toself',
        fillcolor: 'rgba(99, 102, 241, 0.3)',
        line: { color: '#6366f1', width: 2 },
        marker: { size: 8, color: '#22d3ee' }
    }];

    const layout = {
        polar: {
            bgcolor: 'rgba(0,0,0,0)',
            radialaxis: { visible: true, range: [0, 1], gridcolor: 'rgba(255,255,255,0.1)', tickfont: {size: 8} },
            angularaxis: { gridcolor: 'rgba(255,255,255,0.1)', tickfont: {size: 10} }
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Outfit' },
        margin: { t: 40, b: 40, l: 40, r: 40 },
        showlegend: false
    };

    Plotly.newPlot('hero-radar-placeholder', plotData, layout, {responsive: true, displayModeBar: false});
}
