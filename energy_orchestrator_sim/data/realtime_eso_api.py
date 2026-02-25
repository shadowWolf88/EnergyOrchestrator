# -*- coding: utf-8 -*-
"""
Real-time ESO (Electricity System Operator) data integration.

Fetches current and historical UK grid data:
- Carbon intensity (gCO2/kWh)
- Weather forecasts
- Real tariff data from Octopus Energy
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CarbonIntensityAPI:
    """Fetch real UK grid carbon intensity from Electricity Maps API (free tier)."""
    
    BASE_URL = "https://api.electricitymap.org/v3/carbon-intensity"
    
    @staticmethod
    def get_current_intensity(zone: str = "GB") -> Optional[Dict]:
        """
        Get current carbon intensity for UK (GB zone).
        
        Args:
            zone: ISO code (GB for Great Britain)
            
        Returns:
            Dict with 'carbonIntensity' (gCO2/kWh), 'datetime', etc.
            None if API unavailable
        """
        try:
            url = f"{CarbonIntensityAPI.BASE_URL}/latest?zone={zone}"
            # Note: Free tier may require API key. Here we use public endpoint.
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            logger.info(f"ESO Carbon Intensity: {data.get('carbonIntensity', 'N/A')} gCO2/kWh")
            return data
        except Exception as e:
            logger.warning(f"Carbon Intensity API failed (using synthetic): {e}")
            return None
    
    @staticmethod
    def get_forecast(date_from: datetime, date_to: datetime, zone: str = "GB") -> Optional[pd.DataFrame]:
        """
        Get carbon intensity forecast (limited by free tier).
        
        Returns:
            DataFrame with timestamp, carbonIntensity columns
            None if API unavailable
        """
        try:
            url = f"{CarbonIntensityAPI.BASE_URL}/forecast?zone={zone}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse forecast data
            forecasts = data.get('forecast', [])
            if forecasts:
                df = pd.DataFrame([
                    {
                        'timestamp': pd.Timestamp(f['datetime']),
                        'carbon_intensity_gco2_per_kwh': f['carbonIntensity'],
                    }
                    for f in forecasts
                ])
                logger.info(f"Fetched {len(df)} carbon intensity forecasts from ESO")
                return df
        except Exception as e:
            logger.warning(f"Carbon Intensity forecast failed: {e}")
        
        return None


class OctopusEnergyAPI:
    """Fetch real UK tariffs from Octopus Energy API (free, no auth for public rates)."""
    
    BASE_URL = "https://api.octopus.energy/v1/products"
    
    @staticmethod
    def get_agile_tariff(region: str = "E") -> Optional[pd.DataFrame]:
        """
        Get Agile tariff rates for a region.
        
        Args:
            region: GB region code (E=East, L=London, etc.)
            
        Returns:
            DataFrame with timestamp, tariff_£_per_kwh columns
            None if API unavailable
        """
        try:
            # Octopus Agile tariff ID (public)
            product_id = "AGILE-23-12-06"  # Example; may need update
            url = f"{OctopusEnergyAPI.BASE_URL}/{product_id}/electricity-tariffs/"
            
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            rates = data.get('results', [])
            if rates:
                df = pd.DataFrame([
                    {
                        'timestamp': pd.Timestamp(r['valid_from']),
                        'tariff_£_per_kwh': r['unit_rate'] / 100,  # Convert pence to pounds
                    }
                    for r in rates[:48]  # Last 48 periods
                ])
                logger.info(f"Fetched {len(df)} Agile tariff rates from Octopus")
                return df
        except Exception as e:
            logger.warning(f"Octopus Energy API failed: {e}")
        
        return None


class WeatherAPI:
    """Fetch real weather data (solar irradiance proxy)."""
    
    @staticmethod
    def get_uk_weather_forecast(location: str = "london",
                                 api_key: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Get weather forecast (OpenWeatherMap or similar).
        
        Note: Requires free API key from openweathermap.org
        
        Args:
            location: City name
            api_key: OpenWeatherMap API key
            
        Returns:
            DataFrame with timestamp, irradiance_estimate, temperature_c
            None if API unavailable or no key
        """
        if not api_key:
            logger.warning("Weather API requires API key (openweathermap.org) - using synthetic data")
            return None
        
        try:
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            forecasts = []
            for f in data['list']:
                # Estimate irradiance from cloud cover: max_irradiance * (1 - cloud_cover/100)
                cloud_cover = f.get('clouds', {}).get('all', 50)
                irradiance = 1000 * (1 - cloud_cover / 100)  # Simplified
                
                forecasts.append({
                    'timestamp': pd.Timestamp(f['dt'], unit='s'),
                    'irradiance_wm2': irradiance,
                    'temperature_c': f['main']['temp'] - 273.15,  # Kelvin to Celsius
                })
            
            df = pd.DataFrame(forecasts)
            logger.info(f"Fetched {len(df)} weather forecasts from OpenWeatherMap")
            return df
        except Exception as e:
            logger.warning(f"Weather API failed: {e}")
        
        return None


if __name__ == "__main__":
    # Quick test
    print("Testing real ESO APIs...")
    
    # Carbon intensity
    ci = CarbonIntensityAPI.get_current_intensity()
    if ci:
        print(f"✓ Current grid carbon intensity: {ci.get('carbonIntensity')} gCO2/kWh")
    else:
        print("✗ Carbon Intensity API unavailable (expected - requires subscription)")
    
    # Octopus Agile tariff
    agile = OctopusEnergyAPI.get_agile_tariff()
    if agile is not None:
        print(f"✓ Fetched {len(agile)} Agile tariff rates")
    else:
        print("✗ Octopus API unavailable")
