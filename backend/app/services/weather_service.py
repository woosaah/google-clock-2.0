"""Weather service using OpenWeatherMap API."""

import httpx
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache for weather data (to avoid too many API calls)
_weather_cache: Dict[str, Dict] = {}
_cache_ttl = 600  # 10 minutes


class WeatherService:
    """Service for fetching weather data from OpenWeatherMap."""

    def __init__(self, api_key: str):
        """
        Initialize weather service.

        Args:
            api_key: OpenWeatherMap API key
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def get_current_weather(
        self,
        city: str = "San Francisco",
        country: str = "US",
        units: str = "metric"
    ) -> Optional[Dict]:
        """
        Get current weather for a location.

        Args:
            city: City name
            country: Country code (e.g., 'US', 'GB')
            units: Units ('metric' or 'imperial')

        Returns:
            Weather data dictionary or None if error
        """
        cache_key = f"{city},{country},{units}"

        # Check cache first
        if cache_key in _weather_cache:
            cached_data, cached_time = _weather_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=_cache_ttl):
                logger.info(f"Returning cached weather for {city}")
                return cached_data

        if not self.api_key or self.api_key == "your_openweather_api_key_here":
            logger.warning("OpenWeatherMap API key not configured, returning mock data")
            return self._get_mock_weather()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": f"{city},{country}",
                        "appid": self.api_key,
                        "units": units
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    weather = self._parse_weather_response(data, units)

                    # Update cache
                    _weather_cache[cache_key] = (weather, datetime.now())

                    logger.info(f"Weather fetched for {city}: {weather['temperature']}°")
                    return weather

                elif response.status_code == 401:
                    logger.error("Invalid OpenWeatherMap API key")
                    return self._get_mock_weather()

                elif response.status_code == 404:
                    logger.error(f"City not found: {city}, {country}")
                    return self._get_mock_weather()

                else:
                    logger.error(f"Weather API error: {response.status_code}")
                    return self._get_mock_weather()

        except httpx.TimeoutException:
            logger.error("Weather API timeout")
            return self._get_mock_weather()

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return self._get_mock_weather()

    def _parse_weather_response(self, data: Dict, units: str) -> Dict:
        """Parse OpenWeatherMap API response."""
        return {
            "temperature": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"]),
            "icon": data["weather"][0]["icon"],
            "city": data["name"],
            "country": data["sys"]["country"],
            "units": units,
            "timestamp": datetime.now().isoformat()
        }

    def _get_mock_weather(self) -> Dict:
        """Return mock weather data when API is unavailable."""
        return {
            "temperature": 72,
            "feels_like": 70,
            "condition": "Sunny",
            "description": "clear sky",
            "humidity": 45,
            "wind_speed": 10,
            "icon": "01d",
            "city": "San Francisco",
            "country": "US",
            "units": "imperial",
            "timestamp": datetime.now().isoformat(),
            "mock": True  # Indicate this is mock data
        }


# Global weather service instance (initialized in main.py)
weather_service: Optional[WeatherService] = None


def init_weather_service(api_key: str):
    """Initialize global weather service."""
    global weather_service
    weather_service = WeatherService(api_key)
    logger.info("Weather service initialized")


def get_weather_service() -> WeatherService:
    """Get weather service instance."""
    if weather_service is None:
        raise RuntimeError("Weather service not initialized")
    return weather_service
