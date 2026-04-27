/**
 * FairSight AI — Simulation Engine
 * Creates a "WOW" animation showing the multi-agent 
 * Gemini auditing process in real-time.
 */

const SIM_STEPS = [
    { title: "Uploading Data...", detail: "Establishing secure connection to FairSight Cloud", progress: 10 },
    { title: "Agent 1: Data Profiling", detail: "Identifying domain context and sensitive attributes", progress: 25 },
    { title: "Agent 2: Computing Metrics", detail: "Calculating Demographic Parity & Disparate Impact", progress: 45 },
    { title: "Agent 3: Causal Analysis", detail: "Gemini 2.0 Flash identifying proxy bias pathways", progress: 65 },
    { title: "Agent 4: Mitigation Strategy", detail: "Devising optimal fairness-accuracy tradeoff plan", progress: 85 },
    { title: "Agent 5: Audit Complete", detail: "Generating final report and risk assessment", progress: 100 }
];

function startSimulation() {
    const overlay = document.getElementById('sim-overlay');
    const title = document.getElementById('sim-title');
    const stepText = document.getElementById('sim-step');
    const progressBar = document.getElementById('sim-progress');

    overlay.style.display = 'flex';
    
    let currentStep = 0;
    
    const interval = setInterval(() => {
        if (currentStep >= SIM_STEPS.length) {
            clearInterval(interval);
            return;
        }

        const step = SIM_STEPS[currentStep];
        title.innerText = step.title;
        stepText.innerText = step.detail;
        progressBar.style.width = `${step.progress}%`;

        currentStep++;
    }, 1200); // 1.2s per step looks professional and deliberate

    // Store interval to clear if analysis finishes early or fails
    window.simInterval = interval;
}

function stopSimulation() {
    const overlay = document.getElementById('sim-overlay');
    const progressBar = document.getElementById('sim-progress');

    // Smooth finish
    progressBar.style.width = '100%';
    
    setTimeout(() => {
        clearInterval(window.simInterval);
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.style.display = 'none';
            overlay.style.opacity = '1';
        }, 500);
    }, 500);
}
