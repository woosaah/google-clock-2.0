#!/bin/bash
# Google Clock 2.0 - Raspberry Pi 3 Kiosk Setup Script
# This script configures a Raspberry Pi 3 to run the frontend in fullscreen kiosk mode

set -e

echo "========================================="
echo "Google Clock 2.0 - Pi 3 Kiosk Setup"
echo "========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y \
    chromium-browser \
    unclutter \
    xdotool \
    x11-xserver-utils \
    nodejs \
    npm

# Install Node.js 18 (if not already installed)
if ! node --version | grep -q "v18"; then
    echo "Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Configure autostart
echo "Configuring autostart..."
mkdir -p ~/.config/lxsession/LXDE-pi
cat > ~/.config/lxsession/LXDE-pi/autostart <<EOF
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash

# Disable screen blanking
@xset s off
@xset -dpms
@xset s noblank

# Hide mouse cursor
@unclutter -idle 0.1 -root

# Start Google Clock frontend
@/home/pi/google-clock-start.sh
EOF

# Create startup script
echo "Creating startup script..."
cat > ~/google-clock-start.sh <<'EOF'
#!/bin/bash

# Wait for network
while ! ping -c1 192.168.1.243 &>/dev/null; do
    echo "Waiting for network..."
    sleep 2
done

# Load environment variables
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

# Frontend URL (change if different)
FRONTEND_URL="http://localhost:3000"

# Wait for frontend to be available (if running on same Pi)
# If frontend is on different machine, change URL accordingly
for i in {1..30}; do
    if curl -s "$FRONTEND_URL" > /dev/null; then
        break
    fi
    echo "Waiting for frontend to start..."
    sleep 2
done

# Start Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --check-for-update-interval=31536000 \
    --disable-session-crashed-bubble \
    --disable-translate \
    --autoplay-policy=no-user-gesture-required \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --disable-touch-drag-drop \
    --disable-features=IsolateOrigins,site-per-process \
    "$FRONTEND_URL"
EOF

chmod +x ~/google-clock-start.sh

# Disable screen blanking in boot config
echo "Configuring boot settings..."
if ! grep -q "hdmi_blanking=1" /boot/config.txt; then
    echo "hdmi_blanking=1" | sudo tee -a /boot/config.txt
fi

# Configure camera (PS Eye)
echo "Configuring camera support..."
sudo modprobe bcm2835-v4l2
if ! grep -q "bcm2835-v4l2" /etc/modules; then
    echo "bcm2835-v4l2" | sudo tee -a /etc/modules
fi

# Configure audio (PS Eye microphone)
echo "Configuring audio..."
cat > ~/.asoundrc <<'EOF'
pcm.!default {
    type asym
    playback.pcm "plughw:0,0"
    capture.pcm "plughw:1,0"
}

ctl.!default {
    type hw
    card 1
}
EOF

# Create systemd service for frontend (if building locally on Pi)
echo "Creating systemd service for frontend..."
sudo tee /etc/systemd/system/googleclock-frontend.service > /dev/null <<'EOF'
[Unit]
Description=Google Clock 2.0 Frontend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/google-clock-2.0/frontend
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start frontend service
sudo systemctl daemon-reload
sudo systemctl enable googleclock-frontend
# Don't start yet - user needs to build frontend first

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Clone the repository to /home/pi/google-clock-2.0"
echo "2. cd /home/pi/google-clock-2.0/frontend"
echo "3. npm install"
echo "4. Update .env with your backend URL"
echo "5. npm run build"
echo "6. sudo systemctl start googleclock-frontend"
echo "7. Reboot: sudo reboot"
echo ""
echo "The system will automatically start in kiosk mode on boot."
echo ""
