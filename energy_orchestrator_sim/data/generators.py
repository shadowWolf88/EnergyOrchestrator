# -*- coding: utf-8 -*-
"""
Synthetic data generators for weather, tariffs, demand profiles, and carbon intensity.

Provides realistic UK-based data for simulation scenarios.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class WeatherGenerator:
    """Generate synthetic UK weather data (Nottinghamshire)."""
    
    def __init__(self, seed: int = 42):
        """Initialize weather generator."""
        self.rng = np.random.default_rng(seed)
    
    def generate_daily_weather(
        self,
        date: datetime,
        season: str = "winter"  # winter, spring, summer, autumn
    ) -> pd.DataFrame:
        """
        Generate 30-min resolution weather for a day.
        
        Outputs columns: timestamp, irradiance_wm2, temperature_c, cloud_factor
        """
        # Seasonal parameters [min, max] for daily variation
        season_params = {
            "winter": {"temp_range": (-2, 8), "peak_irradiance": 400, "cloud_prob": 0.6},
            "spring": {"temp_range": (5, 14), "peak_irradiance": 600, "cloud_prob": 0.5},
            "summer": {"temp_range": (14, 22), "peak_irradiance": 800, "cloud_prob": 0.4},
            "autumn": {"temp_range": (8, 16), "peak_irradiance": 500, "cloud_prob": 0.55},
        }
        
        params = season_params[season]
        
        # Intra-day profiles
        timestamps = pd.date_range(date, periods=48, freq="30min")
        
        # Temperature: smooth diurnal cycle
        hours = np.arange(48) * 0.5
        temp_min, temp_max = params["temp_range"]
        temperatures = temp_min + (temp_max - temp_min) * 0.5 * (1 - np.cos(2 * np.pi * hours / 24))
        temperatures += self.rng.normal(0, 0.5, 48)  # Add noise
        
        # Solar irradiance: bell curve during daylight, zero at night
        irradiances = np.zeros(48)
        daylight_hours = np.arange(6 * 2, 18 * 2)  # 06:00 to 18:00
        for i in daylight_hours:
            hour_of_day = (i * 0.5) % 24
            irradiances[i] = params["peak_irradiance"] * np.exp(-(hour_of_day - 12)**2 / 16)
        
        # Add cloud variability
        cloud_factors = np.ones(48)
        if self.rng.random() < params["cloud_prob"]:
            # Cloudy period
            cloud_factors[daylight_hours] *= self.rng.uniform(0.3, 0.8, len(daylight_hours))
        else:
            # Mostly clear
            cloud_factors[daylight_hours] *= self.rng.uniform(0.85, 1.0, len(daylight_hours))
        
        irradiances = irradiances * cloud_factors
        irradiances = np.maximum(irradiances, 0)  # No negative irradiance
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'irradiance_wm2': irradiances,
            'temperature_c': temperatures,
            'cloud_factor': cloud_factors,
        })


class TariffGenerator:
    """Generate time-of-use tariff profiles."""
    
    @staticmethod
    def flat_tariff() -> pd.DataFrame:
        """
        Flat tariff: £0.35/kWh all day.
        """
        timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
        return pd.DataFrame({
            'timestamp': timestamps,
            'tariff_£_per_kwh': 0.35 * np.ones(48),
            'tariff_name': 'Flat',
        })
    
    @staticmethod
    def economy_7() -> pd.DataFrame:
        """
        Economy 7: £0.38/kWh peak (07:30-00:30), £0.16/kWh off-peak (00:30-07:30).
        """
        timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
        hours = timestamps.hour + timestamps.minute / 60
        
        # Off-peak: 00:30 to 07:30
        is_offpeak = (hours >= 0.5) & (hours < 7.5)
        tariffs = np.where(is_offpeak, 0.16, 0.38)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'tariff_£_per_kwh': tariffs,
            'tariff_name': 'Economy 7',
        })
    
    @staticmethod
    def agile_pricing(seed: int = 42) -> pd.DataFrame:
        """
        Agile pricing: £0.10-£0.80/kWh mean-reverting random walk.
        
        Simulates half-hourly dynamic pricing with:
        - Diurnal pattern (higher evenings)
        - Random variability
        - Occasional spike pricing
        """
        rng = np.random.default_rng(seed)
        timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
        hours = timestamps.hour + timestamps.minute / 60
        
        # Base diurnal pattern: higher in evenings (17:00-20:00)
        base_tariff = np.where((hours >= 17) & (hours < 20), 0.50, 0.25)
        base_tariff = np.where((hours >= 0) & (hours < 6), 0.15, base_tariff)  # Night discount
        
        # Add random walk component
        random_walk = np.cumsum(rng.normal(0, 0.03, 48))
        random_walk = (random_walk - random_walk.mean()) * 0.1  # Normalize
        
        # Add occasional spikes
        spike_prob = rng.binomial(1, 0.1, 48)
        spikes = spike_prob * rng.uniform(0.3, 0.5, 48)
        
        tariffs = base_tariff + random_walk + spikes
        tariffs = np.clip(tariffs, 0.10, 0.80)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'tariff_£_per_kwh': tariffs,
            'tariff_name': 'Agile',
        })


class CarbonIntensityGenerator:
    """Generate realistic UK grid carbon intensity."""
    
    @staticmethod
    def synthetic_carbon_intensity(seed: int = 42) -> pd.DataFrame:
        """
        UK grid carbon intensity varies 50-800 gCO₂/kWh.
        
        Patterns:
        - Night (wind/nuclear): 50-150 gCO₂/kWh
        - Day (mix): 150-400 gCO₂/kWh
        - Evening peaks (gas/coal): 400-800 gCO₂/kWh
        - Winter higher than summer
        """
        rng = np.random.default_rng(seed)
        timestamps = pd.date_range('2024-01-01', periods=48, freq='30min')
        hours = timestamps.hour + timestamps.minute / 60
        
        # Base diurnal pattern
        intensity = np.zeros(48)
        intensity[(hours >= 0) & (hours < 6)] = rng.uniform(70, 120, np.sum((hours >= 0) & (hours < 6)))  # Night
        intensity[(hours >= 6) & (hours < 12)] = rng.uniform(150, 300, np.sum((hours >= 6) & (hours < 12)))  # Morning
        intensity[(hours >= 12) & (hours < 17)] = rng.uniform(200, 350, np.sum((hours >= 12) & (hours < 17)))  # Afternoon
        intensity[(hours >= 17) & (hours < 21)] = rng.uniform(400, 700, np.sum((hours >= 17) & (hours < 21)))  # Peak
        intensity[(hours >= 21)] = rng.uniform(250, 450, np.sum((hours >= 21)))  # Evening
        
        # Add smoothing
        intensity = pd.Series(intensity).rolling(window=3, center=True, min_periods=1).mean().values
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'carbon_intensity_gco2_per_kwh': intensity,
        })


class DemandProfileGenerator:
    """Generate realistic UK residential demand profiles (BDUK/CREST basis)."""
    
    def __init__(self, seed: int = 42):
        """Initialize demand profile generator."""
        self.rng = np.random.default_rng(seed)
    
    def generate_base_demand(
        self,
        date: datetime,
        profile_type: str = "typical"  # typical, high, low
    ) -> pd.DataFrame:
        """
        Generate base electricity demand profile [kWh per 30-min].
        
        Typical UK household: 8-12 kWh/day
        Peak periods: 08:00-09:00 (morning), 17:00-20:00 (evening)
        """
        timestamps = pd.date_range(date, periods=48, freq="30min")
        hours = timestamps.hour + timestamps.minute / 60
        
        # Base load shape (from BDUK typical profile)
        base = np.ones(48)
        
        # Morning peak (07:00-09:00): 1.5x average
        base[(hours >= 7) & (hours < 9)] *= 1.8
        
        # Daytime minimum (10:00-16:00): 0.4x average
        base[(hours >= 10) & (hours < 16)] *= 0.5
        
        # Evening peak (17:00-20:00): 2.0x average
        base[(hours >= 17) & (hours < 20)] *= 2.2
        
        # Night minimum (22:00-06:00): 0.3x average
        base[(hours >= 22) | (hours < 6)] *= 0.3
        
        # Scale by profile type
        if profile_type == "high":
            base *= 1.3
        elif profile_type == "low":
            base *= 0.7
        
        # Add stochasticity
        noise = self.rng.normal(1.0, 0.15, 48)
        base = base * noise
        base = np.maximum(base, 0)  # No negative demand
        
        # Normalize to realistic daily total: 10 kWh/day = 0.208 kWh per 30min average
        daily_total_kwh = 10.0
        scaling_factor = (daily_total_kwh / 48) / base.mean()
        base = base * scaling_factor
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'demand_base_30min_kwh': base / 2,  # Convert from kW to kWh per 30min
        })


class EVProfileGenerator:
    """Generate stochastic EV arrival/departure patterns."""
    
    def __init__(self, seed: int = 42):
        """Initialize EV profile generator."""
        self.rng = np.random.default_rng(seed)
    
    def generate_ev_event(self) -> Tuple[datetime, datetime, float]:
        """
        Generate EV arrival, departure, and daily energy requirement.
        
        Returns:
            (arrival_time: datetime, departure_time: datetime, required_energy_kwh: float)
        """
        # Arrival time: Gamma distribution, peak 17:00-19:00
        # Scale to 0-24 hours, then convert to datetime
        arrival_hour = self.rng.gamma(shape=2.5, scale=0.67) + 15  # Peak around 17:00
        arrival_hour = np.clip(arrival_hour, 15, 22)  # 15:00 to 22:00
        
        # Departure: next day, 06:00-08:30
        departure_hour = self.rng.uniform(6, 8.5)
        
        # Daily energy: Normal distribution, 30±8 kWh
        required_kwh = self.rng.normal(30, 8)
        required_kwh = np.clip(required_kwh, 15, 60)  # Realistic range
        
        # Create datetime objects (assuming 2024-01-01 as reference)
        arrival_dt = datetime(2024, 1, 1, int(arrival_hour), int((arrival_hour % 1) * 60))
        departure_dt = datetime(2024, 1, 2, int(departure_hour), int((departure_hour % 1) * 60))
        
        return arrival_dt, departure_dt, required_kwh


def generate_simulation_data(
    start_date: datetime,
    num_days: int = 30,
    season: str = "winter",
    tariff_type: str = "agile",
    seed: int = 42,
) -> dict:
    """
    Generate complete synthetic dataset for simulation.
    
    Returns:
        Dict with keys: weather, tariffs, demand, carbon_intensity
    """
    logger.info(f"Generating {num_days}-day synthetic dataset for {season} season")
    
    weather_gen = WeatherGenerator(seed=seed)
    tariff_gen = TariffGenerator()
    carbon_gen = CarbonIntensityGenerator()
    demand_gen = DemandProfileGenerator(seed=seed)
    
    all_data = {
        'weather': [],
        'tariffs': [],
        'demand': [],
        'carbon_intensity': [],
    }
    
    for day_offset in range(num_days):
        date = start_date + timedelta(days=day_offset)
        
        # Weather
        weather = weather_gen.generate_daily_weather(date, season=season)
        all_data['weather'].append(weather)
        
        # Tariffs
        if tariff_type == "flat":
            tariff = tariff_gen.flat_tariff()
        elif tariff_type == "economy7":
            tariff = tariff_gen.economy_7()
        else:  # agile
            tariff = tariff_gen.agile_pricing(seed=seed + day_offset)
        all_data['tariffs'].append(tariff)
        
        # Demand
        demand = demand_gen.generate_base_demand(date, profile_type="typical")
        all_data['demand'].append(demand)
        
        # Carbon intensity
        carbon = carbon_gen.synthetic_carbon_intensity(seed=seed + day_offset)
        all_data['carbon_intensity'].append(carbon)
    
    # Concatenate all days
    return {
        'weather': pd.concat(all_data['weather'], ignore_index=True),
        'tariffs': pd.concat(all_data['tariffs'], ignore_index=True),
        'demand': pd.concat(all_data['demand'], ignore_index=True),
        'carbon_intensity': pd.concat(all_data['carbon_intensity'], ignore_index=True),
    }
