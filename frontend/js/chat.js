/**
 * FairSight AI — Chat Assistant Logic
 * Connects the UI to the Gemini-powered backend chat endpoint.
 */

function initChat() {
    const toggle = document.getElementById('chat-toggle');
    const container = document.getElementById('chat-container');
    const close = document.getElementById('chat-close');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const messages = document.getElementById('chat-messages');

    if (!toggle) return;

    toggle.addEventListener('click', () => container.classList.add('open'));
    close.addEventListener('click', () => container.classList.remove('open'));

    // Global shortcut to open chat from other components
    window.openChat = () => {
        container.classList.add('open');
        input.focus();
    };

    const addMessage = (text, type) => {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerText = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    };

    const handleSend = async () => {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';

        try {
            // Optimization: Only send the essential summary to avoid huge payloads
            let contextStr = "";
            if (window.lastAnalysisResult && typeof window.lastAnalysisResult === 'object') {
                const summary = {
                    filename: window.lastAnalysisResult.filename,
                    overall_score: window.lastAnalysisResult.overall_score,
                    bias_findings: window.lastAnalysisResult.audit?.bias_analysis?.biased_metrics || [],
                    causal_proxies: window.lastAnalysisResult.audit?.causal?.proxy_features || [],
                    mitigation_plan: window.lastAnalysisResult.audit?.mitigation?.short_term_actions || []
                };
                contextStr = JSON.stringify(summary);
            } else if (typeof window.lastAnalysisResult === 'string') {
                contextStr = window.lastAnalysisResult;
            }

            // Failsafe: Use AbortController for a hard frontend timeout (45s)
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 45000);

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal,
                body: JSON.stringify({
                    message: text,
                    context: contextStr
                })
            });
            clearTimeout(timeoutId);

            const data = await response.json();

            if (data.reply) {
                addMessage(data.reply, 'bot');
            } else {
                // Better error detail extraction for FastAPI 422/500 responses
                let errorMsg = "Unknown AI Processing Error";
                if (data.detail) {
                    errorMsg = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
                }
                addMessage(`I'm sorry, I couldn't process that: ${errorMsg}`, 'bot');
            }

        } catch (error) {
            console.error("Chat failed:", error);
            if (error.name === 'AbortError') {
                addMessage("Request timed out. The AI is taking too long—try a simpler question.", 'bot');
            } else {
                addMessage("Connection error: Ensure your backend is running and API keys are valid.", 'bot');
            }
        }
    };

    sendBtn.addEventListener('click', handleSend);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSend();
    });
}
