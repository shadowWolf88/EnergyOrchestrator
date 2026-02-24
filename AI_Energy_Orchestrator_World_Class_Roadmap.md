# AI-Optimized Urban Energy Orchestrator | Implementation Roadmap

## Executive Summary

This document outlines the complete development roadmap for a **production-grade energy micromanagement platform** serving 10–200 UK residential homes. The system combines physics-based simulation, stochastic modelling, integer programming optimization, and interactive visualization to deliver 15–25% peak reduction and 8–12% annual cost savings.

**Target Users**: DNOs, independent aggregators, energy retail innovators, research institutions.

---

## Part 1: System Architecture & Data Flow

### 1.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│         INPUT LAYER (Data & Scenarios)                      │
├─────────────────────────────────────────────────────────────┤
│ • Weather data (location, irradiance, temperature)         │
│ • Tariff structures (Agile, Economy 7, custom)             │
│ • Carbon intensity signals (ESO grid mix)                  │
│ • Household configuration (PV capacity, battery size, EV)  │
│ • Historical demand profiles (BDUK/DEFRA)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│         SIMULATION ENGINE (Core Physics)                    │
│ Solar PV | Battery Storage | EV Load | Demand | Carbon    │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼──────────┐       ┌────▼─────────────────┐
    │ BASELINE      │       │ OPTIMIZATION ENGINE  │
    │ (Greedy)      │       │ (OR-Tools MILP)      │
    └────────────────┘       └────────────────────┘
                           │
         ┌─────────────────┴───────────────────┐
         │                                     │
    ┌────▼────────────┐  ┌────────────────────▼─────┐
    │ Per-Home Results│  │ Estate Aggregation       │
    │ Cost, Peak, CO₂│  │ Peak load, Transformer   │
    └────────────────┘  └──────────────────────────┘
```

### 1.2 Data Requirements & Sources

| Data Category | Specification | Source | Update Frequency |
|--------------|---------------|--------|-------------------|
| **Weather** | 30-min: irradiance, temp, wind, cloud | UK Met Office / PVGIS | Daily |
| **Demand Profiles** | Half-hourly base load, appliance variability | BDUK, DEFRA CREST | Fixed (seasonal) |
| **Tariffs** | Agile, Economy 7, standing charges | Octopus API, EDF | Real-time |
| **Carbon Intensity** | Grid mix (gCO₂/kWh), half-hourly | ESO API | Real-time |
| **Equipment** | PV, battery, EV, charger specs | Manufacturer data | Fixed |

---

## Part 2: Detailed Component Specifications

### 2.1 Household Model
- ID, location, asset capacities
- Real-time generation & load tracking
- SOC (battery & EV), tariffs, carbon signals
- Accumulated cost, peak, CO₂

### 2.2 Solar Model
- P(t) = Prated × Irradiance/1000 × Efficiency × CloudFactor
- Temperature coefficient: −0.4%/°C
- Soiling: 2% annual loss
- Seasonal variation via real UK irradiance

### 2.3 Battery Model
- SOC(t+1) = SOC(t) + ηc·Pc(t)·Δt − Pd(t)·Δt/ηd − Sloss
- Efficiency: 90% round-trip
- Degradation: £35/MWh cycled (6000 cycles → 80% SOH)
- Constraints: 0 ≤ SOC ≤ Emax, no simultaneous charge+discharge

### 2.4 EV Charging Model
- Arrival: Gamma distribution, peak 17:00–20:00
- Daily energy: N(30, 8) kWh, clipped [15, 60]
- Departure: Next day, Uniform[06:00, 08:30]
- Charging power: 3.6–7.4 kW (Type 2 home charger)
- Hard constraint: 100% SOC by departure

### 2.5 Tariff Engine
- Flat: £0.35/kWh
- Economy 7: peak £0.38, off-peak £0.16
- Agile: £0.10–£0.80/kWh (half-hourly dynamic)

### 2.6 Carbon Intensity Model
- Real: ESO Carbon Intensity API
- Synthetic: Diurnal + random variation
  - Peak: 400–800 gCO₂/kWh (winter evenings)
  - Off-peak: 50–150 gCO₂/kWh (wind/nuclear)
- Home emissions: max(Pnet, 0) × CI / 1000 kg

### 2.7 Transformer & Local Congestion Model (Primary DNO Leverage Point)

**Grid Reality**: The LV transformer is the bottleneck, not individual home assets.

- Typical UK rating: 100 kVA → ~100 kW peak thermal capacity (250A at 400V 3-phase)
- Serves 60–80 homes (variable, estate-dependent)
- Thermal inertia: 2–4 hour time constant allows brief overloads (10%), but sustained peak > 100 kW causes premature aging/failure
- Hard constraint: ΣPnet,i(t) ≤ 100 kW (typical feeders), or customer-specific limit
- **Deferral value**: Each 10 kW peak reduction defers transformer upgrade by ~2–3 years (NPV saving: £40–60k per estate)

**Optimization Focus**:
- Minimize peak import (evening 17:00–21:00) via battery discharge + EV shifting
- Minimize peak export (midday, high rooftop PV) via EV charging + heat pump heating
- Reduce import/export volatility (protect feeder voltage, minimize capacitor switching)

---

## Part 3: Simulation Engines

### 3.1 Baseline Simulator
- Greedy rules (independent per home, no optimization)
- EV: charge at 3.6 kW until full
- Battery: discharge only in peak hours, SOC > 30%
- Solar: export all surplus
- Output: per-home & estate cost, peak, CO₂ (control arm)

### 3.2 Optimization Engine (MILP)
- Solver: Google OR-Tools (CBC/Glop)
- Time limit: 60 sec/home/365-day batch
- Optimality gap: <0.1%
- Decision variables: battery charge/discharge, EV charge, SOC states
- **Objective**: min[Cost + **1000·TxStress** + 10·VolatilityPenalty + 1·BatteryDeg + 0.01·CarbonCost]
  - **TxStress** = max(0, Pestate − 100kW)² prioritizes transformer protection
  - VolatilityPenalty = Var(dP/dt) prevents feeder voltage oscillations
- Constraints: battery dynamics, EV arrival/departure, **transformer capacity limit (hard)**
- Rolling horizon: 48-hour windows, 24-hour overlap for efficiency

### 3.3 Estate Aggregation
- Aggregate all homes: Pnet,estate(t) = ΣPnet,i(t)
- Track: transformer loading, peak, cost per household
- Statistical significance (95% CI via Monte Carlo 500 runs)

---

## Part 4: Metrics & Validation

### 4.1 Cost Analyzer
- Total cost: Σ Pimport(t) × r(t) + standing_charge/365
- Peak demand charges (if applicable)
- Unit cost: C_total / E_import
- Cost savings: (Cbaseline − Copt) as £ and %

### 4.2 Peak Load & Transformer Analyzer

**Transformer Health Metrics**:
- Peak load (95th percentile): percentile(Pnet, 0.95)
- Peak reduction: (Pbaseline,95 − Popt,95) / Pbaseline,95 × 100%
- **Transformer upgrade avoidance value**: 
  - If baseline peak > transformer limit (e.g., 420 kW > 350 kW), quantify upgrade cost (e.g., £250k for parallel transformer)
  - If optimization reduces peak ≤ limit (e.g., 330 kW ≤ 350 kW), calculate deferral value at NPV
  - Rule of thumb: £40–80k per home on 50-home estate
  - **Example**: 50-home estate, baseline 420 kW → 350 kW upgrade required (£250k). Optimization → 330 kW → upgrade deferred 10+ years → £250k cost avoided ≈ £5k/home
- Demand response volume (kWh shifted): Σ(Pbaseline − Popt) × Δt
- Load factor improvement: Mean(Pestate) / Max(Pestate) × 100%
- Transformer headroom (safety margin): (100 − max(Pestate)) / 100 × 100%

### 4.3 Carbon Analyzer
- Total CO₂: Σ max(Pnet, 0) × CI / 1000 kg
- CO₂ reduction: (CO₂baseline − CO₂opt) / 1000 tonne
- Avoided cost at £25/tonne shadow price

### 4.4 Statistical Validation
- Energy balance: ±0.5% daily tolerance
- Significance: Monte Carlo 500 runs → mean, std, 95% CI
- Solver: constraints satisfied (0.1% tolerance), gap < 0.1%, no NaN/Inf

---

## Part 5: Implementation Phases

### Phase 1: Core Simulation (Weeks 1–2)
- [ ] HouseholdModel, SolarGenerator, BatteryStorage, EVCharger
- [ ] TariffManager, CarbonModel
- [ ] BaselineSimulator
- [ ] Synthetic data generation
- [ ] Unit tests (>80% coverage)

### Phase 2: Optimization (Weeks 3–4)
- [ ] MILP formulation + OR-Tools solver
- [ ] Estate aggregation
- [ ] Rolling horizon
- [ ] Constraint validation

### Phase 3: Metrics & Analysis (Week 5)
- [ ] Cost/peak/carbon analyzers
- [ ] Statistical tests
- [ ] Energy balance validation

### Phase 4: Dashboard & Polish (Week 6)
- [ ] Streamlit app
- [ ] Plotly dashboards
- [ ] README, Docker, CI/CD

### Phase 5: Validation & Hardening (Ongoing)
- [ ] Benchmark vs real data
- [ ] Sensitivity analysis
- [ ] Cloud deployment
- [ ] API endpoints

---

## Part 6: Success Criteria & KPIs

| KPI | Target | Notes |
|-----|--------|-------|
| **Peak reduction** | 15–25% | vs greedy baseline; reduces transformer stress |
| **Transformer upgrade avoidance** | £40–80k/estate | Example: 50-home estate baseline 420 kW (350 kW limit) → £250k upgrade needed. Optimization → 330 kW → upgrade deferred 10+ years ≈ £5k/home |
| Load factor improvement | 60→75% | Flattens demand curve, extends asset life |
| **Cost savings** | 8–12% / year | £100–200 per home (tariff + peak penalties) |
| Solver time | <60 sec/home/year | Full annual rolling optimization |
| Code coverage | >85% | Unit + integration tests |
| Energy balance | <0.5% error daily | Physics validation |
| Robustness | 99.9% success | No crashes, NaN, infeasible, solver failures |
| Documentation | >95% API coverage | Sphinx + markdown |
| Accuracy vs real | ±5% cost/peak | BDUK/DNO comparison |
| CO₂ reduction | 10–20% | kg/home/year (shifted to low-carbon windows) |

---

## Part 7: Tech Stack (Production-Grade)

**Backend**: Python 3.11+, Pandas 2.0+, NumPy 1.24+, Google OR-Tools 9.7+
**Forecasting**: statsmodels, Prophet, scikit-learn
**Visualization**: Streamlit 1.30+, Plotly
**Testing**: pytest, pytest-cov, hypothesis
**Code Quality**: ruff, mypy, black, isort
**DevOps**: Docker, GitHub Actions, Read the Docs

---

## Part 8: API & Future Integrations

**Planned REST API** (Phase 5):
```
POST /api/v1/simulate
GET /api/v1/tariffs/{region}
GET /api/v1/carbon/current
```

**Integration Opportunities**:
- DNO data exchange (GBEDS format)
- Aggregator platforms (SEISO, Tempus Energy)
- Home Energy Management Systems (HEMS)
- EV charging networks (Pod Point, InstaVolt)

---

## Conclusion

This roadmap delivers a **world-class, peer-reviewed quality** energy simulation and optimization platform. It combines scientific rigor, scalability, and production-readiness. The system will serve as a reference implementation for UK residential DER orchestration, delivering 15–25% peak reductions and 8–12% cost savings while maintaining physics fidelity and regulatory compliance.

**Next Step**: Begin Phase 1 implementation following the Claude Master Prompt directives.
