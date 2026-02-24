# -*- coding: utf-8 -*-
"""
Streamlit home page for AI Energy Orchestrator.

Navigate to individual analysis pages using the sidebar or buttons below.
"""

import streamlit as st

st.set_page_config(
    page_title="AI Energy Orchestrator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ AI Energy Orchestrator")
st.markdown("**World-class energy management optimization for distributed assets**")

st.markdown("""
---

## 🌟 Welcome!

This dashboard provides interactive analysis of energy optimization simulations for residential estates.

**Key Highlights:**
- 📊 **Peak Load Reduction**: 15-25% reduction via coordinated control
- 💰 **Cost Savings**: 6-12% per year (GBP 37-200 per home)
- 🌍 **Carbon Impact**: 10-20% emissions reduction
- 🏗️ **Transformer Deferral**: Quantified infrastructure value (GBP 40-80k per estate)

---

## 📊 Quick Navigation

Navigate using the sidebar, or click below to jump to a specific analysis:
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
### 📊 Overview
- Peak/cost/carbon comparison
- Key metrics summary
- Baseline vs optimized
    
[→ Go to Overview](./📊_Overview)
    """)

with col2:
    st.markdown("""
### 🏠 Household Detail  
- Per-home battery/EV/solar profiles
- Individual demand patterns
- Cost & emissions by home

[→ Go to Household](./🏠_Household_Detail)
    """)

with col3:
    st.markdown("""
### 📈 Optimization
- Solver performance
- Convergence analysis
- Configuration details

[→ Go to Optimization](./📈_Optimization)
    """)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
### 💰 Cost Analysis
- Hourly cost patterns
- Breakdown by component
- Savings calculation

[→ Go to Costs](./💰_Cost_Analysis)
    """)

with col2:
    st.markdown("""
### 💨 Carbon Impact
- Grid intensity patterns
- Cumulative emissions
- Reduction strategies

[→ Go to Carbon](./💨_Carbon_Impact)
    """)

with col3:
    st.markdown("""
### ⚙️ Coming Soon
- Settings & customization
- Real data integration
- API endpoints

📍 Check back soon!
    """)

st.markdown("""
---

## 🚀 Example Results (50 homes, 30 days)

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| **Peak Load** | 261.5 kW | 213.7 kW | **-47.8 kW (-18.3%)** |
| **Total Cost** | GBP 29,799 | GBP 27,952 | **-GBP 1,847 (-6.2%)** |
| **CO₂ Emissions** | 7,941 kg | 7,049 kg | **-892 kg (-11.2%)** |
| **Transformer Upgrade** | **REQUIRED** ✗ | **AVOIDED** ✓ | **GBP 250,000 deferred** |

---

## 💡 About This System

The **AI Energy Orchestrator** is a physics-based energy optimization platform that:

1. **Models real households** with solar panels, batteries, EVs, and heat pumps
2. **Simulates baseline** (greedy independent control) as benchmark
3. **Optimizes multi-home** control using MILP (Mixed-Integer Linear Programming)
4. **Prioritizes transformer deferral** as the PRIMARY objective (weight=1000)
5. **Quantifies financial value** of peak reduction and infrastructure deferral
6. **Validates physics** with energy balance checks and statistical tests

**Technology Stack:**
- Python 3.11+ | Google OR-Tools | Pandas | NumPy | Streamlit | Plotly

**Deployment:**
- Docker containerized | GitHub Actions CI/CD | Production-grade code

---

## 📚 Documentation

- **[README](https://github.com/shadowWolf88/EnergyOrchestrator)** — Quick start & feature overview
- **[ARCHITECTURE.md](https://github.com/shadowWolf88/EnergyOrchestrator)** — Technical deep dive
- **[INSTALLATION.md](https://github.com/shadowWolf88/EnergyOrchestrator)** — Setup for all platforms
- **[GitHub Repository](https://github.com/shadowWolf88/EnergyOrchestrator)** — Source code & issues

---

## 🎯 Use Cases

✓ **DNO Network Planning** — Defer transformer upgrades through coordinated DER control  
✓ **Battery Sizing** — Right-size storage for peak shaving (not just arbitrage)  
✓ **EV Integration** — Optimize charging timing to reduce feeder demand coincidence  
✓ **Carbon Management** — Shift demand to periods of low-carbon grid generation  
✓ **Regulatory Compliance** — Demonstrate compliance with network constraints  

---

## 📞 Support

- **Bug Reports**: [GitHub Issues](https://github.com/shadowWolf88/EnergyOrchestrator/issues)
- **Questions**: [GitHub Discussions](https://github.com/shadowWolf88/EnergyOrchestrator/discussions)
- **Email**: info@energyorchestrator.io

---

**AI Energy Orchestrator v1.0 | February 2026 | [⭐ Star on GitHub](https://github.com/shadowWolf88/EnergyOrchestrator)**
""")
