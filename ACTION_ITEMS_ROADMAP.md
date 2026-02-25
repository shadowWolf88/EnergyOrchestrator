# ⚡ ACTION ITEMS & IMPLEMENTATION ROADMAP
## AI Energy Orchestrator | Phase 2 Planning

---

## PRIORITY 1: CRITICAL PATHS (DO FIRST - Next 2 Weeks)

### 1.1 Error Handling Framework [HOURS: 4-6]

**What:** Wrap all data access and solver operations with proper error handling

**Files to Modify:**
- [core/household.py](energy_orchestrator_sim/core/household.py) - Line 153-172
- [simulation/baseline_engine.py](energy_orchestrator_sim/simulation/baseline_engine.py) - Line 50-70
- [simulation/optimization_engine.py](energy_orchestrator_sim/simulation/optimization_engine.py) - Line 95-120

**Implementation Steps:**

```python
# Step 1: Create error handling utility (NEW FILE)
# energy_orchestrator_sim/utils/error_handling.py

class SimulationError(Exception):
    """Base exception for simulation errors."""
    pass

class DataValidationError(SimulationError):
    """Raised when input data is invalid."""
    pass

class OptimizationError(SimulationError):
    """Raised when solver fails."""
    pass

def validate_dataframe(df, required_columns, min_rows=1):
    """Validate DataFrame has required columns and rows."""
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise DataValidationError(f"Missing columns: {missing}")
    if len(df) < min_rows:
        raise DataValidationError(f"DataFrame has {len(df)} rows, need {min_rows}")
    return df

def safe_get_value(df, col, default=0.0, row_idx=0):
    """Safely get value from DataFrame."""
    try:
        value = df.iloc[row_idx][col]
        if pd.isna(value) or np.isinf(value):
            logger.warning(f"Invalid value {value} in {col}, using default {default}")
            return default
        return float(value)
    except (KeyError, IndexError) as e:
        logger.warning(f"Cannot access {col}: {e}, using default {default}")
        return default

# Step 2: Update baseline_engine.py
# Replace line 50-70:

def run_day(self, date, weather_df, tariff_df, demand_df, carbon_df):
    try:
        validate_dataframe(weather_df, ['timestamp', 'irradiance_wm2', 'temperature_c'])
        validate_dataframe(demand_df, ['timestamp', 'demand_base_30min_kwh'])
        
        day_results = []
        for timestep_idx in range(len(weather_df)):
            try:
                irradiance = safe_get_value(weather_df, 'irradiance_wm2', 0.0, timestep_idx)
                temp = safe_get_value(weather_df, 'temperature_c', 15.0, timestep_idx)
                demand = safe_get_value(demand_df, 'demand_base_30min_kwh', 0.2, timestep_idx)
                
                # Process timestep...
                
            except Exception as e:
                logger.error(f"Timestep {timestep_idx} failed: {e}")
                continue  # Skip to next timestep instead of crashing
        
        return pd.DataFrame(day_results)
        
    except DataValidationError as e:
        logger.error(f"Data validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_day: {e}", exc_info=True)
        raise SimulationError(f"Day simulation failed: {e}")
```

**Testing:**
```bash
# Add test case to tests/test_core_models.py
def test_missing_data_column_handled_gracefully():
    weather_df = pd.DataFrame({'timestamp': [...]})  # Missing irradiance
    with pytest.raises(DataValidationError):
        baseline.run_day(date, weather_df, ...)

def test_nan_values_use_default():
    weather_df = pd.DataFrame({'irradiance_wm2': [np.nan, 100.0]})
    value = safe_get_value(weather_df, 'irradiance_wm2', default=50.0, row_idx=0)
    assert value == 50.0
```

---

### 1.2 Solver Fallback Strategy [HOURS: 2-3]

**What:** When MILP optimization times out or fails, gracefully fall back to baseline control

**File:** [simulation/optimization_engine.py](energy_orchestrator_sim/simulation/optimization_engine.py) - Line 95-125

**Implementation:**

```python
def optimize_household(self, home, horizon_hours=48, **kwargs):
    """Optimize household with graceful fallback."""
    try:
        # Attempt MILP optimization
        control_dict, status = self._solve_milp(home, horizon_hours, **kwargs)
        
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            self.logger.info(f"Optimization successful for {home.config.home_id}: status={status}")
            return control_dict, status
        else:
            self.logger.warning(f"Optimization failed (status={status}), falling back to baseline")
            return self._get_baseline_control(home, horizon_hours), status
            
    except Exception as e:
        self.logger.error(f"Solver error: {e}, using baseline control")
        return self._get_baseline_control(home, horizon_hours), None

def _get_baseline_control(self, home, horizon_hours):
    """Generate baseline greedy control (fallback)."""
    # Reuse logic from BaselineSimulator
    num_timesteps = int((horizon_hours * 60) / 30)
    control = {}
    
    for t in range(num_timesteps):
        control[t] = {
            'battery_charge_kw': 0.0,
            'battery_discharge_kw': 0.0,
            'ev_charge_kw': 3.6 if home.state.ev_present else 0.0,
        }
        
        # Simple discharge rule: evening peak only
        if 17 <= (t * 0.5) % 24 < 20 and home.state.battery_soc_kwh > 3.0:
            control[t]['battery_discharge_kw'] = 2.0
    
    return control
```

**Testing:**
```bash
def test_optimization_fallback_to_baseline():
    """If solver fails, should return baseline control."""
    # Create config with very tight time limit
    config = OptimizationConfig(time_limit_seconds=0.001)
    opt = MILPOptimizer(config)
    
    control, status = opt.optimize_household(home, horizon_hours=48)
    
    # Should have non-empty control dict
    assert len(control) > 0
    assert all('battery_charge_kw' in c for c in control.values())
```

---

### 1.3 Configuration System [HOURS: 6-8]

**What:** Move hardcoded values to YAML config files with validation

**Files to Create:**

```yaml
# energy_orchestrator_sim/config/defaults.yaml

households:
  # Standard UK 3-bedroom house with solar + battery
  pv_capacity_kwp: 4.0
  battery_capacity_kwh: 8.0
  battery_power_kw: 5.0
  battery_efficiency_charge: 0.92
  battery_efficiency_discharge: 0.95
  battery_standing_loss_pct_per_hour: 0.1
  ev_charger_rating_kw: 3.6
  ev_battery_capacity_kwh: 60.0
  heat_pump_capacity_kw: 3.0
  heat_pump_cop: 3.5

estate:
  transformer_capacity_kw: 100.0
  transformer_upgrade_cost_gbp: 250000.0
  num_homes: 50
  num_days: 30

optimization:
  solver_type: CBC
  time_limit_seconds: 60
  num_threads: -1  # Use all available
  optimality_gap_pct: 0.1
  
  weights:
    cost: 1.0
    transformer_stress: 1000.0
    volatility_penalty: 10.0
    carbon: 0.01
    battery_degradation: 1.0

baseline_control:
  ev_charge_kw: 3.6  # Half of max
  battery_discharge_evening_start_hour: 17
  battery_discharge_evening_end_hour: 20
  battery_discharge_peak_threshold_pct: 30
  heat_pump_preheating_start_hour: 22
  heat_pump_preheating_end_hour: 6

data:
  start_date: '2024-01-01'
  season: 'winter'
  tariff_type: 'agile'
  timezone: 'Europe/London'
```

```python
# energy_orchestrator_sim/config/loader.py

import yaml
from pathlib import Path
from typing import Dict, Any
import os

class ConfigLoader:
    """Load and validate configuration from YAML files."""
    
    @staticmethod
    def load_config(config_name='defaults') -> Dict[str, Any]:
        """Load configuration file."""
        config_path = Path(__file__).parent / f'{config_name}.yaml'
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        # Override with environment variables (for deployment)
        config = ConfigLoader._apply_env_overrides(config)
        
        return config
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """Override config values with environment variables."""
        # Pattern: ENERGY_ORCHESTRATOR_SECTION_KEY
        for key in os.environ:
            if key.startswith('ENERGY_'):
                parts = key.split('_')[2:]  # Skip 'ENERGY_ORCHESTRATOR'
                section, param = parts[0].lower(), '_'.join(parts[1:]).lower()
                
                if section in config:
                    try:
                        # Try to convert to appropriate type
                        value = os.environ[key]
                        if value.lower() in ('true', 'false'):
                            config[section][param] = value.lower() == 'true'
                        elif value.replace('.', '').replace('-', '').isdigit():
                            config[section][param] = float(value) if '.' in value else int(value)
                        else:
                            config[section][param] = value
                    except Exception as e:
                        print(f"Warning: Could not parse {key}: {e}")
        
        return config

# Usage in estate_simulator.py:
from config.loader import ConfigLoader

config = ConfigLoader.load_config('defaults')

simulator = EstateSimulator(
    num_homes=config['estate']['num_homes'],
    num_days=config['estate']['num_days'],
    transformer_capacity_kw=config['estate']['transformer_capacity_kw'],
)
```

**Testing:**
```bash
def test_config_loads_defaults():
    config = ConfigLoader.load_config('defaults')
    assert config['households']['pv_capacity_kwp'] == 4.0
    assert config['estate']['transformer_capacity_kw'] == 100.0

def test_config_env_override():
    os.environ['ENERGY_HOUSEHOLDS_PV_CAPACITY'] = '6.0'
    config = ConfigLoader.load_config('defaults')
    assert config['households']['pv_capacity_kwp'] == 6.0
    del os.environ['ENERGY_HOUSEHOLDS_PV_CAPACITY']
```

---

## PRIORITY 2: HIGH-IMPACT FEATURES (Next 3-4 Weeks)

### 2.1 Complete Streamlit Dashboard [HOURS: 16-20]

**Objective:** Make dashboard fully functional with real data loading and interactivity

**Status Check:** Currently only ~50 lines of Overview.py implemented, need full 5 pages

**Implementation Plan:**

```python
# pages/1_📊_Overview.py (Complete rewrite - 40 lines → 200+ lines)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")

@st.cache_data
def load_results():
    """Load baseline and optimized results."""
    baseline = pd.read_csv('simulation_results_baseline.csv')
    optimized = pd.read_csv('simulation_results_optimized.csv')
    return baseline, optimized

try:
    baseline_df, optimized_df = load_results()
except FileNotFoundError:
    st.error("⚠️ Results not found. Run `python main.py` first")
    st.stop()

# KPI Metrics
col1, col2, col3, col4 = st.columns(4)

baseline_peak = baseline_df['net_load_kw'].max() if 'net_load_kw' in baseline_df else 0
optimized_peak = optimized_df['net_load_kw'].max() if 'net_load_kw' in optimized_df else 0
peak_reduction = baseline_peak - optimized_peak
peak_reduction_pct = 100 * peak_reduction / baseline_peak if baseline_peak > 0 else 0

col1.metric(
    "Peak Reduction",
    f"{peak_reduction:.1f} kW",
    f"{peak_reduction_pct:.1f}%",
    delta_color="inverse"
)

baseline_cost = baseline_df['cumulative_cost_gbp'].iloc[-1] if 'cumulative_cost_gbp' in baseline_df else 0
optimized_cost = optimized_df['cumulative_cost_gbp'].iloc[-1] if 'cumulative_cost_gbp' in optimized_df else 0
cost_savings = baseline_cost - optimized_cost
cost_savings_pct = 100 * cost_savings / baseline_cost if baseline_cost > 0 else 0

col2.metric(
    "Cost Savings",
    f"£{cost_savings:.0f}",
    f"{cost_savings_pct:.1f}%",
    delta_color="inverse"
)

baseline_co2 = baseline_df['cumulative_co2_kg'].iloc[-1] if 'cumulative_co2_kg' in baseline_df else 0
optimized_co2 = optimized_df['cumulative_co2_kg'].iloc[-1] if 'cumulative_co2_kg' in optimized_df else 0
co2_reduction = baseline_co2 - optimized_co2

col3.metric(
    "CO₂ Reduction",
    f"{co2_reduction:.0f} kg",
    f"{100*co2_reduction/baseline_co2 if baseline_co2>0 else 0:.1f}%",
    delta_color="inverse"
)

col4.metric(
    "Homes Analyzed",
    baseline_df['home_id'].nunique(),
    "50",
    delta_color="off"
)

# Chart 1: Peak Load Comparison
st.subheader("Peak Load Reduction")
col1, col2 = st.columns(2)

with col1:
    baseline_by_ts = baseline_df.groupby('timestamp')['net_load_kw'].sum()
    optimized_by_ts = optimized_df.groupby('timestamp')['net_load_kw'].sum()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=baseline_by_ts.index, y=baseline_by_ts, name='Baseline', mode='lines'))
    fig.add_trace(go.Scatter(x=optimized_by_ts.index, y=optimized_by_ts, name='Optimized', mode='lines'))
    fig.update_layout(title="Estate Net Load Over Time", xaxis_title="Time", yaxis_title="Power (kW)")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    categories = ['Peak Load', 'Cost', 'CO₂ Emissions']
    baseline_vals = [baseline_peak, baseline_cost, baseline_co2]
    optimized_vals = [optimized_peak, optimized_cost, optimized_co2]
    
    fig = go.Figure(data=[
        go.Bar(name='Baseline', x=categories, y=baseline_vals),
        go.Bar(name='Optimized', x=categories, y=optimized_vals)
    ])
    fig.update_layout(barmode='group', title="KPI Comparison", yaxis_title="Value")
    st.plotly_chart(fig, use_container_width=True)

# Chart 2: Cost Breakdown
st.subheader("Cost Analysis")
baseline_total = baseline_df.groupby('home_id')['cumulative_cost_gbp'].last()
optimized_total = optimized_df.groupby('home_id')['cumulative_cost_gbp'].last()

fig = px.box(
    x=['Baseline', 'Baseline', 'Optimized', 'Optimized'],
    y=list(baseline_total) + list(optimized_total),
    title="Cost Distribution Across Homes"
)
st.plotly_chart(fig, use_container_width=True)

# Chart 3: Transformer Headroom
st.subheader("Transformer Utilization")
st.metric(
    "Baseline Peak vs Capacity",
    f"{baseline_peak:.0f} kW / 100 kW",
    f"Capacity: {max(0, 100 - baseline_peak):.0f} kW remaining"
)
st.metric(
    "Optimized Peak vs Capacity",
    f"{optimized_peak:.0f} kW / 100 kW",
    f"Upgrade: {'AVOIDED ✓' if optimized_peak <= 100 else 'REQUIRED'}",
)

# Data quality check
st.info(f"✓ Data loaded: {len(baseline_df):,} rows | {baseline_df['home_id'].nunique()} homes | {(baseline_df['timestamp'].max() - baseline_df['timestamp'].min()).days} days")
```

**Files to Create/Update:**
- [pages/1_📊_Overview.py](energy_orchestrator_sim/pages/1_📊_Overview.py) - 50 lines → 250 lines
- [pages/2_🏠_Household_Detail.py](energy_orchestrator_sim/pages/2_🏠_Household_Detail.py) - New
- [pages/3_📈_Optimization.py](energy_orchestrator_sim/pages/3_📈_Optimization.py) - New
- [pages/4_💰_Cost_Analysis.py](energy_orchestrator_sim/pages/4_💰_Cost_Analysis.py) - New
- [pages/5_💨_Carbon_Impact.py](energy_orchestrator_sim/pages/5_💨_Carbon_Impact.py) - New

---

### 2.2 Add Edge Case Unit Tests [HOURS: 8-10]

**What:** Add parameterized tests for boundary conditions and error paths

```python
# tests/test_core_models.py (ADD THESE)

class TestEdgeCases:
    """Test boundary conditions and unusual scenarios."""
    
    def test_ev_arrives_near_departure(self, model):
        """EV with insufficient charging time should warn and not strain battery."""
        model.reset_ev(
            arrival=datetime(2024, 1, 15, 23, 45),
            departure=datetime(2024, 1, 16, 0, 15),
            required_energy_kwh=60.0  # Impossible
        )
        
        # Try to charge at max rate
        net_load = model.step(
            t=datetime(2024, 1, 15, 23, 45),
            irradiance_wm2=0,
            temperature_c=5,
            demand_base_kwh=0.2,
            tariff_price=0.35,
            carbon_intensity=300,
            control={'ev_charge_kw': 7.4}
        )
        
        # Should charge what it can in 30 min
        expected_charge = 7.4 * 0.5 * 0.95  # Power × time × efficiency
        assert model.state.ev_soc_kwh <= expected_charge + 0.01
    
    @pytest.mark.parametrize("irradiance,temp,expected_min", [
        (0, 25, 0.0),        # Night
        (1000, 0, 0.8),      # Very cold
        (1000, 60, 0.5),     # Very hot
        (500, 25, 0.4),      # Partial cloud
    ])
    def test_solar_under_various_conditions(self, model, irradiance, temp, expected_min):
        """Solar output should degrade with temperature and clouds."""
        model._update_solar_generation(irradiance, temp)
        assert model.state.pv_generation_kw >= expected_min
    
    def test_battery_simultaneous_charge_discharge(self, model):
        """Battery cannot charge and discharge simultaneously."""
        model.state.battery_soc_kwh = 4.0
        
        model._update_battery_soc(charge_kw=3.0, discharge_kw=2.0, minutes=30)
        
        # Should have logged a warning about simultaneous operation
        # In future, optimizer constraint should prevent this
    
    def test_battery_deep_discharge_protection(self, model):
        """Battery should not discharge below minimum SOC."""
        model.state.battery_soc_kwh = 1.0  # 1 kWh
        min_soc = 0.2 * model.config.battery_capacity_kwh  # 20% = 1.6 kWh
        
        # Try to discharge aggressively
        model._update_battery_soc(charge_kw=0.0, discharge_kw=5.0, minutes=30)
        
        assert model.state.battery_soc_kwh >= min_soc - 1e-6

# tests/test_simulation.py (ADD THESE)

@pytest.mark.parametrize("num_homes,num_days", [
    (1, 1),      # Minimal
    (50, 30),    # Standard
    (100, 7),    # Large estate
])
def test_simulation_scaling(num_homes, num_days):
    """Simulation should scale linea...to 100+ homes."""
    import time
    
    sim = EstateSimulator(
        num_homes=num_homes,
        num_days=num_days,
        seed=42
    )
    
    start = time.time()
    sim.run_full_simulation()
    elapsed = time.time() - start
    
    # Rough performance target: 0.5 sec per home-month
    max_time = (num_homes * num_days / 30) * 0.5 + 5  # +5s overhead
    assert elapsed < max_time, f"Simulation took {elapsed:.1f}s, target {max_time:.1f}s"

def test_energy_balance_validation():
    """Energy balance check should catch conservation violations."""
    validator = StatisticalValidator()
    
    # Create data with deliberate imbalance
    results = pd.DataFrame({
        'home_id': ['H001'] * 48,
        'timestamp': pd.date_range('2024-01-01', periods=48, freq='30min'),
        'net_load_kw': [1.0] * 48,  # All import
        'pv_generation_kw': [0.0] * 48,
        'demand_total_kw': [0.5] * 48,  # Doesn't match
        'battery_soc_kwh': [5.0] * 48,
    })
    
    balance = validator.energy_balance_check(results)
    assert balance['status'] == 'FAIL'  # Should detect imbalance
```

---

### 2.3 Advanced Plotting & Interactivity [HOURS: 6-8]

```python
# energy_orchestrator_sim/pages/interactive_utils.py (NEW)

import streamlit as st
import plotly.express as px
import pandas as pd

class InteractiveDashboard:
    """Utilities for interactive dashboard components."""
    
    @staticmethod
    def filter_panel(df):
        """Sidebar filters for results."""
        st.sidebar.header("Filters")
        
        homes = st.sidebar.multiselect(
            "Select Homes",
            sorted(df['home_id'].unique()),
            default=sorted(df['home_id'].unique())[:10]  # First 10 by default
        )
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(df['timestamp'].min(), df['timestamp'].max()),
            min_value=df['timestamp'].min(),
            max_value=df['timestamp'].max()
        )
        
        filtered = df[
            (df['home_id'].isin(homes)) &
            (df['timestamp'].dt.date >= date_range[0]) &
            (df['timestamp'].dt.date <= date_range[1])
        ]
        
        st.sidebar.metric("Rows Selected", len(filtered))
        
        return filtered
    
    @staticmethod
    def battery_heatmap(results_df):
        """Heatmap of battery SOC across homes and time."""
        pivot = results_df.pivot_table(
            index='home_id',
            columns='timestamp',
            values='battery_soc_kwh',
            aggfunc='mean'
        )
        
        fig = px.imshow(
            pivot,
            labels=dict(x="Time", y="Home", color="Battery SOC (kWh)"),
            title="Battery State of Charge Heatmap",
            aspect="auto"
        )
        
        return fig
```

---

## PRIORITY 3: PRODUCTION HARDENING (Weeks 5-6)

### 3.1 Input Validation Framework [HOURS: 4-5]

Create centralized input validation:

```python
# energy_orchestrator_sim/utils/validation.py (NEW)

from pydantic import BaseModel, Field, validator
from typing import Optional
import pandas as pd

class HouseholdConfigSchema(BaseModel):
    """Validated household configuration."""
    home_id: str = Field(..., min_length=1, max_length=50)
    pv_capacity_kwp: float = Field(default=4.0, gt=0, le=50)  # 0-50 kWp realistic
    battery_capacity_kwh: float = Field(default=8.0, gt=0, le=200)  # 0-200 kWh realistic
    
    @validator('home_id')
    def home_id_format(cls, v):
        """Validate home_id format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('home_id must be alphanumeric')
        return v

class DataFrameValidator:
    """Validate input DataFrames."""
    
    @staticmethod
    def validate_weather_data(df: pd.DataFrame):
        """Ensure weather DataFrame has required columns and valid ranges."""
        required = ['timestamp', 'irradiance_wm2', 'temperature_c']
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        
        # Check ranges
        if (df['irradiance_wm2'] < 0).any() or (df['irradiance_wm2'] > 1500).any():
            raise ValueError("Irradiance out of range [0, 1500] W/m²")
        
        if (df['temperature_c'] < -50).any() or (df['temperature_c'] > 60).any():
            raise ValueError("Temperature out of range [-50, 60] °C")
        
        return True
```

---

## SUMMARY TIMELINE

```
Week 1:
  Mon-Tue: Error handling + solver fallback (6h)
  Wed-Thu: Configuration system (8h)
  Fri: Testing & integration (4h)

Week 2-3:
  Dashboard pages 1-3 (12h)
  Dashboard pages 4-5 + polish (8h)

Week 4:
  Edge case tests (10h)
  Input validation (4h)
  Integration testing (4h)

Week 5:
  Performance optimization (8h)
  Documentation updates (4h)

Week 6:
  Final integration & testing (6h)
  Launch readiness review (2h)

---
TOTAL: ~80 hours of development
TEAM: 1-2 developers over 6 weeks
OUTCOME: Production-ready Phase 2 release
```

---

**Next Action:** Start with Priority 1 items (Error Handling + Solver Fallback)  
**Decision Point:** After Week 1, evaluate if configuration system fits your deployment model  
**Check-in:** Daily standup to track progress against timeline

