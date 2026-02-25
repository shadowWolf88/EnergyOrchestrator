# Stage 2 Master Prompt | TORQ — Dashboard, Real Data & AI Forecasting

> **TORQ** = Transformer Orchestration & Resource Quantification

## Context: Where We Are

You are continuing development of **TORQ** — a production-grade Python simulation and optimisation platform for UK residential microgrids. The core simulation engine is complete (Phases 1–5A). The codebase lives in `energy_orchestrator_sim/` and includes:

- `simulation/` — MILP optimization engine (OR-Tools CBC) + baseline greedy simulator
- `core/` — `HouseholdModel`, `SolarGenerator`, `BatteryStorageModel`, `EVChargingModel`, `TariffManager`, `CarbonIntensityModel`
- `metrics/` — `CostAnalyzer`, `PeakAnalyzer`, `CarbonAnalyzer`, `TransformerAnalyzer`
- `data/generators.py` — synthetic weather, tariff, demand, carbon data
- `data/realtime_eso_api.py` — ESO Carbon Intensity API client (exists but not wired up)
- `streamlit_app.py` + `pages/` — 5-page Streamlit dashboard (currently shows hardcoded demo data)
- `main.py` — CLI simulation runner
- Simulation results CSVs: `simulation_results_baseline.csv`, `simulation_results_optimized.csv`

**Phase 5B Mission**: Upgrade the dashboard from a static display to a live analytical tool, integrate real UK data APIs, add AI forecasting, and prepare for the Hockerton Housing Project pilot case.

---

## Priority 1: Dashboard Live Data & Interactive Controls

**Problem**: All dashboard pages currently display hardcoded numbers or random `np.random` data. The real simulation results are in CSV files but never loaded.

**Required Deliverables:**

### 1.1 Load Real CSV Data in Dashboard Pages

In each page (`pages/1_📊_Overview.py` through `pages/5_💨_Carbon_Impact.py`), replace hardcoded demo data with:

```python
import os, pandas as pd

@st.cache_data
def load_results():
    base_path = os.path.dirname(os.path.dirname(__file__))
    baseline = pd.read_csv(os.path.join(base_path, "simulation_results_baseline.csv"), parse_dates=["timestamp"])
    optimized = pd.read_csv(os.path.join(base_path, "simulation_results_optimized.csv"), parse_dates=["timestamp"])
    return baseline, optimized
```

If CSVs don't exist, show a friendly `st.warning("No simulation results found. Run the simulation first.")` with a button to trigger it.

### 1.2 Settings Page (Page 6)

Create `pages/6_⚙️_Settings.py`:

```
Parameters to expose:
- Number of homes (slider: 10–200, default 50)
- Simulation days (10, 30, 90, 365)
- Tariff type (Flat / Economy 7 / Agile)
- Transformer upgrade threshold (kW)
- Transformer upgrade cost (£)
- Random seed
- Use real weather data toggle (when API available)
- Use real carbon intensity toggle (when API available)

"Run Simulation" button:
- Calls subprocess.run(["python", "main.py", "--homes", str(n), ...])
- Shows progress spinner
- Reloads all cached data on completion
```

### 1.3 About Page (Page 7)

Create `pages/7_ℹ️_About.py`:
- Project overview, tech stack, use cases
- Link to GitHub (user to update URL)
- Contributors section
- Version info
- Move the existing "About" content from the home page here

---

## Priority 2: Real UK Data API Integrations

### 2.1 ESO Carbon Intensity API

Wire up `data/realtime_eso_api.py` which already exists. Add to `data/__init__.py` and expose in dashboard.

```python
# Target endpoint: https://api.carbonintensity.org.uk/intensity
# Half-hourly regional intensity for Yorkshire/East Midlands (regionid=7)
# Fallback to synthetic data if API unavailable

class CarbonIntensityAPIClient:
    BASE_URL = "https://api.carbonintensity.org.uk"

    def get_current_intensity(self) -> float:
        """Current gCO2/kWh for GB grid."""

    def get_24h_forecast(self) -> pd.DataFrame:
        """48 half-hourly forecast periods."""

    def get_regional(self, region_id: int = 7) -> pd.DataFrame:
        """East Midlands regional intensity (Hockerton area)."""
```

### 2.2 Octopus Agile Tariff API

```python
# Target: https://api.octopus.energy/v1/products/AGILE-FLEX-22-11-25/electricity-tariffs/E-1R-AGILE-FLEX-22-11-25-C/standard-unit-rates/
# No API key needed for price data

class OctopusAgileClient:
    def get_current_rates(self, period_from: datetime, period_to: datetime) -> pd.DataFrame:
        """Return half-hourly Agile prices (p/kWh) for given window."""

    def get_tomorrow_rates(self) -> pd.DataFrame:
        """Day-ahead Agile prices, published ~4pm daily."""
```

### 2.3 PVGIS Solar Irradiance

```python
# Target: https://re.jrc.ec.europa.eu/api/v5_2/seriescalc
# Lat/lon: Hockerton = 53.08°N, 0.94°W
# Free, no API key, returns hourly/monthly irradiance

class PVGISClient:
    HOCKERTON_LAT = 53.08
    HOCKERTON_LON = -0.94

    def get_monthly_profile(self, year: int = 2024) -> pd.DataFrame:
        """Monthly irradiance profile for Nottinghamshire."""

    def get_typical_year(self) -> pd.DataFrame:
        """Typical Meteorological Year (TMY) half-hourly irradiance."""
```

---

## Priority 3: AI Forecasting Modules

Create the `ai/` directory that is specified in the architecture but does not yet exist.

### 3.1 `ai/demand_forecaster.py`

```python
from statsmodels.tsa.statespace.sarimax import SARIMAX

class DemandForecaster:
    """
    SARIMA-based 24-hour demand forecast.

    Inputs: historical 30-min demand time series (HouseholdModel output)
    Outputs: 48 half-hourly forecast values + 90% prediction interval

    Seasonal order: (1,1,1,48) — captures daily seasonality
    Used in: rolling MILP horizon to replace synthetic look-ahead
    """

    def fit(self, demand_series: pd.Series) -> None: ...
    def forecast(self, steps: int = 48) -> Tuple[np.ndarray, np.ndarray, np.ndarray]: ...
    # Returns: (mean_forecast, lower_90ci, upper_90ci)
```

### 3.2 `ai/solar_forecaster.py`

```python
class SolarForecaster:
    """
    Day-ahead solar irradiance forecast using:
    - Seasonal base profile (PVGIS TMY)
    - Cloud probability adjustment (from Met Office NWP or synthetic Markov chain)

    Inputs: date, season, cloud_forecast (0–1 probability)
    Outputs: 48 half-hourly irradiance values (W/m²)
    """
```

### 3.3 `ai/ev_predictor.py`

```python
class EVArrivalPredictor:
    """
    Bayesian arrival time + energy need predictor.

    Uses historical departure/arrival patterns to predict:
    - Arrival time distribution (Gamma, mean 17:30)
    - Energy needed (Normal, mean 30 kWh)
    - Departure window (Uniform 06:00–08:30)

    Used in: optimization engine to pre-position battery SOC before predicted EV arrival.
    """
```

---

## Priority 4: Heat Pump Integration

Create `core/heat_pump.py`:

```python
class HeatPumpModel:
    """
    Air-source heat pump with:
    - COP(T) curve: COP = 3.5 - 0.1 * (T_flow - T_outside) / 10
      (COP degrades as outdoor temp drops below 7°C)
    - Thermal mass pre-heating: charge thermal storage during low-carbon windows
    - Minimum run time: 30 minutes (avoid short cycling)
    - Rated capacity: 5–12 kW thermal (typical UK ASHP)
    - Electrical demand: kW_thermal / COP(T)

    Key optimization lever: pre-heat during:
    - Low Agile tariff windows (00:30–07:30)
    - High solar generation (midday in summer)
    - Low carbon intensity windows
    """

    def calculate_cop(self, outdoor_temp_c: float, flow_temp_c: float = 45.0) -> float: ...
    def calculate_electrical_demand(self, thermal_output_kw: float, outdoor_temp_c: float) -> float: ...
    def step(self, timestep: int, outdoor_temp: float, heating_demand_kw: float) -> dict: ...
```

Extend `HouseholdModel` in `core/household.py` with optional `heat_pump: Optional[HeatPumpModel] = None`.

---

## Priority 5: Vehicle-to-Grid (V2G)

Extend `core/household.py` and the MILP in `simulation/optimization_engine.py`:

```python
# In EVChargingModel:
v2g_enabled: bool = False  # Bidirectional charging capability
v2g_max_discharge_kw: float = 3.6  # Typically same as charge rate

# In MILPOptimizer: add decision variables:
# ev_discharge_kw(t): Power exported from EV to home/grid
# Constraint: ev_charge_kw(t) + ev_discharge_kw(t) ≤ max_charger_kw
# Constraint: ev_discharge only when vehicle is plugged in
# Constraint: must still meet departure SOC requirement
```

---

## Priority 6: REST API (FastAPI)

Create `api/app.py`:

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="AI Energy Orchestrator API", version="2.0.0")

class SimulationRequest(BaseModel):
    num_homes: int = 50
    num_days: int = 30
    tariff_type: str = "agile"
    transformer_kw: float = 250.0
    seed: int = 42

@app.post("/api/v1/simulate")
async def run_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Trigger simulation, return run_id for polling."""

@app.get("/api/v1/results/{run_id}")
async def get_results(run_id: str):
    """Return KPIs + CSV download URL when complete."""

@app.get("/api/v1/carbon/current")
async def get_carbon():
    """Live ESO grid carbon intensity (proxy)."""

@app.get("/api/v1/tariff/agile")
async def get_agile_tariff():
    """Live Octopus Agile half-hourly rates (proxy)."""
```

Add `uvicorn` and `fastapi` to `requirements.txt`. Run alongside Streamlit on separate port (8001).

---

## Priority 7: Sensitivity Analysis Module

Create `analysis/sensitivity.py`:

```python
class SensitivityAnalyzer:
    """
    Systematic parameter sensitivity analysis.

    Parameters to vary:
    - solar_capacity_kwp: [3.0, 4.0, 5.0, 6.0]
    - battery_capacity_kwh: [5, 7.5, 10, 15]
    - ev_fraction: [0.25, 0.5, 0.75, 1.0]  # fraction of homes with EV
    - tariff_type: ["flat", "economy7", "agile"]
    - num_homes: [10, 25, 50, 100, 200]

    For each combination, run full simulation and record:
    - peak_reduction_pct
    - cost_savings_pct
    - carbon_reduction_pct
    - transformer_headroom_kw

    Output: 2D heatmaps (solar_cap × battery_cap), bar charts (tariff comparison)
    Export: sensitivity_results.csv, sensitivity_report.md
    """
```

---

## Priority 8: Hockerton Pilot Configuration

Create `config/hockerton_config.yaml`:

```yaml
estate_name: "Hockerton Housing Project"
location:
  latitude: 53.08
  longitude: -0.94
  region: "East Midlands"
  weather_station: "Nottinghamshire"

homes:
  count: 9
  type: "earth-sheltered passive solar"

assets_per_home:
  solar_kwp: 2.5        # Original 1995 array + subsequent upgrades (estimate)
  battery_kwh: 7.5      # Assumed home battery (to verify)
  ev_fraction: 0.67     # ~6/9 homes with EVs (estimate)
  heat_pump: false      # Originally designed with passive solar + thermal mass
  wind_turbine_kw: 2.5  # Shared community wind turbine (25 kW / 9 homes est.)

grid:
  transformer_kw: 50    # Small rural connection (to verify with WPD/NGED)
  export_enabled: true  # SEG tariff assumed
  tariff: "agile"

simulation:
  days: 365
  seasons: ["winter", "spring", "summer", "autumn"]
  monte_carlo_runs: 500
```

---

## Codebase Conventions (Maintain These)

- **Language**: Python 3.11+, type hints throughout
- **Style**: black + ruff (configured in `pyproject.toml`) — run `make format` before committing
- **Tests**: Add `tests/test_*.py` for every new module; maintain >85% coverage
- **Logging**: Use `logging.getLogger(__name__)` — no bare `print()` statements
- **Docstrings**: Every class and public method — include units in parameter names (e.g., `capacity_kwh: float`)
- **No simultaneous charge+discharge**: Enforce in every battery/EV model update
- **Energy units**: Always kWh for stored energy, kW for power, £ for cost, kg CO₂ for emissions
- **Time resolution**: 30-minute half-hour periods (Δt = 0.5 hours)
- **Reproducibility**: Every stochastic function accepts `seed: int = 42`

---

## File Creation Checklist for Stage 2

| File | Purpose |
|------|---------|
| `pages/6_⚙️_Settings.py` | Interactive simulation config + run button |
| `pages/7_ℹ️_About.py` | Project info, use cases, tech stack |
| `ai/__init__.py` | Package init |
| `ai/demand_forecaster.py` | SARIMA 24h demand forecast |
| `ai/solar_forecaster.py` | Day-ahead irradiance forecast |
| `ai/ev_predictor.py` | EV arrival/energy prediction |
| `core/heat_pump.py` | ASHP model with COP curve |
| `api/app.py` | FastAPI REST endpoints |
| `api/__init__.py` | Package init |
| `analysis/sensitivity.py` | Parameter sensitivity analysis |
| `analysis/benchmark.py` | BDUK/DNO comparison |
| `analysis/__init__.py` | Package init |
| `config/hockerton_config.yaml` | Hockerton pilot configuration |
| `tests/test_heat_pump.py` | Heat pump unit tests |
| `tests/test_forecasting.py` | Forecasting module tests |
| `tests/test_api.py` | API endpoint tests |
| `VALIDATION_REPORT.md` | Benchmark findings for credibility |

**Additions to existing files:**
- `data/realtime_eso_api.py` — complete the implementation
- `data/generators.py` — add `PVGISWeatherGenerator` (real data option)
- `core/household.py` — add `heat_pump` optional asset, `v2g_enabled` flag
- `simulation/optimization_engine.py` — add V2G decision variables + heat pump scheduling
- `requirements.txt` — add `fastapi>=0.104`, `uvicorn>=0.24`, `httpx>=0.25`

---

## Success Criteria for Stage 2

| Metric | Target |
|--------|--------|
| Dashboard loads real CSV data | 100% of pages |
| Settings page triggers live simulation | Functional |
| ESO carbon API integration | Live data in Carbon Impact page |
| Agile tariff API integration | Live pricing in Cost Analysis page |
| AI demand forecast | MAPE < 15% on holdout period |
| Heat pump model | COP validation within ±5% of manufacturer data |
| REST API | All 4 endpoints functional, <2s response |
| Sensitivity analysis | 4-variable grid, heatmap output |
| Hockerton config | Full 365-day simulation runnable |
| Test coverage | Maintained >85% |

---

**"This stage transforms TORQ from a demonstration simulator into a credible, real-data-driven platform ready for pilot deployment at Hockerton and DNO conversations."**

---

**Document Version:** 2.0 | **Product:** TORQ | **Created:** February 2026 | **Supersedes:** `AI_Energy_Orchestrator_Claude_Master_Prompt.md` (Stage 1)
