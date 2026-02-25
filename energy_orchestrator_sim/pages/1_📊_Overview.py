# -*- coding: utf-8 -*-
"""
Streamlit page: Overview dashboard with summary metrics and comparisons.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="TORQ | Overview", page_icon="📊")

st.title("📊 Estate Overview")

st.markdown("""
Baseline (greedy, independent control) vs TORQ-optimised (coordinated MILP) — 50 homes, 30 days.
""")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Homes",
        "50",
        "Baseline + Optimized",
        delta_color="off"
    )

with col2:
    st.metric(
        "Simulation Period",
        "30 days",
        "Jan 1 - Jan 30, 2024",
        delta_color="off"
    )

with col3:
    st.metric(
        "Peak Reduction",
        "47.8 kW",
        "-18.3%",
        delta_color="inverse"
    )

with col4:
    st.metric(
        "Upgrade Avoidance",
        "GBP 250k",
        "Transformer deferred",
        delta_color="inverse"
    )

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Peak Load Comparison")
    
    peak_data = {
        'Scenario': ['Baseline', 'Optimized'],
        'Peak Load (kW)': [261.5, 213.7],
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    scenarios = peak_data['Scenario']
    peaks = peak_data['Peak Load (kW)']
    limit = 250  # 50-home estate transformer upgrade threshold (kW)
    
    bars = ax.bar(scenarios, peaks, color=['#ef4444', '#10b981'], alpha=0.8, width=0.6)
    ax.axhline(y=limit, color='#f59e0b', linestyle='--', linewidth=2, label=f'Transformer Limit ({limit} kW)')
    ax.set_ylabel('Load (kW)', fontsize=12, fontweight='bold')
    ax.set_title('Peak Load: Baseline vs Optimized', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 300)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f} kW',
               ha='center', va='bottom', fontweight='bold')
    
    st.pyplot(fig)

with col_right:
    st.subheader("💰 Cost Breakdown")
    
    cost_data = pd.DataFrame({
        'Category': ['Baseline', 'Optimized', 'Savings'],
        'Cost (GBP)': [29799, 27952, 1847],
    })
    
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#ef4444', '#10b981', '#3b82f6']
    bars = ax.bar(cost_data['Category'], cost_data['Cost (GBP)'], color=colors, alpha=0.8, width=0.6)
    ax.set_ylabel('Cost (GBP)', fontsize=12, fontweight='bold')
    ax.set_title('30-Day Total Cost Comparison', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 35000)
    ax.grid(axis='y', alpha=0.3)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'GBP {height:,.0f}',
               ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    st.pyplot(fig)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🌍 Carbon Savings")
    fig, ax = plt.subplots(figsize=(8, 5))
    carbon_data = ['Baseline', 'Optimized']
    carbon_values = [7941, 7049]
    colors = ['#ef4444', '#10b981']
    bars = ax.bar(carbon_data, carbon_values, color=colors, alpha=0.8, width=0.5)
    ax.set_ylabel('CO₂ Emissions (kg)', fontsize=12, fontweight='bold')
    ax.set_title('30-Day Carbon Emissions', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 9000)
    ax.grid(axis='y', alpha=0.3)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:,.0f} kg',
               ha='center', va='bottom', fontweight='bold')
    
    st.pyplot(fig)

with col_right:
    st.subheader("📈 Key Metrics Summary")
    metrics_summary = pd.DataFrame({
        'Metric': [
            'Cost Reduction',
            'Peak Reduction',
            'CO₂ Reduction',
            'Per-Home Savings',
            'Upgrade Avoidance',
        ],
        'Value': [
            '6.2%',
            '18.3%',
            '11.2%',
            'GBP 36.95',
            'GBP 5,000',
        ],
        'Status': [
            '✓ Positive',
            '✓ Positive',
            '✓ Positive',
            '✓ Positive',
            '✓ Avoided',
        ],
    })
    st.dataframe(metrics_summary, use_container_width=True, hide_index=True)
