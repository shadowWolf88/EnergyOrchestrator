# -*- coding: utf-8 -*-
"""
Baseline (non-optimized) simulator using greedy heuristics.

Establishes control arm for comparing optimization benefits.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict
import logging

from core.household import HouseholdModel, HouseholdConfig

logger = logging.getLogger(__name__)


class BaselineSimulator:
    """
    Non-optimized household simulator using greedy heuristics.
    
    Rules:
    - EV: Charge immediately upon arrival at 3.6 kW (half max)
    - Battery: Discharge only in evening peak hours (17:00-20:00) if SOC > 30%
    - Solar: Export all surplus
    - Heat pump: Off except winter evening pre-heating
    """
    
    def __init__(self, households: List[HouseholdModel]):
        """Initialize baseline simulator."""
        self.households = households
        self.logger = logger.getChild("BaselineSimulator")
        self.timeline = []
    
    def run_day(
        self,
        date: datetime,
        weather_df: pd.DataFrame,
        tariff_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        carbon_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Run baseline simulation for one day across all households.
        
        Returns:
            DataFrame with timestep, home_id, net_load_kw, and state variables
        """
        day_results = []
        
        for timestep_idx in range(len(weather_df)):
            row_data = {
                'timestamp': weather_df.iloc[timestep_idx]['timestamp'],
                'irradiance_wm2': weather_df.iloc[timestep_idx]['irradiance_wm2'],
                'temperature_c': weather_df.iloc[timestep_idx]['temperature_c'],
                'tariff_£_per_kwh': tariff_df.iloc[timestep_idx]['tariff_£_per_kwh'],
                'carbon_intensity_gco2_per_kwh': carbon_df.iloc[timestep_idx]['carbon_intensity_gco2_per_kwh'],
                'demand_base_kwh': demand_df.iloc[timestep_idx]['demand_base_30min_kwh'],
            }
            
            # Simulate each household
            for home in self.households:
                # Determine greedy control actions
                control = self._get_greedy_control(home, row_data)
                
                # Execute timestep
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
                result['scenario'] = 'baseline'
                result['net_load_kw'] = net_load
                day_results.append(result)
        
        return pd.DataFrame(day_results)
    
    def _get_greedy_control(self, home: HouseholdModel, row_data: dict) -> dict:
        """
        Calculate greedy control actions for a household.
        
        Returns:
            Dict with control actions (battery_charge_kw, battery_discharge_kw, ev_charge_kw, etc.)
        """
        t = row_data['timestamp']
        hour = t.hour
        minute = t.minute
        
        control = {
            'battery_charge_kw': 0.0,
            'battery_discharge_kw': 0.0,
            'ev_charge_kw': 0.0,
            'heat_pump_output_kw': 0.0,
        }
        
        # ===== EV CHARGING =====
        # Charge immediately if present, at half max power (conservative)
        if home.state.ev_present and home.state.ev_soc_kwh < home.config.ev_battery_capacity_kwh - 1e-3:
            control['ev_charge_kw'] = 3.6  # Half of typical 7.4 kW max
        
        # ===== BATTERY DISCHARGE =====
        # Discharge during evening peak (17:00-20:00) if SOC > 30%
        is_evening_peak = 17 <= hour < 20
        if is_evening_peak and home.state.battery_soc_kwh > 0.3 * home.config.battery_capacity_kwh:
            # Drain gradually over the hour
            available_energy = home.state.battery_soc_kwh - 0.2 * home.config.battery_capacity_kwh
            control['battery_discharge_kw'] = min(
                available_energy * 2,  # Over 30 minutes
                home.config.battery_power_kw
            )
        
        # ===== HEAT PUMP =====
        # Pre-heat during night (off-peak): 22:00-06:00
        if not home.config.has_heat_pump:
            control['heat_pump_output_kw'] = 0.0
        elif (hour >= 22 or hour < 6) and home.state.demand_base_kw < 1.0:
            # Off-peak heating window
            control['heat_pump_output_kw'] = 0.5 * home.config.heat_pump_capacity_kw
        
        return control


class EstateBaselineSimulator:
    """Run baseline simulation for entire estate."""
    
    def __init__(self, households: List[HouseholdModel]):
        """Initialize estate simulator."""
        self.households = households
        self.simulator = BaselineSimulator(households)
        self.logger = logger.getChild("EstateBaseline")
    
    def run(
        self,
        start_date: datetime,
        num_days: int,
        data_dict: Dict,  # From generators.generate_simulation_data()
    ) -> Dict:
        """
        Run baseline for entire period.
        
        Returns:
            Dict with 'results_df' (timeline) and 'kpis' (aggregated metrics)
        """
        all_results = []
        
        for day_idx in range(num_days):
            day_start = start_date + pd.Timedelta(days=day_idx)
            day_end = day_start + pd.Timedelta(days=1)
            
            # Extract data for this day
            weather = data_dict['weather'][
                (data_dict['weather']['timestamp'] >= day_start) &
                (data_dict['weather']['timestamp'] < day_end)
            ].reset_index(drop=True)
            
            tariff = data_dict['tariffs'][
                (data_dict['tariffs']['timestamp'] >= day_start) &
                (data_dict['tariffs']['timestamp'] < day_end)
            ].reset_index(drop=True)
            
            demand = data_dict['demand'][
                (data_dict['demand']['timestamp'] >= day_start) &
                (data_dict['demand']['timestamp'] < day_end)
            ].reset_index(drop=True)
            
            carbon = data_dict['carbon_intensity'][
                (data_dict['carbon_intensity']['timestamp'] >= day_start) &
                (data_dict['carbon_intensity']['timestamp'] < day_end)
            ].reset_index(drop=True)
            
            # Reset EV states for new day
            for home in self.households:
                # Randomly assign some homes EV arrival
                if np.random.random() < 0.7:  # 70% of homes have EV on any given day
                    arrival = day_start + pd.Timedelta(hours=17)
                    departure = day_start + pd.Timedelta(days=1, hours=7)
                    required_kwh = np.random.normal(30, 8)
                    home.reset_ev(arrival, departure, max(15, min(60, required_kwh)))
                else:
                    home.clear_ev()
            
            # Run day
            day_results = self.simulator.run_day(
                day_start, weather, tariff, demand, carbon
            )
            all_results.append(day_results)
        
        results_df = pd.concat(all_results, ignore_index=True)
        
        # Calculate KPIs
        kpis = self._calculate_kpis(results_df)
        
        return {
            'results_df': results_df,
            'kpis': kpis,
        }
    
    def _calculate_kpis(self, results_df: pd.DataFrame) -> dict:
        """Calculate key performance indicators from baseline results."""
        
        # Aggregate per home
        per_home = results_df.groupby('home_id').agg({
            'cumulative_cost_gbp': 'last',
            'peak_load_kw': 'max',
            'cumulative_co2_kg': 'last',
        }).reset_index()
        
        per_home.columns = ['home_id', 'total_cost_gbp', 'peak_load_kw', 'total_co2_kg']
        
        # Estate totals
        kpis = {
            'scenario': 'baseline',
            'num_homes': len(self.households),
            'total_cost_gbp': results_df.groupby('home_id')['cumulative_cost_gbp'].last().sum(),
            'avg_cost_per_home_gbp': per_home['total_cost_gbp'].mean(),
            'estate_peak_load_kw': max(
                results_df.groupby('timestamp')['net_load_kw'].sum() if 'net_load_kw' in results_df else [100]
            ),
            'total_co2_kg': results_df.groupby('home_id')['cumulative_co2_kg'].last().sum(),
            'avg_co2_per_home_kg': per_home['total_co2_kg'].mean(),
            'per_home_stats': per_home,
        }
        
        return kpis


if __name__ == "__main__":
    # Quick test
    from data.generators import generate_simulation_data
    
    # Generate data
    data = generate_simulation_data(
        start_date=pd.Timestamp('2024-01-01'),
        num_days=2,
        season='winter',
        tariff_type='agile',
    )
    
    # Create test households
    homes = [
        HouseholdModel(HouseholdConfig(home_id=f"H{i:03d}"))
        for i in range(5)
    ]
    
    # Run baseline
    sim = EstateBaselineSimulator(homes)
    results = sim.run(
        start_date=pd.Timestamp('2024-01-01'),
        num_days=2,
        data_dict=data,
    )
    
    print("Baseline KPIs:")
    for k, v in results['kpis'].items():
        if k != 'per_home_stats':
            print(f"  {k}: {v}")
