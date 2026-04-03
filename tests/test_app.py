"""
Comprehensive test suite for TransformerIQ Analyzer.
Tests parser, calculator, and Flask routes.
"""
import pytest
import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.parser import parse_transformer_data, detect_test_type, detect_separator, clean_content
from app.utils.calculator import (
    compute_rms, compute_average_power, detect_frequency,
    analyze_no_load_test, analyze_short_circuit_test,
    compute_combined_analysis, generate_waveform_data,
    compute_harmonic_analysis, extract_complete_cycles,
)
from app.main import create_app


# ── Fixtures ──

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_noload_csv():
    """Generate sample no-load test CSV in Festo format."""
    t = np.arange(0, 50, 0.098)
    f = 50.0
    V = 240 * np.sqrt(2) * np.sin(2 * np.pi * f * t / 1000)
    I = 0.015 * np.sqrt(2) * np.sin(2 * np.pi * f * t / 1000 - np.radians(85))
    P = V * I
    
    lines = [
        "Oscilloscope Trace Export,,,,,,",
        "Festo Didactic LVDAC-EMS 3.21,,,,,,",
        ",,,,,,",
        ",,,,,,",
        ",,Ch1,,Ch2,,Ch3",
        "Time ,,E1,,I1,,P1",
        "(ms),,(V),,(A),,(W)",
    ]
    for i in range(len(t)):
        lines.append(f"{t[i]:.3f},,{V[i]:.1f},,{I[i]:.4f},,{P[i]:.2f}")
    return "\n".join(lines)

@pytest.fixture
def sample_sc_csv():
    """Generate sample short-circuit test CSV in Festo format."""
    t = np.arange(0, 50, 0.098)
    f = 50.0
    V = 35 * np.sqrt(2) * np.sin(2 * np.pi * f * t / 1000)
    I = 0.3 * np.sqrt(2) * np.sin(2 * np.pi * f * t / 1000 - np.radians(40))
    P = V * I
    
    lines = [
        "Oscilloscope Trace Export,,,,,,",
        "Festo Didactic LVDAC-EMS 3.21,,,,,,",
        ",,,,,,",
        ",,,,,,",
        ",,Ch1,,Ch2,,Ch3",
        "Time ,,E1,,I1,,P1",
        "(ms),,(V),,(A),,(W)",
    ]
    for i in range(len(t)):
        lines.append(f"{t[i]:.3f},,{V[i]:.1f},,{I[i]:.4f},,{P[i]:.2f}")
    return "\n".join(lines)

@pytest.fixture
def sample_noload_tsv():
    """Generate sample no-load test in TSV format (like .txt files)."""
    t = np.arange(0, 50, 0.098)
    f = 50.0
    V = 340 * np.sin(2 * np.pi * f * t / 1000)
    I = 0.02 * np.sin(2 * np.pi * f * t / 1000 - np.radians(80))
    P = V * I
    
    lines = [
        "Oscilloscope Trace Export\t\t",
        "Festo Didactic LVDAC-EMS 3.21\t\t",
        "\t\t",
        "\t\t",
        "\t\tCh1\t\tCh2\t\tCh3",
        "Time \t\tE1\t\tI1\t\tP1",
        "(ms)\t\t(V)\t\t(A)\t\t(W)",
    ]
    for i in range(len(t)):
        lines.append(f"{t[i]:.3f}\t\t{V[i]:.1f}\t\t{I[i]:.4f}\t\t{P[i]:.2f}")
    return "\n".join(lines)


# ── Parser Tests ──

class TestParser:
    def test_detect_separator_csv(self):
        content = "a,,b,,c\n1,,2,,3"
        assert detect_separator(content) == ','
    
    def test_detect_separator_tsv(self):
        content = "a\t\tb\t\tc\n1\t\t2\t\t3"
        assert detect_separator(content) == '\t'
    
    def test_clean_content_bom(self):
        content = "\ufeffHello"
        assert clean_content(content) == "Hello"
    
    def test_clean_content_crlf(self):
        content = "line1\r\nline2\r\n"
        result = clean_content(content)
        assert '\r' not in result
    
    def test_parse_festo_csv(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv, "test.csv")
        assert 'Time_ms' in df.columns
        assert 'Voltage_V' in df.columns
        assert 'Current_A' in df.columns
        assert 'Power_W' in df.columns
        assert len(df) > 100
    
    def test_parse_festo_tsv(self, sample_noload_tsv):
        df = parse_transformer_data(sample_noload_tsv, "test.txt")
        assert 'Time_ms' in df.columns
        assert 'Voltage_V' in df.columns
        assert 'Current_A' in df.columns
        assert len(df) > 100
    
    def test_parse_sc_csv(self, sample_sc_csv):
        df = parse_transformer_data(sample_sc_csv, "sc.csv")
        assert len(df) > 100
        # SC data should have lower voltage
        assert df['Voltage_V'].abs().max() < 100
    
    def test_detect_noload(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        test_type = detect_test_type(df)
        assert test_type == 'no_load'
    
    def test_detect_shortcircuit(self, sample_sc_csv):
        df = parse_transformer_data(sample_sc_csv)
        test_type = detect_test_type(df)
        assert test_type == 'short_circuit'
    
    def test_parse_empty_raises(self):
        with pytest.raises(ValueError):
            parse_transformer_data("")
    
    def test_parse_simple_csv(self):
        content = "Time,Voltage,Current,Power\n0,100,0.5,50\n1,200,0.3,60\n2,150,0.4,60"
        df = parse_transformer_data(content, "simple.csv")
        assert len(df) == 3
    
    def test_sorted_by_time(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        assert df['Time_ms'].is_monotonic_increasing


# ── Calculator Tests ──

class TestCalculator:
    def test_compute_rms_sine(self):
        t = np.linspace(0, 1, 10000)
        signal = 100 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t)
        rms = compute_rms(signal)
        assert abs(rms - 100) < 1.0  # Should be ~100V RMS
    
    def test_compute_rms_dc(self):
        signal = np.ones(100) * 5.0
        assert abs(compute_rms(signal) - 5.0) < 0.001
    
    def test_compute_average_power(self):
        t = np.linspace(0, 0.02, 1000)  # One cycle at 50Hz
        v = 100 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t)
        i = 2 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t)
        p_avg = compute_average_power(v, i)
        assert abs(p_avg - 200) < 5  # P = Vrms * Irms * cos(0) = 100*2 = 200W
    
    def test_detect_frequency_50hz(self):
        t = np.arange(0, 100, 0.1)  # ms
        v = np.sin(2 * np.pi * 50 * t / 1000)
        freq = detect_frequency(t, v)
        assert abs(freq - 50) < 2
    
    def test_noload_analysis(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        results = analyze_no_load_test(df)
        assert results['test_type'] == 'No-Load Test'
        assert results['V_oc'] > 0
        assert results['I_o'] > 0
        assert results['P_core'] >= 0
        assert 0 <= results['PF_nl'] <= 1
        assert results['R_c'] > 0
        assert results['X_m'] > 0
        assert results['I_c'] >= 0
        assert results['I_m'] >= 0
        # Verify I_o^2 ≈ I_c^2 + I_m^2
        io_sq = results['I_o'] ** 2
        sum_sq = results['I_c'] ** 2 + results['I_m'] ** 2
        assert abs(io_sq - sum_sq) / max(io_sq, 1e-10) < 0.01
    
    def test_sc_analysis(self, sample_sc_csv):
        df = parse_transformer_data(sample_sc_csv)
        results = analyze_short_circuit_test(df)
        assert results['test_type'] == 'Short-Circuit Test'
        assert results['V_sc'] > 0
        assert results['I_sc'] > 0
        assert results['P_cu'] >= 0
        assert 0 <= results['PF_sc'] <= 1
        assert results['Z_eq'] > 0
        assert results['R_eq'] >= 0
        assert results['X_eq'] >= 0
        # Verify Z^2 ≈ R^2 + X^2
        z_sq = results['Z_eq'] ** 2
        sum_sq = results['R_eq'] ** 2 + results['X_eq'] ** 2
        assert abs(z_sq - sum_sq) / max(z_sq, 1e-10) < 0.01
    
    def test_combined_analysis(self, sample_noload_csv, sample_sc_csv):
        nl_df = parse_transformer_data(sample_noload_csv)
        sc_df = parse_transformer_data(sample_sc_csv)
        nl_results = analyze_no_load_test(nl_df)
        sc_results = analyze_short_circuit_test(sc_df)
        combined = compute_combined_analysis(nl_results, sc_results)
        
        assert combined['S_rated'] > 0
        assert len(combined['voltage_regulation']) == 5
        assert len(combined['efficiency_data']) == 10
        assert 0 < combined['max_efficiency'] <= 100
        assert combined['x_max_efficiency'] > 0
    
    def test_waveform_data(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        wf = generate_waveform_data(df)
        assert 'time' in wf
        assert 'voltage' in wf
        assert 'current' in wf
        assert len(wf['time']) == len(wf['voltage'])
    
    def test_harmonic_analysis(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        harmonics = compute_harmonic_analysis(df)
        assert 'voltage_harmonics' in harmonics
        assert 'current_harmonics' in harmonics
        assert 'thd_voltage' in harmonics
        assert harmonics['thd_voltage'] >= 0
        # Fundamental should be 100%
        if harmonics['voltage_harmonics']:
            assert harmonics['voltage_harmonics'][0]['percent'] == 100.0
    
    def test_extract_complete_cycles(self, sample_noload_csv):
        df = parse_transformer_data(sample_noload_csv)
        df_cycles = extract_complete_cycles(df)
        assert len(df_cycles) <= len(df)
        assert len(df_cycles) > 10


# ── Flask Route Tests ──

class TestRoutes:
    def test_index(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Transformer' in response.data
    
    def test_health(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
    
    def test_analyze_no_files(self, client):
        response = client.post('/analyze')
        assert response.status_code == 400
    
    def test_analyze_noload_only(self, client, sample_noload_csv):
        from io import BytesIO
        data = {
            'no_load_file': (BytesIO(sample_noload_csv.encode()), 'noload.csv'),
        }
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['no_load'] is not None
        assert result['no_load']['V_oc'] > 0
    
    def test_analyze_sc_only(self, client, sample_sc_csv):
        from io import BytesIO
        data = {
            'short_circuit_file': (BytesIO(sample_sc_csv.encode()), 'sc.csv'),
        }
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['short_circuit'] is not None
    
    def test_analyze_both(self, client, sample_noload_csv, sample_sc_csv):
        from io import BytesIO
        data = {
            'no_load_file': (BytesIO(sample_noload_csv.encode()), 'noload.csv'),
            'short_circuit_file': (BytesIO(sample_sc_csv.encode()), 'sc.csv'),
        }
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['no_load'] is not None
        assert result['short_circuit'] is not None
        assert result['combined'] is not None
    
    def test_analyze_invalid_file(self, client):
        from io import BytesIO
        data = {
            'no_load_file': (BytesIO(b'invalid data'), 'test.exe'),
        }
        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result.get('errors', [])) > 0 or result.get('error')
    
    def test_export_report(self, client):
        payload = {
            'no_load': {
                'V_oc': 240.0, 'I_o': 0.015, 'P_core': 2.5, 'PF_nl': 0.7,
                'theta_nl_deg': 45.0, 'I_c': 0.01, 'I_m': 0.012,
                'R_c': 24000, 'X_m': 20000, 'frequency_Hz': 50.0,
                'S_o': 3.6, 'Q_o': 2.88,
            },
            'short_circuit': {
                'V_sc': 35.0, 'I_sc': 0.3, 'P_cu': 8.0, 'PF_sc': 0.76,
                'theta_sc_deg': 40.0, 'Z_eq': 116.7, 'R_eq': 88.9,
                'X_eq': 75.5, 'R1_approx': 44.4, 'R2_approx': 44.4,
                'X1_approx': 37.7, 'X2_approx': 37.7, 'frequency_Hz': 50.0,
                'S_sc': 10.5, 'Q_sc': 6.8,
            },
            'combined': None,
            'nl_harmonics': None,
            'sc_harmonics': None,
        }
        response = client.post('/export-report', 
                              data=json.dumps(payload),
                              content_type='application/json')
        assert response.status_code == 200
        assert b'Transformer' in response.data


# ── Edge Case Tests ──

class TestEdgeCases:
    def test_very_small_current(self):
        """Test with extremely small current values."""
        t = np.arange(0, 20, 0.1)
        content = "Time,E1,I1,P1\n"
        for ti in t:
            v = 300 * np.sin(2 * np.pi * 50 * ti / 1000)
            i = 0.001 * np.sin(2 * np.pi * 50 * ti / 1000 - 1.4)
            content += f"{ti},{v:.2f},{i:.6f},{v*i:.6f}\n"
        df = parse_transformer_data(content)
        result = analyze_no_load_test(df)
        assert result['V_oc'] > 0
        assert result['I_o'] > 0
    
    def test_dc_offset(self):
        """Test with DC offset in signals."""
        t = np.arange(0, 40, 0.1)
        content = "Time,E1,I1,P1\n"
        for ti in t:
            v = 10 + 30 * np.sin(2 * np.pi * 50 * ti / 1000)
            i = 0.05 + 0.2 * np.sin(2 * np.pi * 50 * ti / 1000 - 0.5)
            content += f"{ti},{v:.2f},{i:.4f},{v*i:.4f}\n"
        df = parse_transformer_data(content)
        result = analyze_short_circuit_test(df)
        assert result['Z_eq'] > 0
    
    def test_noisy_data(self):
        """Test with added noise."""
        np.random.seed(42)
        t = np.arange(0, 40, 0.1)
        content = "Time,E1,I1,P1\n"
        for ti in t:
            v = 240 * np.sin(2 * np.pi * 50 * ti / 1000) + np.random.normal(0, 5)
            i = 0.01 * np.sin(2 * np.pi * 50 * ti / 1000 - 1.3) + np.random.normal(0, 0.001)
            content += f"{ti},{v:.2f},{i:.6f},{v*i:.6f}\n"
        df = parse_transformer_data(content)
        result = analyze_no_load_test(df)
        assert result['V_oc'] > 150  # RMS of 240V peak ≈ 169.7V, noise shouldn't drop it below 150
    
    def test_60hz_data(self):
        """Test with 60Hz signal."""
        t = np.arange(0, 50, 0.098)
        content = "Time,E1,I1,P1\n"
        for ti in t:
            v = 120 * np.sqrt(2) * np.sin(2 * np.pi * 60 * ti / 1000)
            i = 0.5 * np.sqrt(2) * np.sin(2 * np.pi * 60 * ti / 1000 - 0.6)
            content += f"{ti},{v:.2f},{i:.4f},{v*i:.4f}\n"
        df = parse_transformer_data(content)
        result = analyze_short_circuit_test(df)
        assert abs(result['frequency_Hz'] - 60) < 5
    
    def test_semicolon_separated(self):
        """Test semicolon-separated data."""
        content = "Time;E1;I1;P1\n0;100;0.5;50\n0.1;200;0.3;60\n0.2;-50;0.1;-5"
        df = parse_transformer_data(content, "test.csv")
        assert len(df) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
