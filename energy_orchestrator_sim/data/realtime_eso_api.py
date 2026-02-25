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
    """
    Fetch real UK grid carbon intensity from the National Grid ESO Carbon Intensity API.

    Endpoint: https://api.carbonintensity.org.uk  (completely free, no API key required)
    Documentation: https://carbon-intensity.github.io/api-definitions/

    Regional IDs:
        1=North Scotland, 2=South Scotland, 3=North West England,
        4=North East England, 5=Yorkshire, 6=North Wales & Merseyside,
        7=South Wales, 8=West Midlands, 9=East Midlands (Hockerton area),
        10=East England, 11=South West England, 12=South England,
        13=London, 14=South East England
    """

    BASE_URL = "https://api.carbonintensity.org.uk"
    EAST_MIDLANDS_REGION_ID = 9  # Covers Nottinghamshire / Hockerton

    @staticmethod
    def get_current_intensity() -> Optional[Dict]:
        """
        Get current national GB carbon intensity (no API key required).

        Returns:
            Dict with 'intensity' (forecast + actual gCO2/kWh), 'generationmix', etc.
            None if API unavailable.
        """
        try:
            url = f"{CarbonIntensityAPI.BASE_URL}/intensity"
            response = requests.get(url, timeout=5, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
            entry = data.get("data", [{}])[0]
            intensity = entry.get("intensity", {})
            value = intensity.get("actual") or intensity.get("forecast")
            logger.info(f"ESO Carbon Intensity: {value} gCO2/kWh")
            return entry
        except Exception as e:
            logger.warning(f"Carbon Intensity API failed (using synthetic): {e}")
            return None

    @staticmethod
    def get_24h_forecast() -> Optional[pd.DataFrame]:
        """
        Get 24-hour ahead national carbon intensity forecast (48 half-hourly periods).

        Returns:
            DataFrame with columns: timestamp, carbon_intensity_gco2_per_kwh
            None if API unavailable.
        """
        try:
            url = f"{CarbonIntensityAPI.BASE_URL}/intensity/date/{datetime.now().strftime('%Y-%m-%d')}"
            response = requests.get(url, timeout=10, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()

            records = []
            for entry in data.get("data", []):
                intensity = entry.get("intensity", {})
                value = intensity.get("actual") or intensity.get("forecast")
                if value is not None:
                    records.append({
                        "timestamp": pd.Timestamp(entry["from"]),
                        "carbon_intensity_gco2_per_kwh": float(value),
                    })

            if records:
                df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
                logger.info(f"Fetched {len(df)} carbon intensity periods from ESO API")
                return df
        except Exception as e:
            logger.warning(f"Carbon Intensity 24h forecast failed: {e}")

        return None

    @staticmethod
    def get_regional_intensity(region_id: int = 9) -> Optional[Dict]:
        """
        Get current regional carbon intensity (East Midlands = region 9).

        Args:
            region_id: ESO regional ID (default 9 = East Midlands / Nottinghamshire)

        Returns:
            Dict with intensity data for the region, or None on failure.
        """
        try:
            url = f"{CarbonIntensityAPI.BASE_URL}/regional/regionid/{region_id}"
            response = requests.get(url, timeout=5, headers={"Accept": "application/json"})
            response.raise_for_status()
            data = response.json()
            entry = data.get("data", [{}])[0]
            logger.info(f"Regional (East Midlands) intensity fetched")
            return entry
        except Exception as e:
            logger.warning(f"Regional Carbon Intensity API failed: {e}")
            return None


class OctopusEnergyAPI:
    """
    Fetch real UK Agile tariff rates from Octopus Energy API.

    Completely free, no API key required for public product rates.
    Documentation: https://developer.octopus.energy/docs/api/
    Region codes: A=East Midlands, B=East England, C=London, D=Merseyside,
                  E=West Midlands, F=North East, G=North West, H=South England,
                  J=South East, K=South West, L=South Wales, M=Yorkshire,
                  N=North Scotland, P=South Scotland
    """

    BASE_URL = "https://api.octopus.energy/v1"
    # East Midlands region = A (covers Nottinghamshire)
    EAST_MIDLANDS_REGION = "A"

    @staticmethod
    def _get_current_agile_product_code() -> Optional[str]:
        """Discover the current live Agile Octopus product code via the products API."""
        try:
            resp = requests.get(
                f"{OctopusEnergyAPI.BASE_URL}/products/?is_variable=true&is_prepay=false",
                timeout=10,
            )
            resp.raise_for_status()
            for product in resp.json().get("results", []):
                if "AGILE" in product.get("code", "") and product.get("is_available"):
                    return product["code"]
        except Exception as e:
            logger.warning(f"Octopus product discovery failed: {e}")
        return "AGILE-FLEX-22-11-25"  # Fallback to known historic code

    @staticmethod
    def get_agile_tariff(
        region: str = "A",
        period_from: Optional[datetime] = None,
        period_to: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get Agile Octopus half-hourly tariff rates for a region.

        Args:
            region: Octopus region code (default A = East Midlands / Nottinghamshire)
            period_from: Start datetime (default: 24h ago)
            period_to: End datetime (default: now)

        Returns:
            DataFrame with columns: timestamp, tariff_gbp_per_kwh
            None if API unavailable.
        """
        try:
            product_code = OctopusEnergyAPI._get_current_agile_product_code()
            tariff_code = f"E-1R-{product_code}-{region}"
            url = (
                f"{OctopusEnergyAPI.BASE_URL}/products/{product_code}"
                f"/electricity-tariffs/{tariff_code}/standard-unit-rates/"
            )

            params = {}
            if period_from:
                params["period_from"] = period_from.isoformat()
            if period_to:
                params["period_to"] = period_to.isoformat()

            response = requests.get(url, timeout=10, params=params)
            response.raise_for_status()
            data = response.json()

            rates = data.get("results", [])
            if rates:
                df = pd.DataFrame([
                    {
                        "timestamp": pd.Timestamp(r["valid_from"]),
                        "tariff_gbp_per_kwh": r["value_inc_vat"] / 100,  # pence → pounds
                    }
                    for r in rates
                ]).sort_values("timestamp").reset_index(drop=True)
                logger.info(f"Fetched {len(df)} Agile tariff rates from Octopus ({region})")
                return df
        except Exception as e:
            logger.warning(f"Octopus Energy Agile API failed: {e}")

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
    # Quick connectivity test — run: python data/realtime_eso_api.py
    print("Testing real ESO/Octopus APIs (no API key required)...")

    # National carbon intensity
    ci = CarbonIntensityAPI.get_current_intensity()
    if ci:
        intensity = ci.get("intensity", {})
        val = intensity.get("actual") or intensity.get("forecast")
        print(f"✓ National grid carbon intensity: {val} gCO2/kWh")
    else:
        print("✗ Carbon Intensity API unavailable")

    # East Midlands regional intensity
    regional = CarbonIntensityAPI.get_regional_intensity(region_id=9)
    if regional:
        print(f"✓ East Midlands regional data received")
    else:
        print("✗ Regional Carbon Intensity API unavailable")

    # 24h forecast
    forecast = CarbonIntensityAPI.get_24h_forecast()
    if forecast is not None:
        print(f"✓ Fetched {len(forecast)} carbon intensity half-hour periods")
    else:
        print("✗ Carbon Intensity 24h forecast unavailable")

    # Octopus Agile tariff
    agile = OctopusEnergyAPI.get_agile_tariff(region="A")
    if agile is not None:
        print(f"✓ Fetched {len(agile)} Agile tariff rates (East Midlands)")
        print(f"  Range: {agile['tariff_gbp_per_kwh'].min():.4f}–{agile['tariff_gbp_per_kwh'].max():.4f} GBP/kWh")
    else:
        print("✗ Octopus Agile API unavailable")
