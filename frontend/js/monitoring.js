/**
 * FairSight AI — Live Ops Monitoring Logic
 * Handles real-time SSE stream, pulse charting, and incident investigation.
 */

(function() {
    let pulseChart = null;
    let eventSource = null;
    const pulseHistory = { x: [], y: [] };
    const MAX_POINTS = 30;

    window.initMonitoring = function() {
        if (eventSource) return; // Already running
        
        console.log("Initializing Real-Time Monitoring Pulse...");
        initPulseChart();
        startStreaming();
        loadIncidents();
    };

    function initPulseChart() {
        const trace = {
            x: pulseHistory.x,
            y: pulseHistory.y,
            type: 'scatter',
            mode: 'lines',
            fill: 'tozeroy',
            line: { color: '#6366f1', width: 3, shape: 'spline' },
            fillcolor: 'rgba(99, 102, 241, 0.1)'
        };

        const layout = {
            margin: { t: 5, b: 40, l: 30, r: 10 }, // Increased bottom margin
            height: 140, // Increased height slightly to fit labels
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            showlegend: false,
            xaxis: { 
                showgrid: false, 
                color: 'rgba(255,255,255,0.4)',
                nticks: 5, // Limit number of labels to prevent overlapping
                tickfont: { size: 10 }
            },
            yaxis: { 
                gridcolor: 'rgba(255,255,255,0.05)', 
                range: [0.6, 1.0],
                tickfont: { size: 10 }
            }
        };

        Plotly.newPlot('live-pulse-chart', [trace], layout, { displayModeBar: false });
    }

    function startStreaming() {
        // Reset engine first
        fetch('/api/monitoring/reset', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ context: window.lastAnalysisResult })
        });

        eventSource = new EventSource('/api/monitoring/stream');

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            updatePulseUI(data);
        };

        eventSource.addEventListener('incident', function(event) {
            const incident = JSON.parse(event.data);
            addIncidentToFeed(incident);
            triggerRedAlert();
        });

        eventSource.onerror = function() {
            console.error("Monitoring stream lost. Reconnecting...");
        };
    }

    function updatePulseUI(data) {
        // Update Score
        const scoreEl = document.getElementById('live-score-value');
        scoreEl.innerText = data.score;
        
        // Update Badge
        const badge = document.getElementById('pulse-status-badge');
        badge.innerText = data.status;
        badge.className = `badge badge-${data.status === 'Healthy' ? 'success' : 'danger'}`;

        // Update Chart
        pulseHistory.x.push(data.time);
        pulseHistory.y.push(data.score);
        
        if (pulseHistory.x.length > MAX_POINTS) {
            pulseHistory.x.shift();
            pulseHistory.y.shift();
        }

        Plotly.update('live-pulse-chart', { x: [pulseHistory.x], y: [pulseHistory.y] });
    }

    function addIncidentToFeed(incident) {
        const feed = document.getElementById('incident-feed');
        
        // Remove placeholder if it's there
        if (feed.querySelector('.placeholder-text')) {
            feed.innerHTML = '';
        }

        const div = document.createElement('div');
        div.className = `incident-item high pulse-card`;
        div.id = `incident-${incident.id}`;
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-weight: 600; color: #ef4444;"><i class="fas fa-biohazard"></i> ${incident.id}</span>
                <span class="text-muted" style="font-size: 0.8rem;">${incident.timestamp.split(' ')[1]}</span>
            </div>
            <div style="font-size: 0.9rem; margin-bottom: 1rem;">${incident.diagnosis}</div>
            <button class="btn btn-primary btn-sm" onclick="investigateIncident('${incident.id}')" id="btn-inspect-${incident.id}">
                <i class="fas fa-search-plus"></i> Guardian Inspect
            </button>
            <div class="guardian-report text-muted" style="display:none; margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1rem; font-size: 0.85rem; font-style: italic;">
                Analyzing...
            </div>
        `;
        feed.prepend(div);
    }

    window.investigateIncident = async function(id) {
        const btn = document.getElementById(`btn-inspect-${id}`);
        const reportDiv = document.querySelector(`#incident-${id} .guardian-report`);
        const item = document.getElementById(`incident-${id}`);
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Investigating...';
        reportDiv.style.display = 'block';

        try {
            const res = await fetch(`/api/monitoring/investigate/${id}`, { method: 'POST' });
            const data = await res.json();
            
            reportDiv.innerText = data.report;
            item.classList.remove('high');
            item.classList.add('investigated');
            btn.innerHTML = '<i class="fas fa-check-circle"></i> Analyzed by Guardian';
        } catch (err) {
            reportDiv.innerText = "Error during Gemini investigation.";
            btn.disabled = false;
            btn.innerHTML = 'Retry Inspection';
        }
    };

    function triggerRedAlert() {
        const container = document.getElementById('monitoring-pulse-container');
        container.classList.add('red-alert-active');
        
        // Remove after 10 seconds
        setTimeout(() => {
            container.classList.remove('red-alert-active');
        }, 10000);
    }

    async function loadIncidents() {
        const res = await fetch('/api/monitoring/incidents');
        const data = await res.json();
        const feed = document.getElementById('incident-feed');
        
        if (data.incidents.length > 0) {
            feed.innerHTML = '';
            data.incidents.forEach(addIncidentToFeed);
        }
    }
})();
