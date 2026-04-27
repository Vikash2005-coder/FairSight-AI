"""
FairSight AI — India Bias Atlas
Maps regional/geographic bias to an interactive map of India.
Uses Folium + GeoJSON for state-level visualization.
"""

import pandas as pd
import numpy as np
import folium
import os
import json

def generate_india_atlas(df: pd.DataFrame, region_col: str, target_col: str) -> str:
    """
    Analyzes outcome rates across Indian regions/states.
    Generates a Folium map HTML file and returns its path.
    """
    
    # 1. Map dataset labels to official State names (Fuzzy mapping)
    # Most datasets might have 'Mumbai', 'Bangalore', 'Rural UP', etc.
    # We map them to official Indian states for the choropleth.
    
    state_mapping = {
        'Mumbai': 'Maharashtra', 'Pune': 'Maharashtra', 'Rural Maharashtra': 'Maharashtra',
        'Bangalore': 'Karnataka', 'Bengaluru': 'Karnataka', 'Hassan': 'Karnataka',
        'Delhi': 'NCT of Delhi', 'NCR': 'NCT of Delhi',
        'Hyderabad': 'Telangana',
        'Chennai': 'Tamil Nadu', 'Madurai': 'Tamil Nadu',
        'Kolkata': 'West Bengal',
        'Rural UP': 'Uttar Pradesh', 'Lucknow': 'Uttar Pradesh', 'Noida': 'Uttar Pradesh',
        'Rural Bihar': 'Bihar', 'Patna': 'Bihar',
        'Ahmedabad': 'Gujarat', 'Surat': 'Gujarat',
        'Kochi': 'Kerala', 'Trivandrum': 'Kerala',
    }

    def map_to_state(region):
        for key, val in state_mapping.items():
            if key.lower() in str(region).lower():
                return val
        return None

    df['mapped_state'] = df[region_col].apply(map_to_state)
    
    # Filter only mapped states
    mapped_df = df.dropna(subset=['mapped_state'])
    
    if mapped_df.empty:
        return "" # No regional data found

    # 2. Compute Outcomes per State
    state_stats = mapped_df.groupby('mapped_state')[target_col].agg(['mean', 'count']).reset_index()
    state_stats.columns = ['state', 'approval_rate', 'count']
    
    # Calculate Disparity Index (Rate / National Average)
    national_avg = df[target_col].mean()
    state_stats['disparity_index'] = state_stats['approval_rate'] / national_avg if national_avg > 0 else 1.0
    
    # 3. Create Map
    # Initial center: Central India
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5, tiles='cartodbdark_matter')

    # Note: In a real production app, we'd load a GeoJSON file.
    # For the hackathon demo, we use a placeholder or simplified markers if GeoJSON isn't available.
    
    # Let's add markers for biased regions
    for _, row in state_stats.iterrows():
        color = 'red' if row['disparity_index'] < 0.8 else 'orange' if row['disparity_index'] < 0.95 else 'green'
        
        popup_text = f"<b>{row['state']}</b><br>" \
                     f"Approval Rate: {row['approval_rate']:.2%}<br>" \
                     f"Disparity: {row['disparity_index']:.2f}x avg<br>" \
                     f"Sample Size: {row['count']}"
        
        folium.CircleMarker(
            location=_get_state_coords(row['state']),
            radius=15,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(popup_text, max_width=250)
        ).add_to(m)

    output_path = "frontend/atlas_map.html"
    os.makedirs("frontend", exist_ok=True)
    m.save(output_path)
    
    return "/static/atlas_map.html"

def _get_state_coords(state):
    """Helper for state coordinates"""
    coords = {
        'Maharashtra': [19.7515, 75.7139],
        'Karnataka': [15.3173, 75.7139],
        'NCT of Delhi': [28.6139, 77.2090],
        'Telangana': [18.1124, 79.0193],
        'Tamil Nadu': [11.1271, 78.6569],
        'Uttar Pradesh': [26.8467, 80.9462],
        'Bihar': [25.0961, 85.3131],
        'West Bengal': [22.9868, 87.8550],
        'Gujarat': [22.2587, 71.1924],
        'Kerala': [10.8505, 76.2711]
    }
    return coords.get(state, [20.0, 78.0])
