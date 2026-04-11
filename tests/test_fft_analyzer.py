#!/usr/bin/env python3
"""
Unit tests for FFTAnalyzer - testable without Raspberry Pi hardware.
"""

import unittest
import numpy as np
import sys
import os

# Mock RPi.GPIO and sounddevice before importing main
sys.modules['RPi'] = type(sys)('RPi')
sys.modules['RPi.GPIO'] = type(sys)('RPi.GPIO')
gpio_mock = sys.modules['RPi.GPIO']
gpio_mock.BCM = 11
gpio_mock.OUT = 0
gpio_mock.LOW = 0
gpio_mock.HIGH = 1
gpio_mock.setmode = lambda *a, **kw: None
gpio_mock.setup = lambda *a, **kw: None
gpio_mock.output = lambda *a, **kw: None
gpio_mock.cleanup = lambda *a, **kw: None

sys.modules['sounddevice'] = type(sys)('sounddevice')
sys.modules['sounddevice'].rec = lambda *a, **kw: np.zeros((4096, 1), dtype='int32')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import FFTAnalyzer


class TestFFTAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = FFTAnalyzer(sample_rate=48000, fft_size=4096)

    def test_init_defaults(self):
        """FFTAnalyzer initializes with correct default parameters."""
        self.assertEqual(self.analyzer.sample_rate, 48000)
        self.assertEqual(self.analyzer.fft_size, 4096)
        self.assertEqual(len(self.analyzer.freq_bins), 2048)

    def test_freq_bins_range(self):
        """Frequency bins span from 0 to Nyquist frequency."""
        self.assertAlmostEqual(self.analyzer.freq_bins[0], 0.0)
        max_freq = self.analyzer.sample_rate / 2
        self.assertLess(self.analyzer.freq_bins[-1], max_freq)

    def test_compute_fft_correct_length(self):
        """compute_fft returns spectrum with fft_size/2 bins."""
        audio = np.random.randn(4096)
        result = self.analyzer.compute_fft(audio)
        self.assertEqual(len(result), self.analyzer.fft_size // 2)

    def test_compute_fft_short_audio_padded(self):
        """Short audio data is zero-padded to fft_size."""
        audio = np.random.randn(1024)
        result = self.analyzer.compute_fft(audio)
        self.assertEqual(len(result), self.analyzer.fft_size // 2)

    def test_compute_fft_long_audio_truncated(self):
        """Long audio data is truncated to fft_size."""
        audio = np.random.randn(8192)
        result = self.analyzer.compute_fft(audio)
        self.assertEqual(len(result), self.analyzer.fft_size // 2)

    def test_compute_fft_returns_db(self):
        """FFT output is in decibels (finite values)."""
        audio = np.random.randn(4096)
        result = self.analyzer.compute_fft(audio)
        self.assertTrue(np.all(np.isfinite(result)))

    def test_compute_fft_silence(self):
        """Silent audio produces very low dB values."""
        audio = np.zeros(4096)
        result = self.analyzer.compute_fft(audio)
        # With epsilon of 1e-10, silence should give ~-200 dB
        self.assertTrue(np.all(result < -100))

    def test_compute_fft_sine_wave_peak(self):
        """A sine wave produces a peak at the correct frequency bin."""
        freq = 1000  # 1kHz
        t = np.arange(4096) / 48000
        audio = np.sin(2 * np.pi * freq * t)
        result = self.analyzer.compute_fft(audio)
        peak_idx = np.argmax(result)
        peak_freq = self.analyzer.freq_bins[peak_idx]
        # Peak should be within one bin width of 1kHz
        bin_width = 48000 / 4096
        self.assertAlmostEqual(peak_freq, freq, delta=bin_width)

    def test_detect_leakage_identical_spectra(self):
        """Identical spectra should show minimal leakage."""
        spectrum = np.random.randn(2048) * 10 - 50  # typical dB values
        result = self.analyzer.detect_leakage(spectrum, spectrum)
        self.assertAlmostEqual(result['average_leakage_db'], 0.0)
        self.assertAlmostEqual(result['max_leakage_db'], 0.0)

    def test_detect_leakage_high_leakage(self):
        """Test spectrum much louder than reference triggers HIGH severity."""
        ref_spectrum = np.full(2048, -60.0)
        test_spectrum = np.full(2048, -50.0)  # 10 dB higher
        result = self.analyzer.detect_leakage(ref_spectrum, test_spectrum)
        self.assertEqual(result['overall_severity'], 'HIGH')
        self.assertGreater(result['average_leakage_db'], 0)

    def test_detect_leakage_low_leakage(self):
        """Test spectrum slightly louder than reference shows low severity."""
        ref_spectrum = np.full(2048, -60.0)
        test_spectrum = np.full(2048, -75.0)  # 15 dB lower
        result = self.analyzer.detect_leakage(ref_spectrum, test_spectrum)
        self.assertEqual(result['overall_severity'], 'LOW')

    def test_detect_leakage_minimal(self):
        """Test spectrum much quieter than reference shows minimal severity."""
        ref_spectrum = np.full(2048, -40.0)
        test_spectrum = np.full(2048, -80.0)  # 40 dB lower
        result = self.analyzer.detect_leakage(ref_spectrum, test_spectrum)
        self.assertEqual(result['overall_severity'], 'MINIMAL')

    def test_detect_leakage_returns_required_keys(self):
        """detect_leakage returns all required result keys."""
        spectrum = np.random.randn(2048) * 10 - 50
        result = self.analyzer.detect_leakage(spectrum, spectrum)
        self.assertIn('leaky_bands', result)
        self.assertIn('average_leakage_db', result)
        self.assertIn('max_leakage_db', result)
        self.assertIn('overall_severity', result)

    def test_detect_leakage_leaky_bands_structure(self):
        """Leaky bands contain frequency, leakage_db, and severity."""
        ref_spectrum = np.full(2048, -60.0)
        test_spectrum = np.full(2048, -50.0)
        result = self.analyzer.detect_leakage(ref_spectrum, test_spectrum)
        self.assertGreater(len(result['leaky_bands']), 0)
        band = result['leaky_bands'][0]
        self.assertIn('frequency', band)
        self.assertIn('leakage_db', band)
        self.assertIn('severity', band)

    def test_classify_leakage_severity_levels(self):
        """Classification returns correct severity for known dB values."""
        self.assertEqual(self.analyzer._classify_leakage(0), 'HIGH')
        self.assertEqual(self.analyzer._classify_leakage(-3), 'HIGH')
        self.assertEqual(self.analyzer._classify_leakage(-7), 'MEDIUM')
        self.assertEqual(self.analyzer._classify_leakage(-15), 'LOW')
        self.assertEqual(self.analyzer._classify_leakage(-25), 'MINIMAL')

    def test_custom_fft_size(self):
        """FFTAnalyzer works with non-default FFT sizes."""
        analyzer = FFTAnalyzer(sample_rate=44100, fft_size=2048)
        self.assertEqual(analyzer.fft_size, 2048)
        self.assertEqual(len(analyzer.freq_bins), 1024)
        audio = np.random.randn(2048)
        result = analyzer.compute_fft(audio)
        self.assertEqual(len(result), 1024)


if __name__ == '__main__':
    unittest.main()
