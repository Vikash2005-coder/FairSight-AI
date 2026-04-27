/**
 * FairSight AI — India Bias Atlas Logic
 * Triggers the generation of the map and loads it into the UI.
 */

window.loadAtlas = async function() {
    const frame = document.getElementById('atlas-frame');
    if (!frame) return;

    try {
        // Use the map URL from the last analysis if available, otherwise fetch generic
        let mapUrl = '/static/atlas_map.html';
        
        if (window.currentState && window.currentState.mapUrl) {
            mapUrl = window.currentState.mapUrl;
            console.log("Loading session-specific map:", mapUrl);
        } else {
            const response = await fetch('/api/get-atlas');
            const data = await response.json();
            if (data.map_url) mapUrl = data.map_url;
        }

        // Append timestamp for extra cache-busting safety
        frame.src = `${mapUrl}?t=${new Date().getTime()}`;
    } catch (error) {
        console.error("Failed to load Atlas:", error);
    }
};
