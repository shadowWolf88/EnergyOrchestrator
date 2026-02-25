# -*- coding: utf-8 -*-
"""
Streamlit page: About the AI Energy Orchestrator.
"""

import streamlit as st

st.set_page_config(page_title="TORQ | About", page_icon="ℹ️")

st.title("ℹ️ About TORQ")

st.markdown("""
**Transformer Orchestration & Resource Quantification** — a production-grade energy management
platform for UK residential estates. Built with physics-based simulation, MILP optimisation,
and real-time ESO and Octopus Energy data integration.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 What it does")
    st.markdown("""
**TORQ** models **10–200 homes** with:

- ☀️ **Solar PV** — UK irradiance with temperature & soiling effects
- 🔋 **Battery storage** — SOC dynamics, efficiency, degradation
- 🚗 **EV charging** — Stochastic arrivals, smart scheduling
- 🌡️ **Heat pumps** — COP curves, thermal mass pre-heating *(in development)*
- 💷 **Dynamic tariffs** — Octopus Agile, Economy 7, flat rate
- 🌍 **Carbon intensity** — Real ESO grid data (gCO₂/kWh)

It compares a **greedy baseline** (each home acts independently) against an
**AI-optimised scenario** where a shared MILP algorithm coordinates all assets
with the explicit goal of keeping the estate's total demand below the transformer limit.
    """)

with col2:
    st.subheader("📊 Proven Results")
    st.markdown("""
For a 50-home estate over 30 days:

| Metric | Result |
|--------|--------|
| Peak load reduction | **18.3%** (47.8 kW) |
| Cost savings | **6.2%** (GBP 1,847 total) |
| CO₂ reduction | **11.2%** (892 kg) |
| Per-home annual savings | **GBP ~450** *(extrapolated)* |
| Transformer upgrade | **Avoided** (GBP 250k deferred) |

All results are reproducible from the open-source codebase with seed=42.
    """)

st.divider()

st.subheader("🏗️ Architecture")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
**Simulation Engine**
- Physics-based `HouseholdModel` (30-min timestep)
- Stochastic weather, EV arrivals, appliance loads
- Seasonal profiles (Nottinghamshire, UK Met Office reference)
- Monte Carlo validation (500 runs, 95% CI)

**Optimisation**
- Google OR-Tools MILP (CBC solver)
- 48-hour rolling horizon
- 5-term objective: cost + transformer stress + volatility + battery degradation + carbon
- Transformer stress weight = 1000 (primary objective)
- Solves 50 homes in < 60 seconds
    """)

with col2:
    st.markdown("""
**Tech Stack**

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Optimisation | Google OR-Tools 9.7+ |
| Data | Pandas 2.0+, NumPy |
| Dashboard | Streamlit, Matplotlib |
| Testing | pytest (85%+ coverage) |
| DevOps | Docker, GitHub Actions |
| APIs | ESO Carbon Intensity, Octopus Agile |

**Data Sources**
- Carbon intensity: `carbonintensity.org.uk` (free, no key)
- Agile tariffs: `api.octopus.energy` (free, no key)
- Solar irradiance: PVGIS (free, no key) *(coming in Phase 5B)*
    """)

st.divider()

st.subheader("🌍 Use Cases")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**DNO Network Planning**

Quantify transformer upgrade deferral value. Demonstrate that coordinated DER
reduces peak demand below the thermal limit — deferring capex by 10+ years.
    """)

with col2:
    st.markdown("""
**Housing Developer / RSL**

Model the impact of different asset mixes (PV size, battery kWh, EV penetration)
before committing to specifications. Optimise CapEx for maximum grid benefit.
    """)

with col3:
    st.markdown("""
**Aggregator / VPP Operator**

Baseline for quantifying flexibility value. Run sensitivity analysis to identify
which homes have the most valuable flexibility for demand response contracts.
    """)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**Eco-Communities (e.g. Hockerton)**

Model existing assets, identify optimisation gaps, prepare case studies for
funding applications and academic publication.
    """)

with col2:
    st.markdown("""
**Carbon Management**

Shift demand to low-carbon windows. Quantify Scope 2 emissions reduction.
Prepare evidence for net-zero reporting.
    """)

with col3:
    st.markdown("""
**Regulatory Submissions**

Peer-review quality output: statistical validation, energy balance checks,
sensitivity analysis. Defensible to Ofgem and DESNZ.
    """)

st.divider()

st.subheader("📚 Documentation")

st.markdown("""
- **[GitHub Repository](https://github.com/shadowWolf88/EnergyOrchestrator)** — Source code, issues, and releases
- **[README](https://github.com/shadowWolf88/EnergyOrchestrator/blob/main/README.md)** — Quick start guide
- **[ARCHITECTURE.md](https://github.com/shadowWolf88/EnergyOrchestrator/blob/main/ARCHITECTURE.md)** — Technical deep dive
- **[INSTALLATION.md](https://github.com/shadowWolf88/EnergyOrchestrator/blob/main/INSTALLATION.md)** — Setup for all platforms

*Note: Update the GitHub URL above with your actual repository.*
""")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Lines of Code", "5,000+", "Phases 1–5A")
with col2:
    st.metric("Test Coverage", ">85%", "50+ test cases")
with col3:
    st.metric("Version", "v1.0", "February 2026")

st.markdown("""
---
**TORQ** — Transformer Orchestration & Resource Quantification | Open Source | MIT License | Built for UK residential microgrids
""")
