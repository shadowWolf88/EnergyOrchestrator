# -*- coding: utf-8 -*-
"""
Core household and asset models.

Implements physics-based modelling of residential energy assets including
solar generation, battery storage, EV charging, and demand profiles.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class HouseholdConfig:
    """Configuration for a single household."""
    
    home_id: str
    latitude: float = 52.6  # Nottinghamshire default
    longitude: float = -1.1
    
    # PV System
    pv_capacity_kwp: float = 10.0  # 5-15 kWp typical
    pv_orientation: str = "south"  # south, southwest, southeast
    pv_tilt_degrees: float = 30.0
    pv_efficiency: float = 0.20  # 20% module efficiency
    
    # Battery System
    battery_capacity_kwh: float = 10.0  # 5-15 kWh typical
    battery_power_kw: float = 5.0  # 3-10 kW
    battery_efficiency_charge: float = 0.95
    battery_efficiency_discharge: float = 0.95
    battery_standing_loss_pct_per_hour: float = 0.1
    
    # EV Charger
    has_ev: bool = True
    ev_charger_rating_kw: float = 7.4  # Type 2: 3.6-7.4 kW
    ev_battery_capacity_kwh: float = 60.0  # Typical BEV
    
    # Heat Pump (optional)
    has_heat_pump: bool = False
    heat_pump_capacity_kw: float = 10.0
    
    # General
    timezone: str = "Europe/London"


@dataclass
class HouseholdState:
    """Current state of a household at a timestep."""
    
    timestamp: datetime
    
    # Generation
    pv_generation_kw: float = 0.0
    
    # Demand
    demand_base_kw: float = 0.0  # From profile
    demand_appliance_kw: float = 0.0  # Stochastic
    demand_ev_kw: float = 0.0
    demand_heat_pump_kw: float = 0.0
    
    # Assets
    battery_soc_kwh: float = 5.0  # Starts half-charged
    ev_present: bool = False
    ev_soc_kwh: float = 0.0
    ev_required_energy_kwh: float = 30.0
    ev_departure_time: Optional[datetime] = None
    
    # External
    tariff_price_gbp_per_kwh: float = 0.35  # GBP = £
    carbon_intensity_gco2_per_kwh: float = 300.0
    
    # Accumulated metrics
    cumulative_cost_gbp: float = 0.0  # GBP = £
    total_import_kwh: float = 0.0
    total_export_kwh: float = 0.0
    peak_load_kw: float = 0.0
    co2_emitted_kg: float = 0.0
    battery_cycles: float = 0.0  # For degradation tracking


class HouseholdModel:
    """
    Physics-based model of a residential household with distributed energy resources.
    
    Tracks 30-minute timesteps with stochastic demand, solar generation, battery SOC,
    and EV charging constraints.
    """
    
    def __init__(self, config: HouseholdConfig):
        """Initialize household model."""
        self.config = config
        self.state = HouseholdState(timestamp=datetime.now())
        self.logger = logger.getChild(f"Household-{config.home_id}")
        self._rng = np.random.default_rng(seed=hash(config.home_id) % (2**32))
        
    def step(
        self,
        t: datetime,
        irradiance_wm2: float,
        temperature_c: float,
        demand_base_kwh: float,
        tariff_price: float,
        carbon_intensity: float,
        control: Optional[dict] = None,
    ) -> float:
        """
        Execute one 30-minute timestep.
        
        Args:
            t: Timestamp
            irradiance_wm2: Solar irradiance [W/m²]
            temperature_c: Ambient temperature [°C]
            demand_base_kwh: Base demand for 30 min [kWh]
            tariff_price: Tariff [£/kWh]
            carbon_intensity: Grid carbon intensity [gCO₂/kWh]
            control: Dict with optional control actions {
                'battery_charge_kw': float,
                'battery_discharge_kw': float,
                'ev_charge_kw': float,
                'heat_pump_output_kw': float
            }
        
        Returns:
            Net load [kW] (positive = import, negative = export)
        """
        if control is None:
            control = {}
        
        # Update timestamp
        self.state.timestamp = t
        self.state.tariff_price_gbp_per_kwh = tariff_price
        self.state.carbon_intensity_gco2_per_kwh = carbon_intensity
        
        # ===== GENERATION =====
        self._update_solar_generation(irradiance_wm2, temperature_c)
        
        # ===== DEMAND =====
        self.state.demand_base_kw = demand_base_kwh * 2  # Convert 30min to kW
        self.state.demand_appliance_kw = self._sample_appliance_demand()
        
        # EV demand (if present and not fully charged)
        self.state.demand_ev_kw = control.get('ev_charge_kw', 0.0)
        if self.state.demand_ev_kw > 0 and self.state.ev_present:
            self._update_ev_soc(self.state.demand_ev_kw, minutes=30)
        
        # Heat pump demand
        self.state.demand_heat_pump_kw = control.get('heat_pump_output_kw', 0.0)
        
        # ===== BATTERY =====
        battery_in = control.get('battery_charge_kw', 0.0)
        battery_out = control.get('battery_discharge_kw', 0.0)
        self._update_battery_soc(battery_in, battery_out, minutes=30)
        
        # ===== CONSTRAINTS CHECK =====
        violations = self._check_constraints(control)
        if violations:
            self.logger.warning(f"Constraint violations at {t}: {violations}")
        
        # ===== NET LOAD CALCULATION =====
        total_demand = (
            self.state.demand_base_kw + 
            self.state.demand_appliance_kw + 
            self.state.demand_ev_kw + 
            self.state.demand_heat_pump_kw
        )
        
        net_load_kw = total_demand - self.state.pv_generation_kw + battery_out - battery_in
        
        # ===== METRICS UPDATE =====
        self._update_metrics(net_load_kw, tariff_price, carbon_intensity)
        
        return net_load_kw
    
    def _update_solar_generation(self, irradiance_wm2: float, temperature_c: float) -> None:
        """
        Calculate solar generation: P = Prated × (Irradiance/1000) × Efficiency × TempCoeff
        
        Temperature coefficient: -0.4%/°C (typical Si modules)
        """
        temp_coeff = 1.0 - 0.004 * (temperature_c - 25)
        soiling_loss = 0.98  # 2% annual average
        
        self.state.pv_generation_kw = (
            self.config.pv_capacity_kwp * 
            (irradiance_wm2 / 1000.0) * 
            self.config.pv_efficiency *
            temp_coeff *
            soiling_loss
        )
        self.state.pv_generation_kw = max(0.0, self.state.pv_generation_kw)
    
    def _sample_appliance_demand(self) -> float:
        """
        Stochastic appliance demand (cooking, showers, kettle, etc.).
        
        Model as mixture of small random spikes (0-1 kW) with occasional larger loads.
        """
        # 80% chance of small demand, 20% chance of larger spike
        if self._rng.random() < 0.2:
            return self._rng.normal(1.5, 0.5)  # Mean 1.5 kW, std 0.5
        else:
            return self._rng.exponential(0.3)  # Small random spikes
    
    def _update_battery_soc(self, charge_kw: float, discharge_kw: float, minutes: float = 30) -> None:
        """
        Update battery SOC: SOC(t+1) = SOC(t) + ηc·Pc·Δt - Pd·Δt/ηd - Sloss
        """
        dt_hours = minutes / 60.0
        
        # Verify no simultaneous charge/discharge (should be enforced by optimizer)
        if charge_kw > 1e-6 and discharge_kw > 1e-6:
            self.logger.warning(f"Simultaneous charge/discharge detected: C={charge_kw}, D={discharge_kw}")
            discharge_kw = 0.0
        
        # Energy delta
        charge_energy = charge_kw * dt_hours * self.config.battery_efficiency_charge
        discharge_energy = discharge_kw * dt_hours / self.config.battery_efficiency_discharge
        standing_loss = self.config.battery_capacity_kwh * (self.config.battery_standing_loss_pct_per_hour / 100) * dt_hours
        
        # Update SOC
        self.state.battery_soc_kwh = (
            self.state.battery_soc_kwh + 
            charge_energy - 
            discharge_energy - 
            standing_loss
        )
        
        # Clamp to bounds
        self.state.battery_soc_kwh = np.clip(
            self.state.battery_soc_kwh,
            0.0,
            self.config.battery_capacity_kwh
        )
        
        # Track cycles for degradation
        if charge_kw > 0 or discharge_kw > 0:
            energy_cycled = (charge_energy + discharge_energy) / self.config.battery_capacity_kwh
            self.state.battery_cycles += energy_cycled
    
    def _update_ev_soc(self, charge_kw: float, minutes: float = 30) -> None:
        """Update EV battery SOC."""
        if not self.state.ev_present:
            return
        
        dt_hours = minutes / 60.0
        energy_added = charge_kw * dt_hours * 0.95  # 95% charger efficiency
        self.state.ev_soc_kwh = min(
            self.state.ev_soc_kwh + energy_added,
            self.config.ev_battery_capacity_kwh
        )
    
    def _check_constraints(self, control: dict) -> list:
        """Check operational constraints."""
        violations = []
        
        # Battery constraints
        if control.get('battery_charge_kw', 0) > self.config.battery_power_kw + 1e-6:
            violations.append(f"Battery charge exceeds power limit: {control['battery_charge_kw']} > {self.config.battery_power_kw}")
        
        if control.get('battery_discharge_kw', 0) > self.config.battery_power_kw + 1e-6:
            violations.append(f"Battery discharge exceeds power limit: {control['battery_discharge_kw']} > {self.config.battery_power_kw}")
        
        # EV constraints
        if self.state.ev_present and self.state.ev_departure_time:
            if self.state.ev_soc_kwh < self.state.ev_required_energy_kwh and self.state.timestamp >= self.state.ev_departure_time:
                violations.append(f"EV not charged by departure: {self.state.ev_soc_kwh} < {self.state.ev_required_energy_kwh}")
        
        return violations
    
    def _update_metrics(self, net_load_kw: float, tariff: float, carbon_intensity: float) -> None:
        """Update accumulated metrics."""
        dt_hours = 0.5  # 30 minutes
        
        # Cost (tariff + standing charge)
        energy_imported_kwh = max(net_load_kw, 0) * dt_hours
        self.state.cumulative_cost_gbp += energy_imported_kwh * tariff
        self.state.cumulative_cost_gbp += tariff * dt_hours / 48  # Standing charge
        
        # Energy balance
        self.state.total_import_kwh += energy_imported_kwh
        self.state.total_export_kwh += max(-net_load_kw, 0) * dt_hours
        
        # Peak tracking
        self.state.peak_load_kw = max(self.state.peak_load_kw, max(net_load_kw, 0))
        
        # CO₂ emissions
        emissions_kg = max(net_load_kw, 0) * carbon_intensity / 1000
        self.state.co2_emitted_kg += emissions_kg
    
    def reset_ev(self, arrival_time: datetime, departure_time: datetime, required_energy_kwh: float) -> None:
        """Set EV arrival/departure for the day."""
        self.state.ev_present = True
        self.state.ev_departure_time = departure_time
        self.state.ev_required_energy_kwh = required_energy_kwh
        self.state.ev_soc_kwh = 0.0  # Arrives with empty battery
    
    def clear_ev(self) -> None:
        """EV leaves."""
        self.state.ev_present = False
        self.state.ev_soc_kwh = 0.0
        self.state.ev_departure_time = None
    
    def get_state_dict(self) -> dict:
        """Export state as dictionary for metrics/dashboard."""
        return {
            'timestamp': self.state.timestamp,
            'home_id': self.config.home_id,
            'pv_generation_kw': self.state.pv_generation_kw,
            'demand_total_kw': (
                self.state.demand_base_kw + 
                self.state.demand_appliance_kw + 
                self.state.demand_ev_kw + 
                self.state.demand_heat_pump_kw
            ),
            'battery_soc_kwh': self.state.battery_soc_kwh,
            'battery_soc_pct': 100 * self.state.battery_soc_kwh / self.config.battery_capacity_kwh,
            'ev_soc_kwh': self.state.ev_soc_kwh if self.state.ev_present else 0.0,
            'ev_present': self.state.ev_present,
            'tariff_gbp_per_kwh': self.state.tariff_price_gbp_per_kwh,
            'carbon_intensity_gco2_per_kwh': self.state.carbon_intensity_gco2_per_kwh,
            'cumulative_cost_gbp': self.state.cumulative_cost_gbp,
            'peak_load_kw': self.state.peak_load_kw,
            'cumulative_co2_kg': self.state.co2_emitted_kg,
        }
