# -*- coding: utf-8 -*-
"""
Streamlit page: Household-level analysis with per-home asset profiles.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Household Detail", page_icon="🏠")

st.title("🏠 Household-Level Analysis")

# Load demo data
@st.cache_data
def load_demo_data():
    n_homes = 50
    n_days = 30
    n_timesteps = n_days * 48
    
    dates = pd.date_range("2024-01-01", periods=n_timesteps, freq="30min")
    
    data = {
        'timestamp': dates,
        'home_id': np.random.choice([f'H{i:04d}' for i in range(1, n_homes + 1)], n_timesteps),
        'demand_total_kw': np.random.exponential(1.5, n_timesteps),
        'pv_generation_kw': np.maximum(0, 4.0 * np.sin(np.linspace(0, n_timesteps*np.pi/(n_timesteps/4), n_timesteps)) * 0.8),
        'net_load_kw': np.random.normal(1.0, 0.8, n_timesteps),
        'battery_soc_kwh': np.random.uniform(2, 8, n_timesteps),
        'ev_soc_kwh': np.random.uniform(10, 50, n_timesteps),
        'cumulative_cost_gbp': np.cumsum(np.random.exponential(0.05, n_timesteps)),
        'cumulative_co2_kg': np.cumsum(np.random.exponential(0.3, n_timesteps)),
    }
    
    return pd.DataFrame(data)

data = load_demo_data()
homes = sorted(data['home_id'].unique())

selected_home = st.selectbox("Select household:", homes, index=0)
home_data = data[data['home_id'] == selected_home]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Home", selected_home, delta_color="off")

with col2:
    total_cost = home_data['cumulative_cost_gbp'].iloc[-1]
    st.metric("Total Cost", f"GBP {total_cost:.2f}", delta_color="off")

with col3:
    total_co2 = home_data['cumulative_co2_kg'].iloc[-1]
    st.metric("CO₂ Emitted", f"{total_co2:.1f} kg", delta_color="off")

with col4:
    avg_demand = home_data['demand_total_kw'].mean()
    st.metric("Avg Demand", f"{avg_demand:.2f} kW", delta_color="off")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔋 Battery State of Charge")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(home_data['timestamp'], home_data['battery_soc_kwh'], linewidth=2, color='#3b82f6')
    ax.fill_between(home_data['timestamp'], 0, home_data['battery_soc_kwh'], alpha=0.3, color='#3b82f6')
    ax.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax.set_ylabel('Battery SOC (kWh)', fontsize=11, fontweight='bold')
    ax.set_title('Battery State of Charge (30 days)', fontsize=13, fontweight='bold')
    ax.grid(alpha=0.3)
    st.pyplot(fig)

with col_right:
    st.subheader("🚗 EV State of Charge")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(home_data['timestamp'], home_data['ev_soc_kwh'], linewidth=2, color='#10b981')
    ax.fill_between(home_data['timestamp'], 0, home_data['ev_soc_kwh'], alpha=0.3, color='#10b981')
    ax.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax.set_ylabel('EV SOC (kWh)', fontsize=11, fontweight='bold')
    ax.set_title('EV Charging Pattern (30 days)', fontsize=13, fontweight='bold')
    ax.grid(alpha=0.3)
    st.pyplot(fig)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("☀️ Solar Generation")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(home_data['timestamp'], home_data['pv_generation_kw'], width=0.02, color='#f59e0b', alpha=0.8)
    ax.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax.set_ylabel('Generation (kW)', fontsize=11, fontweight='bold')
    ax.set_title('Solar PV Generation (30 days)', fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    st.pyplot(fig)

with col_right:
    st.subheader("💡 Demand Profile")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(home_data['timestamp'], home_data['demand_total_kw'], width=0.02, color='#8b5cf6', alpha=0.8)
    ax.set_xlabel('Time', fontsize=11, fontweight='bold')
    ax.set_ylabel('Demand (kW)', fontsize=11, fontweight='bold')
    ax.set_title('Household Demand Profile (30 days)', fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    st.pyplot(fig)
