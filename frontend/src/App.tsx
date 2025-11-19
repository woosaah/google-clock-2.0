/**
 * Main App component for Google Clock 2.0
 * Frontend handles: Display, Camera I/O, Audio I/O, Touch input
 * Backend handles: All processing, decision making, command orchestration
 */

import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { Clock } from './components/Clock';
import { Weather } from './components/Weather';
import { CameraCapture } from './components/CameraCapture';
import { AudioCapture } from './components/AudioCapture';
import { wsService } from './services/websocket';
import { Settings } from './types';

const AppContainer = styled.div<{ brightness: number }>`
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  overflow: hidden;
  filter: brightness(${props => props.brightness}%);
  transition: filter 0.5s ease;
`;

const StatusBar = styled.div`
  position: fixed;
  top: 1rem;
  right: 1rem;
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
`;

const StatusIndicator = styled.div<{ connected: boolean }>`
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: ${props => props.connected ? '#4ade80' : '#f87171'};
`;

function App() {
  const [connected, setConnected] = useState(false);
  const [settings, setSettings] = useState<Settings>({});
  const [brightness, setBrightness] = useState(100);

  useEffect(() => {
    // Connect to backend WebSocket
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:5000/ws';
    wsService.connect(wsUrl);

    // Handle connection status
    wsService.on('connection_status', (data: any) => {
      setConnected(data.connected);
      if (data.connected) {
        console.log('Connected to backend');
        // Request initial settings
        wsService.send('request_update', { type: 'settings' });
      }
    });

    // Handle settings updates from backend
    wsService.on('settings_updated', (data: any) => {
      console.log('Settings updated:', data);
      setSettings(data);

      // Apply brightness settings
      if (data.display) {
        const hour = new Date().getHours();
        const { auto_dim, dim_start_hour, dim_end_hour, dim_brightness } = data.display;

        if (auto_dim &&
            ((hour >= dim_start_hour) || (hour < dim_end_hour))) {
          setBrightness(dim_brightness);
        } else {
          setBrightness(data.display.brightness || 100);
        }
      }
    });

    // Handle backend commands
    wsService.on('command', handleBackendCommand);

    // Handle WebSocket disconnection
    return () => {
      wsService.disconnect();
    };
  }, []);

  const handleBackendCommand = (command: any) => {
    console.log('Backend command:', command);

    switch (command.type) {
      case 'capture_frame':
        // Camera capture will be handled by CameraCapture component
        break;

      case 'start_listening':
        // Audio capture will be handled by AudioCapture component
        break;

      case 'stop_listening':
        // Stop audio capture
        break;

      case 'show_greeting':
        // PersonGreeting component will handle this
        break;

      case 'update_widgets':
        // Update displayed widgets
        break;

      case 'speak':
        // Play TTS audio
        if (command.data?.audio) {
          playAudio(command.data.audio);
        }
        break;

      case 'play_media':
        // Media player will handle this
        break;

      default:
        console.warn('Unknown command type:', command.type);
    }
  };

  const playAudio = (audioBase64: string) => {
    try {
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      audio.play().catch(err => console.error('Error playing audio:', err));
    } catch (err) {
      console.error('Error creating audio:', err);
    }
  };

  return (
    <AppContainer brightness={brightness}>
      <StatusBar>
        <StatusIndicator connected={connected} />
        <span>{connected ? 'Connected' : 'Disconnected'}</span>
      </StatusBar>

      <Clock
        format={settings.clock_format?.format || '24hr'}
        showSeconds={settings.clock_format?.show_seconds ?? true}
      />

      <Weather
        city={settings.weather_location?.city}
        units={settings.weather_location?.units as 'metric' | 'imperial'}
      />

      {/* Hardware I/O Components (Hidden - handle camera & mic) */}
      <CameraCapture
        enabled={process.env.REACT_APP_ENABLE_CAMERA !== 'false'}
        motionSensitivity={settings.voice?.sensitivity ? settings.voice.sensitivity * 100 : 50}
        motionFps={1}
      />

      <AudioCapture
        enabled={process.env.REACT_APP_ENABLE_VOICE !== 'false'}
        bufferDuration={3}
        chunkSize={100}
      />

      {/* Future components:
          - PersonGreeting (overlay when person detected)
          - MediaPlayer (fullscreen when playing)
          - APIWidgets (custom data displays)
      */}
    </AppContainer>
  );
}

export default App;
