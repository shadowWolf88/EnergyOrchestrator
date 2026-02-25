# -*- coding: utf-8 -*-
"""
Streamlit page: Simulation settings and live run trigger.
"""

import subprocess
import sys
import os
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Settings", page_icon="⚙️")

st.title("⚙️ Simulation Settings")

st.markdown("""
Configure and run the energy optimisation simulation. Results will be saved to CSV
and loaded automatically by all dashboard pages.
""")

st.divider()

# ── Estate Configuration ─────────────────────────────────────────────────────

st.subheader("🏘️ Estate Configuration")

col1, col2, col3 = st.columns(3)

with col1:
    num_homes = st.slider(
        "Number of homes",
        min_value=10,
        max_value=200,
        value=50,
        step=10,
        help="Homes on the estate (10–200)"
    )

with col2:
    num_days = st.selectbox(
        "Simulation period",
        options=[7, 14, 30, 90, 365],
        index=2,
        format_func=lambda x: f"{x} days",
        help="Length of simulation"
    )

with col3:
    seed = st.number_input(
        "Random seed",
        min_value=0,
        max_value=9999,
        value=42,
        help="Fix seed for reproducible results"
    )

st.divider()

# ── Grid Configuration ────────────────────────────────────────────────────────

st.subheader("🔌 Grid & Transformer Configuration")

col1, col2 = st.columns(2)

with col1:
    transformer_kw = st.number_input(
        "Transformer upgrade threshold (kW)",
        min_value=50,
        max_value=1000,
        value=250,
        step=25,
        help="Peak demand above this threshold triggers a DNO upgrade requirement"
    )

with col2:
    upgrade_cost = st.number_input(
        "Transformer upgrade cost (GBP)",
        min_value=50000,
        max_value=1000000,
        value=250000,
        step=25000,
        format="%d",
        help="Estimated cost of DNO transformer/cable upgrade"
    )

st.divider()

# ── Tariff & Data Configuration ───────────────────────────────────────────────

st.subheader("💷 Tariff & Data Sources")

col1, col2 = st.columns(2)

with col1:
    tariff_type = st.selectbox(
        "Tariff type",
        options=["agile", "economy7", "flat"],
        index=0,
        format_func=lambda x: {
            "agile": "Agile (half-hourly dynamic)",
            "economy7": "Economy 7 (peak/off-peak)",
            "flat": "Flat rate (£0.35/kWh)"
        }[x]
    )

with col2:
    use_real_carbon = st.toggle(
        "Use live ESO carbon intensity",
        value=False,
        help="Fetches real-time data from carbonintensity.org.uk (no API key needed)"
    )

st.divider()

# ── Preset Scenarios ─────────────────────────────────────────────────────────

st.subheader("📋 Preset Scenarios")

preset = st.selectbox(
    "Load preset scenario",
    options=[
        "custom",
        "hockerton",
        "small_urban",
        "medium_suburban",
        "large_rural",
    ],
    format_func=lambda x: {
        "custom": "Custom (use sliders above)",
        "hockerton": "Hockerton Housing Project (9 homes, Nottinghamshire)",
        "small_urban": "Small Urban Estate (25 homes)",
        "medium_suburban": "Medium Suburban (50 homes — default)",
        "large_rural": "Large Rural Estate (100 homes, high solar)",
    }[x]
)

if preset == "hockerton":
    st.info(
        "**Hockerton Housing Project preset** — 9 eco-homes, Nottinghamshire. "
        "Adjust solar/battery specs after discussing with the project team."
    )
    num_homes = 9
    num_days = 30
    transformer_kw = 50
    tariff_type = "agile"
    st.markdown(
        "Preset applied: **9 homes**, **30 days**, **50 kW transformer**, **Agile tariff**. "
        "Click Run Simulation below."
    )
elif preset == "small_urban":
    num_homes = 25
    transformer_kw = 150
elif preset == "large_rural":
    num_homes = 100
    transformer_kw = 500

st.divider()

# ── Run Simulation ────────────────────────────────────────────────────────────

st.subheader("🚀 Run Simulation")

col_info, col_btn = st.columns([3, 1])

with col_info:
    st.markdown(f"""
**Ready to simulate:**
- **{num_homes} homes** over **{num_days} days**
- Transformer threshold: **{transformer_kw:,} kW** | Upgrade cost: **£{upgrade_cost:,}**
- Tariff: **{tariff_type}** | Seed: **{seed}**
- Carbon data: **{"Live ESO API" if use_real_carbon else "Synthetic (UK profile)"}**

This will overwrite any existing `simulation_results_*.csv` files.
    """)

with col_btn:
    run_button = st.button("▶ Run Simulation", type="primary", use_container_width=True)

if run_button:
    # Build command
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(app_dir, "main.py")

    cmd = [
        sys.executable, main_py,
        "--homes", str(num_homes),
        "--days", str(num_days),
        "--transformer-kw", str(transformer_kw),
        "--upgrade-cost", str(upgrade_cost),
        "--seed", str(seed),
    ]

    with st.spinner(f"Running simulation ({num_homes} homes, {num_days} days)… this may take up to 60 seconds."):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=app_dir,
            )

            if result.returncode == 0:
                st.success("✅ Simulation completed! Navigate to any dashboard page to see updated results.")
                st.cache_data.clear()
                with st.expander("Show simulation log"):
                    st.code(result.stdout or "(no output)", language="text")
            else:
                st.error("❌ Simulation failed. See error below.")
                with st.expander("Error details"):
                    st.code(result.stderr or result.stdout or "(no output)", language="text")

        except subprocess.TimeoutExpired:
            st.error("⏰ Simulation timed out (>5 minutes). Try fewer homes or days.")
        except Exception as e:
            st.error(f"❌ Could not launch simulation: {e}")

st.divider()

# ── Current Results Summary ───────────────────────────────────────────────────

st.subheader("📁 Current Results")

app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
baseline_path = os.path.join(app_dir, "simulation_results_baseline.csv")
optimized_path = os.path.join(app_dir, "simulation_results_optimized.csv")

col1, col2 = st.columns(2)

with col1:
    if os.path.exists(baseline_path):
        size = os.path.getsize(baseline_path) / 1024
        mtime = pd.Timestamp(os.path.getmtime(baseline_path), unit="s").strftime("%Y-%m-%d %H:%M")
        st.metric("Baseline CSV", f"{size:.0f} KB", f"Last run: {mtime}")
    else:
        st.warning("No baseline results found. Run the simulation first.")

with col2:
    if os.path.exists(optimized_path):
        size = os.path.getsize(optimized_path) / 1024
        mtime = pd.Timestamp(os.path.getmtime(optimized_path), unit="s").strftime("%Y-%m-%d %H:%M")
        st.metric("Optimised CSV", f"{size:.0f} KB", f"Last run: {mtime}")
    else:
        st.warning("No optimised results found. Run the simulation first.")
