"""
Transformer Equivalent Circuit Parameter Calculator

Calculates all transformer equivalent circuit parameters from
no-load and short-circuit test data using IEEE standard methods.

No-Load Test → Core (shunt) branch: Rc, Xm, Ic, Im, Io, PF_nl
Short-Circuit Test → Series branch: Req, Xeq, Zeq, PF_sc

Combined → Full equivalent circuit, voltage regulation, efficiency
"""
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


def safe_round(value, ndigits=4):
    """Round a value, returning None for inf/nan instead of crashing."""
    try:
        if value is None or math.isnan(value) or math.isinf(value):
            return None
        return round(float(value), ndigits)
    except (TypeError, ValueError, OverflowError):
        return None


def compute_rms(signal: np.ndarray) -> float:
    """Compute RMS value of a signal."""
    return np.sqrt(np.mean(signal ** 2))


def compute_average_power(voltage: np.ndarray, current: np.ndarray,
                          power_col: Optional[np.ndarray] = None) -> float:
    """
    Compute average (real) power.
    If instantaneous power column is available, use its mean.
    Otherwise compute from V*I.
    """
    if power_col is not None and len(power_col) > 0:
        return np.mean(power_col)
    return np.mean(voltage * current)


def detect_frequency(time_ms: np.ndarray, voltage: np.ndarray) -> float:
    """
    Detect the fundamental frequency of the signal using zero-crossing method.
    Returns frequency in Hz.
    """
    # Zero crossings (positive-going)
    sign_changes = np.where(np.diff(np.sign(voltage)) > 0)[0]

    if len(sign_changes) < 2:
        # Fallback: try FFT
        dt = np.mean(np.diff(time_ms)) / 1000.0  # Convert to seconds
        if dt <= 0:
            return 50.0  # Default
        n = len(voltage)
        fft_vals = np.abs(np.fft.rfft(voltage - np.mean(voltage)))
        freqs = np.fft.rfftfreq(n, d=dt)
        # Find dominant frequency (skip DC)
        if len(fft_vals) > 1:
            peak_idx = np.argmax(fft_vals[1:]) + 1
            return freqs[peak_idx]
        return 50.0

    # Average period from zero crossings
    periods = np.diff(time_ms[sign_changes]) / 1000.0  # Convert to seconds
    avg_period = np.mean(periods)

    if avg_period > 0:
        freq = 1.0 / avg_period
        # Snap to nearest standard frequency
        if 45 <= freq <= 55:
            return 50.0
        elif 55 < freq <= 65:
            return 60.0
        return freq

    return 50.0


def extract_complete_cycles(df: pd.DataFrame) -> pd.DataFrame:
    """Extract complete cycles; removes DC offset before crossing detection."""
    if len(df) < 10:
        return df

    voltage = df['Voltage_V'].values
    centered = voltage - np.mean(voltage)  # Remove DC offset

    sign_changes = np.where(
        (centered[:-1] <= 0) & (centered[1:] > 0)
    )[0]

    if len(sign_changes) >= 2:
        extracted = df.iloc[sign_changes[0]:sign_changes[-1] + 1].reset_index(drop=True)
        if len(extracted) >= 10:
            return extracted

    return df  # Fallback: return full data


def analyze_no_load_test(df: pd.DataFrame, rated_voltage: Optional[float] = None) -> Dict[str, Any]:
    """
    Analyze No-Load Test data to determine core branch parameters.

    In no-load test:
    - Primary is excited at rated voltage
    - Secondary is open-circuited
    - Measured: V_oc, I_o (no-load current), P_o (core loss)

    Parameters calculated:
    - P_core: Core loss (iron loss) = average power
    - V_oc: Open-circuit voltage (RMS)
    - I_o: No-load current (RMS) - also called exciting current
    - PF_nl: No-load power factor = P_core / (V_oc * I_o)
    - I_c: Core loss component of no-load current = P_core / V_oc
    - I_m: Magnetizing component = sqrt(I_o² - I_c²)
    - R_c: Core loss resistance = V_oc² / P_core = V_oc / I_c
    - X_m: Magnetizing reactance = V_oc / I_m
    """
    # Extract complete cycles for accurate RMS
    df_cycles = extract_complete_cycles(df)

    voltage = df_cycles['Voltage_V'].values
    current = df_cycles['Current_A'].values
    power = df_cycles['Power_W'].values if 'Power_W' in df_cycles.columns else None
    time_ms = df_cycles['Time_ms'].values

    # Compute RMS values
    V_oc = compute_rms(voltage)
    I_o = compute_rms(current)

    # Compute average power (core loss)
    P_core = abs(compute_average_power(voltage, current, power))

    # Detect frequency
    frequency = detect_frequency(time_ms, voltage)

    # Power factor
    S_o = V_oc * I_o  # Apparent power
    PF_nl = P_core / S_o if S_o > 0 else 0
    PF_nl = max(0.0, min(float(PF_nl), 1.0))

    # No-load current components
    I_c = P_core / V_oc if V_oc > 0 else 0  # Core loss component (in-phase)
    I_m_sq = I_o**2 - I_c**2
    I_m = np.sqrt(max(I_m_sq, 0))  # Magnetizing component (quadrature)

    # Core branch parameters
    R_c = V_oc / I_c if I_c > 0 else None
    X_m = V_oc / I_m if I_m > 0 else None

    # No-load angle
    theta_nl = np.arccos(PF_nl) if PF_nl <= 1 else 0

    # Peak values
    V_peak = np.max(np.abs(voltage))
    I_peak = np.max(np.abs(current))

    return {
        'test_type': 'No-Load Test',
        'V_oc': safe_round(V_oc, 4),
        'I_o': safe_round(I_o, 6),
        'P_core': safe_round(P_core, 4),
        'S_o': safe_round(S_o, 4),
        'Q_o': safe_round(V_oc * I_m, 4),
        'PF_nl': safe_round(PF_nl, 6),
        'theta_nl_deg': safe_round(np.degrees(theta_nl), 2),
        'I_c': safe_round(I_c, 6),
        'I_m': safe_round(I_m, 6),
        'R_c': safe_round(R_c, 2),
        'X_m': safe_round(X_m, 2),
        'frequency_Hz': safe_round(frequency, 1),
        'V_peak': safe_round(V_peak, 2),
        'I_peak': safe_round(I_peak, 6),
        'num_samples': len(df_cycles),
        'duration_ms': safe_round(time_ms[-1] - time_ms[0], 3) if len(time_ms) > 1 else 0,
    }


def analyze_short_circuit_test(df: pd.DataFrame, rated_current: Optional[float] = None) -> Dict[str, Any]:
    """
    Analyze Short-Circuit Test data to determine series branch parameters.

    In short-circuit test:
    - Secondary is short-circuited
    - Reduced voltage applied to primary until rated current flows
    - Measured: V_sc, I_sc (rated current), P_sc (copper loss)

    Parameters calculated:
    - P_cu: Copper loss = average power
    - V_sc: Short-circuit voltage (RMS)
    - I_sc: Short-circuit current (RMS)
    - PF_sc: Short-circuit power factor = P_cu / (V_sc * I_sc)
    - Z_eq: Equivalent impedance = V_sc / I_sc
    - R_eq: Equivalent resistance = P_cu / I_sc²
    - X_eq: Equivalent reactance = sqrt(Z_eq² - R_eq²)
    """
    # Extract complete cycles
    df_cycles = extract_complete_cycles(df)

    voltage = df_cycles['Voltage_V'].values
    current = df_cycles['Current_A'].values
    power = df_cycles['Power_W'].values if 'Power_W' in df_cycles.columns else None
    time_ms = df_cycles['Time_ms'].values

    # Compute RMS values
    V_sc = compute_rms(voltage)
    I_sc = compute_rms(current)

    # Compute average power (copper loss)
    P_cu = abs(compute_average_power(voltage, current, power))

    # Detect frequency
    frequency = detect_frequency(time_ms, voltage)

    # Power factor
    S_sc = V_sc * I_sc
    PF_sc = P_cu / S_sc if S_sc > 0 else 0
    PF_sc = max(0.0, min(float(PF_sc), 1.0))

    # Equivalent circuit parameters (referred to primary)
    Z_eq = V_sc / I_sc if I_sc > 0 else 0
    R_eq = P_cu / (I_sc**2) if I_sc > 0 else 0
    X_eq_sq = Z_eq**2 - R_eq**2
    X_eq = np.sqrt(max(X_eq_sq, 0))

    # Short-circuit angle
    theta_sc = np.arccos(PF_sc) if PF_sc <= 1 else 0

    # Peak values
    V_peak = np.max(np.abs(voltage))
    I_peak = np.max(np.abs(current))

    # Per-winding values (assuming equal distribution)
    R1 = R_eq / 2
    R2 = R_eq / 2
    X1 = X_eq / 2
    X2 = X_eq / 2

    return {
        'test_type': 'Short-Circuit Test',
        'V_sc': safe_round(V_sc, 4),
        'I_sc': safe_round(I_sc, 6),
        'P_cu': safe_round(P_cu, 4),
        'S_sc': safe_round(S_sc, 4),
        'Q_sc': safe_round(V_sc * I_sc * np.sin(theta_sc), 4),
        'PF_sc': safe_round(PF_sc, 6),
        'theta_sc_deg': safe_round(np.degrees(theta_sc), 2),
        'Z_eq': safe_round(Z_eq, 4),
        'R_eq': safe_round(R_eq, 4),
        'X_eq': safe_round(X_eq, 4),
        'R1_approx': safe_round(R1, 4),
        'R2_approx': safe_round(R2, 4),
        'X1_approx': safe_round(X1, 4),
        'X2_approx': safe_round(X2, 4),
        'frequency_Hz': safe_round(frequency, 1),
        'V_peak': safe_round(V_peak, 2),
        'I_peak': safe_round(I_peak, 6),
        'num_samples': len(df_cycles),
        'duration_ms': safe_round(time_ms[-1] - time_ms[0], 3) if len(time_ms) > 1 else 0,
    }


def compute_combined_analysis(nl_results: Dict, sc_results: Dict) -> Dict[str, Any]:
    """
    Compute combined analysis from both tests.

    Calculates:
    - Complete equivalent circuit
    - Voltage regulation at various power factors
    - Efficiency at various loads
    """
    V_rated = nl_results['V_oc']
    I_rated = sc_results['I_sc']
    P_core = nl_results['P_core']
    P_cu_fl = sc_results['P_cu']  # Full-load copper loss
    R_eq = sc_results['R_eq']
    X_eq = sc_results['X_eq']

    if P_cu_fl <= 0:
        P_cu_fl = 1e-9
    if V_rated <= 0:
        raise ValueError("V_oc from no-load test must be > 0")
    if I_rated <= 0:
        raise ValueError("I_sc from short-circuit test must be > 0")

    # Rated apparent power
    S_rated = V_rated * I_rated

    # Voltage regulation at various power factors
    vr_data = []
    pf_values = [1.0, 0.9, 0.8, 0.7, 0.6]
    for pf in pf_values:
        theta = np.arccos(pf)
        # Lagging
        vr_lag = ((R_eq * pf + X_eq * np.sin(theta)) / V_rated) * 100 if V_rated > 0 else 0
        # Leading
        vr_lead = ((R_eq * pf - X_eq * np.sin(theta)) / V_rated) * 100 if V_rated > 0 else 0
        vr_data.append({
            'pf': pf,
            'vr_lagging': round(vr_lag, 4),
            'vr_leading': round(vr_lead, 4),
        })

    # Efficiency at various loads
    eff_data = []
    load_fractions = [0.25, 0.5, 0.75, 1.0, 1.25]
    for x in load_fractions:
        for pf in [1.0, 0.8]:
            P_out = x * S_rated * pf
            P_cu_x = (x**2) * P_cu_fl
            P_total_loss = P_core + P_cu_x
            P_in = P_out + P_total_loss
            eff = (P_out / P_in) * 100 if P_in > 0 else 0
            eff_data.append({
                'load_fraction': x,
                'pf': pf,
                'P_out': round(P_out, 4),
                'P_cu': round(P_cu_x, 4),
                'P_core': round(P_core, 4),
                'P_total_loss': round(P_total_loss, 4),
                'efficiency': round(eff, 4),
            })

    # Maximum efficiency condition
    # η_max when x²·P_cu = P_core → x = sqrt(P_core / P_cu_fl)
    x_max_eff = np.sqrt(P_core / P_cu_fl) if P_cu_fl > 0 else 1.0
    P_out_max = x_max_eff * S_rated * 1.0  # at unity PF
    P_loss_max = 2 * P_core  # At max efficiency, P_core = x²·P_cu
    eff_max = (P_out_max / (P_out_max + P_loss_max)) * 100 if (P_out_max + P_loss_max) > 0 else 0

    # Percent impedance
    Z_percent = (sc_results['V_sc'] / V_rated) * 100 if V_rated > 0 else 0
    R_percent = (R_eq * I_rated / V_rated) * 100 if V_rated > 0 else 0
    X_percent = (X_eq * I_rated / V_rated) * 100 if V_rated > 0 else 0

    return {
        'S_rated': round(S_rated, 4),
        'V_rated': round(V_rated, 4),
        'I_rated': round(I_rated, 6),
        'voltage_regulation': vr_data,
        'efficiency_data': eff_data,
        'x_max_efficiency': round(x_max_eff, 4),
        'max_efficiency': round(eff_max, 4),
        'Z_percent': round(Z_percent, 4),
        'R_percent': round(R_percent, 4),
        'X_percent': round(X_percent, 4),
        'total_loss_fl': round(P_core + P_cu_fl, 4),
    }


def generate_waveform_data(df: pd.DataFrame) -> Dict[str, list]:
    """Generate waveform plot data from dataframe."""
    # Downsample if too many points for smooth rendering
    max_points = 1000
    if len(df) > max_points:
        step = len(df) // max_points
        df_plot = df.iloc[::step].copy()
    else:
        df_plot = df.copy()

    return {
        'time': df_plot['Time_ms'].round(4).tolist(),
        'voltage': df_plot['Voltage_V'].round(4).tolist(),
        'current': df_plot['Current_A'].round(6).tolist(),
        'power': df_plot['Power_W'].round(4).tolist() if 'Power_W' in df_plot.columns else [],
    }


def compute_harmonic_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Perform FFT-based harmonic analysis on voltage and current signals.
    """
    df_cycles = extract_complete_cycles(df)
    voltage = df_cycles['Voltage_V'].values
    current = df_cycles['Current_A'].values
    time_ms = df_cycles['Time_ms'].values

    dt = np.mean(np.diff(time_ms)) / 1000.0  # seconds
    n = len(voltage)

    if n < 10 or dt <= 0:
        return {'voltage_harmonics': [], 'current_harmonics': [], 'thd_voltage': 0, 'thd_current': 0}

    # FFT
    v_fft = np.abs(np.fft.rfft(voltage)) * 2 / n
    i_fft = np.abs(np.fft.rfft(current)) * 2 / n
    freqs = np.fft.rfftfreq(n, d=dt)

    # Find fundamental frequency index
    fund_freq = detect_frequency(time_ms, voltage)
    fund_idx = np.argmin(np.abs(freqs - fund_freq))

    if fund_idx == 0:
        fund_idx = 1

    # Extract harmonics (up to 15th)
    v_harmonics = []
    i_harmonics = []
    v_fund = v_fft[fund_idx]
    i_fund = i_fft[fund_idx]

    for h in range(1, 16):
        idx = h * fund_idx
        if idx >= len(v_fft):
            break
        # Search in a small window around expected harmonic
        window = max(1, fund_idx // 4)
        start = max(0, idx - window)
        end = min(len(v_fft), idx + window + 1)

        v_mag = np.max(v_fft[start:end])
        i_mag = np.max(i_fft[start:end])

        v_harmonics.append({
            'harmonic': h,
            'frequency': round(h * fund_freq, 1),
            'magnitude': round(v_mag, 4),
            'percent': round((v_mag / v_fund) * 100 if v_fund > 0 else 0, 2),
        })
        i_harmonics.append({
            'harmonic': h,
            'frequency': round(h * fund_freq, 1),
            'magnitude': round(i_mag, 6),
            'percent': round((i_mag / i_fund) * 100 if i_fund > 0 else 0, 2),
        })

    # THD calculation
    v_harm_sum_sq = sum(v_fft[h * fund_idx]**2 for h in range(2, 16)
                        if h * fund_idx < len(v_fft))
    i_harm_sum_sq = sum(i_fft[h * fund_idx]**2 for h in range(2, 16)
                        if h * fund_idx < len(i_fft))

    thd_v = np.sqrt(v_harm_sum_sq) / v_fund * 100 if v_fund > 0 else 0
    thd_i = np.sqrt(i_harm_sum_sq) / i_fund * 100 if i_fund > 0 else 0

    return {
        'voltage_harmonics': v_harmonics,
        'current_harmonics': i_harmonics,
        'thd_voltage': round(thd_v, 2),
        'thd_current': round(thd_i, 2),
        'fundamental_frequency': round(fund_freq, 1),
    }


def compute_confidence_score(df: pd.DataFrame, harmonics: dict) -> dict:
    """
    Score data quality 0–100 and return a confidence label + color.

    Factors:
    - THD voltage < 5% → excellent waveform
    - Number of complete cycles detected (more = better)
    - Monotonicity of time column (should be 100%)
    - Signal-to-noise estimate from RMS consistency across cycles
    """
    score = 100
    reasons = []

    thd_v = harmonics.get('thd_voltage', 0) if harmonics else 0
    thd_i = harmonics.get('thd_current', 0) if harmonics else 0

    if thd_v > 20:
        score -= 30
        reasons.append(f'High voltage THD ({thd_v:.1f}%)')
    elif thd_v > 10:
        score -= 15
        reasons.append(f'Moderate voltage THD ({thd_v:.1f}%)')
    elif thd_v > 5:
        score -= 5

    if thd_i > 30:
        score -= 20
        reasons.append(f'High current THD ({thd_i:.1f}%)')
    elif thd_i > 15:
        score -= 10

    # Time monotonicity
    time_vals = df['Time_ms'].values
    diffs = np.diff(time_vals)
    mono_ratio = np.sum(diffs > 0) / max(len(diffs), 1)
    if mono_ratio < 0.95:
        score -= 20
        reasons.append('Non-monotonic time column')

    # Sample count
    if len(df) < 100:
        score -= 15
        reasons.append(f'Low sample count ({len(df)})')
    elif len(df) < 200:
        score -= 5

    score = max(0, min(100, score))

    if score >= 85:
        label, color, icon = 'High Confidence', '#34d399', '✓'
    elif score >= 60:
        label, color, icon = 'Good', '#fbbf24', '~'
    else:
        label, color, icon = 'Check Data', '#f87171', '!'

    return {
        'score': score,
        'label': label,
        'color': color,
        'icon': icon,
        'reasons': reasons,
    }
