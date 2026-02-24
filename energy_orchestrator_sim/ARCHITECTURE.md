# Architecture & Design

Comprehensive technical architecture of AI Energy Orchestrator.

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Interface Layer                          │
│                 (Streamlit Dashboard - Phase 2)                  │
├─────────────────────────────────────────────────────────────────┤
│                  Simulation Orchestration                        │
│          EstateSimulator (end-to-end workflow runner)            │
├──────────────┬──────────────────────┬──────────────────────┤
│  Baseline    │  Optimization        │  Metrics Analysis    │
│  Simulator   │  Engine (MILP)       │  & Reporting         │
├──────────────┼──────────────────────┼──────────────────────┤
│          Physical Simulation Layer (30-min timesteps)           │
│         HouseholdModel × N (physics-based dynamics)             │
├─────────────────────────────────────────────────────────────────┤
│                    Data Generation                               │
│  Weather │ Demand │ Tariffs │ Carbon │ EV Profiles              │
├─────────────────────────────────────────────────────────────────┤
│                   OR-Tools MILP Solver                           │
│         (Google OR-Tools 9.7+ with CBC backend)                 │
└─────────────────────────────────────────────────────────────────┘
```

## Module Dependency Graph

```
main.py
  ↓
EstateSimulator
  ├─→ HouseholdModel (core.household) ×N homes
  ├─→ generate_simulation_data (data.generators)
  ├─→ EstateBaselineSimulator
  │     └─→ BaselineSimulator
  │           └─→ HouseholdModel
  ├─→ EstateOptimizer
  │     ├─→ MILPOptimizer (per-home)
  │     │     └─→ OptimizationConfig
  │     └─→ Google OR-Tools
  └─→ MetricsCalculator
        ├─→ CostAnalyzer
        ├─→ PeakAnalyzer
        ├─→ CarbonAnalyzer
        ├─→ TransformerAnalyzer
        └─→ StatisticalValidator
```

## Data Flow

### Scenario 1: Baseline Greedy Heuristic

```
Exogenous Data (Weather, Demand, Tariffs)
         ↓
EstateBaselineSimulator.run()
         ↓
    [For each day]:
    ├─→ BaselineSimulator.run_one_day()
    │    ├─→ For each home:
    │    │    ├─→ HouseholdModel.step() ×48 timesteps/day
    │    │    │    Input:  temp, irradiance, demand, tariff, carbon
    │    │    │    Process: Solar gen, Battery SOC, EV charge, Net load
    │    │    │    Output: net_load_kw, cost, CO₂
    │    │    └─→ Greedy rules (EV 3.6 kW, battery discharge 17:00-20:00)
    │    └─→ Accumulate costs, peaks, CO₂
    └─→ Export DataFrame: timestamp, home_id, demand, generation, cost, ...
         ↓
Results CSV: simulation_results_baseline.csv
```

### Scenario 2: MILP Optimization

```
Exogenous Data + Home Configs
         ↓
EstateOptimizer.optimize()
         ↓
  ┌─────────────────────────────────────┐
  │  For each 48-hour rolling window:   │
  ├─────────────────────────────────────┤
  │  Build MILP model:                  │
  │  ├─ Decision variables:             │
  │  │  • battery_charge(t) ∀t,home     │
  │  │  • battery_discharge(t) ∀t,home  │
  │  │  • ev_charge(t) ∀t,home          │
  │  │  • import/export(t) ∀t,estate    │
  │  └─ Constraints:                    │
  │     • Battery SOC dynamics          │
  │     • EV charging deadline          │
  │     • Power limits (C/D rates)      │
  │     • No simultaneous C+D           │
  │     • Transformer limit (aggregate) │
  │  ├─ Objective:                      │
  │  │  Min: cost + 1000×Tx_stress      │
  │  │       + volatility + carbon      │
  │  └─ Solve (CBC, 60s, 0.1% gap)      │
  │                                      │
  │  Extract optimal control actions    │
  │  (battery_charge_kw, ev_charge_kw)  │
  └─────────────────────────────────────┘
         ↓
  [Simulate with optimized controls]:
  ├─→ For each home, apply control actions
  │    └─→ HouseholdModel.step() with optimized power setpoints
  └─→ Measure outcomes (cost, peak, CO₂)
         ↓
Results CSV: simulation_results_optimized.csv
```

## Class Hierarchy & Responsibilities

### Core Physics Models

```python
HouseholdConfig (dataclass)
  - pv_capacity_kwp: 4.0
  - battery_capacity_kwh: 8.0
  - ev_charger_rating_kw: 3.6
  - heat_pump_capacity_kw: 3.0
  - [22 parameters total]

HouseholdState (dataclass)
  - timestamp, home_id
  - pv_generation_kw, demand_total_kw
  - battery_soc_kwh, ev_soc_kwh, ev_present
  - cumulative_cost_£, cumulative_co2_kg
  - [30+ state variables]

HouseholdModel
  - config: HouseholdConfig
  - state: HouseholdState
  - Methods:
    • step(temp, irr, demand, tariff, carbon, ...) → net_load_kw
    • _update_solar_generation() - Temperature-derated PV model
    • _update_battery_soc() - 92% charge, 95% discharge eff
    • _update_ev_soc() - EV charging with deadline constraint
    • _check_constraints() - Enforce power/SOC limits
    • _update_metrics() - Accumulate KPIs
```

### Simulation Engines

```python
BaselineSimulator
  - Simple greedy rules per home
  - EV: charge at charger limit (3.6 kW)
  - Battery: discharge during peak hours only
  - Solar: export all excess

EstateBaselineSimulator
  - Runs BaselineSimulator across all homes & days
  - Aggregates KPIs (cost, peak, CO₂)
  - Output: DataFrame with per-home, per-timestep results

OptimizationConfig
  - solver_time_limit_seconds: 60
  - objective_weight_cost: 1.0
  - objective_weight_transformer_stress: 1000.0
  - objective_weight_volatility_penalty: 10.0
  - [solver & objective parameters]

MILPOptimizer (per-home MILP solver)
  - Formulates single-home optimization problem
  - OR-Tools solver interface
  - Methods:
    • optimize_household(home_id, data, horizon=48h)
      → control dict {t: {actions}}

EstateOptimizer
  - Multi-home coordination wrapper
  - Can invoke MILPOptimizer per-home or unified estate-wide MILP
  - Methods:
    • optimize() → DataFrame with control actions applied
```

### Metrics & Analysis

```python
CostAnalyzer (static methods per scenario)
  • calculate_total_cost(results_df) → £
  • calculate_unit_cost(results_df) → £/kWh

PeakAnalyzer
  • calculate_estate_peak_load(results_df) → kW
  • calculate_peak_percentile(results_df, 95) → kW
  • calculate_transformer_headroom() → kW
  • calculate_overload_frequency() → timesteps

CarbonAnalyzer
  • calculate_total_emissions(results_df) → kg CO₂
  • calculate_emissions_intensity() → gCO₂/kWh

TransformerAnalyzer
  • calculate_transformer_upgrade_avoidance(baseline_peak, opt_peak, ...)
    → {upgrade_avoided: bool, financial_value_£: float}

MetricsCalculator
  • calculate_scenario_kpis(results_df, name) → Dict
    {total_cost, peak, volatility, emissions, headroom, ...}
  • calculate_comparison_metrics(baseline_kpis, opt_kpis)
    → {cost_reduction_£, peak_reduction_%, upgrade_avoidance_£, ...}

StatisticalValidator
  • monte_carlo_confidence_interval(values) → CI 95%
  • energy_balance_check(results_df) → violation rate %
```

### Orchestration

```python
EstateSimulator (Orchestrator)
  - num_homes, num_days, transformer_capacity_kw
  - _generate_home_configs() - Create N household configs
  - generate_simulation_inputs() - Create synthetic data
  - run_baseline_scenario() - Execute greedy baseline
  - run_optimization_scenario() - Execute MILP optimization
  - calculate_metrics() - Compare scenarios
  - validate_results() - Energy balance, confidence intervals
  - run_full_simulation() - Complete workflow
```

## Data Structures

### Simulation Input Data

```python
pd.DataFrame with columns:
  timestamp (datetime64)
  home_id (str)
  weather_temperature_celsius (float)
  weather_irradiance_w_per_m2 (float)
  demand_total_kw (float)           # Baseline demand (no response)
  tariff_price_£_per_kwh (float)   # Electricity price
  carbon_intensity_g_per_kwh (float) # Grid carbon intensity
  ev_arrival_time (datetime64)       # If EV arriving today
  ev_departure_time (datetime64)
  ev_required_energy_kwh (float)
  [Generated by data/generators.py]
```

### Baseline Results Output

```python
pd.DataFrame with columns:
  timestamp, home_id
  demand_total_kw
  pv_generation_kw
  battery_charge_kw, battery_discharge_kw
  battery_soc_kwh
  ev_charge_kw, ev_soc_kwh, ev_present
  heat_pump_output_kw
  net_load_kw                # Total import/export
  import_power_kw, export_power_kw
  cumulative_cost_£
  cumulative_co2_kg
  [Produced by BaselineSimulator]
```

### Optimization Results Output

```python
Similar to baseline, but with:
  Optimized control actions applied (battery_charge_kw etc.)
  Typically lower cumulative_cost_£ and cumulative_co2_kg
  Lower peak net_load_kw
  [Produced by EstateOptimizer]
```

### Metrics Output

```python
Dict with:
  baseline_kpis: {
    'total_cost_£': 3000,
    'estate_peak_kw': 261.5,
    'peak_95th_percentile_kw': 250,
    'total_co2_kg': 8000,
    'load_volatility_std_kw': 45,
    ...
  }
  optimized_kpis: { ... similar keys ... }
  comparison: {
    'cost_reduction_£': 200,
    'cost_reduction_pct': 6.7,
    'peak_reduction_kw': 47.8,
    'peak_reduction_pct': 18.3,
    'transformer_upgrade_avoidance_£': 250000,
    'co2_reduction_kg': 892,
    ...
  }
  validation: {
    'baseline_energy_balance': {'overall_violation_rate_pct': 0.3, ...},
    'optimization_energy_balance': {...},
    'baseline_cost_ci': {...},
    'optimized_cost_ci': {...},
  }
```

## MILP Formulation (Detailed)

### Decision Variables (per home, per timestep)

```
binary_charge[t] ∈ {0,1}        | Prevents simultaneous C+D
battery_charge_kw[t] ≥ 0         | Battery charging power [kW]
battery_discharge_kw[t] ≥ 0      | Battery discharging power [kW]
battery_soc_kwh[t] ∈ [0, E_max]  | Battery state of charge [kWh]

ev_charge_kw[t] ≥ 0             | EV charging power [kW]
ev_soc_kwh[t] ∈ [0, E_EV_max]   | EV state of charge [kWh]

import_kw[t] ≥ 0                | Power imported from grid [kW]
export_kw[t] ≥ 0                | Power exported to grid [kW]

heat_pump_output_kw[t] ≥ 0      | Heat pump output [kW] (optional)
```

### Constraints

**1. Battery Dynamics:**
```
SOC(t+1) = SOC(t) + ηc·Pc(t)·Δt − Pd(t)·Δt/ηd − Sloss
```

**2. No Simultaneous Charge + Discharge:**
```
Pc(t) ≤ P_max · binary_charge[t]
Pd(t) ≤ P_max · (1 − binary_charge[t])
```

**3. EV Arrival/Departure:**
```
If EV not present:  ev_charge_kw[t] = 0
If EV present:      EV charging deadline satisfied
                    SOC_EV(t_departure) ≥ E_required
```

**4. Power Balance (per timestep, per home):**
```
Import(t) − Export(t) = Demand(t) + Pc(t) + Pev_c(t) − PV(t) − Pd(t)
```

**5. Transformer Hard Constraint (estate-wide):**
```
ΣImport(i,t) − ΣExport(i,t) ≤ Tx_capacity ∀t
  (aggregate net load across all homes ≤ limit)
```

**6. SOC Bounds:**
```
0 ≤ SOC(t) ≤ E_max
SOC(t) ≥ E_min  (maintain minimum charge)
```

### Objective Function

```
Minimize:

  Z = Cost + TxStress + VolatilityPenalty + BatteryDeg + Carbon

  Cost = Σ_t Σ_i [Import(i,t) × Tariff(t) × Δt]

  TxStress = w_tx · Σ_t max(0, ΣNetLoad(t) − Tx_limit)²
           = 1000 × Σ_t max(0, ΣLoad(t) − 100)²

  VolatilityPenalty = w_vol · Σ_t |dP/dt|
                    = 10 × Σ_t |Import(t+1) − Import(t)|

  BatteryDeg = w_bdeg · Σ_t Σ_i [Pc(i,t) + Pd(i,t)] × £35/MWh
             = 1 × Σ cost of battery wear

  Carbon = w_carbon · Σ_t Σ_i [Import(i,t) × CI(t)]
         = 0.01 × Σ CO₂ impact
```

**Weights (user-configurable):**
| Term | Weight | Rationale |
|------|--------|-----------|
| Cost | 1.0 | Unit cost (£) |
| TxStress | 1000 | **Primary leverage point** |
| VolatilityPenalty | 10 | Feeder voltage stability |
| BatteryDeg | 1.0 | Asset longevity (£/cycle) |
| Carbon | 0.01 | Environmental (minor weight) |

## Solver Configuration

```python
OptimizationConfig(
    solver='CBC',                           # OR-Tools backend
    solver_time_limit_seconds=60,           # Max compute time
    solver_relative_gap_tolerance=0.001,    # 0.1% optimality
    solver_log_search=False,                # Suppress verbose output
    
    # Objective weights
    objective_weight_cost=1.0,
    objective_weight_transformer_stress=1000.0,
    objective_weight_volatility_penalty=10.0,
    objective_weight_battery_degradation=1.0,
    objective_weight_carbon_cost=0.01,
)
```

## Performance Characteristics

### Time Complexity

| Component | Complexity | Notes |
|-----------|-----------|-------|
| Baseline (1 home, 1 day) | O(48) | 48 × 30-min steps |
| Baseline (N homes, D days) | O(N × D × 48) | Linear scaling |
| MILP (1 home, 48 hours) | O(k²) | k=96 variables, ~1-3 sec |
| MILP (N homes, 48 hours) | O(N × k²) | With multi-home coordination |

### Space Complexity

| Scenario | Decision Variables | Constraints | Memory (MB) |
|----------|-------------------|-------------|-----------|
| 1 home, 48h | ~200 | ~150 | 5 |
| 50 homes, 48h | ~10,000 | ~7,500 | 120 |
| 100 homes, 48h | ~20,000 | ~15,000 | 240 |

### Solver Performance

```
Scenario: 50 homes, 48-hour rolling window,
          transformer limit = 100 kW, cost minimization

Metrics:
  Setup time:     1.2 sec
  Solving time:   12.5 sec  (CBC, default settings)
  Extracting:     0.3 sec
  Total:          ~14 sec per window

Typical Result:
  Peak reduction: 18-22%
  Cost reduction: 5-8%
  Gap tolerance: <0.1% (near-optimal)
```

## Error Handling

### Graceful Degradation

```
If optimization fails:
  ├─ Solver timeout → Return greedy baseline control
  ├─ Infeasible problem → Relax constraint, retry
  └─ Solver error → Log & use baseline

If data validation fails:
  ├─ Missing columns → Inject defaults
  ├─ Out-of-range values → Clip to bounds
  └─ Constraint violation → Log warning, continue
```

### Energy Conservation Validation

```
Daily balance check: |LHS − RHS| / LHS < 0.5%
  where:
    LHS = Import + PV
    RHS = Demand + Export + ΔSOCbattery
  
If fails → Log warning (may indicate bug in physics model)
```

---

## Phase 2-4 Roadmap

| Phase | Duration | Key Features |
|-------|----------|--------------|
| Phase 1 (✓ Complete) | Jan 2024 | Core physics + baseline + MILP |
| Phase 2 (Mar 2024) | 6 weeks | Streamlit dashboard, multiple feeders |
| Phase 3 (May 2024) | 8 weeks | Stochastic optimization, demand flexibility |
| Phase 4 (Aug 2024) | 6 weeks | Distribution OPF, real-time control |

---

Last updated: 2024-01
