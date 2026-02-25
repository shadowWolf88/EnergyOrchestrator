# -*- coding: utf-8 -*-
"""
TORQ — Transformer Orchestration & Resource Quantification
Home page: navigation hub and executive summary.
"""

import streamlit as st

st.set_page_config(
    page_title="TORQ | Grid Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ TORQ")
st.markdown("**Transformer Orchestration & Resource Quantification** — coordinating distributed energy assets to defer grid infrastructure upgrades")

st.markdown("""
---

## Platform Results at a Glance

| Metric | Baseline | TORQ-Optimised | Impact |
|--------|----------|----------------|--------|
| **Peak Load** | 261.5 kW | 213.7 kW | **−18.3% (47.8 kW)** |
| **Energy Cost** | GBP 29,799 | GBP 27,952 | **−6.2% (GBP 1,847)** |
| **CO₂ Emissions** | 7,941 kg | 7,049 kg | **−11.2% (892 kg)** |
| **Transformer Upgrade** | REQUIRED ✗ | AVOIDED ✓ | **GBP 250,000 deferred** |

*50 homes, 30-day simulation, Nottinghamshire, seed=42*

---

## Navigate
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
### 📊 Overview
- Estate peak vs transformer limit
- Cost and carbon comparison
- Key performance indicators
    """)
    st.page_link("pages/1_📊_Overview.py", label="→ Overview", icon="📊")

with col2:
    st.markdown("""
### 🏠 Household Detail
- Per-home battery, EV and solar profiles
- Individual demand patterns
- Cost & emissions by household
    """)
    st.page_link("pages/2_🏠_Household_Detail.py", label="→ Household Detail", icon="🏠")

with col3:
    st.markdown("""
### 📈 Optimisation
- MILP solver performance
- Convergence analysis
- Objective weights & configuration
    """)
    st.page_link("pages/3_📈_Optimization.py", label="→ Optimisation", icon="📈")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
### 💰 Cost Analysis
- Half-hourly cost patterns
- Breakdown by component
- Savings attribution
    """)
    st.page_link("pages/4_💰_Cost_Analysis.py", label="→ Cost Analysis", icon="💰")

with col2:
    st.markdown("""
### 💨 Carbon Impact
- Live ESO grid intensity
- Cumulative emissions
- Reduction by strategy
    """)
    st.page_link("pages/5_💨_Carbon_Impact.py", label="→ Carbon Impact", icon="💨")

with col3:
    st.markdown("""
### ⚙️ Settings & Run
- Configure estate parameters
- Launch live simulation
- Preset scenarios (incl. Hockerton)
    """)
    st.page_link("pages/6_⚙️_Settings.py", label="→ Settings & Run", icon="⚙️")

st.markdown("""
---

## How TORQ Works

**TORQ** treats the estate's LV transformer as the primary constraint — not a secondary consideration. Every asset decision (when to charge a battery, when to charge an EV, when to pre-heat via heat pump) is weighed against a shared objective: keep aggregate demand below the transformer's thermal limit.

1. **Physics simulation** — 30-minute timestep models for solar PV, battery storage, EV charging, and demand
2. **Greedy baseline** — each home acts independently (the counterfactual)
3. **MILP optimisation** — all homes coordinated in a single mathematical programme (Google OR-Tools)
4. **Transformer-first objective** — stress weight = 1,000 vs cost weight = 1 (infrastructure deferral is the primary value)
5. **Validated output** — energy balance checks, Monte Carlo confidence intervals, per-home KPIs

**The result**: the grid upgrade you will never need.

---

## Documentation & Support

- **[GitHub Repository](https://github.com/shadowWolf88/EnergyOrchestrator)** — source code & issues *(update URL)*
- **[About TORQ](pages/7_ℹ️_About.py)** — technical architecture, use cases, version info
- **Email**: info@torq.energy

---

**TORQ v1.0 | February 2026 | Transformer Orchestration & Resource Quantification**
""")
