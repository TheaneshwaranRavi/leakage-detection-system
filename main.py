#!/usr/bin/env python3
"""
5-Microphone Live Leakage Detection System
GitHub: https://github.com/YOUR_USERNAME/leakage-detection-system
"""

import numpy as np
import matplotlib.pyplot as plt
import sounddevice as sd
import time
import json
import threading
import queue
from datetime import datetime
from scipy import signal
from scipy.fft import fft, fftfreq
import RPi.GPIO as GPIO
import psutil
from flask import Flask, jsonify

class MicrophoneArray:
    def __init__(self):
        self.pins = {'A': 5, 'B': 6, 'C': 13, 'INH': 19}
        self.mic_map = {'reference': 0, 'quadrant1': 1, 'quadrant2': 2, 'quadrant3': 3, 'quadrant4': 4}
        GPIO.setmode(GPIO.BCM)
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        print("Microphone array initialized")
    
    def select_microphone(self, mic_name):
        if mic_name not in self.mic_map:
            raise ValueError(f"Invalid microphone: {mic_name}")
        channel = self.mic_map[mic_name]
        GPIO.output(self.pins['INH'], GPIO.LOW)
        GPIO.output(self.pins['A'], (channel >> 0) & 1)
        GPIO.output(self.pins['B'], (channel >> 1) & 1)
        GPIO.output(self.pins['C'], (channel >> 2) & 1)
        time.sleep(0.01)
    
    def disable_all(self):
        GPIO.output(self.pins['INH'], GPIO.HIGH)

class FFTAnalyzer:
    def __init__(self, sample_rate=48000, fft_size=4096):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.freq_bins = fftfreq(fft_size, 1/sample_rate)[:fft_size//2]
        self.thresholds = {'low': 20, 'medium': 10, 'high': 5}
    
    def compute_fft(self, audio_data):
        if len(audio_data) < self.fft_size:
            audio_data = np.pad(audio_data, (0, self.fft_size - len(audio_data)))
        else:
            audio_data = audio_data[:self.fft_size]
        window = np.hanning(self.fft_size)
        windowed_data = audio_data * window
        fft_result = fft(windowed_data)
        magnitude = np.abs(fft_result[:self.fft_size//2])
        magnitude_db = 20 * np.log10(magnitude + 1e-10)
        return magnitude_db
    
    def detect_leakage(self, ref_spectrum, test_spectrum):
        leakage_db = test_spectrum - ref_spectrum
        leaky_bands = []
        for i, diff in enumerate(leakage_db):
            if diff > -self.thresholds['high']:
                freq = self.freq_bins[i]
                leaky_bands.append({
                    'frequency': freq,
                    'leakage_db': diff,
                    'severity': self._classify_leakage(diff)
                })
        avg_leakage = np.mean(leakage_db)
        max_leakage = np.max(leakage_db)
        return {
            'leaky_bands': leaky_bands,
            'average_leakage_db': avg_leakage,
            'max_leakage_db': max_leakage,
            'overall_severity': self._classify_leakage(avg_leakage)
        }
    
    def _classify_leakage(self, leakage_db):
        if leakage_db > -self.thresholds['high']:
            return 'HIGH'
        elif leakage_db > -self.thresholds['medium']:
            return 'MEDIUM'
        elif leakage_db > -self.thresholds['low']:
            return 'LOW'
        else:
            return 'MINIMAL'

class LiveLeakageSystem:
    def __init__(self):
        self.mic_array = MicrophoneArray()
        self.fft_analyzer = FFTAnalyzer()
        self.sample_rate = 48000
        self.chunk_size = 4096
        self.recording_duration = 0.1
        self.current_results = {}
        self.is_running = False
        self.cpu_usage = 0
        self.memory_usage = 0
    
    def record_microphone(self, mic_name, duration=None):
        if duration is None:
            duration = self.recording_duration
        self.mic_array.select_microphone(mic_name)
        try:
            audio_data = sd.rec(int(duration * self.sample_rate), 
                              samplerate=self.sample_rate, channels=1, dtype='int32', blocking=True)
            return audio_data.flatten()
        except Exception as e:
            print(f"Recording error: {e}")
            return np.array([])
    
    def analyze_all_microphones(self):
        print("Starting multi-microphone analysis...")
        ref_data = self.record_microphone('reference')
        ref_spectrum = self.fft_analyzer.compute_fft(ref_data)
        results = {
            'timestamp': datetime.now().isoformat(),
            'quadrants': {}
        }
        for quad_num in range(1, 5):
            mic_name = f'quadrant{quad_num}'
            print(f"Recording {mic_name}...")
            quad_data = self.record_microphone(mic_name)
            quad_spectrum = self.fft_analyzer.compute_fft(quad_data)
            leakage_info = self.fft_analyzer.detect_leakage(ref_spectrum, quad_spectrum)
            results['quadrants'][mic_name] = {
                'spectrum': quad_spectrum.tolist(),
                'leakage_analysis': leakage_info,
                'rms_level': float(np.sqrt(np.mean(quad_data**2))),
                'peak_level': float(np.max(np.abs(quad_data)))
            }
        self.mic_array.disable_all()
        return results

# Web Interface
app = Flask(__name__)
system = LiveLeakageSystem()

@app.route('/')
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Leakage Detection</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .status { background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .quadrant { display: inline-block; width: 45%; margin: 10px; padding: 15px; border: 2px solid #ccc; border-radius: 5px; }
            .high { background: #ffcccc; border-color: #ff0000; }
            .medium { background: #ffffcc; border-color: #ffff00; }
            .low { background: #ccffcc; border-color: #00ff00; }
            .minimal { background: #cceeff; border-color: #0099ff; }
            h1 { color: #333; }
            h3 { margin-top: 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔊 Live Leakage Detection Dashboard</h1>
            <div id="status" class="status">Loading...</div>
            <div id="quadrants"></div>
        </div>
        <script>
            function updateDashboard() {
                fetch('/api/results')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status').innerHTML = 
                            `<strong>Last Update:</strong> ${data.timestamp}<br>
                             <strong>System:</strong> CPU ${data.cpu_usage}% | Memory ${data.memory_usage}%`;
                        
                        let quadrantsHtml = '';
                        for (let quad in data.quadrants) {
                            let quadData = data.quadrants[quad];
                            let severity = quadData.leakage_analysis.overall_severity.toLowerCase();
                            quadrantsHtml += 
                                `<div class="quadrant ${severity}">
                                    <h3>${quad.toUpperCase()}</h3>
                                    <p><strong>RMS Level:</strong> ${quadData.rms_level.toFixed(2)}</p>
                                    <p><strong>Peak Level:</strong> ${quadData.peak_level.toFixed(2)}</p>
                                    <p><strong>Avg Leakage:</strong> ${quadData.leakage_analysis.average_leakage_db.toFixed(1)} dB</p>
                                    <p><strong>Max Leakage:</strong> ${quadData.leakage_analysis.max_leakage_db.toFixed(1)} dB</p>
                                    <p><strong>Severity:</strong> ${quadData.leakage_analysis.overall_severity}</p>
                                    <p><strong>Problem Frequencies:</strong> ${quadData.leakage_analysis.leaky_bands.length}</p>
                                 </div>`;
                        }
                        document.getElementById('quadrants').innerHTML = quadrantsHtml;
                    })
                    .catch(error => {
                        document.getElementById('status').innerHTML = 'Error loading data: ' + error;
                    });
            }
            
            setInterval(updateDashboard, 2000);
            updateDashboard();
        </script>
    </body>
    </html>
    '''

@app.route('/api/results')
def get_api_results():
    if system.current_results:
        results = system.current_results.copy()
        results['cpu_usage'] = system.cpu_usage
        results['memory_usage'] = system.memory_usage
        return jsonify(results)
    return jsonify({'error': 'No results available'})

def monitoring_loop():
    while system.is_running:
        try:
            system.cpu_usage = psutil.cpu_percent()
            system.memory_usage = psutil.virtual_memory().percent
            system.current_results = system.analyze_all_microphones()
            time.sleep(2.0)
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(2.0)

def main():
    print("🚀 Starting 5-Microphone Leakage Detection System")
    print("=" * 60)
    
    system.is_running = True
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()
    
    try:
        print("🌐 Starting web dashboard...")
        print("📊 Access at: http://localhost:5000")
        print("⏹️  Press Ctrl+C to stop")
        print("=" * 60)
        
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        system.is_running = False
        system.mic_array.disable_all()
        GPIO.cleanup()
        print("✅ System stopped")

if __name__ == "__main__":
    main()
