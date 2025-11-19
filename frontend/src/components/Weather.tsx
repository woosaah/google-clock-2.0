/**
 * Weather widget component
 */

import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Weather as WeatherType, WeatherProps } from '../types';
import { apiService } from '../services/api';

const WeatherContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  backdrop-filter: blur(10px);
  color: white;
  min-width: 250px;
`;

const Temperature = styled.div`
  font-size: 4rem;
  font-weight: 300;
  line-height: 1;
`;

const Condition = styled.div`
  font-size: 1.5rem;
  margin-top: 0.5rem;
  opacity: 0.9;
`;

const Details = styled.div`
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  font-size: 1rem;
  opacity: 0.8;
`;

const Detail = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
`;

const DetailLabel = styled.span`
  font-size: 0.8rem;
  opacity: 0.7;
`;

const DetailValue = styled.span`
  font-weight: 500;
`;

const ErrorMessage = styled.div`
  color: #ff6b6b;
  font-size: 1rem;
`;

const LoadingMessage = styled.div`
  opacity: 0.7;
  font-size: 1rem;
`;

export const Weather: React.FC<WeatherProps> = ({
  city,
  units = 'metric',
}) => {
  const [weather, setWeather] = useState<WeatherType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWeather = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiService.getWeather();
        setWeather(response.data);
      } catch (err: any) {
        console.error('Error fetching weather:', err);
        setError('Unable to load weather');
      } finally {
        setLoading(false);
      }
    };

    fetchWeather();

    // Refresh weather every 10 minutes
    const interval = setInterval(fetchWeather, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, [city, units]);

  if (loading) {
    return (
      <WeatherContainer>
        <LoadingMessage>Loading weather...</LoadingMessage>
      </WeatherContainer>
    );
  }

  if (error || !weather) {
    return (
      <WeatherContainer>
        <ErrorMessage>{error || 'Weather unavailable'}</ErrorMessage>
      </WeatherContainer>
    );
  }

  const tempUnit = units === 'metric' ? '°C' : '°F';
  const windUnit = units === 'metric' ? 'km/h' : 'mph';

  return (
    <WeatherContainer>
      <Temperature>
        {Math.round(weather.temperature)}{tempUnit}
      </Temperature>
      <Condition>{weather.condition}</Condition>
      <Details>
        <Detail>
          <DetailLabel>Humidity</DetailLabel>
          <DetailValue>{weather.humidity}%</DetailValue>
        </Detail>
        <Detail>
          <DetailLabel>Wind</DetailLabel>
          <DetailValue>{weather.wind_speed} {windUnit}</DetailValue>
        </Detail>
      </Details>
    </WeatherContainer>
  );
};

export default Weather;
