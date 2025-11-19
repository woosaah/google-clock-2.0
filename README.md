# Google Clock 2.0 - Smart Display System

A distributed smart display system with clock, weather, voice assistant, media casting, and smart home integration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Local Network (192.168.1.x)              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │ Raspberry Pi 3        │ │  deathstar   │                  │
│  │ (Frontend)   │◄───────┤ (Backend)     │                  │
│  │              │ WebSocket│              │                  │
│  │ - React UI   │         │ - Flask API   │                  │
│  │ - Audio I/O  │         │ - PostgreSQL  │                  │
│  │ - PS Eye Cam │         │ - Media Files │                  │
│  └──────────────┘         │ - COLEHUB     │                  │
│                            └───────┬───────┘                  │
│                                    │ HTTP/REST                │
│                                    │                          │
│                            ┌───────▼───────┐                  │
│                            │  AI Server    │                  │
│                            │ (RTX 4070)    │                  │
│                            │               │                  │
│                            │ - Ollama      │                  │
│                            │ - Whisper STT │                  │
│                            │ - Wake Word   │                  │
│                            │ - TTS         │                  │
│                            └───────────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (Raspberry Pi 3)
- **Location**: `/frontend`
- **Tech Stack**: React + TypeScript, WebSocket client
- **Display**: Fullscreen kiosk mode (Chromium)
- **Features**:
  - Clock display (customizable)
  - Weather widget
  - Calendar events
  - Media player (video/audio/photos)
  - Voice assistant UI
  - Smart home controls

### Backend (deathstar - 192.168.1.243)
- **Location**: `/backend`
- **Tech Stack**: FastAPI + Python, PostgreSQL, WebSocket server
- **Features**:
  - API integrations (weather, calendar, smart home)
  - Media queue management
  - COLEHUB database integration
  - Audio processing coordination
  - Business logic & state management

### AI Server (Separate Machine)
- **Location**: `/ai-server`
- **Tech Stack**: Python, Ollama, Whisper, Porcupine
- **Features**:
  - Wake word detection
  - Speech-to-text (Whisper)
  - Natural language processing (Ollama)
  - Text-to-speech generation

## Core Features

### Phase 1 (MVP)
- [x] Basic clock display (12/24hr toggle)
- [x] Weather widget (OpenWeatherMap)
- [x] Backend-frontend communication (WebSocket + REST)

### Phase 2 (Media & Voice)
- [ ] Remote URL casting (YouTube, web videos)
- [ ] Local media playback (deathstar:/media/clock/)
- [ ] Voice assistant pipeline
- [ ] Media control panel

### Phase 3 (Integrations)
- [ ] COLEHUB integration (Cole's points/tasks)
- [ ] Google Calendar integration
- [ ] Photo frame rotation
- [ ] Radio/music streaming

### Phase 4 (Advanced)
- [ ] Smart home controls (WiFi switches, MQTT)
- [ ] Alarms & timers
- [ ] Advanced voice commands
- [ ] Auto-dimming based on time

## Media Features

### Remote Casting
- Paste YouTube/Vimeo/direct video URLs
- Queue management (play next, multiple videos)
- Web control panel: `http://deathstar:5000/clock-remote`

### Local Media
- Browse files from `deathstar:/media/clock/`
- Supported formats:
  - Video: MP4, MKV, AVI
  - Audio: MP3, FLAC, WAV
  - Photos: JPG, PNG
- Thumbnail generation
- Metadata display

### Playback Modes
- **Video**: Fullscreen with overlay controls
- **Audio**: Background playback with mini player
- **Photos**: Slideshow with configurable timing

## Setup Instructions

### Prerequisites
- Raspberry Pi 3 with Raspbian/Raspberry Pi OS
- deathstar server with PostgreSQL running
- AI server with NVIDIA GPU (for Ollama/Whisper)
- Local network connectivity (192.168.1.x)

### Backend Setup (deathstar)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL=postgresql://user:pass@localhost/googleclock
# - OPENWEATHER_API_KEY=your_key
# - AI_SERVER_URL=http://192.168.1.x:8000

# Initialize database
python app/init_db.py

# Run backend
python app/main.py
# Or use systemd service:
sudo cp deployment/systemd/googleclock-backend.service /etc/systemd/system/
sudo systemctl enable googleclock-backend
sudo systemctl start googleclock-backend
```

### Frontend Setup (Raspberry Pi 3)

```bash
cd frontend
npm install
npm run build

# Copy build to Pi web directory
# Or use the automated setup script:
cd ../deployment/pi-setup
./setup-kiosk.sh
```

### AI Server Setup

```bash
cd ai-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama2
ollama pull mistral

# Run AI server
python main.py
```

## Configuration

### Environment Variables

**Backend (.env)**:
```env
DATABASE_URL=postgresql://user:pass@192.168.1.243/googleclock
OPENWEATHER_API_KEY=your_api_key
GOOGLE_CALENDAR_CREDENTIALS=/path/to/credentials.json
AI_SERVER_URL=http://192.168.1.x:8000
MEDIA_DIR=/media/clock
FRONTEND_URL=http://192.168.1.x:3000
```

**Frontend (.env)**:
```env
REACT_APP_BACKEND_URL=http://192.168.1.243:5000
REACT_APP_WS_URL=ws://192.168.1.243:5000/ws
```

**AI Server (.env)**:
```env
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=base
WAKE_WORD=hey_google
```

## API Documentation

### Backend REST API

#### Media Queue
- `POST /api/cast` - Queue remote URL for playback
- `GET /api/cast/queue` - Get current queue
- `POST /api/cast/control` - Control playback (play/pause/stop)
- `DELETE /api/cast/queue/:id` - Remove from queue

#### Local Media
- `GET /api/media/browse` - Browse local media files
- `POST /api/media/play` - Play local media file
- `GET /api/media/stream/:id` - Stream media file

#### Settings
- `GET /api/settings` - Get current settings
- `PUT /api/settings` - Update settings

#### Voice Assistant
- `POST /api/voice/process` - Process voice command
- `POST /api/voice/tts` - Generate TTS audio

### WebSocket Events

**Backend → Frontend**:
- `clock_update` - Time sync
- `weather_update` - Weather data
- `cast_queued` - Media added to queue
- `cast_ready` - Media ready to play
- `cast_playing` - Playback status
- `cast_stopped` - Playback ended
- `voice_detected` - Wake word detected
- `voice_response` - Assistant response

**Frontend → Backend**:
- `request_update` - Request data refresh
- `media_control` - Playback control command
- `settings_change` - Settings updated
- `voice_audio` - Audio stream chunk

## Database Schema

### media_queue
```sql
CREATE TABLE media_queue (
  id SERIAL PRIMARY KEY,
  url TEXT,
  local_path TEXT,
  title TEXT,
  thumbnail_url TEXT,
  media_type TEXT, -- 'video', 'audio', 'photo'
  duration INTEGER,
  file_size BIGINT,
  queued_at TIMESTAMP DEFAULT NOW(),
  played_at TIMESTAMP,
  status TEXT DEFAULT 'queued',
  source TEXT DEFAULT 'remote'
);
```

### media_library
```sql
CREATE TABLE media_library (
  id SERIAL PRIMARY KEY,
  file_path TEXT UNIQUE NOT NULL,
  filename TEXT,
  media_type TEXT,
  duration INTEGER,
  resolution TEXT,
  file_size BIGINT,
  thumbnail_path TEXT,
  added_at TIMESTAMP DEFAULT NOW(),
  last_played TIMESTAMP,
  play_count INTEGER DEFAULT 0
);
```

### settings
```sql
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value JSONB,
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## Hardware

### Raspberry Pi 3
- PS Eye camera (4-mic array, USB)
- 7" touchscreen (800x480 or 1024x600)
- Speaker output (3.5mm or USB)
- WiFi connection

### Recommended Accessories
- USB sound card (better audio quality)
- Powered USB hub (for PS Eye + other devices)
- Heat sinks + fan (for extended use)

## Performance Optimizations

### Frontend (Pi 3)
- React.memo for components
- useMemo for expensive calculations
- Lazy loading for thumbnails
- Progressive image loading
- Debounced seek bar updates

### Backend
- Connection pooling for PostgreSQL
- Redis caching (optional)
- Async I/O for media streaming
- Thumbnail pre-generation

### Media Playback
- Use OMXPlayer for video (hardware acceleration)
- HTML5 player for audio/photos
- Stream chunks rather than full files
- Format-specific optimizations

## Troubleshooting

### Frontend not connecting to backend
- Check firewall settings on deathstar
- Verify WebSocket port (5000) is open
- Check network connectivity: `ping 192.168.1.243`

### Video playback stuttering
- Try OMXPlayer instead of HTML5
- Reduce video quality/resolution
- Check CPU usage on Pi: `top`
- Ensure sufficient power supply (2.5A recommended)

### Voice assistant not responding
- Check AI server is running
- Verify audio input device: `arecord -l`
- Test microphone: `arecord -d 5 test.wav && aplay test.wav`
- Check wake word sensitivity setting

### Media not appearing in browser
- Verify MEDIA_DIR path exists on deathstar
- Check file permissions: `ls -la /media/clock/`
- Trigger manual scan: `curl http://deathstar:5000/api/media/scan`

## Development

### Running in Development Mode

**Backend**:
```bash
cd backend
source venv/bin/activate
python app/main.py --debug
```

**Frontend**:
```bash
cd frontend
npm start
# Access at http://localhost:3000
```

**AI Server**:
```bash
cd ai-server
source venv/bin/activate
python main.py --debug
```

### Testing
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## License
MIT

## Contributing
Pull requests welcome! Please open an issue first to discuss major changes.

## Credits
- Built for Raspberry Pi 3
- Uses Ollama for AI processing
- Weather data from OpenWeatherMap
- Voice processing with Whisper
