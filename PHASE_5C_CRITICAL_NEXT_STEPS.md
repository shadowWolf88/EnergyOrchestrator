# ⚡ CRITICAL NEXT STEPS: Phase 5C Hardening Sprint

**Status Date:** February 25, 2026  
**Deadline for Production Pilot:** March 4, 2026 (7 days)  
**Team:** 1 engineer, 8-10 days of work

---

## 🔴 BLOCKERS: MUST FIX THIS WEEK

### 1. **ENERGY BALANCE VALIDATION STATUS** [Priority: CRITICAL]

**Current Issue:** 
- Documentation claims validation passes, but actual implementation may have bugs
- Impact: If validation fails, results are unverifiable for DNO/regulatory use

**Action Items:**
```
Task 1: RUN the simulator and capture actual validation output
  → `python -m energy_orchestrator_sim.simulation.estate_simulator`
  → Check logs for: "✓ Energy balance check PASSED" OR "✗ FAILED"
  
Task 2: If FAILS, debug the energy_balance_check() function
  → Suspected issue: Daily balance equation has floating-point errors
  → Likely cause: Battery standing loss not accounted properly
  → Fix: Add explicit standing loss term to balance equation
  
Task 3: If PASSES, verify calculation is correct
  → Check against manual example (1 home, 1 day)
  → Validate that import + PV = demand + export + Δbattery SOC
  → Document actual tolerance achieved
```

**Time Estimate:** 2-4 hours investigation + fix

**Success Criteria:**
- [ ] Actual run log shows "✓ Energy balance check PASSED"
- [ ] Validation tolerance documented (current claim: <0.5%, typical: <0.1%)
- [ ] Test case added to prevent regression

---

### 2. **REAL DATA API INTEGRATION** [Priority: HIGH]

**Current Issue:**
- API stubs exist but no live data
- Cannot validate against real ESO/Octopus data
- Blocks credibility with DNOs

**Action Items:**

**2a. ESO Carbon Intensity (FREE - no auth needed)**
```python
# File: energy_orchestrator_sim/data/realtime_eso_api.py

# Current (stub):
def get_current_intensity(self) -> Optional[float]:
    return None  # Placeholder

# Action: Implement using free Electricity Maps API
# Endpoint: https://api.electricitymap.org/v3/carbon-intensity/latest?zone=GB
# No authentication required for basic tier (50 req/day)

# Test with:
curl "https://api.electricitymap.org/v3/carbon-intensity/latest?zone=GB"
```

**Time:** 1 hour

**2b. Octopus Energy Tariff (PUBLIC - no auth needed)**
```python
# Partial implementation exists - just needs caching

# File: energy_orchestrator_sim/data/realtime_eso_api.py

# Current state: GET /v1/products endpoint works
# Action: Add caching (TariffsPerGBpDaily.csv caches for 24h)
#         Add error handling (retry on 429, timeout after 5s)

# Test with:
curl "https://api.octopus.energy/v1/products/AGILE-22-11-01/rates/?page_size=1500"
```

**Time:** 1.5 hours

**2c. OpenWeatherMap Weather Forecast**
```python
# Requires API key (free tier: 1000 req/day, 5-day forecast)

# File: energy_orchestrator_sim/data/realtime_eso_api.py

# Current: Stub only

# Action: 
#   1. Add config parameter for API key
#   2. Implement GET /forecast.json for UK postcode
#   3. Parse response → hourly irradiance estimate (cloud %)
#   4. Cache for 3 hours

# Setup:
#   1. User signs up at https://openweathermap.org/api (free)
#   2. Adds API key to .env: OPENWEATHER_API_KEY=xxx
#   3. System loads via: os.getenv('OPENWEATHER_API_KEY')

# Test with (replace KEY):
curl "https://api.openweathermap.org/data/2.5/forecast?q=London&appid=KEY"
```

**Time:** 2 hours

**Subtotal:** 4.5 hours for all 3 APIs

**Success Criteria:**
- [ ] ESO live intensity data shows in logs
- [ ] Octopus Agile rates loaded and cached
- [ ] OpenWeatherMap forecast shown in dashboard
- [ ] Fallback to synthetic data if API fails
- [ ] Unit tests mock API responses

---

### 3. **UNCERTAINTY QUANTIFICATION** [Priority: HIGH]

**Current Issue:**
- Results show "5% peak reduction" with no confidence interval
- Cannot tell DNO: "5% reduction with 95% confidence" vs "could be 2-8%"
- Risk-averse regulators won't fund without this

**Action Items:**

```python
# Current state: StatisticalValidator.monte_carlo_confidence_interval() exists
# Status: Implemented but not used in results reporting

# Action 1: Wire it into estate_simulator.py results
#   File: simulation/estate_simulator.py
#   Add to calculate_metrics():
#     cost_ci = validator.monte_carlo_confidence_interval(
#         baseline_costs, confidence=0.95, num_bootstrap=500
#     )
#     peak_ci = validator.monte_carlo_confidence_interval(
#         baseline_peaks, confidence=0.95, num_bootstrap=500
#     )
#   Store in: comparison['cost_reduction_ci'], comparison['peak_reduction_ci']

# Action 2: Sensitivity analysis
#   Create grid: PV_capacity ±30%, demand ±20%, tariff ±15%
#   Run 8 scenarios, observe cost/peak ranges
#   Document in dashboard

# Action 3: Report in CSV exports
#   Add columns: cost_lower_95ci, cost_upper_95ci, peak_lower_95ci, peak_upper_95ci
```

**Time:** 3 hours

**Success Criteria:**
- [ ] Configuration section shows "Cost reduction: £1,847 [£1,520 - £2,100 at 95% CI]"
- [ ] Peak reduction shows confidence interval
- [ ] Sensitivity heatmap in dashboard (PV ±%, demand ±% grid)
- [ ] CSV exports include CI columns

---

## 🟡 QUICK WINS: EASY HIGH-VALUE (2-3 hours each)

### 4. **2-Home Coordination Patch** [Priority: MEDIUM → Quick Peak Gain]

**Current Issue:**
- Per-home independent optimization caps peak reduction at ~5% (MVP heuristic)
- Could get 8-12% immediately with just 2-home coordination

**Action Item:**
```python
# File: simulation/optimization_engine.py

# Current: MILPOptimizer.optimize_household(home_id, horizon_hours=48)
#         Each home optimized independently

# Quick patch: Optimize pairs of homes together
class PairOptimizer:
    def optimize_pair(self, home1_data, home2_data, horizon_hours=48):
        """
        Combine two homes' MILP problem:
        - Shared transformer constraint: import1 + import2 < transformer_capacity
        - Separate cost objectives (each home minimizes own cost)
        - Allows peer loads to offset (e.g., home1 charges when home2 discharges)
        """
        # Similar MILPOptimizer structure, just with 2x variables + 1 shared constraint
        # Expected peak reduction: 8-12% vs current 5%

# Usage:
#   pairs = [(homes[i], homes[i+1]) for i in range(0, len(homes), 2)]
#   for pair in pairs:
#       pair_opt = PairOptimizer()
#       results[pair[0]].update(pair_opt.optimize_pair(...))
```

**Expected Outcome:**
- Peak reduction: 5% → 8-12%
- Solved in same time (parallel processing)
- Proof-of-concept for Phase 6B multi-home MILP

**Time:** 2-3 hours

---

### 5. **Tariff Recommendation Engine** [Priority: MEDIUM → Customer Value]

**Action Item:**
```python
# File: simulation/estate_simulator.py (new method)

def compare_tariffs(self, home_ids: List[int] = None) -> pd.DataFrame:
    """
    For each tariff strategy (Flat, Economy 7, Agile, Custom),
    run simulation and return cost comparison.
    """
    tariffs = ['flat_40p', 'economy7_24h', 'agile_variable']
    results = []
    
    for tariff_name in tariffs:
        # Re-run simulation with different tariff
        self.tariff_manager.set_tariff_strategy(tariff_name)
        cost = self.simulate_baseline(use_tariff=tariff_name)
        
        results.append({
            'tariff': tariff_name,
            'annual_cost_gbp': cost * 12,  # Scale 30-day sample
            'peak_kw': self.baseline_results['net_load_kw'].max(),
            'carbon_kg': self.baseline_results['carbon_cumulative_kg'].iloc[-1],
            'complexity': ['simple', 'medium', 'high'][len(tariffs.index(tariff_name))],
        })
    
    return pd.DataFrame(results).sort_values('annual_cost_gbp')

# Dashboard adds new page:
#   "Tariff Analysis" → Comparison table + recommendation
#   "Switch tariff from {current} to {recommended} to save £{savings}"
```

**Expected Outcome:**
- Identify best tariff for each home (potential 8-15% savings if on wrong tariff)
- Differentiated feature vs competitors
- Customer-facing value prop

**Time:** 2-3 hours

---

### 6. **Geospatial Visualization** [Priority: MEDIUM → Demo Impact]

**Action Item:**
```python
# File: pages/6_🗺️_Network_Topology.py (NEW)

import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

def show_network_map():
    """
    Interactive map of estate:
    - Homes as markers: color by battery SOC (green=full, red=empty)
    - Transformer as central hub
    - Power flow animation (thickness/color by flow direction)
    - Heatmap overlay of peak utilization by hour
    """
    
    # Get estate boundary (bounding box of home coordinates)
    # For demo: assume homes within 1km radius of transformer
    transformer_lat, transformer_lon = 51.5074, -0.1278  # London example
    
    m = folium.Map(
        location=[transformer_lat, transformer_lon],
        zoom_start=15
    )
    
    # Add homes as circles (size = battery capacity, color = SOC %)
    for home in self.homes:
        battery_soc_pct = home.state.battery_soc_kwh / home.config.battery_capacity_kwh * 100
        color = get_color_for_soc(battery_soc_pct)  # Green → Red gradient
        
        folium.CircleMarker(
            location=[home.lat, home.lon],
            radius=10,
            popup=f"Home {home.id}: Battery {battery_soc_pct:.0f}%",
            color=color,
            fill=True,
            fillOpacity=0.7
        ).add_to(m)
    
    # Add transformer as central hub
    folium.CircleMarker(
        location=[transformer_lat, transformer_lon],
        radius=20,
        popup="Distribution Transformer 10/0.4kV",
        color='purple',
    ).add_to(m)
    
    st_folium(m, width=800, height=600)

show_network_map()
```

**Expected Outcome:**
- Wow-factor for demos + regulatory presentations
- Visual understanding of network topology
- Quick identification of problem homes

**Time:** 2-3 hours

---

## 📊 PRIORITY MATRIX: 7-Day Sprint Schedule

```
Day 1-2:
  ✓ Fix energy balance validation [4 hrs]
  ✓ Implement 3 real data APIs [4 hrs]

Day 3-4:
  ✓ Uncertainty quantification [3 hrs]
  ✓ 2-home coordination patch [3 hrs]

Day 5:
  ✓ Tariff recommendation engine [2 hrs]
  ✓ Geospatial visualization [2 hrs]

Day 6-7:
  ✓ Integration testing
  ✓ Documentation updates
  ✓ Pilot readiness review
```

**Total Time:** ~24 hours of focused engineering

---

## 🎯 SUCCESS CRITERIA FOR PHASE 5C COMPLETION

- [ ] Energy balance validation **CONFIRMED PASSING** (with tolerance documented)
- [ ] Real ESO Carbon Intensity API **LIVE** (shows actual GB grid intensity)
- [ ] Octopus Energy Agile tariffs **CACHED** (updates every 24h)
- [ ] OpenWeatherMap forecast **INTEGRATED** (weather updates via API)
- [ ] Uncertainty quantification **REPORTED** (cost ±95% CI in results)
- [ ] 2-home coordination **PATCHED** (peak reduction 5% → 8-12%)
- [ ] Tariff comparison **WORKING** (shows best tariff for customer)
- [ ] Geospatial dashboard **LIVE** (interactive estate map)
- [ ] All changes **TESTED** (pytest suite 200+ test cases)
- [ ] GitHub **COMMITTED** (clean main branch)

---

## 💰 POST-PHASE 5C VALUE

After these 7 days:

| Feature | Value | Timeline |
|---------|-------|----------|
| Energy validation | Credibility for regulators | Immediate |
| Real data APIs | Live vs simulated results | Immediate |
| Uncertainty bounds | Risk quantification for DNOs | Immediate |
| 2-home coord | Peak reduction 5%→12% | Immediate |
| Tariff analysis | 8-15% customer savings | Quick demo win |
| Geospatial viz | Regulatory presentations | Demo impact |

**Result:** Move from 7.5/10 → 8.5/10 production readiness ✨

---

## 📋 EXECUTION CHECKLIST

```markdown
### Setup Phase (Day 1, 2 hours)
- [ ] Checkout fresh main branch
- [ ] Review test suite structure (tests/ directory)
- [ ] Set up pytest: `pytest tests/ -v`
- [ ] Verify baseline simulation runs

### Energy Balance Fix (Day 1, 2-4 hours)
- [ ] Run estate_simulator, capture validation status
- [ ] If FAILS: Debug energy_balance_check() function
  - [ ] Add logging to daily balance equation
  - [ ] Identify missing term (battery standing loss?)
  - [ ] Fix equation + tolerance bounds
  - [ ] Add unit test to validate
- [ ] If PASSES: Document actual tolerance, add test case
- [ ] **Commit:** `git commit -m "fix: confirm energy balance validation PASS"`

### Real Data APIs (Day 2-3, 4 hours)
- [ ] ESO Carbon Intensity: Implement + test live
- [ ] Octopus Tariffs: Add caching + error handling
- [ ] OpenWeatherMap: Integrate forecast (requires API key)
- [ ] Unit tests mock API responses
- [ ] **Commit:** `git commit -m "feat: real data API integration"`

### Uncertainty Quantification (Day 4, 3 hours)
- [ ] Wire monte_carlo_confidence_interval() into results
- [ ] Add sensitivity analysis grid (3 parameters, 8 scenarios)
- [ ] Update CSV exports with CI columns
- [ ] **Commit:** `git commit -m "feat: uncertainty quantification"`

### 2-Home Coordination (Day 4, 3 hours)
- [ ] Implement PairOptimizer class
- [ ] Test peak reduction 5%→8-12%
- [ ] Add to estate_simulator
- [ ] **Commit:** `git commit -m "feat: 2-home coordination patch"`

### Quick Wins (Day 5, 2-3 hours each)
- [ ] Tariff recommendation engine → new page in dashboard
- [ ] Geospatial visualization → folium map + stream interaction
- [ ] **Commit:** `git commit -m "feat: tariff comparison & geospatial viz"`

### Integration & Testing (Day 6-7, 4 hours)
- [ ] Full simulation end-to-end with all features
- [ ] Run pytest suite (target: 200+ tests)
- [ ] Update README with new features
- [ ] **Final commit:** `git commit -m "chore: Phase 5C complete - pilot ready"`
- [ ] Prepare: Pilot launch presentation

### Deliverables
- [ ] Simulation output with all new features
- [ ] Test coverage report (pytest-cov)
- [ ] Updated documentation
- [ ] GitHub summary (7 commits, 2000+ LOC changes)
```

---

## 🚀 WHAT THIS ENABLES

Once Phase 5C complete:

✅ **DNO Credibility:** "This is validated physics with 95% confidence intervals"  
✅ **Live Validation:** "Real ESO carbon intensity, not synthetic"  
✅ **Customer Value:** "Your best tariff is Agile, saves £400/year"  
✅ **Better Optimization:** "Even simple pairwise coordination gives 12% peak reduction"  
✅ **Visual Impact:** "See your estate on an interactive map"  

**Result:** Ready for serious DNO pilot + customer acquisition

---

**Document Created:** February 25, 2026 | **Next Review:** March 4, 2026
