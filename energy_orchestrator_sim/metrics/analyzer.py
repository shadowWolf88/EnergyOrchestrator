# -*- coding: utf-8 -*-
"""
Metrics analysis: cost, peak, carbon, and transformer metrics.

Calculates KPIs from simulation results and provides statistical validation.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class CostAnalyzer:
    """Analyze cost metrics."""
    
    @staticmethod
    def calculate_total_cost(results_df: pd.DataFrame) -> float:
        """Total cost across all homes and timesteps."""
        return results_df.groupby('home_id')['cumulative_cost_gbp'].last().sum()
    
    @staticmethod
    def calculate_cost_per_home(results_df: pd.DataFrame) -> pd.Series:
        """Cost per household."""
        return results_df.groupby('home_id')['cumulative_cost_gbp'].last()
    
    @staticmethod
    def calculate_unit_cost(results_df: pd.DataFrame) -> float:
        """Average unit cost [GBP/kWh]."""
        total_cost = results_df.groupby('home_id')['cumulative_cost_gbp'].last().sum()
        total_energy = results_df['demand_total_kw'].sum() * 0.5  # 30-min timesteps  
        return total_cost / total_energy if total_energy > 0 else 0.0


class PeakAnalyzer:
    """Analyze peak load and demand response metrics."""
    
    @staticmethod
    def calculate_estate_peak_load(results_df: pd.DataFrame) -> float:
        """Peak load aggregated across estate [kW]."""
        # Group by timestamp, sum net_load across homes
        if 'net_load_kw' not in results_df.columns:
            return 0.0
        estate_load = results_df.groupby('timestamp')['net_load_kw'].sum()
        return estate_load.max()
    
    @staticmethod
    def calculate_peak_percentile(results_df: pd.DataFrame, percentile: float = 95) -> float:
        """95th percentile peak load [kW]."""
        if 'net_load_kw' not in results_df.columns:
            return 0.0
        estate_load = results_df.groupby('timestamp')['net_load_kw'].sum()
        return np.percentile(estate_load, percentile)
    
    @staticmethod
    def calculate_transformer_headroom(
        results_df: pd.DataFrame,
        transformer_capacity_kw: float = 100.0
    ) -> float:
        """Available headroom in transformer [kW]."""
        peak = PeakAnalyzer.calculate_estate_peak_load(results_df)
        return max(0, transformer_capacity_kw - peak)
    
    @staticmethod
    def calculate_overload_frequency(
        results_df: pd.DataFrame,
        transformer_capacity_kw: float = 100.0
    ) -> int:
        """Number of 30-min periods with overload."""
        if 'net_load_kw' not in results_df.columns:
            return 0
        estate_load = results_df.groupby('timestamp')['net_load_kw'].sum()
        return (estate_load > transformer_capacity_kw).sum()
    
    @staticmethod
    def calculate_load_volatility(results_df: pd.DataFrame) -> float:
        """Standard deviation of import/export rate [kW]."""
        if 'net_load_kw' not in results_df.columns:
            return 0.0
        estate_load = results_df.groupby('timestamp')['net_load_kw'].sum()
        return estate_load.std()


class CarbonAnalyzer:
    """Analyze carbon emissions."""
    
    @staticmethod
    def calculate_total_emissions(results_df: pd.DataFrame) -> float:
        """Total CO₂ emissions [kg]."""
        return results_df.groupby('home_id')['cumulative_co2_kg'].last().sum()
    
    @staticmethod
    def calculate_emissions_per_home(results_df: pd.DataFrame) -> pd.Series:
        """CO₂ per household [kg]."""
        return results_df.groupby('home_id')['cumulative_co2_kg'].last()
    
    @staticmethod
    def calculate_emissions_intensity(results_df: pd.DataFrame) -> float:
        """gCO₂/kWh consumed."""
        total_co2_kg = CarbonAnalyzer.calculate_total_emissions(results_df)
        total_energy_kwh = results_df['demand_total_kw'].sum() * 0.5
        return (total_co2_kg * 1000) / total_energy_kwh if total_energy_kwh > 0 else 0.0


class TransformerAnalyzer:
    """Analyze transformer stress and DNO upgrade avoidance."""
    
    @staticmethod
    def calculate_transformer_upgrade_avoidance(
        baseline_peak_kw: float,
        optimized_peak_kw: float,
        thermal_limit_kw: float = 100.0,
        upgrade_cost_gbp: float = 250000.0,
    ) -> Dict:
        """
        Quantify infrastructure deferral value.
        
        Example:
          Baseline peak: 420 kW (exceeds 100 kW limit)
          Optimized: 330 kW (below limit)
          Upgrade cost: £250k
          Deferral value: £250k (upgrade avoided)
        
        Returns:
            Dict with upgrade_needed, upgrade_deferred, financial_value_£
        """
        baseline_exceeds = baseline_peak_kw > thermal_limit_kw
        optimized_compliant = optimized_peak_kw <= thermal_limit_kw
        
        if baseline_exceeds and optimized_compliant:
            # Upgrade was needed, now avoided
            return {
                'upgrade_needed_baseline': True,
                'upgrade_avoided': True,
                'financial_value_gbp': upgrade_cost_gbp,
                'baseline_exceedance_kw': baseline_peak_kw - thermal_limit_kw,
                'optimized_headroom_kw': thermal_limit_kw - optimized_peak_kw,
            }
        elif baseline_exceeds and not optimized_compliant:
            # Still need upgrade, but reduced headroom
            return {
                'upgrade_needed_baseline': True,
                'upgrade_avoided': False,
                'financial_value_gbp': 0.0,
                'baseline_exceedance_kw': baseline_peak_kw - thermal_limit_kw,
                'optimized_exceedance_kw': optimized_peak_kw - thermal_limit_kw,
                'exceedance_reduction_kw': baseline_peak_kw - optimized_peak_kw,
            }
        else:
            # No upgrade needed
            return {
                'upgrade_needed_baseline': False,
                'upgrade_avoided': False,
                'financial_value_gbp': 0.0,
                'baseline_headroom_kw': thermal_limit_kw - baseline_peak_kw,
                'optimized_headroom_kw': thermal_limit_kw - optimized_peak_kw,
            }


class MetricsCalculator:
    """Unified metrics calculation from results."""
    
    def __init__(self, transformer_capacity_kw: float = 100.0):
        """Initialize metrics calculator."""
        self.transformer_capacity_kw = transformer_capacity_kw
    
    def calculate_scenario_kpis(
        self,
        results_df: pd.DataFrame,
        scenario_name: str = "scenario",
    ) -> Dict:
        """Calculate all KPIs for a scenario."""
        
        # Ensure we have required columns
        if 'net_load_kw' not in results_df.columns:
            # Reconstruct if missing
            results_df['net_load_kw'] = results_df['demand_total_kw'] - results_df.get('pv_generation_kw', 0)
        
        kpis = {
            'scenario': scenario_name,
            'num_homes': results_df['home_id'].nunique(),
            'num_days': (results_df['timestamp'].max() - results_df['timestamp'].min()).days,
            
            # Cost metrics
            'total_cost_gbp': CostAnalyzer.calculate_total_cost(results_df),
            'cost_per_home_gbp': CostAnalyzer.calculate_cost_per_home(results_df).mean(),
            'unit_cost_gbp_per_kwh': CostAnalyzer.calculate_unit_cost(results_df),
            
            # Peak metrics
            'estate_peak_kw': PeakAnalyzer.calculate_estate_peak_load(results_df),
            'peak_95th_percentile_kw': PeakAnalyzer.calculate_peak_percentile(results_df, 95),
            'transformer_headroom_kw': PeakAnalyzer.calculate_transformer_headroom(results_df, self.transformer_capacity_kw),
            'overload_frequency_timesteps': PeakAnalyzer.calculate_overload_frequency(results_df, self.transformer_capacity_kw),
            'load_volatility_std_kw': PeakAnalyzer.calculate_load_volatility(results_df),
            
            # Carbon metrics
            'total_co2_kg': CarbonAnalyzer.calculate_total_emissions(results_df),
            'co2_per_home_kg': CarbonAnalyzer.calculate_emissions_per_home(results_df).mean(),
            'emissions_intensity_gco2_per_kwh': CarbonAnalyzer.calculate_emissions_intensity(results_df),
        }
        
        return kpis
    
    def calculate_comparison_metrics(
        self,
        baseline_kpis: Dict,
        optimized_kpis: Dict,
        num_homes: int = 50,
        upgrade_cost_gbp: float = 250000.0,
    ) -> Dict:
        """Compare baseline vs optimized scenario."""
        
        # Absolute reductions
        cost_reduction_gbp = baseline_kpis['total_cost_gbp'] - optimized_kpis['total_cost_gbp']
        cost_reduction_pct = 100 * cost_reduction_gbp / baseline_kpis['total_cost_gbp']
        cost_per_home_reduction = cost_reduction_gbp / num_homes
        
        peak_reduction_kw = baseline_kpis['estate_peak_kw'] - optimized_kpis['estate_peak_kw']
        peak_reduction_pct = 100 * peak_reduction_kw / baseline_kpis['estate_peak_kw']
        
        co2_reduction_kg = baseline_kpis['total_co2_kg'] - optimized_kpis['total_co2_kg']
        co2_reduction_pct = 100 * co2_reduction_kg / baseline_kpis['total_co2_kg']
        
        # Transformer metrics
        tx_analysis = TransformerAnalyzer.calculate_transformer_upgrade_avoidance(
            baseline_peak_kw=baseline_kpis['estate_peak_kw'],
            optimized_peak_kw=optimized_kpis['estate_peak_kw'],
            thermal_limit_kw=self.transformer_capacity_kw,
            upgrade_cost_gbp=upgrade_cost_gbp,
        )
        
        return {
            'cost_reduction_gbp': cost_reduction_gbp,
            'cost_reduction_pct': cost_reduction_pct,
            'cost_reduction_per_home_gbp': cost_per_home_reduction,
            'peak_reduction_kw': peak_reduction_kw,
            'peak_reduction_pct': peak_reduction_pct,
            'co2_reduction_kg': co2_reduction_kg,
            'co2_reduction_pct': co2_reduction_pct,
            'co2_reduction_per_home_kg': co2_reduction_kg / num_homes,
            'transformer_upgrade_avoidance_gbp': tx_analysis['financial_value_gbp'],
            'transformer_upgrade_avoidance_per_home_gbp': tx_analysis['financial_value_gbp'] / num_homes if tx_analysis['financial_value_gbp'] > 0 else 0.0,
            'load_volatility_reduction_pct': 100 * (baseline_kpis['load_volatility_std_kw'] - optimized_kpis['load_volatility_std_kw']) / baseline_kpis['load_volatility_std_kw'],
            'transformer_analysis': tx_analysis,
        }


class StatisticalValidator:
    """Statistical significance testing for results."""
    
    @staticmethod
    def monte_carlo_confidence_interval(
        values: List[float],
        confidence: float = 0.95,
        num_bootstrap: int = 500,
    ) -> Dict:
        """
        Bootstrap confidence interval.
        
        Returns:
            Dict with mean, std, lower, upper, ci_width
        """
        rng = np.random.default_rng()
        bootstrap_means = []
        
        for _ in range(num_bootstrap):
            sample = rng.choice(values, size=len(values), replace=True)
            bootstrap_means.append(sample.mean())
        
        bootstrap_means = np.array(bootstrap_means)
        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, alpha / 2 * 100)
        upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)
        
        return {
            'mean': np.mean(values),
            'std': np.std(values),
            'lower_ci': lower,
            'upper_ci': upper,
            'ci_width': upper - lower,
            'confidence_level': confidence,
        }
    
    @staticmethod
    def energy_balance_check(results_df: pd.DataFrame, tolerance_pct: float = 0.5) -> Dict:
        """
        Validate energy conservation: Import + PV = Demand + Export + Δ SOC
        
        Returns:
            Dict with errors_pct, violations, status
        """
        results = {}
        
        for home_id in results_df['home_id'].unique():
            home_data = results_df[results_df['home_id'] == home_id].sort_values('timestamp')
            
            # Daily aggregation
            daily_groups = home_data.groupby(home_data['timestamp'].dt.date)
            
            violations = 0
            for date, day_data in daily_groups:
                daily_import = day_data[day_data['net_load_kw'] > 0]['net_load_kw'].sum() * 0.5
                daily_pv = day_data['pv_generation_kw'].sum() * 0.5
                daily_demand = day_data['demand_total_kw'].sum() * 0.5
                daily_export = day_data[day_data['net_load_kw'] < 0]['net_load_kw'].sum() * -0.5
                
                soc_initial = day_data.iloc[0].get('battery_soc_kwh', 0)
                soc_final = day_data.iloc[-1].get('battery_soc_kwh', 0)
                delta_soc = soc_final - soc_initial
                
                # Balance check
                lhs = daily_import + daily_pv
                rhs = daily_demand + daily_export + delta_soc
                error_pct = 100 * abs(lhs - rhs) / max(lhs, rhs) if max(lhs, rhs) > 0 else 0
                
                if error_pct > tolerance_pct:
                    violations += 1
            
            results[home_id] = {
                'balance_violations': violations,
                'total_days': len(daily_groups),
                'violation_rate_pct': 100 * violations / len(daily_groups),
            }
        
        overall_violation_rate = sum(r['balance_violations'] for r in results.values()) / sum(r['total_days'] for r in results.values()) if results else 0
        
        return {
            'per_home': results,
            'overall_violation_rate_pct': overall_violation_rate * 100,
            'status': 'PASS' if overall_violation_rate < tolerance_pct / 100 else 'FAIL',
        }


if __name__ == "__main__":
    # Test metrics calculation
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Create dummy results
    timestamps = pd.date_range('2024-01-01', periods=96, freq='30min')
    data = []
    for t in timestamps:
        for home_id in ['H001', 'H002']:
            data.append({
                'timestamp': t,
                'home_id': home_id,
                'cumulative_cost_£': np.random.normal(50, 10),
                'cumulative_co2_kg': np.random.normal(100, 20),
                'demand_total_kw': np.random.exponential(1.5),
                'pv_generation_kw': max(0, np.random.normal(3, 2)),
                'net_load_kw': np.random.normal(2, 1),
                'battery_soc_kwh': np.random.uniform(2, 8),
            })
    
    df = pd.DataFrame(data)
    
    calc = MetricsCalculator()
    baseline_kpis = calc.calculate_scenario_kpis(df, 'baseline')
    print("Baseline KPIs:")
    for k, v in baseline_kpis.items():
        print(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
