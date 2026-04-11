# 🔊 5-Microphone Live Leakage Detection System

Real-time audio leakage detection with FFT analysis for mask testing, built for Raspberry Pi.

## Overview

This system uses a 5-microphone array with a CD74HC4067 analog multiplexer to detect sound leakage through masks or other barriers. It captures audio from a reference microphone and four quadrant microphones, performs FFT-based spectral analysis, and identifies frequency bands with significant leakage.

### Architecture

```
                    ┌─────────────────┐
                    │   Raspberry Pi   │
                    │                  │
  Mic 0 (Ref) ────►│  CD74HC4067 MUX │
  Mic 1 (Q1)  ────►│  GPIO Control    │──► I2S ADC ──► FFT Analysis
  Mic 2 (Q2)  ────►│  (A, B, C, INH) │
  Mic 3 (Q3)  ────►│                  │──► Flask Web Dashboard
  Mic 4 (Q4)  ────►│                  │     (port 5000)
                    └─────────────────┘
```

- **Reference Mic (Y0):** Captures the source audio signal
- **Quadrant 1-4 (Y1-Y4):** Positioned around the test subject to detect leakage

### How It Works

1. Records audio from the reference microphone
2. Sequentially records audio from each quadrant microphone
3. Computes FFT spectra for all recordings
4. Compares each quadrant's spectrum against the reference
5. Classifies leakage severity per frequency band: **HIGH**, **MEDIUM**, **LOW**, or **MINIMAL**
6. Displays results on a live-updating web dashboard

## Hardware Requirements

- Raspberry Pi (3B+ or later recommended)
- 5× I2S MEMS microphones (e.g., INMP441 or SPH0645)
- 1× CD74HC4067 16-channel analog multiplexer
- I2S ADC module
- Jumper wires

### GPIO Pin Mapping

| Multiplexer Pin | GPIO (BCM) | Description           |
|-----------------|------------|-----------------------|
| A (S0)          | 5          | Channel select bit 0  |
| B (S1)          | 6          | Channel select bit 1  |
| C (S2)          | 13         | Channel select bit 2  |
| INH (Enable)    | 19         | Inhibit (active high) |

## 🚀 Quick Installation (One Command)

**On your Raspberry Pi, run this single command:**

```bash
curl -sSL https://raw.githubusercontent.com/TheaneshwaranRavi/leakage-detection-system/main/install.sh | bash
```

This will:
- Install system dependencies (Python, PortAudio, Git)
- Clone the repository
- Install Python packages from `requirements.txt`
- Enable the I2S audio interface
- Configure ALSA audio
- Create and start a systemd service

## Manual Installation

```bash
# Clone the repository
git clone https://github.com/TheaneshwaranRavi/leakage-detection-system.git
cd leakage-detection-system

# Install dependencies
pip3 install -r requirements.txt

# Enable I2S on Raspberry Pi
sudo raspi-config nonint do_i2s 0

# Run the system
python3 main.py
```

## Usage

Once running, access the web dashboard at:

```
http://<raspberry-pi-ip>:5000
```

The dashboard displays:
- **Real-time system metrics** (CPU, memory usage)
- **Per-quadrant leakage analysis** with color-coded severity
- **RMS and peak audio levels** for each microphone
- **Average and maximum leakage** in dB
- **Number of problem frequencies** detected

### Service Management

```bash
# Check status
sudo systemctl status leakage-detection

# View logs
sudo journalctl -u leakage-detection -f

# Stop service
sudo systemctl stop leakage-detection

# Start service
sudo systemctl start leakage-detection

# Restart service
sudo systemctl restart leakage-detection
```

## Running Tests

```bash
pip3 install numpy scipy
python3 -m pytest tests/ -v
```

Tests cover the FFT analysis engine and leakage detection logic without requiring Raspberry Pi hardware.

## Project Structure

```
leakage-detection-system/
├── main.py              # Main application (microphone array, FFT, web dashboard)
├── install.sh           # One-command installer for Raspberry Pi
├── requirements.txt     # Python dependencies
├── tests/
│   └── test_fft_analyzer.py  # Unit tests for FFT analysis
├── .gitignore
└── README.md
```

## Configuration

Key parameters in `main.py`:

| Parameter           | Default | Description                          |
|---------------------|---------|--------------------------------------|
| `sample_rate`       | 48000   | Audio sample rate (Hz)               |
| `fft_size`          | 4096    | FFT window size (samples)            |
| `recording_duration`| 0.1     | Duration per microphone recording (s)|
| `threshold_high`    | 5 dB    | High leakage severity threshold      |
| `threshold_medium`  | 10 dB   | Medium leakage severity threshold    |
| `threshold_low`     | 20 dB   | Low leakage severity threshold       |

## License

This project is open source. See the repository for license details.
