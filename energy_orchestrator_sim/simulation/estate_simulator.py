# -*- coding: utf-8 -*-
"""
End-to-end estate simulation framework.

Orchestrates baseline vs optimization scenarios across multiple homes and days.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

from core.household import HouseholdModel, HouseholdConfig
from data.generators import generate_simulation_data
from simulation.baseline_engine import EstateBaselineSimulator
from simulation.optimization_engine import EstateOptimizer, OptimizationConfig
from metrics.analyzer import MetricsCalculator, StatisticalValidator

logger = logging.getLogger(__name__)


class EstateSimulator:
    """
    Full estate simulation: baseline vs optimization comparison.
    
    Workflow:
    1. Generate synthetic data (weather, demand, prices, EV arrivals)
    2. Run baseline greedy heuristic simulation
    3. Run MILP optimization across all homes
    4. Calculate KPIs and statistical validation
    5. Generate comparison report
    """
    
    def __init__(
        self,
        num_homes: int = 50,
        num_days: int = 30,
        transformer_capacity_kw: float = 100.0,
        transformer_upgrade_cost_gbp: float = 250000.0,
        seed: Optional[int] = None,
    ):
        """Initialize simulator."""
        self.num_homes = num_homes
        self.num_days = num_days
        self.transformer_capacity_kw = transformer_capacity_kw
        self.transformer_upgrade_cost_gbp = transformer_upgrade_cost_gbp
        
        if seed is not None:
            np.random.seed(seed)
        
        self.home_configs = self._generate_home_configs()
        self.sim_data = None
        self.baseline_results = None
        self.optimization_results = None
        self.baseline_kpis = None
        self.optimization_kpis = None
        self.comparison_metrics = None
    
    def _generate_home_configs(self) -> Dict[str, HouseholdConfig]:
        """Create household configurations (modest variation)."""
        configs = {}
        
        # Base configuration
        base_config = HouseholdConfig(
            pv_capacity_kwp=4.0,
            battery_capacity_kwh=8.0,
            battery_min_soc_pct=20,
            battery_max_soc_pct=95,
            battery_charge_efficiency_pct=92,
            battery_discharge_efficiency_pct=95,
            battery_standing_loss_pct_per_hour=0.1,
            ev_charger_rating_kw=3.6,
            ev_min_soc_pct=10,
            heat_pump_capacity_kw=3.0,
            heat_pump_cop=3.5,
            thermal_mass_kwh=5.0,
        )
        
        # Vary by 10-15% across homes
        for i in range(self.num_homes):
            home_id = f"H{i+1:04d}"
            scalar = max(0.85, min(1.15, np.random.normal(1.0, 0.08)))
            
            configs[home_id] = HouseholdConfig(
                pv_capacity_kwp=base_config.pv_capacity_kwp * scalar,
                battery_capacity_kwh=base_config.battery_capacity_kwh * scalar,
                battery_min_soc_pct=base_config.battery_min_soc_pct,
                battery_max_soc_pct=base_config.battery_max_soc_pct,
                battery_charge_efficiency_pct=base_config.battery_charge_efficiency_pct,
                battery_discharge_efficiency_pct=base_config.battery_discharge_efficiency_pct,
                battery_standing_loss_pct_per_hour=base_config.battery_standing_loss_pct_per_hour,
                ev_charger_rating_kw=base_config.ev_charger_rating_kw,
                ev_min_soc_pct=base_config.ev_min_soc_pct,
                heat_pump_capacity_kw=base_config.heat_pump_capacity_kw * scalar,
                heat_pump_cop=base_config.heat_pump_cop,
                thermal_mass_kwh=base_config.thermal_mass_kwh * scalar,
            )
        
        return configs
    
    def generate_simulation_inputs(self) -> pd.DataFrame:
        """Generate synthetic data for all households."""
        logger.info(f"Generating simulation data: {self.num_homes} homes, {self.num_days} days")
        
        self.sim_data = generate_simulation_data(
            num_days=self.num_days,
            num_homes=self.num_homes,
        )
        
        logger.info(f"Generated {len(self.sim_data)} rows of simulation data")
        return self.sim_data
    
    def run_baseline_scenario(self) -> pd.DataFrame:
        """Run greedy baseline heuristics."""
        logger.info("Running baseline scenario...")
        
        if self.sim_data is None:
            self.generate_simulation_inputs()
        
        baseline_engine = EstateBaselineSimulator(
            home_configs=self.home_configs,
            sim_data=self.sim_data,
        )
        
        self.baseline_results = baseline_engine.run()
        logger.info(f"Baseline complete: {len(self.baseline_results)} rows")
        
        return self.baseline_results
    
    def run_optimization_scenario(self) -> pd.DataFrame:
        """Run MILP optimization."""
        logger.info("Running optimization scenario...")
        
        if self.sim_data is None:
            self.generate_simulation_inputs()
        
        opt_config = OptimizationConfig(
            solver_time_limit_seconds=60,
            solver_relative_gap_tolerance=0.001,
            objective_weight_cost=1.0,
            objective_weight_transformer_stress=1000.0,
            objective_weight_volatility_penalty=10.0,
            objective_weight_battery_degradation=1.0,
            objective_weight_carbon_cost=0.01,
        )
        
        optimizer = EstateOptimizer(
            home_configs=self.home_configs,
            sim_data=self.sim_data,
            config=opt_config,
            transformer_capacity_kw=self.transformer_capacity_kw,
        )
        
        self.optimization_results = optimizer.optimize()
        logger.info(f"Optimization complete: {len(self.optimization_results)} rows")
        
        return self.optimization_results
    
    def calculate_metrics(self) -> Tuple[Dict, Dict, Dict]:
        """Calculate KPIs for both scenarios."""
        logger.info("Calculating metrics...")
        
        metrics_calc = MetricsCalculator(
            transformer_capacity_kw=self.transformer_capacity_kw
        )
        
        self.baseline_kpis = metrics_calc.calculate_scenario_kpis(
            self.baseline_results,
            scenario_name="baseline",
        )
        
        self.optimization_kpis = metrics_calc.calculate_scenario_kpis(
            self.optimization_results,
            scenario_name="optimized",
        )
        
        self.comparison_metrics = metrics_calc.calculate_comparison_metrics(
            baseline_kpis=self.baseline_kpis,
            optimized_kpis=self.optimization_kpis,
            num_homes=self.num_homes,
            upgrade_cost_gbp=self.transformer_upgrade_cost_gbp,
        )
        
        return self.baseline_kpis, self.optimization_kpis, self.comparison_metrics
    
    def validate_results(self) -> Dict:
        """Statistical validation of results."""
        logger.info("Validating results...")
        
        validator = StatisticalValidator()
        
        # Energy balance check
        baseline_balance = validator.energy_balance_check(self.baseline_results)
        optimization_balance = validator.energy_balance_check(self.optimization_results)
        
        # Confidence intervals for key metrics
        baseline_costs = self.baseline_results.groupby('home_id')['cumulative_cost_gbp'].last().values
        optimization_costs = self.optimization_results.groupby('home_id')['cumulative_cost_gbp'].last().values
        
        cost_ci_baseline = validator.monte_carlo_confidence_interval(baseline_costs.tolist())
        cost_ci_optimized = validator.monte_carlo_confidence_interval(optimization_costs.tolist())
        
        return {
            'baseline_energy_balance': baseline_balance,
            'optimization_energy_balance': optimization_balance,
            'baseline_cost_ci': cost_ci_baseline,
            'optimized_cost_ci': cost_ci_optimized,
        }
    
    def run_full_simulation(self) -> Dict:
        """Execute complete baseline → optimization → analysis workflow."""
        logger.info("=" * 80)
        logger.info("ESTATE SIMULATION: BASELINE vs OPTIMIZATION")
        logger.info("=" * 80)
        
        # Generate inputs
        self.generate_simulation_inputs()
        
        # Run scenarios
        self.run_baseline_scenario()
        self.run_optimization_scenario()
        
        # Calculate metrics
        baseline_kpis, opt_kpis, comparison = self.calculate_metrics()
        
        # Validate
        validation = self.validate_results()
        
        # Compile report
        report = {
            'simulation_config': {
                'num_homes': self.num_homes,
                'num_days': self.num_days,
                'transformer_capacity_kw': self.transformer_capacity_kw,
                'transformer_upgrade_cost_gbp': self.transformer_upgrade_cost_gbp,
            },
            'baseline_kpis': baseline_kpis,
            'optimization_kpis': opt_kpis,
            'comparison': comparison,
            'validation': validation,
        }
        
        # Log summary
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: Dict):
        """Print summary to logs."""
        config = report['simulation_config']
        comp = report['comparison']
        
        logger.info("=" * 80)
        logger.info("SIMULATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Homes: {config['num_homes']}, Days: {config['num_days']}")
        logger.info(f"Transformer capacity: {config['transformer_capacity_kw']} kW")
        logger.info("")
        logger.info("COST IMPACT")
        logger.info(f"  Reduction: £{comp['cost_reduction_£']:.2f} ({comp['cost_reduction_pct']:.1f}%)")
        logger.info(f"  Per home: £{comp['cost_reduction_per_home_£']:.2f}")
        logger.info("")
        logger.info("PEAK LOAD REDUCTION")
        logger.info(f"  Reduction: {comp['peak_reduction_kw']:.1f} kW ({comp['peak_reduction_pct']:.1f}%)")
        logger.info(f"  Baseline peak: {report['baseline_kpis']['estate_peak_kw']:.1f} kW")
        logger.info(f"  Optimized peak: {report['optimization_kpis']['estate_peak_kw']:.1f} kW")
        logger.info(f"  Transformer capacity: {config['transformer_capacity_kw']} kW")
        logger.info("")
        logger.info("TRANSFORMER IMPACT (PRIMARY VALUE)")
        if comp['transformer_upgrade_avoidance_gbp'] > 0:
            logger.info(f"  ✓ Upgrade AVOIDED")
            logger.info(f"  Financial value: GBP {comp['transformer_upgrade_avoidance_gbp']:.0f}")
            logger.info(f"  Per home value: GBP {comp['transformer_upgrade_avoidance_per_home_gbp']:.2f}")
        else:
            logger.info(f"  Upgrade still required or unnecessary")
            logger.info(f"  Financial value: GBP 0")
        
        logger.info("")
        logger.info("CARBON IMPACT")
        logger.info(f"  Reduction: {comp['co2_reduction_kg']:.0f} kg ({comp['co2_reduction_pct']:.1f}%)")
        logger.info(f"  Per home: {comp['co2_reduction_per_home_kg']:.1f} kg")
        logger.info("")
        logger.info("VALIDATION")
        if report['validation']['baseline_energy_balance']['status'] == 'PASS':
            logger.info(f"  ✓ Energy balance check PASSED")
        else:
            logger.info(f"  ✗ Energy balance check FAILED")
        logger.info("=" * 80)
    
    def export_results(self, prefix: str = "simulation_results"):
        """Export results to CSV files."""
        baseline_file = f"{prefix}_baseline.csv"
        optimization_file = f"{prefix}_optimized.csv"
        
        self.baseline_results.to_csv(baseline_file, index=False)
        self.optimization_results.to_csv(optimization_file, index=False)
        
        logger.info(f"Exported baseline to {baseline_file}")
        logger.info(f"Exported optimization to {optimization_file}")


if __name__ == "__main__":
    # Example usage
    sim = EstateSimulator(
        num_homes=10,
        num_days=7,
        transformer_capacity_kw=100.0,
        seed=42,
    )
    
    report = sim.run_full_simulation()
    sim.export_results("test_simulation")
