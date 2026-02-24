"""
Tests for simulation engines: baseline and optimization.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.household import HouseholdConfig
from data.generators import generate_simulation_data
from simulation.baseline_engine import BaselineSimulator, EstateBaselineSimulator
from simulation.estate_simulator import EstateSimulator
from metrics.analyzer import MetricsCalculator


@pytest.fixture
def sample_config():
    """Standard household config."""
    return HouseholdConfig(
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


@pytest.fixture
def sim_data():
    """Generate small test dataset."""
    return generate_simulation_data(num_days=2, num_homes=3)


class TestBaselineSimulator:
    """Test baseline greedy heuristic."""
    
    def test_baseline_runs_without_error(self, sample_config, sim_data):
        """Baseline should run and return DataFrame."""
        configs = {f"H{i}": sample_config for i in range(3)}
        
        baseline = BaselineSimulator(
            home_configs=configs,
            sim_data=sim_data,
        )
        
        results = baseline.run_one_day(day_data=sim_data.head(48))
        
        assert isinstance(results, pd.DataFrame)
        assert len(results) > 0
    
    def test_baseline_columns_present(self, sample_config, sim_data):
        """Results should have required columns."""
        configs = {f"H{i}": sample_config for i in range(3)}
        
        baseline = BaselineSimulator(
            home_configs=configs,
            sim_data=sim_data,
        )
        
        results = baseline.run_one_day(day_data=sim_data.head(48))
        
        required_cols = ['home_id', 'timestamp', 'demand_total_kw', 'pv_generation_kw']
        for col in required_cols:
            assert col in results.columns
    
    def test_estate_baseline_aggregates(self, sample_config, sim_data):
        """Estate baseline should aggregate KPIs."""
        configs = {f"H{i}": sample_config for i in range(3)}
        
        estate_baseline = EstateBaselineSimulator(
            home_configs=configs,
            sim_data=sim_data,
        )
        
        results = estate_baseline.run()
        
        assert isinstance(results, pd.DataFrame)
        assert len(results) > 0
        assert 'cumulative_cost_£' in results.columns
        assert 'cumulative_co2_kg' in results.columns


class TestMetricsCalculation:
    """Test metrics analysis."""
    
    def test_metrics_calculator_computes_kpis(self, sample_config, sim_data):
        """Metrics should calculate cost, peak, carbon."""
        # Create minimal results dataframe
        configs = {f"H{i}": sample_config for i in range(3)}
        estate_baseline = EstateBaselineSimulator(
            home_configs=configs,
            sim_data=sim_data,
        )
        results = estate_baseline.run()
        
        calc = MetricsCalculator(transformer_capacity_kw=100.0)
        kpis = calc.calculate_scenario_kpis(results, scenario_name="test")
        
        assert 'total_cost_£' in kpis
        assert 'estate_peak_kw' in kpis
        assert 'total_co2_kg' in kpis
        assert kpis['total_cost_£'] > 0
        assert kpis['total_co2_kg'] > 0
    
    def test_comparison_metrics(self, sample_config, sim_data):
        """Comparison should show delta between scenarios."""
        configs = {f"H{i}": sample_config for i in range(3)}
        estate_baseline = EstateBaselineSimulator(
            home_configs=configs,
            sim_data=sim_data,
        )
        results = estate_baseline.run()
        
        calc = MetricsCalculator(transformer_capacity_kw=100.0)
        baseline_kpis = calc.calculate_scenario_kpis(results, "baseline")
        
        # Create "optimized" by slightly reducing values
        optimized_results = results.copy()
        optimized_results['cumulative_cost_£'] *= 0.95
        optimized_results['cumulative_co2_kg'] *= 0.90
        optimized_results['net_load_kw'] *= 0.95
        
        optimized_kpis = calc.calculate_scenario_kpis(optimized_results, "optimized")
        
        comparison = calc.calculate_comparison_metrics(baseline_kpis, optimized_kpis, num_homes=3)
        
        assert comparison['cost_reduction_£'] > 0
        assert comparison['cost_reduction_pct'] > 0
        assert comparison['peak_reduction_kw'] > 0
        assert comparison['co2_reduction_kg'] > 0


class TestEstateSimulator:
    """Test full estate simulation."""
    
    def test_estate_simulator_initialization(self):
        """Simulator should initialize with defaults."""
        sim = EstateSimulator(
            num_homes=5,
            num_days=2,
            transformer_capacity_kw=100.0,
            seed=42,
        )
        
        assert sim.num_homes == 5
        assert sim.num_days == 2
        assert len(sim.home_configs) == 5
    
    def test_baseline_simulation_completes(self):
        """Baseline simulation should run without error."""
        sim = EstateSimulator(
            num_homes=3,
            num_days=1,
            transformer_capacity_kw=100.0,
            seed=42,
        )
        
        sim.generate_simulation_inputs()
        results = sim.run_baseline_scenario()
        
        assert isinstance(results, pd.DataFrame)
        assert len(results) > 0
    
    def test_metrics_calculated(self):
        """Metrics should be computed after simulation."""
        sim = EstateSimulator(
            num_homes=3,
            num_days=1,
            transformer_capacity_kw=100.0,
            seed=42,
        )
        
        sim.generate_simulation_inputs()
        sim.run_baseline_scenario()
        
        baseline_kpis, _, _ = sim.calculate_metrics()
        
        assert baseline_kpis is not None
        assert 'total_cost_£' in baseline_kpis
        assert baseline_kpis['total_cost_£'] > 0


class TestTransformerUpgradeAvoidance:
    """Test transformer constraint handling."""
    
    def test_upgrade_avoidance_calculation(self):
        """Should detect when upgrade is avoided."""
        from metrics.analyzer import TransformerAnalyzer
        
        result = TransformerAnalyzer.calculate_transformer_upgrade_avoidance(
            baseline_peak_kw=420.0,
            optimized_peak_kw=330.0,
            thermal_limit_kw=350.0,
            upgrade_cost_£=250000.0,
        )
        
        assert result['upgrade_avoided'] == True
        assert result['financial_value_£'] == 250000.0
    
    def test_upgrade_still_needed(self):
        """Should detect when upgrade still needed."""
        from metrics.analyzer import TransformerAnalyzer
        
        result = TransformerAnalyzer.calculate_transformer_upgrade_avoidance(
            baseline_peak_kw=420.0,
            optimized_peak_kw=380.0,  # Still above limit
            thermal_limit_kw=350.0,
            upgrade_cost_£=250000.0,
        )
        
        assert result['upgrade_avoided'] == False
        assert result['financial_value_£'] == 0.0
    
    def test_upgrade_not_needed(self):
        """Should detect when no upgrade needed."""
        from metrics.analyzer import TransformerAnalyzer
        
        result = TransformerAnalyzer.calculate_transformer_upgrade_avoidance(
            baseline_peak_kw=80.0,  # Well below limit
            optimized_peak_kw=70.0,
            thermal_limit_kw=100.0,
            upgrade_cost_£=250000.0,
        )
        
        assert result['upgrade_avoided'] == False
        assert result['financial_value_£'] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
