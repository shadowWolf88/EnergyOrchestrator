# Claude Master Prompt | AI-Optimized Urban Energy Orchestrator

## Executive Context

You are a senior energy systems software architect with expertise in:
- Quantitative modelling & optimization
- Power systems engineering
- Distributed energy resource (DER) orchestration
- UK energy market regulations & standards

**Mission**: Generate a production-grade, peer-reviewed-quality Python simulation framework for UK residential microgrids. This must be **world-class**—comparable to commercial energy modelling platforms used by DNOs and aggregators.

---

## Core Objective

Build a **high-fidelity, scalable simulation engine** for 10–200 UK residential homes with:

- **Generation**: Solar PV (10–15 kWp typical)
- **Storage**: Battery systems (5–15 kWh, 3–10 kW)
- **Loads**: Base consumption + stochastic appliances + EV charging + optional heat pump
- **Market Integration**: Time-of-use tariffs (Agile-style) + half-hourly settlement
- **Grid Constraints**: Transformer capacity, voltage limits, DNO constraints
- **Decarbonization**: Real-time carbon intensity signals + CO₂ tracking
- **Optimization**: MILP-based demand response & storage arbitrage
- **Validation**: Baseline vs AI-optimized with statistical significance testing

This is **not a toy implementation**. Prioritize scientific rigor, real-world constraints, and scalability.

---

## Part 1: Technical Requirements

### 1.1 Temporal & Spatial Resolution

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Time step | 30 minutes | UK settlement period; ESO data granularity |
| Simulation periods | 30-day + 365-day | Monthly planning + annual performance |
| Number of homes | 10–200 | Transformer loading (250 A, ~100 kVA) |
| Seasons | 4 (Jan, Apr, Jul, Oct) | Solar + heating variation |
| Monte Carlo samples | 500–1000 | Statistical significance (95% CI) |

### 1.2 Physical Models (with Equations)

#### Solar Generation
$$P_{\text{solar}}(t) = P_{\text{rated}} \cdot \text{Irradiance}(t) / 1000 \cdot \text{Efficiency} \cdot \text{CloudFactor}(t)$$

**Specifications**:
- Typical capacity: 10 kWp (S-facing, 30° pitch)
- Seasonal efficiency degradation; monthly cloud probability from UK Met Office (hockerton, ssouthwell, notthinghamshire)
- Temperature coefficient: −0.4%/°C
- Soiling losses: ≈2% annual

#### Battery Energy Storage

**State of Charge (SOC):**
$$\text{SOC}(t+1) = \text{SOC}(t) + \eta_c P_c(t) \Delta t - P_d(t) \Delta t / \eta_d - S_{\text{loss}}$$

**Constraints**:
- $0 \le \text{SOC}(t) \le E_{\max}$
- $P_c(t) \le P_{c,\max}$; $P_d(t) \le P_{d,\max}$
- Charging/discharging efficiency: 90–95%
- Degradation proxy: £35/MWh cycled (6000 cycles → 80% SOH)

#### EV Charging

**Stochastic Arrival/Departure**:
- Arrival: Gamma distribution, peak 17:00–18:00
- Daily energy need: $E_{\text{required}} \sim N(30, 8)$ kWh
- Departure: Uniform 06:00–08:00 next day
- Charging rate: 3.6–7.4 kW (typical home charger)

**Constraint**: Must achieve $\text{SOC}_{\text{EV}} = 100\%$ by departure time.

#### Tariff Structures

1. **Flat**: £0.35/kWh all day
2. **Economy 7**: £0.16/kWh (00:30–07:30), £0.38/kWh rest
3. **Agile (half-hourly)**: £0.10–£0.80/kWh based on wholesale market + DNO uplift

#### Carbon Intensity

- Real-time grid intensity: 0–800 gCO₂/kWh (from ESO API or synthetic)
- Home-level CO₂: $\text{Emissions}(t) = (P_{\text{net}}(t) \cdot \text{CI}(t)) / 1000$ kg CO₂

### 1.3 Optimization Objectives

**Primary**: Minimize over 48-hour rolling window:

$$\min \left[ \text{Cost} + \alpha \cdot \text{PeakPenalty} + \beta \cdot \text{BatteryDeg} + \gamma \cdot \text{CarbonCost} \right]$$

Where:
- $\text{Cost}$ = sum of all tariff charges (supply + DNO standing charge)
- $\text{PeakPenalty}$ = £15/kW for half-hourly peaks > 8 kW (demand response incentive)
- $\text{BatteryDeg}$ = £35/MWh cycled
- $\text{CarbonCost}$ = implicit shadow value (0–£50/tonne CO₂)
- Weights: $\alpha = 10$, $\beta = 1$, $\gamma = 0.01$ (tunable)

**Constraints**:
1. Battery charge/discharge limits
2. EV arrival/departure + SOC requirement
3. **Transformer capacity (hard constraint)**: $\sum P_{\text{net},i}(t) \le 100$ kW (typical 250A, 11kV/400V)
   - This is the **primary leverage point** for DNO infrastructure deferral
   - Thermal headroom: transformers rate at 100% continuous for ~4 hours, limiting peak import/export
4. **Local voltage constraints** (if modelled): 0.94–1.06 pu (feeder voltage stability)
5. Non-negativity: $P_c, P_d \ge 0$ (no simultaneous charging/discharging)

### 1.4 Transformer-Centric Optimization (Grid-Realistic Leverage Point)

The **transformer constraint is the dominant real-world limiting factor** in UK LV networks. While individual homes can shift load, the aggregate effect on the feeder transformer determines DNO capital investment deferral.

**Problem Statement**:
- Baseline estate loading: 420 kW peak (winter 18:00–20:00)
- Transformer thermal limit: 350 kW continuous (250A, 100 kVA rating)
- Required DNO upgrade: £250k (replace/parallel transformer + cable uprating)
- **Cost to delay upgrade 10 years** via optimization: ~£40–80k per home (NPV impact)

**Optimization Strategy**:
$$\min \left[ \text{Cost} + \alpha \cdot \text{TxStress} + \beta \cdot \text{VolatilityPenalty} \right]$$

Where:
- $\text{TxStress}(t) = \max(0, P_{\text{net, estate}}(t) - P_{\text{limit}})^2$ (penalizes overload)
- $\text{VolatilityPenalty} = \lambda \cdot \text{Var}(\frac{dP}{dt})$ (penalizes rapid ramping)
- Weights: $\alpha = 1000$ (strong transformer priority), $\beta = 10$ (voltage stability)

**Result**:
- Baseline peak: 420 kW → Optimized peak: 330 kW (21% reduction)
- Upgrade threshold: 350 kW → comfortably below with margin
- **Transformer upgrade deferred indefinitely** = £250k saved (≈£5k per home on 50-home estate)

### 1.5 Baseline Scenario (Non-Optimized)

**Greedy heuristics**:
- EV: Charge immediately upon arrival at 3.6 kW
- Battery: Discharge only if imminent peak (conservative)
- Solar: Export all surplus generation
- No demand response

Used as **control** for statistical comparison.

### 1.5 Estate Aggregation & Local Congestion Management

For $n$ homes, **jointly optimize distributed energy assets to reduce transformer stress and peak import/export volatility**:

$$P_{\text{net}, \text{estate}}(t) = \sum_{i=1}^{n} \left[ P_{\text{solar},i}(t) - P_{\text{load},i}(t) - P_{\text{EV},i}(t) + P_{\text{battery},i}(t) \right]$$

**Transformer Loading & Congestion**:
- Peak transformer loading: $L_{\text{peak}} = \max_t P_{\text{net, estate}}(t) / 100 \text{ kW}$
- Overload frequency: # of 30-min periods where $L > 95\%$ capacity
- Import/Export volatility: $\sigma(P_{\text{net, estate}})$ (standard deviation of net power)

**Control Strategy**:
- Battery discharge during peak import periods (evening peaks, winter)
- EV charging shifted to off-peak windows (night, windy/sunny windows)
- Solar export managed to flatten aggregate ramping (minimize $\frac{dP}{dt}$ during solar sunrise/sunset)
- Heat pump pre-heating during low-congestion periods

**Key Metrics**:
- **Transformer peak reduction**: % drop in 95th percentile load
- **DNO upgrade avoidance**: Quantified cost of deferred transformer/cable upgrades (£/home)
- **Load factor improvement**: Ratio of mean to peak load (higher = better utilization)
- Cost savings: per household per annum
- CO₂ avoided: kg/home/year

---

## Part 2: Deliverables & Architecture

### 2.1 Project Structure

```
energy_orchestrator_sim/
├── data/
│   ├── weather/           # UK/Nottinghamshire weather + solar irradiance
│   ├── tariffs/           # Agile, Economy 7, custom tariff curves
│   ├── profiles/          # BDUK, DEFRA appliance usage patterns
│   ├── carbon/            # Grid carbon intensity (ESO or synthetic)
│   └── __init__.py
│
├── core/
│   ├── household.py       # HouseholdModel class (30-min timestep)
│   ├── solar.py           # SolarGenerator (with cloud, soiling)
│   ├── battery.py         # BatteryStorage (SOC, efficiency, degradation)
│   ├── ev.py              # EVCharger (stochastic arrival/departure)
│   ├── tariff.py          # TariffManager (flat/Economy 7/Agile)
│   ├── carbon.py          # CarbonModel (grid intensity)
│   ├── transformer.py     # TransformerConstraint (capacity, overload tracking)
│   └── __init__.py
│
├── simulation/
│   ├── baseline_engine.py # BaselineSimulator (greedy heuristics)
│   ├── optimization_engine.py # OptimizationEngine (OR-Tools MILP)
│   ├── solver_config.py   # Solver parameters, time limits, tolerances
│   ├── constraints.py     # ConstraintSet (battery, EV, transformer)
│   └── __init__.py
│
├── ai/
│   ├── demand_forecaster.py # ARIMA/Prophet for base load prediction
│   ├── solar_forecaster.py  # Sky camera simulator or historical cloud patterns
│   ├── ev_predictor.py      # Arrival/departure probability
│   └── __init__.py
│
├── metrics/
│   ├── cost_analyzer.py     # Tariff-based cost + DNO charges
│   ├── peak_analyzer.py     # Peak reduction, demand response metrics
│   ├── carbon_analyzer.py   # CO₂ avoidance, grid carbon tracking
│   ├── thermal_analyzer.py  # Heat pump metrics (if applicable)
│   ├── statistics.py        # Statistical significance tests (t-tests, CI)
│   └── __init__.py
│
├── dashboard/
│   ├── streamlit_app.py     # Interactive visualization + scenario builder
│   ├── pages/
│   │   ├── overview.py      # KPI cards, estate summary
│   │   ├── household_detail.py  # Single-home deep dive
│   │   ├── optimization.py  # Solver diagnostics, convergence metrics
│   │   ├── tariff_explorer.py   # Tariff comparison
│   │   └── carbon_dashboard.py  # Grid carbon signals + impact
│   └── __init__.py
│
├── tests/
│   ├── test_core_models.py      # Unit tests (battery, solar, EV)
│   ├── test_simulation_engine.py # Integration: baseline vs optimization
│   ├── test_constraints.py       # Constraint validation
│   ├── test_metrics.py           # Metric calculation accuracy
│   └── test_energy_balance.py    # Energy conservation (input = output)
│
├── config/
│   ├── default_config.yaml      # Household parameters, solver settings
│   ├── tariff_definitions.yaml  # Tariff curves
│   └── scenarios.yaml            # Pre-built scenarios
│
├── docs/
│   ├── MODEL_SPECIFICATION.md   # Detailed equations, assumptions
│   ├── API.md                   # Module/class interface docs
│   ├── USER_GUIDE.md            # Dashboard + CLI instructions
│   └── VALIDATION_REPORT.md     # Benchmarks vs real data
│
├── main.py                      # CLI entry point (run simulations, export results)
├── requirements.txt             # Dependencies
├── pyproject.toml              # Modern Python packaging
├── Dockerfile                   # Container for reproducibility
├── .env.example               # Configuration template
└── README.md                  # Quick start
```

### 2.2 Tech Stack (Production-Grade)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Type hints, performance, ecosystem |
| **Data** | Pandas 2.0+, Polars (optional) | Vectorized time series, multi-index support |
| **Numerics** | NumPy 1.24+ | FFT, matrix ops |
| **Optimization** | Google OR-Tools 9.7+ | MILP solver, proven in production |
| **forecasting** | statsmodels, Prophet | ARIMA for demand, seasonal models |
| **Visualization** | Streamlit, Plotly | Interactive dashboards, web-native |
| **Testing** | pytest, pytest-cov | Unit + integration + coverage |
| **Code Quality** | ruff, mypy, black | Automatic linting, type checking, formatting |
| **Logging** | Python logging + structlog | Structured, production-ready |
| **Container** | Docker, docker-compose | Reproducible environments |
| **CI/CD** | GitHub Actions | Automated testing + release |

---

## Part 3: Validation & Benchmarks

### 3.1 Validation Strategy

1. **Energy Balance Check**: For every home, $\sum P_{\text{in}} = \sum P_{\text{out}}$ hourly (tolerance: ±0.5%)
2. **Comparison vs Real Data**: 
   - Validate solar generation against UK regional PV data
   - Demand profiles against BDUK/DEFRA open data
   - Tariff costs against known suppliers
3. **Sensitivity Analysis**: Vary key parameters (PV capacity, battery efficiency, EV arrival time) → observe cost/peak impact
4. **Solver Validation**: 
   - Check optimality gap < 0.1% (feasible within 60s)
   - Constraint violations: zero
5. **Statistical Significance**: Run Monte Carlo 500 times; report 95% confidence intervals

### 3.2 World-Class Benchmarks (Success Criteria)

| Metric | Target | Notes |
|--------|--------|-------|
| **Peak reduction** | 15–25% | vs greedy baseline; moves peak import below transformer thermal limit |
| **Transformer upgrade avoidance** | £40–80k/estate | Example: 50-home estate with baseline peak 420 kW (exceeds 350 kW limit) requires £250k DNO upgrade. Optimization reduces peak to 330 kW, defers upgrade 10+ years = £40–80k value/home |
| Load factor improvement | 60→75% | Flattens demand curve, improves transformer utilization |
| **Cost savings** | 8–12% | per household per annum (£100–200/home) |
| CO₂ reduction | 10–20% | kg/home/year (shifted consumption to low-carbon windows) |
| Import/export volatility | −30–40% | Reduced σ(Pestate) protects feeder voltage stability |
| Solver speed | <60 sec/home | 365-day annual optimization (rolling 48-hour windows) |
| Accuracy vs real | ±5% | cost/energy/peak predictions vs BDUK/DNO data |
| Model robustness | 99.9% | no NaN, inf, or infeasible solutions |

---

## Part 4: Implementation Priorities

**Phase 1 (MVP)**: Core models, baseline, basic optimization
**Phase 2**: Dashboard, estate aggregation, statistical validation
**Phase 3**: Advanced AI forecasting, heat pump integration, API
**Phase 4**: Cloud deployment, real-time capability, commercial hardening

---

## Execution Directives

1. **Scientific Rigor**: Every equation documented; assumptions listed; edge cases handled
2. **Scalability**: Code must handle 200 homes in <5 min (batch), <100ms (single query)
3. **Reproducibility**: All randomness seeded; results deterministic given seed
4. **Testing**: >85% code coverage; every optimization model tested
5. **Documentation**: Sphinx-level API docs; markdown user guides
6. **Production-Ready**: Error handling, logging, config management, CI/CD

**"Begin implementation now with complete rigour and ambition—this is a market-grade product, not a prototype."**
