# Google Clock 2.0 Deployment Guide

Complete deployment guide for all three components of the Google Clock 2.0 system.

## Overview

- **Backend**: deathstar server (192.168.1.243) - PostgreSQL, FastAPI, orchestration
- **AI Server**: Separate machine with NVIDIA GPU - Face recognition, voice processing
- **Frontend**: Raspberry Pi 3 - Display, camera, microphone, kiosk mode

## Prerequisites

### Backend (deathstar)
- Ubuntu/Debian-based Linux
- PostgreSQL 12+ installed and running
- Python 3.9+
- Network accessible at 192.168.1.243

### AI Server
- Ubuntu/Debian-based Linux
- NVIDIA GPU (RTX 4070 or similar)
- CUDA 11.8+ installed
- Python 3.9+
- Ollama installed

### Frontend (Raspberry Pi 3)
- Raspberry Pi OS (Bullseye or newer)
- PS Eye camera connected via USB
- 7" touchscreen or HDMI display
- Network connectivity to backend

## Deployment Steps

### 1. Backend Setup (deathstar)

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-org/google-clock-2.0.git
cd google-clock-2.0/backend

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Create PostgreSQL database
sudo -u postgres createdb googleclock
sudo -u postgres createuser googleclock_user -P

# Initialize database
python app/init_db.py

# Test backend
python app/main.py
# Access http://192.168.1.243:5000 to verify

# Install systemd service
sudo cp ../deployment/systemd/googleclock-backend.service /etc/systemd/system/
sudo nano /etc/systemd/system/googleclock-backend.service  # Update paths

sudo systemctl daemon-reload
sudo systemctl enable googleclock-backend
sudo systemctl start googleclock-backend
sudo systemctl status googleclock-backend

# View logs
sudo journalctl -u googleclock-backend -f
```

### 2. AI Server Setup

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-org/google-clock-2.0.git
cd google-clock-2.0/ai-server

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (this may take a while)
pip install -r requirements.txt

# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama2
ollama pull mistral

# Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Test AI server
python main.py
# Access http://localhost:8000 to verify

# Install systemd service
sudo cp ../deployment/systemd/googleclock-ai-server.service /etc/systemd/system/
sudo nano /etc/systemd/system/googleclock-ai-server.service  # Update paths

sudo systemctl daemon-reload
sudo systemctl enable googleclock-ai-server
sudo systemctl start googleclock-ai-server
sudo systemctl status googleclock-ai-server

# View logs
sudo journalctl -u googleclock-ai-server -f
```

### 3. Frontend Setup (Raspberry Pi 3)

#### Method A: Pre-built (Recommended for Pi 3)

Build the frontend on a more powerful machine, then deploy to Pi:

```bash
# On your development machine
cd google-clock-2.0/frontend
npm install
npm run build

# Copy build directory to Pi
scp -r build pi@raspberrypi.local:/home/pi/googleclock-frontend/

# On the Pi, serve with a simple HTTP server
ssh pi@raspberrypi.local
cd /home/pi/googleclock-frontend
python3 -m http.server 3000
```

#### Method B: Build on Pi (slower)

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Clone repository
cd ~
git clone https://github.com/your-org/google-clock-2.0.git
cd google-clock-2.0/frontend

# Install dependencies (this takes ~30 minutes on Pi 3)
npm install

# Configure environment
cp .env.example .env
nano .env  # Update REACT_APP_BACKEND_URL

# Build for production
npm run build

# Or run development server (not recommended for production)
npm start
```

#### Setup Kiosk Mode

```bash
# Run the kiosk setup script
cd ~/google-clock-2.0/deployment/pi-setup
chmod +x setup-kiosk.sh
./setup-kiosk.sh

# Follow the prompts
# After completion, reboot
sudo reboot
```

## Configuration

### Backend Environment Variables

Edit `/opt/google-clock-2.0/backend/.env`:

```env
DATABASE_URL=postgresql://googleclock_user:password@localhost/googleclock
OPENWEATHER_API_KEY=your_api_key
AI_SERVER_URL=http://192.168.1.x:8000
MEDIA_DIR=/media/clock
CORS_ORIGINS=http://192.168.1.x:3000
```

### AI Server Environment Variables

Edit `/opt/google-clock-2.0/ai-server/.env`:

```env
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=base
WAKE_WORD_ENGINE=porcupine
PORCUPINE_ACCESS_KEY=your_key
```

### Frontend Environment Variables

Edit `/home/pi/google-clock-2.0/frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://192.168.1.243:5000
REACT_APP_WS_URL=ws://192.168.1.243:5000/ws
```

## Media Setup

Create media directories on deathstar:

```bash
sudo mkdir -p /media/clock/{videos,audio,photos,thumbnails}
sudo chown -R your-username:your-username /media/clock
sudo chmod -R 755 /media/clock
```

## Firewall Configuration

### Backend (deathstar)

```bash
sudo ufw allow 5000/tcp  # Backend API
sudo ufw allow from 192.168.1.0/24  # Allow local network
```

### AI Server

```bash
sudo ufw allow 8000/tcp  # AI Server API
sudo ufw allow from 192.168.1.243  # Only allow backend
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
sudo journalctl -u googleclock-backend -n 50

# Check PostgreSQL
sudo systemctl status postgresql
psql -U googleclock_user -d googleclock -c "SELECT 1;"

# Check port
sudo netstat -tlnp | grep 5000
```

### AI Server GPU not detected

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Frontend not loading

```bash
# On Pi, check frontend is running
curl http://localhost:3000

# Check network connectivity
ping 192.168.1.243

# Check Chromium process
ps aux | grep chromium

# Restart X session
sudo systemctl restart lightdm
```

### PS Eye camera not working

```bash
# Check camera is detected
ls -la /dev/video*

# Test camera
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all

# Capture test frame
ffmpeg -f v4l2 -i /dev/video0 -frames 1 test.jpg
```

### PS Eye microphone not working

```bash
# Check audio devices
arecord -l

# Test recording
arecord -D plughw:1,0 -d 5 test.wav
aplay test.wav
```

## Monitoring

### Check all services

```bash
# Backend
sudo systemctl status googleclock-backend

# AI Server
sudo systemctl status googleclock-ai-server

# Frontend (on Pi)
sudo systemctl status googleclock-frontend
```

### View logs

```bash
# Backend
sudo journalctl -u googleclock-backend -f

# AI Server
sudo journalctl -u googleclock-ai-server -f

# Frontend
sudo journalctl -u googleclock-frontend -f
```

## Updates

### Update backend

```bash
cd /opt/google-clock-2.0
sudo git pull
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart googleclock-backend
```

### Update AI server

```bash
cd /opt/google-clock-2.0
sudo git pull
cd ai-server
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart googleclock-ai-server
```

### Update frontend

```bash
# Build on dev machine
cd google-clock-2.0/frontend
git pull
npm install
npm run build

# Deploy to Pi
scp -r build/* pi@raspberrypi.local:/home/pi/googleclock-frontend/
ssh pi@raspberrypi.local 'sudo reboot'
```

## Backup

### Database backup

```bash
# On deathstar
pg_dump -U googleclock_user googleclock > backup_$(date +%Y%m%d).sql

# Restore
psql -U googleclock_user googleclock < backup_20231201.sql
```

### Face encodings backup

```bash
# Backup
cp /opt/google-clock-2.0/ai-server/models/face_encodings.pkl ~/backups/

# Restore
cp ~/backups/face_encodings.pkl /opt/google-clock-2.0/ai-server/models/
```

## Security Recommendations

1. **Change default passwords** in all .env files
2. **Enable firewall** on all machines
3. **Use HTTPS** in production (setup nginx reverse proxy)
4. **Restrict database access** to localhost only
5. **Regular updates**: `sudo apt update && sudo apt upgrade`
6. **Backup database** regularly (daily cron job)
7. **Monitor logs** for suspicious activity

## Performance Tuning

### Backend

- Enable Redis caching for API responses
- Use PostgreSQL connection pooling
- Enable gzip compression in nginx

### AI Server

- Use smaller Whisper model (tiny/base) for faster STT
- Reduce face recognition frequency
- Cache API responses aggressively

### Frontend (Pi 3)

- Lower camera resolution (320x240 for motion detection)
- Reduce motion detection frequency (1 fps)
- Use hardware video decoding (OMXPlayer)
- Minimize JavaScript in browser

## Support

For issues, please open a GitHub issue with:
- Component (backend/ai-server/frontend)
- Error logs
- System information
- Steps to reproduce
