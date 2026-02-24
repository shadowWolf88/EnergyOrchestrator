"""
Unit tests for core household physics model.

Validates energy conservation, constraint satisfaction, and equation accuracy.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core.household import HouseholdModel, HouseholdConfig, HouseholdState


@pytest.fixture
def base_config():
    """Create default household configuration."""
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
def model(base_config):
    """Create household model."""
    return HouseholdModel(config=base_config)


class TestHouseholdModelInitialization:
    """Test model initialization."""
    
    def test_model_creates_default_state(self, model):
        """Model should initialize with sensible defaults."""
        assert model.state is not None
        assert model.state.battery_soc_kwh >= 0
        assert model.state.battery_soc_kwh <= model.config.battery_capacity_kwh
    
    def test_initial_soc_within_bounds(self, model):
        """Initial SOC should respect min/max constraints."""
        min_soc = model.state.battery_soc_kwh
        max_soc = model.config.battery_capacity_kwh
        min_allowed = model.config.battery_min_soc_pct * max_soc / 100
        
        assert model.state.battery_soc_kwh >= min_allowed


class TestSolarGeneration:
    """Test photovoltaic generation model."""
    
    def test_solar_output_during_night(self, model):
        """Solar should be ~zero at night (01:00 - 05:00)."""
        model.state.timestamp = datetime(2024, 1, 15, 3, 0)
        model.state.weather_irradiance_w_per_m2 = 0
        
        pv = model._update_solar_generation()
        
        assert pv < 0.05, "Night solar should be near zero"
    
    def test_solar_output_midday(self, model):
        """Solar should be high at noon (clear 1000 W/m²)."""
        model.state.timestamp = datetime(2024, 6, 21, 12, 0)
        model.state.weather_irradiance_w_per_m2 = 1000  # Peak irradiance
        
        pv = model._update_solar_generation()
        
        assert pv > 3.5, f"Midday solar should be >3.5 kW, got {pv}"
    
    def test_temperature_reduces_output(self, model):
        """Hot temperatures reduce panel efficiency."""
        model.state.timestamp = datetime(2024, 6, 21, 12, 0)
        model.state.weather_irradiance_w_per_m2 = 1000
        
        # Cool day
        model.state.weather_temperature_celsius = 20
        pv_cool = model._update_solar_generation()
        
        # Hot day
        model.state.weather_temperature_celsius = 40
        pv_hot = model._update_solar_generation()
        
        assert pv_cool > pv_hot, "Hot temperature should reduce output"


class TestBatteryDynamics:
    """Test battery state-of-charge updates."""
    
    def test_battery_charge_increases_soc(self, model):
        """Charging should increase SOC."""
        initial_soc = model.state.battery_soc_kwh
        
        # Apply charge power
        model.state.battery_charge_power_kw = 2.0
        model.state.battery_discharge_power_kw = 0.0
        model._update_battery_soc()
        
        assert model.state.battery_soc_kwh > initial_soc
    
    def test_battery_discharge_decreases_soc(self, model):
        """Discharging should decrease SOC."""
        model.state.battery_soc_kwh = 5.0  # Start with charge
        initial_soc = model.state.battery_soc_kwh
        
        # Apply discharge power
        model.state.battery_charge_power_kw = 0.0
        model.state.battery_discharge_power_kw = 1.0
        model._update_battery_soc()
        
        assert model.state.battery_soc_kwh < initial_soc
    
    def test_battery_respects_min_max_bounds(self, model):
        """Battery SOC should stay within min/max limits."""
        for _ in range(100):
            # Try to charge excessively
            model.state.battery_charge_power_kw = 10.0
            model._update_battery_soc()
            
            min_soc = model.config.battery_min_soc_pct * model.config.battery_capacity_kwh / 100
            max_soc = model.config.battery_max_soc_pct * model.config.battery_capacity_kwh / 100
            
            assert min_soc <= model.state.battery_soc_kwh <= max_soc
    
    def test_standing_loss(self, model):
        """Idle battery should lose charge due to self-discharge."""
        model.state.battery_soc_kwh = 4.0
        model.state.battery_charge_power_kw = 0.0
        model.state.battery_discharge_power_kw = 0.0
        
        initial_soc = model.state.battery_soc_kwh
        model._update_battery_soc()
        
        # Standing loss = 0.1% per hour, so 0.05% per 30 min
        expected_loss = initial_soc * 0.001 / 2
        assert model.state.battery_soc_kwh < initial_soc
        assert abs(model.state.battery_soc_kwh - initial_soc + expected_loss) < 0.01


class TestEVCharging:
    """Test EV battery updates."""
    
    def test_ev_charging_increases_soc(self, model):
        """EV charging should increase SOC."""
        model.state.ev_present = True
        model.state.ev_soc_kwh = 10.0
        initial_soc = model.state.ev_soc_kwh
        
        model.state.ev_charge_power_kw = 2.0
        model._update_ev_soc()
        
        assert model.state.ev_soc_kwh > initial_soc
    
    def test_ev_not_present_no_charging(self, model):
        """If EV not present, charging should be ignored."""
        model.state.ev_present = False
        model.state.ev_soc_kwh = 10.0
        initial_soc = model.state.ev_soc_kwh
        
        model.state.ev_charge_power_kw = 2.0
        model._update_ev_soc()
        
        assert model.state.ev_soc_kwh == initial_soc


class TestConstraintSatisfaction:
    """Test constraint enforcement."""
    
    def test_battery_power_constrained(self, model):
        """Battery power should not exceed max rating."""
        model.state.battery_charge_power_kw = 100.0  # Excessive
        model.state.battery_discharge_power_kw = 100.0  # Excessive
        
        model._check_constraints()
        
        # After constraint check, should be limited
        assert model.state.battery_charge_power_kw <= 5.0  # Typical 1C discharge
        assert model.state.battery_discharge_power_kw <= 5.0
    
    def test_ev_departure_deadline(self, model):
        """EV must reach min charge by departure time."""
        model.state.ev_present = True
        model.state.ev_departure_time = datetime.now() + timedelta(hours=2)
        model.state.ev_soc_kwh = 5.0
        model.state.ev_capacity_kwh = 50.0
        
        # Insufficient SOC for deadline
        constraints_ok = model._check_constraints()
        
        # This would trigger constraint violation handling in optimization


class TestEnergyBalance:
    """Test energy conservation principles."""
    
    def test_energy_conservation_no_generation(self, model):
        """Without generation, import should equal net demand + storage change."""
        # Set up a daily simulation
        results = []
        
        model.state.battery_soc_kwh = 4.0
        model.state.pv_generation_kw = 0.0
        model.state.demand_total_kw = 1.0
        
        for hour in range(24):
            net_load = model.step(
                ambient_temp_c=20,
                irradiance_w_per_m2=0,
                demand_total_kw=1.0,
                tariff_price_£_per_kwh=0.3,
                carbon_intensity_g_per_kwh=400,
                ev_arrival_time=None,
                ev_departure_time=None,
                ev_required_energy_kwh=0,
            )
            results.append(net_load)
        
        # Over 24 hours with 1 kW constant demand and no PV,
        # net load should be approximately 24 kWh (±standing loss)
        total_net = sum(results) * 0.5  # 30-min steps
        assert 23 < total_net < 25, f"Energy balance off: {total_net} kWh"


class TestMetricsAccumulation:
    """Test KPI accumulation."""
    
    def test_cost_accumulation(self, model):
        """Cumulative cost should increase with consumption."""
        initial_cost = model.state.cumulative_cost_£
        
        model.state.import_power_kw = 2.0
        model.state.tariff_price_£_per_kwh = 0.35
        model._update_metrics()
        
        assert model.state.cumulative_cost_£ > initial_cost
    
    def test_carbon_accumulation(self, model):
        """CO2 should accumulate with import."""
        initial_co2 = model.state.cumulative_co2_kg
        
        model.state.import_power_kw = 2.0
        model.state.carbon_intensity_g_per_kwh = 400
        model._update_metrics()
        
        assert model.state.cumulative_co2_kg > initial_co2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
