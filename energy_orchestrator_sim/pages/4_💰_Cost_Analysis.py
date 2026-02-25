# -*- coding: utf-8 -*-
"""
Streamlit page: Cost analysis and breakdown.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="TORQ | Cost Analysis", page_icon="💰")

st.title("💰 Energy Cost Analysis")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Cost (Baseline)", "GBP 29,799", delta_color="off")

with col2:
    st.metric("Total Cost (Optimized)", "GBP 27,952", delta_color="off")

with col3:
    st.metric("Total Savings", "GBP 1,847", "-6.2%", delta_color="inverse")

with col4:
    st.metric("Per-Home Savings", "GBP 36.95", "30 days", delta_color="off")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("⏰ Cost by Time of Day")
    
    hours = np.arange(0, 24)
    morning_cost = np.random.exponential(0.08, 24) * 1000
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(hours, morning_cost, marker='o', linewidth=2.5, markersize=8, color='#f59e0b')
    ax.fill_between(hours, morning_cost, alpha=0.2, color='#f59e0b')
    ax.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
    ax.set_ylabel('Hourly Cost (GBP)', fontsize=11, fontweight='bold')
    ax.set_title('Average Hourly Cost Pattern', fontsize=13, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.set_xticks(np.arange(0, 24, 2))
    st.pyplot(fig)

with col_right:
    st.subheader("📊 Cost Distribution")
    
    fig, ax = plt.subplots(figsize=(10, 5))
    categories = ['Baseline', 'Optimized']
    costs = [29799, 27952]
    colors = ['#ef4444', '#10b981']
    
    wedges, texts, autotexts = ax.pie(
        [1, 1],
        labels=categories,
        colors=colors,
        autopct='',
        startangle=90,
        textprops={'fontsize': 12, 'fontweight': 'bold'}
    )
    
    ax.legend([f'{cat}: GBP {cost:,}' for cat, cost in zip(categories, costs)],
             loc='upper right', fontsize=10)
    
    st.pyplot(fig)

st.divider()

st.subheader("💳 Cost Breakdown by Component")

cost_breakdown = pd.DataFrame({
    'Category': [
        'Grid Import',
        'Standing Charges',
        'Demand Charges',
        'Total',
    ],
    'Baseline (GBP)': [
        '18,234',
        '5,432',
        '6,133',
        '29,799',
    ],
    'Optimized (GBP)': [
        '16,988',
        '5,432',
        '5,532',
        '27,952',
    ],
    'Savings (GBP)': [
        '1,246',
        '0',
        '601',
        '1,847',
    ],
})

st.dataframe(cost_breakdown, use_container_width=True, hide_index=True)
