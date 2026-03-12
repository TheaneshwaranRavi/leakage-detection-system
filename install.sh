#!/bin/bash

echo "🚀 Installing Leakage Detection System from GitHub..."
echo "=" * 60

# Update system
echo "📦 Updating system packages..."
sudo apt update -y
sudo apt upgrade -y

# Install Python dependencies
echo "🐍 Installing Python packages..."
sudo apt install -y python3-pip python3-dev portaudio19-dev

# Install Python libraries
pip3 install numpy scipy matplotlib sounddevice pyaudio flask psutil RPi.GPIO

# Enable I2S (non-interactive)
echo "🔧 Enabling I2S interface..."
sudo raspi-config nonint do_i2s 0

# Create ALSA configuration
echo "🔊 Configuring audio system..."
sudo tee /etc/asound.conf > /dev/null <<'EOF'
pcm.!default {
    type hw
    card 0
    device 0
}
ctl.!default {
    type hw
    card 0
}
EOF

# Set permissions
chmod +x main.py
chmod +x install.sh

# Create systemd service
echo "⚙️  Creating system service..."
sudo tee /etc/systemd/system/leakage-detection.service > /dev/null <<'EOF'
[Unit]
Description=Leakage Detection System
After=network.target sound.target
Wants=leakage-detection.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/leakage-detection-system
ExecStart=/usr/bin/python3 /home/pi/leakage-detection-system/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable leakage-detection
sudo systemctl start leakage-detection

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "🎉 INSTALLATION COMPLETE!"
echo "=" * 60
echo "🌐 Web Dashboard: http://$IP:5000"
echo "📊 Service Status: sudo systemctl status leakage-detection"
echo "📋 View Logs: sudo journalctl -u leakage-detection -f"
echo "⏹️  Stop Service: sudo systemctl stop leakage-detection"
echo "▶️  Start Service: sudo systemctl start leakage-detection"
echo ""
echo "🔊 5-Microphone System Ready!"
echo "   • Reference Mic (Y0)"
echo "   • Quadrant 1 (Y1)"
echo "   • Quadrant 2 (Y2)"
echo "   • Quadrant 3 (Y3)"
echo "   • Quadrant 4 (Y4)"
echo ""
