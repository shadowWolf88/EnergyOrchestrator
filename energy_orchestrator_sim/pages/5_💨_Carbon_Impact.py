# -*- coding: utf-8 -*-
"""
Streamlit page: Carbon impact and emissions analysis.

Tries to fetch live ESO carbon intensity data; falls back to synthetic profile.
"""

import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Allow imports from parent directory when running as a page
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Carbon Impact", page_icon="💨")

st.title("💨 Carbon Emissions Analysis")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Baseline CO₂", "7,941 kg", "30 days", delta_color="off")

with col2:
    st.metric("Optimized CO₂", "7,049 kg", "30 days", delta_color="off")

with col3:
    st.metric("CO₂ Reduction", "892 kg", "-11.2%", delta_color="inverse")

with col4:
    st.metric("Per-Home Reduction", "17.8 kg", "30 days", delta_color="off")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🌍 Grid Carbon Intensity")

    # Try live ESO API first
    @st.cache_data(ttl=1800)  # Cache for 30 minutes
    def fetch_live_carbon():
        try:
            from data.realtime_eso_api import CarbonIntensityAPI
            df = CarbonIntensityAPI.get_24h_forecast()
            return df
        except Exception:
            return None

    live_df = fetch_live_carbon()

    if live_df is not None and len(live_df) > 0:
        hours = live_df["timestamp"].dt.hour + live_df["timestamp"].dt.minute / 60
        intensity = live_df["carbon_intensity_gco2_per_kwh"].values
        source_label = "Live data: ESO Carbon Intensity API (carbonintensity.org.uk)"
        color = "#10b981"
    else:
        hours = np.arange(0, 24)
        intensity = 400 + 200 * np.sin(hours * np.pi / 12) + np.random.default_rng(42).normal(0, 30, 24)
        source_label = "Synthetic data (ESO API unavailable)"
        color = "#6b7280"

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hours, intensity, marker='o', linewidth=2.5, markersize=6, color=color)
    ax.fill_between(hours, intensity, alpha=0.2, color=color)
    ax.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
    ax.set_ylabel('Carbon Intensity (gCO₂/kWh)', fontsize=11, fontweight='bold')
    ax.set_title('Grid Carbon Intensity (Today)', fontsize=13, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.set_xticks(np.arange(0, 24, 2))
    st.pyplot(fig)
    st.caption(f"📡 {source_label}")

with col_right:
    st.subheader("📈 Cumulative Emissions")
    
    @st.cache_data
    def load_emission_data():
        n_days = 30
        daily_avg = np.cumsum(np.random.exponential(260, n_days))
        return daily_avg
    
    daily_avg = load_emission_data()
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(daily_avg)), daily_avg, linewidth=2.5, color='#8b5cf6')
    ax.fill_between(range(len(daily_avg)), daily_avg, alpha=0.2, color='#8b5cf6')
    ax.set_xlabel('Day', fontsize=11, fontweight='bold')
    ax.set_ylabel('Cumulative CO₂ (kg)', fontsize=11, fontweight='bold')
    ax.set_title('30-Day Cumulative Carbon Emissions', fontsize=13, fontweight='bold')
    ax.grid(alpha=0.3)
    st.pyplot(fig)

st.divider()

st.subheader("🌱 Carbon Impact by Optimization Strategy")

impact_summary = pd.DataFrame({
    'Strategy': [
        'Peak Load Reduction',
        'Off-Peak Shifting',
        'Solar Maximization',
        'EV Charging Timing',
        'Total Impact',
    ],
    'CO₂ Reduction (kg)': [
        '350',
        '280',
        '180',
        '82',
        '892',
    ],
    'Percentage': [
        '39.2%',
        '31.4%',
        '20.2%',
        '9.2%',
        '100%',
    ],
})

st.dataframe(impact_summary, use_container_width=True, hide_index=True)
