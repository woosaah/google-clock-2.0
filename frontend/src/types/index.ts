/**
 * TypeScript type definitions for Google Clock 2.0
 */

// Media Types
export interface MediaItem {
  id: number;
  url?: string;
  local_path?: string;
  title: string;
  thumbnail_url?: string;
  media_type: 'video' | 'audio' | 'photo';
  duration?: number;
  file_size?: number;
  status: 'queued' | 'playing' | 'played' | 'error';
  source: 'remote' | 'local';
  queued_at: string;
}

export interface LocalMediaFile {
  id: number;
  filename: string;
  type: 'video' | 'audio' | 'photo';
  size: number;
  duration?: number;
  thumbnail?: string;
}

// Weather Types
export interface Weather {
  temperature: number;
  condition: string;
  humidity: number;
  wind_speed: number;
  icon: string;
}

// Calendar Types
export interface CalendarEvent {
  id: number;
  summary: string;
  start: string;
  end: string;
  all_day: boolean;
  location?: string;
}

// Person Detection Types
export interface Person {
  id: number;
  name: string;
  greeting_morning?: string;
  greeting_afternoon?: string;
  greeting_evening?: string;
  preferences?: Record<string, any>;
}

export interface Detection {
  id: number;
  person_id?: number;
  person?: Person;
  detected_at: string;
  confidence: number;
  first_of_day: boolean;
  greeted: boolean;
}

// API Integration Types
export interface APIIntegration {
  id: number;
  name: string;
  url: string;
  method: string;
  schedule_interval?: number;
  enabled: boolean;
  last_run?: string;
  next_run?: string;
  last_response?: any;
  error_count: number;
}

// Response Rule Types
export interface ResponseRule {
  id: number;
  name: string;
  trigger_type: 'person' | 'time' | 'data' | 'manual';
  trigger_config: Record<string, any>;
  conditions?: Array<Record<string, any>>;
  actions: Array<Record<string, any>>;
  enabled: boolean;
  priority: number;
  last_triggered?: string;
  trigger_count: number;
}

// Settings Types
export interface ClockSettings {
  format: '12hr' | '24hr';
  show_seconds: boolean;
}

export interface DisplaySettings {
  brightness: number;
  auto_dim: boolean;
  dim_start_hour: number;
  dim_end_hour: number;
  dim_brightness: number;
}

export interface VoiceSettings {
  enabled: boolean;
  wake_word: string;
  sensitivity: number;
  volume: number;
}

export interface MediaSettings {
  auto_play: boolean;
  default_volume: number;
  slideshow_duration: number;
}

export interface Settings {
  clock_format?: ClockSettings;
  display?: DisplaySettings;
  voice?: VoiceSettings;
  media?: MediaSettings;
  weather_location?: {
    city: string;
    country: string;
    units: string;
  };
}

// WebSocket Message Types
export interface WSMessage {
  type: string;
  data: any;
}

export interface ConnectionStatus {
  connected: boolean;
  error?: string;
}

// Component Props Types
export interface ClockProps {
  format?: '12hr' | '24hr';
  showSeconds?: boolean;
}

export interface WeatherProps {
  city?: string;
  units?: 'metric' | 'imperial';
}

export interface GreetingProps {
  person: Person;
  timeOfDay: 'morning' | 'afternoon' | 'evening';
  customInfo?: string;
}

export interface MediaPlayerProps {
  item: MediaItem;
  onEnded?: () => void;
  onError?: (error: Error) => void;
}

export interface TransportControlsProps {
  playing: boolean;
  volume: number;
  currentTime: number;
  duration: number;
  onPlayPause: () => void;
  onVolumeChange: (volume: number) => void;
  onSeek: (time: number) => void;
  onStop: () => void;
}
