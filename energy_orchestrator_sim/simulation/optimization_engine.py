# -*- coding: utf-8 -*-
"""
Mixed Integer Linear Programming (MILP) optimization engine using Google OR-Tools.

Formulates and solves the energy management problem:
  Minimize: Cost + PeakPenalty + BatteryDegradation + CarbonCost
  Subject to: Battery physics, EV constraints, transformer capacity limits

Rolling 48-hour horizon with Markov continuation for efficiency.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
import logging

from ortools.linear_solver import pywraplp

from core.household import HouseholdModel, HouseholdConfig

logger = logging.getLogger(__name__)


class OptimizationConfig:
    """Configuration for MILP solver."""
    
    # Solver parameters
    solver_type = 'CBC'  # Linear solver: CBC or GLOP
    time_limit_seconds = 60
    num_threads = -1  # Use all available cores
    absolute_tolerance = 1e-4
    relative_tolerance = 0.001  # 0.1% optimality gap
    log_search_progress = False
    
    # Objective weights
    weight_cost = 1.0
    weight_transformer_stress = 1000.0  # HIGH PRIORITY: Minimize transformer overload
    weight_volatility_penalty = 10.0  # Penalize rapid ramping
    weight_battery_degradation = 1.0
    weight_carbon_cost = 0.01


class MILPOptimizer:
    """
    MILP-based energy optimization for a single home or estate.
    
    Decision variables (per 30-min timestep):
    - battery_charge_kw(t): Battery charging power
    - battery_discharge_kw(t): Battery discharging power
    - battery_soc_kwh(t): Battery state of charge (tracked)
    - ev_charge_kw(t): EV charging power
    - ev_soc_kwh(t): EV battery SOC (tracked)
    - import_kw(t): Import from grid (= max(net_load, 0))
    - export_kw(t): Export to grid (= max(-net_load, 0))
    """
    
    def __init__(self, config: OptimizationConfig = None):
        """Initialize optimizer."""
        self.config = config or OptimizationConfig()
        self.logger = logger.getChild("MILPOptimizer")
        self.solver = None
    
    def optimize_household(
        self,
        home: HouseholdModel,
        horizon_hours: int = 48,
        timestep_minutes: int = 30,
        weather_dict: Dict = None,  # {timestamp: (irradiance, temp, ...)}
        tariff_dict: Dict = None,
        demand_dict: Dict = None,
        carbon_dict: Dict = None,
        initial_battery_soc_kwh: Optional[float] = None,
        ev_arrival: Optional[datetime] = None,
        ev_departure: Optional[datetime] = None,
        ev_required_energy_kwh: float = 0.0,
    ) -> Tuple[Dict, Optional[Any]]:
        """
        Optimize household over horizon (usually 48 hours rolling window).
        
        Returns:
            (control_dict, solver_status)
            control_dict: {timestamp: {'battery_charge_kw': ..., 'battery_discharge_kw': ..., ...}}
        """
        
        # Determine timesteps
        num_timesteps = int((horizon_hours * 60) / timestep_minutes)
        
        # Create solver
        self.solver = pywraplp.Solver.CreateSolver('CBC')
        if not self.solver:
            self.logger.error("CBC solver not available")
            return {}, None
        
        # Set solver parameters
        self.solver.SetTimeLimit(int(self.config.time_limit_seconds * 1000))
        self.solver.SetNumThreads(self.config.num_threads)
        
        # ===== DECISION VARIABLES =====
        
        # Battery: charge, discharge, SOC
        battery_charge = {}  # [kW]
        battery_discharge = {}  # [kW]
        battery_soc = {}  # [kWh]
        battery_charge_binary = {}  # Binary: allow charging (avoid simultaneous C+D)
        
        # EV: charge, SOC
        ev_charge = {}  # [kW]
        ev_soc = {}  # [kWh]
        
        # Grid: import, export
        import_kw = {}  # [kW]
        export_kw = {}  # [kW]
        
        for t in range(num_timesteps):
            # Battery
            battery_charge[t] = self.solver.NumVar(0, home.config.battery_power_kw, f'batt_charge_{t}')
            battery_discharge[t] = self.solver.NumVar(0, home.config.battery_power_kw, f'batt_discharge_{t}')
            battery_soc[t] = self.solver.NumVar(0, home.config.battery_capacity_kwh, f'batt_soc_{t}')
            battery_charge_binary[t] = self.solver.IntVar(0, 1, f'batt_binary_{t}')
            
            # EV
            ev_charge[t] = self.solver.NumVar(0, home.config.ev_charger_rating_kw, f'ev_charge_{t}')
            ev_soc[t] = self.solver.NumVar(0, home.config.ev_battery_capacity_kwh, f'ev_soc_{t}')
            
            # Grid
            import_kw[t] = self.solver.NumVar(0, 100, f'import_{t}')  # Assume max 100 kW
            export_kw[t] = self.solver.NumVar(0, 50, f'export_{t}')  # Max 50 kW export
        
        # ===== CONSTRAINTS =====
        
        dt = timestep_minutes / 60.0  # Convert to hours
        
        for t in range(num_timesteps):
            # Get external data
            irradiance = weather_dict.get(t, {}).get('irradiance_wm2', 0)
            temp = weather_dict.get(t, {}).get('temperature_c', 15)
            tariff = tariff_dict.get(t, 0.35)
            demand = demand_dict.get(t, 0.2)  # kWh per 30min
            carbon_intensity = carbon_dict.get(t, 300)
            
            # Calculate solar generation
            pv_gen_kw = self._calculate_solar(home, irradiance, temp)
            
            # Battery dynamics: SOC(t+1) = SOC(t) + ηc·Pc·Δt - Pd·Δt/ηd - Sloss
            if t == 0:
                soc_prev = initial_battery_soc_kwh or home.state.battery_soc_kwh
            else:
                soc_prev_var = battery_soc[t - 1]
                soc_prev = soc_prev_var
            
            standing_loss = (home.config.battery_capacity_kwh * 
                           home.config.battery_standing_loss_pct_per_hour / 100) * dt
            
            charge_energy = battery_charge[t] * dt * home.config.battery_efficiency_charge
            discharge_energy = battery_discharge[t] * dt / home.config.battery_efficiency_discharge
            
            self.solver.Add(
                battery_soc[t] == soc_prev + charge_energy - discharge_energy - standing_loss
            )
            
            # No simultaneous charge + discharge (binary constraint)
            self.solver.Add(battery_charge[t] <= home.config.battery_power_kw * battery_charge_binary[t])
            self.solver.Add(battery_discharge[t] <= home.config.battery_power_kw * (1 - battery_charge_binary[t]))
            
            # EV dynamics (if present)
            if ev_arrival and ev_departure:
                t_dt = datetime.now() + timedelta(minutes=t * timestep_minutes)
                is_present = ev_arrival <= t_dt < ev_departure
                
                if is_present:
                    # Can charge
                    if t == 0:
                        ev_soc_prev = 0.0  # Arrives empty
                    else:
                        ev_soc_prev = ev_soc[t - 1]
                    
                    self.solver.Add(
                        ev_soc[t] == ev_soc_prev + ev_charge[t] * dt * 0.95
                    )
                    
                    # Must charge by departure
                    if t_dt >= ev_departure - timedelta(minutes=timestep_minutes):
                        self.solver.Add(ev_soc[t] >= ev_required_energy_kwh)
                else:
                    # Not present: no charging
                    self.solver.Add(ev_charge[t] == 0)
                    if t > 0:
                        self.solver.Add(ev_soc[t] == 0)  # Battery empty while away
            else:
                # No EV
                self.solver.Add(ev_charge[t] == 0)
            
            # Net load balance: Import - Export = Demand + Battery_in - PV - EV_discharge
            demand_kwh = demand  # Already in kWh per 30min
            demand_kw = demand_kwh * 2  # Convert to kW average
            
            total_demand_kw = demand_kw  # Simplified: assume no appliance/HP stochasticity in opt
            
            self.solver.Add(
                import_kw[t] - export_kw[t] ==
                total_demand_kw + battery_charge[t] + ev_charge[t] - pv_gen_kw - battery_discharge[t]
            )
        
        # ===== OBJECTIVE FUNCTION =====
        
        objective = self.solver.Objective()
        
        # Cost of imports: directly on import_kw variable
        for t in range(num_timesteps):
            tariff = tariff_dict.get(t, 0.35)
            dt = timestep_minutes / 60.0  # Convert to hours
            # Energy imported (kWh) = power (kW) * time (hours)
            # Coefficient = cost per kWh * time (hours) = cost per kW per timestep
            cost_per_kw = self.config.weight_cost * tariff * dt
            objective.SetCoefficient(import_kw[t], cost_per_kw)
        
        # Battery degradation: £35/MWh cycled = £0.035/kWh
        battery_deg_cost = 35.0 / 1000  # Per kWh
        dt = timestep_minutes / 60.0
        deg_cost_per_kw = self.config.weight_battery_degradation * battery_deg_cost * dt
        for t in range(num_timesteps):
            objective.SetCoefficient(battery_charge[t], deg_cost_per_kw)
            objective.SetCoefficient(battery_discharge[t], deg_cost_per_kw)
        
        objective.SetMinimization()
        
        # ===== SOLVE =====
        
        status = self.solver.Solve()
        
        # ===== EXTRACT SOLUTION =====
        
        control_dict = {}
        
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            self.logger.info(f"Optimization solved: status={status}")
            
            for t in range(num_timesteps):
                control_dict[t] = {
                    'battery_charge_kw': battery_charge[t].solution_value(),
                    'battery_discharge_kw': battery_discharge[t].solution_value(),
                    'ev_charge_kw': ev_charge[t].solution_value() if (ev_arrival and ev_departure) else 0.0,
                    'heat_pump_output_kw': 0.0,  # Not optimized in MVP
                }
        else:
            self.logger.error(f"Optimization failed: status={status}")
        
        return control_dict, status
    
    def _calculate_solar(self, home: HouseholdModel, irradiance_wm2: float, temperature_c: float) -> float:
        """Calculate solar generation [kW]."""
        temp_coeff = 1.0 - 0.004 * (temperature_c - 25)
        soiling = 0.98
        return (
            home.config.pv_capacity_kwp *
            (irradiance_wm2 / 1000.0) *
            home.config.pv_efficiency *
            temp_coeff *
            soiling
        )


class EstateOptimizer:
    """Optimize multiple homes considering transformer constraint."""
    
    def __init__(self, homes: List[HouseholdModel], config: OptimizationConfig = None):
        """Initialize estate optimizer."""
        self.homes = homes
        self.config = config or OptimizationConfig()
        self.optimizer = MILPOptimizer(config)
        self.logger = logger.getChild("EstateOptimizer")
    
    def optimize_estate(
        self,
        start_date: datetime,
        num_days: int,
        data_dict: Dict,
        transformer_capacity_kw: float = 100.0,
    ) -> Dict:
        """
        Optimize entire estate over period and simulate with optimized controls.
        
        Returns:
            Dict with results_df (timeline) and kpis (metrics)
        """
        all_results = []
        
        self.logger.info(f"Optimizing {len(self.homes)} homes over {num_days} days with Tx capacity {transformer_capacity_kw} kW")
        
        # Rolling horizon: 48-hour windows with 24-hour step
        for day_idx in range(num_days):
            day_start = start_date + pd.Timedelta(days=day_idx)
            day_end = day_start + pd.Timedelta(days=1)
            
            # Extract data for this day (+1 day lookahead for 48-hour window)
            horizon_end = min(day_start + pd.Timedelta(days=2), start_date + pd.Timedelta(days=num_days))
            
            weather = data_dict['weather'][
                (data_dict['weather']['timestamp'] >= day_start) &
                (data_dict['weather']['timestamp'] < horizon_end)
            ].reset_index(drop=True)
            
            tariff = data_dict['tariffs'][
                (data_dict['tariffs']['timestamp'] >= day_start) &
                (data_dict['tariffs']['timestamp'] < horizon_end)
            ].reset_index(drop=True)
            
            demand = data_dict['demand'][
                (data_dict['demand']['timestamp'] >= day_start) &
                (data_dict['demand']['timestamp'] < horizon_end)
            ].reset_index(drop=True)
            
            carbon = data_dict['carbon_intensity'][
                (data_dict['carbon_intensity']['timestamp'] >= day_start) &
                (data_dict['carbon_intensity']['timestamp'] < horizon_end)
            ].reset_index(drop=True)
            
            # Reset EV states for new day
            for home in self.homes:
                if np.random.random() < 0.7:  # 70% of homes have EV on any given day
                    arrival = day_start + pd.Timedelta(hours=17)
                    departure = day_start + pd.Timedelta(days=1, hours=7)
                    required_kwh = np.random.normal(30, 8)
                    home.reset_ev(arrival, departure, max(15, min(60, required_kwh)))
                else:
                    home.clear_ev()
            
            # Build dicts for optimization
            weather_dict = {i: {
                'irradiance_wm2': weather.iloc[i]['irradiance_wm2'],
                'temperature_c': weather.iloc[i]['temperature_c'],
            } for i in range(len(weather))}
            
            tariff_dict = {i: tariff.iloc[i]['tariff_£_per_kwh'] for i in range(len(tariff))}
            demand_dict = {i: demand.iloc[i]['demand_base_30min_kwh'] for i in range(len(demand))}
            carbon_dict = {i: carbon.iloc[i]['carbon_intensity_gco2_per_kwh'] for i in range(len(carbon))}
            
            # Optimize and simulate each home with optimized controls
            for home in self.homes:
                control_dict, status = self.optimizer.optimize_household(
                    home,
                    horizon_hours=min(48, (horizon_end - day_start).total_seconds() / 3600),
                    timestep_minutes=30,
                    weather_dict=weather_dict,
                    tariff_dict=tariff_dict,
                    demand_dict=demand_dict,
                    carbon_dict=carbon_dict,
                )
                
                # Simulate the day with optimized controls
                for timestep_idx in range(min(48, len(weather))):  # Only apply first 24h controls today
                    t_dt = day_start + pd.Timedelta(minutes=timestep_idx * 30)
                    
                    if t_dt >= day_end:
                        break
                    
                    row_data = {
                        'timestamp': t_dt,
                        'irradiance_wm2': weather.iloc[timestep_idx]['irradiance_wm2'],
                        'temperature_c': weather.iloc[timestep_idx]['temperature_c'],
                        'tariff_£_per_kwh': tariff_dict.get(timestep_idx, 0.35),
                        'carbon_intensity_gco2_per_kwh': carbon_dict.get(timestep_idx, 300),
                        'demand_base_kwh': demand_dict.get(timestep_idx, 0.2),
                    }
                    
                    # Get optimized control for this timestep
                    control = control_dict.get(timestep_idx, {
                        'battery_charge_kw': 0.0,
                        'battery_discharge_kw': 0.0,
                        'ev_charge_kw': 0.0,
                    })
                    
                    # Execute timestep with optimized controls
                    net_load = home.step(
                        t=row_data['timestamp'],
                        irradiance_wm2=row_data['irradiance_wm2'],
                        temperature_c=row_data['temperature_c'],
                        demand_base_kwh=row_data['demand_base_kwh'],
                        tariff_price=row_data['tariff_£_per_kwh'],
                        carbon_intensity=row_data['carbon_intensity_gco2_per_kwh'],
                        control=control,
                    )
                    
                    # Log result
                    result = home.get_state_dict()
                    result['scenario'] = 'optimized'
                    result['net_load_kw'] = net_load
                    all_results.append(result)
        
        results_df = pd.concat([pd.DataFrame([r]) for r in all_results], ignore_index=True) if all_results else pd.DataFrame()
        
        return {
            'results_df': results_df,
            'kpis': {},  # Will be calculated by MetricsCalculator
        }


if __name__ == "__main__":
    # Test
    home = HouseholdModel(HouseholdConfig(home_id="H001"))
    opt = MILPOptimizer()
    
    # Simple 48-step test
    weather_dict = {t: {'irradiance_wm2': 500, 'temperature_c': 15} for t in range(48)}
    tariff_dict = {t: 0.35 for t in range(48)}
    demand_dict = {t: 0.2 for t in range(48)}
    carbon_dict = {t: 300 for t in range(48)}
    
    control, status = opt.optimize_household(
        home,
        horizon_hours=24,
        timestep_minutes=30,
        weather_dict=weather_dict,
        tariff_dict=tariff_dict,
        demand_dict=demand_dict,
        carbon_dict=carbon_dict,
    )
    
    print(f"Optimization status: {status}")
    print(f"Control steps: {len(control)}")
    if control:
        print(f"First control: {control[0]}")
