"""
FairSight AI — India Bias Atlas Generator (Data-Driven Pro)
Specifically handles real-time geographical bias from analysis results.
"""

import folium
import os

# ── 1. Global Coordinate Lookup (India + World Cities) ──
GLOBAL_COORDINATES = {
    # ── Indian States ──────────────
    "andhrapradesh": [15.9129, 79.7400], "arunachalpradesh": [28.2180, 94.7278],
    "assam": [26.2006, 92.9376], "bihar": [25.0961, 85.3131], "chhattisgarh": [21.2787, 81.8661],
    "goa": [15.2993, 74.1240], "gujarat": [22.2587, 71.1924], "haryana": [29.0588, 76.0856],
    "himachalpradesh": [31.1048, 77.1734], "jharkhand": [23.6102, 85.2799],
    "karnataka": [15.3173, 75.7139], "kerala": [10.8505, 76.2711], "madhyapradesh": [23.4733, 77.9470],
    "maharashtra": [19.7515, 75.7139], "manipur": [24.6637, 93.9063], "meghalaya": [25.4670, 91.3662],
    "mizoram": [23.1645, 92.9376], "nagaland": [26.1584, 94.5624], "odisha": [20.9517, 85.0985],
    "punjab": [31.1471, 75.3412], "rajasthan": [27.0238, 74.2179], "sikkim": [27.5330, 88.5122],
    "tamilnadu": [11.1271, 78.6569], "telangana": [18.1124, 79.0193], "tripura": [23.9408, 91.9882],
    "uttarpradesh": [26.8467, 80.9462], "uttarakhand": [30.0668, 79.0193], "westbengal": [22.9868, 87.8550],
    "delhi": [28.7041, 77.1025], "ncr": [28.7041, 77.1025],
    # ── Indian Cities ──────────────
    "mumbai": [19.0760, 72.8777], "bangalore": [12.9716, 77.5946], "bengaluru": [12.9716, 77.5946],
    "chennai": [13.0827, 80.2707], "hyderabad": [17.3850, 78.4867], "kolkata": [22.5726, 88.3639],
    "pune": [18.5204, 73.8567], "ahmedabad": [23.0225, 72.5714], "lucknow": [26.8467, 80.9462],
    "patna": [25.5941, 85.1376], "jaipur": [26.9124, 75.7873], "bhopal": [23.2599, 77.4126],
    "gurgaon": [28.4595, 77.0266], "noida": [28.5355, 77.3910], "kochi": [9.9312, 76.2673],
    "chandigarh": [30.7333, 76.7794], "nagpur": [21.1458, 79.0882],
    # ── USA ────────────────────────
    "newyork": [40.7128, -74.0060], "new york": [40.7128, -74.0060],
    "sanfrancisco": [37.7749, -122.4194], "san francisco": [37.7749, -122.4194],
    "chicago": [41.8781, -87.6298], "austin": [30.2672, -97.7431],
    "seattle": [47.6062, -122.3321], "boston": [42.3601, -71.0589],
    "atlanta": [33.7490, -84.3880], "detroit": [42.3314, -83.0458],
    "losangeles": [34.0522, -118.2437], "houston": [29.7604, -95.3698],
    # ── United Kingdom ─────────────
    "london": [51.5074, -0.1278], "manchester": [53.4808, -2.2426],
    "birmingham": [52.4862, -1.8904], "edinburgh": [55.9533, -3.1883],
    # ── Germany ────────────────────
    "berlin": [52.5200, 13.4050], "munich": [48.1351, 11.5820], "hamburg": [53.5753, 10.0153],
    # ── Australia ──────────────────
    "sydney": [-33.8688, 151.2093], "melbourne": [-37.8136, 144.9631],
    # ── Canada ─────────────────────
    "toronto": [43.6532, -79.3832], "vancouver": [49.2827, -123.1207],
    # ── Singapore / UAE ────────────
    "singapore": [1.3521, 103.8198], "dubai": [25.2048, 55.2708], "abudhabi": [24.4539, 54.3773],
    # ── Region fallback ────────────
    "metro": [28.6139, 77.2090], "urban": [19.0760, 72.8777], "rural": [25.0961, 85.3131]
}

def generate_dynamic_map(analysis_data: dict, filename: str):
    # Check if dataset has global spread to decide the map center & zoom
    has_global_data = any(
        r.get("lat") is not None for r in analysis_data.get("regions", [])
    ) if isinstance(analysis_data, dict) else False

    map_center = [20, 0] if has_global_data else [22.5937, 78.9629]
    zoom = 2 if has_global_data else 5

    m = folium.Map(
        location=map_center,
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        control_scale=True
    )

    # The analysis_data passed here is already the geo_analysis dictionary from tabular_detector.py
    geo_analysis = analysis_data if isinstance(analysis_data, dict) else {"has_geo": False}
    
    if geo_analysis.get("has_geo") and geo_analysis.get("regions"):
        print(f"[MapGenerator] Truly dynamic: Generating {len(geo_analysis['regions'])} markers.")
    # Add heat layer or error message
    if geo_analysis.get("has_geo") and geo_analysis.get("regions"):
        print(f"[MapGenerator] Truly dynamic: Generating {len(geo_analysis['regions'])} markers.")
        for region in geo_analysis["regions"]:
            _add_dynamic_marker(m, region)
    else:
        print("[MapGenerator] Fallback: No geographical data found in dataset.")
        # Attempt to get column names for diagnostics
        available_cols = geo_analysis.get("all_columns", [])
        _add_no_geo_message(m, filename, found_cols=available_cols)

    # ── 3. Post-Processing & Saving ──
    from datetime import datetime
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Add a "Live Audit" Watermark to the map
    watermark_html = f"""
    <div style="
        position: fixed; 
        bottom: 10px; right: 10px; 
        z-index: 1000;
        background: rgba(15, 15, 20, 0.8);
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 8px 15px;
        color: #10b981;
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        border-radius: 6px;
        backdrop-filter: blur(4px);
        pointer-events: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    ">
        <i class="fas fa-satellite-dish"></i> <b>LIVE AI AUDIT:</b> {now_str}<br>
        <span style="color: #888; font-size: 0.7rem;">India Bias Atlas | Session: {timestamp}</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(watermark_html))

    # Save logic - unique filename for this session
    backend_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(backend_dir)
    frontend_dir = os.path.join(project_root, "frontend")
    os.makedirs(frontend_dir, exist_ok=True)
    
    # Use a high-precision timestamp to ensure uniqueness
    map_filename = f"atlas_map_{timestamp}.html"
    output_path = os.path.join(frontend_dir, map_filename)
    m.save(output_path)
    # Also save as the standard fallback for UI stability
    default_path = os.path.join(frontend_dir, "atlas_map.html")
    m.save(default_path)
    
    print(f"[MapGenerator] Map saved: {output_path}")
    return map_filename

def _add_dynamic_marker(m, region):
    name = region["name"]
    normalized_name = name.lower().replace(" ", "").replace("_", "")

    # Priority 1: Use lat/lon embedded in the region data (from dataset columns)
    if region.get("lat") is not None and region.get("lon") is not None:
        coords = [float(region["lat"]), float(region["lon"])]
    # Priority 2: Look up in our global dictionary
    elif normalized_name in GLOBAL_COORDINATES:
        coords = GLOBAL_COORDINATES[normalized_name]
    # Priority 3: Try partial match (e.g. "New York" matches "newyork")
    else:
        compact = normalized_name.replace(" ", "")
        coords = GLOBAL_COORDINATES.get(compact, None)
        if coords is None:
            # Last resort: skip unknown locations rather than pile on India
            print(f"[MapGenerator] Skipping unknown location: {name}")
            return
    
    score = region["fairness_score"]
    status = region["status"]
    
    # Determine color based on status
    if status == "fair" or status == "green":
        color = "#10b981" # Green
    elif status == "caution" or status == "orange":
        color = "#f59e0b" # Orange
    else:
        color = "#ef4444" # Red
    
    # Popup Content
    label = "Local Fairness" if not region.get("is_fallback") else "Outcome (Approval) Rate"
    
    folium.CircleMarker(
        location=coords,
        radius=14 if status == "fair" else 22,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        popup=folium.Popup(f"""
            <div style='font-family: Inter, sans-serif; min-width: 200px;'>
                <b style='color: {color}; font-size: 1.1rem;'>{status.upper()} BIAS</b><br>
                <span style='font-weight: 700;'>Location: {name.upper()}</span><br>
                <hr style='margin: 8px 0; border: 0; border-top: 1px solid #333;'>
                <b>{label}:</b> {score}%<br>
                <b>Sample Size:</b> {region['sample_size']} applicants<br>
                <p style='font-size: 0.8rem; color: #888; margin-top: 8px;'>
                    {'Extractive fairness analysis.' if not region.get('is_fallback') else 'Statistical outcome density map.'}
                </p>
            </div>
        """, max_width=300)
    ).add_to(m)

def _add_no_geo_message(m, filename, found_cols=[]):
    """
    Adds a helpful diagnostic message to the map when no geo-data is found.
    """
    col_str = ", ".join(found_cols[:5]) + ("..." if len(found_cols) > 5 else "")
    info_text = f"Columns found: [{col_str}]" if found_cols else "Search Keywords: 'State', 'Region', 'Pincode', 'City'"
    
    html = f"""
    <div style="
        position: fixed; 
        top: 50%; left: 50%; 
        transform: translate(-50%, -50%);
        z-index: 1001;
        background: rgba(20, 20, 25, 0.95);
        color: #fff;
        padding: 40px;
        border-radius: 20px;
        border: 2px solid #ff4b2b;
        text-align: center;
        font-family: 'Inter', sans-serif;
        box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        max-width: 500px;
    ">
        <h2 style="color: #ff4b2b; margin-bottom: 20px;">
           <i class="fas fa-exclamation-triangle"></i> No Geo-Data Detected
        </h2>
        <p style="font-size: 1.1rem; opacity: 0.9; margin-bottom: 15px;">
            The dataset <b>{filename}</b> does not contain any detected geographical columns.
        </p>
        <p style="font-size: 0.9rem; color: #ff8a75; background: rgba(255, 75, 43, 0.1); padding: 10px; border-radius: 8px;">
            {info_text}
        </p>
        <p style="font-size: 0.85rem; color: #aaa; margin-top: 20px;">
            India Bias Atlas requires regional identifiers (State name, Pincode, or City) to plot hotspots.
        </p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(html))

if __name__ == "__main__":
    # Test
    generate_dynamic_map({"geo_analysis": {"has_geo": False}}, "job_description.txt")
