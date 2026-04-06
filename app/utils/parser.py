"""
Universal Transformer Test Data Parser
Handles CSV, TSV, TXT files from Festo Didactic LVDAC-EMS and other formats.
Robustly parses any oscilloscope trace export format.
"""
import pandas as pd
import numpy as np
import io
import re


def detect_separator(content: str) -> str:
    """Auto-detect delimiter: tab, comma, semicolon."""
    lines = content.strip().split('\n')
    data_lines = [ln for ln in lines if re.search(r'\d', ln)]
    if not data_lines:
        return ','
    sample = '\n'.join(data_lines[:10])
    tab_count = sample.count('\t')
    comma_count = sample.count(',')
    semi_count = sample.count(';')
    counts = {'\\t': tab_count, ',': comma_count, ';': semi_count}
    winner = max(counts, key=counts.get)
    return '\t' if winner == '\\t' else winner


def clean_content(content: str) -> str:
    """Remove BOM and normalize line endings."""
    content = content.lstrip('\ufeff')
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    return content


def find_header_and_data(content: str, sep: str) -> tuple:
    """
    Locate the header row and data start in oscilloscope exports.
    Returns (channel_names, unit_row_idx, data_start_idx, lines)
    """
    lines = content.strip().split('\n')
    header_idx = None
    units_idx = None
    data_start = None
    channel_names = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Detect channel header row (contains Ch1, Ch2, E1, I1, Time, etc.)
        lower = stripped.lower()
        if any(kw in lower for kw in ['time', 'ch1', 'ch2', 'e1', 'i1']):
            # Check if this is the label row (Time, E1, I1, P1...)
            if 'e1' in lower or 'i1' in lower or 'p1' in lower:
                parts = [p.strip() for p in re.split(f'[{re.escape(sep)}]', stripped) if p.strip()]
                if any(p.lower() in ['e1', 'i1', 'p1', 'time', 'time '] for p in parts):
                    channel_names = parts
                    header_idx = i
            elif 'time' in lower and header_idx is None:
                parts = [p.strip() for p in re.split(f'[{re.escape(sep)}]', stripped) if p.strip()]
                channel_names = parts
                header_idx = i
        # Detect units row (contains (V), (A), (W), (ms))
        if '(v)' in lower or '(a)' in lower or '(w)' in lower or '(ms)' in lower:
            units_idx = i
        # Detect first data row (starts with a number)
        if data_start is None and header_idx is not None:
            if i > header_idx and (units_idx is None or i > units_idx):
                # Check if this line starts with numeric data
                parts = [p.strip() for p in re.split(f'[{re.escape(sep)}]', stripped) if p.strip()]
                if parts:
                    try:
                        float(parts[0])
                        data_start = i
                    except ValueError:
                        pass

    return channel_names, units_idx, data_start, lines


def parse_festo_format(content: str, sep: str) -> pd.DataFrame:
    """Parse Festo Didactic LVDAC-EMS oscilloscope export format."""
    channel_names, units_idx, data_start, lines = find_header_and_data(content, sep)

    if data_start is None:
        raise ValueError("Could not find data rows in the file")

    # Extract data rows
    data_rows = []
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        parts = [p.strip() for p in re.split(f'[{re.escape(sep)}]', stripped)]
        # Filter out empty strings (from double separators like ,,)
        numeric_parts = []
        for p in parts:
            if p:
                try:
                    numeric_parts.append(float(p))
                except ValueError:
                    pass
        if len(numeric_parts) >= 2:  # At least time + one channel
            data_rows.append(numeric_parts)

    if not data_rows:
        raise ValueError("No numeric data found in file")

    # Determine column count from data
    max_cols = max(len(r) for r in data_rows)
    # Pad shorter rows
    for i in range(len(data_rows)):
        while len(data_rows[i]) < max_cols:
            data_rows[i].append(np.nan)

    # Build column names
    # Clean channel names
    clean_names = [n.strip() for n in channel_names if n.strip() and n.strip().lower() not in ['off', '()', '']]

    # Map to standard names
    col_names = []
    for name in clean_names:
        name_lower = name.lower().strip()
        if name_lower in ['time', 'time ']:
            col_names.append('Time_ms')
        elif name_lower == 'e1':
            col_names.append('Voltage_V')
        elif name_lower == 'i1':
            col_names.append('Current_A')
        elif name_lower == 'p1':
            col_names.append('Power_W')
        else:
            col_names.append(name)

    # Ensure we have enough column names
    while len(col_names) < max_cols:
        col_names.append(f'Col_{len(col_names)}')
    col_names = col_names[:max_cols]

    df = pd.DataFrame(data_rows, columns=col_names)
    return df


def parse_simple_csv(content: str, sep: str) -> pd.DataFrame:
    """Fallback parser for simple CSV/TSV files."""
    try:
        df = pd.read_csv(io.StringIO(content), sep=sep)
        # Try to identify columns
        rename_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'time' in col_lower:
                rename_map[col] = 'Time_ms'
            elif 'volt' in col_lower or col_lower == 'v' or col_lower == 'e1':
                rename_map[col] = 'Voltage_V'
            elif 'curr' in col_lower or col_lower == 'a' or col_lower == 'i1':
                rename_map[col] = 'Current_A'
            elif 'pow' in col_lower or col_lower == 'w' or col_lower == 'p1':
                rename_map[col] = 'Power_W'
        if rename_map:
            df = df.rename(columns=rename_map)
        return df
    except Exception:
        raise ValueError("Could not parse file as simple CSV/TSV")


def brute_force_extract(content: str) -> pd.DataFrame:
    """
    Last-resort parser: scans every line, grabs rows with ≥2 floats.
    Strips all non-numeric characters before attempting float conversion.
    """
    rows = []
    for line in content.split('\n'):
        cleaned = re.sub(r'[^\d\.\-\,\;\t\s]', ' ', line)
        parts = re.split(r'[\s,;\t]+', cleaned.strip())
        nums = []
        for p in parts:
            p = p.strip()
            if p:
                try:
                    nums.append(float(p))
                except ValueError:
                    pass
        if len(nums) >= 2:
            rows.append(nums)

    if not rows:
        raise ValueError("No numeric data could be extracted from the file.")

    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append(np.nan)

    return pd.DataFrame(rows)


def infer_column_roles(df: pd.DataFrame) -> pd.DataFrame:
    """
    Infer Time, Voltage, Current, Power columns from data characteristics
    when column names are absent or unrecognised.
    Strategy: Time = most monotonically increasing col;
              Voltage = largest RMS among remainder;
              Current = second largest RMS; Power = third.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        raise ValueError("Need at least 2 numeric columns.")

    col_rms = {}
    col_monotonic = {}
    for col in numeric_cols:
        vals = df[col].dropna().values
        if len(vals) == 0:
            continue
        col_rms[col] = np.sqrt(np.mean(vals ** 2))
        diffs = np.diff(vals)
        col_monotonic[col] = np.sum(diffs > 0) / max(len(diffs), 1)

    time_col = max(col_monotonic, key=col_monotonic.get)
    remaining = [c for c in numeric_cols if c != time_col]
    if not remaining:
        raise ValueError("Could not separate time from signal columns.")

    remaining_sorted = sorted(remaining, key=lambda c: col_rms.get(c, 0), reverse=True)

    rename = {time_col: 'Time_ms', remaining_sorted[0]: 'Voltage_V'}
    if len(remaining_sorted) >= 2:
        rename[remaining_sorted[1]] = 'Current_A'
    if len(remaining_sorted) >= 3:
        rename[remaining_sorted[2]] = 'Power_W'

    df = df.rename(columns=rename)

    if 'Time_ms' not in df.columns and 'Voltage_V' in df.columns:
        n = len(df)
        df.insert(0, 'Time_ms', np.arange(n) * (1000 / (50 * 100)))

    return df


def parse_transformer_data(file_content: str, filename: str = '') -> pd.DataFrame:
    """
    Universal parser with 3-strategy fallback chain.
    Strategy 1: Festo LVDAC-EMS format
    Strategy 2: Simple pandas CSV/TSV
    Strategy 3: Brute-force numeric extraction
    Never raises unless the file has zero numeric data.
    """
    content = clean_content(file_content)
    if not content.strip():
        raise ValueError("File is empty")

    sep = detect_separator(content)
    df = None
    errors = []

    # Strategy 1
    try:
        df = parse_festo_format(content, sep)
        if len(df) < 5:
            raise ValueError("Too few rows from Festo parser")
    except Exception as e:
        errors.append(f"Festo: {e}")
        df = None

    # Strategy 2
    if df is None:
        try:
            df = parse_simple_csv(content, sep)
            if len(df) < 5:
                raise ValueError("Too few rows from CSV parser")
        except Exception as e:
            errors.append(f"CSV: {e}")
            df = None

    # Strategy 3
    if df is None:
        try:
            df = brute_force_extract(content)
        except Exception as e:
            errors.append(f"BruteForce: {e}")
            df = None

    if df is None or len(df) < 3:
        raise ValueError(
            f"Could not parse file after all strategies. "
            f"Details: {'; '.join(errors)}"
        )

    # Column identification — try to use names, fall back to inference
    required = ['Time_ms', 'Voltage_V', 'Current_A']
    if any(c not in df.columns for c in required):
        df = infer_column_roles(df)

    # Final check
    still_missing = [c for c in required if c not in df.columns]
    if still_missing:
        raise ValueError(
            f"Could not identify required columns: {still_missing}. "
            f"Found: {list(df.columns)}"
        )

    # Coerce to numeric, drop bad rows
    for col in ['Time_ms', 'Voltage_V', 'Current_A']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['Time_ms', 'Voltage_V', 'Current_A'])

    # Power column
    if 'Power_W' not in df.columns:
        df['Power_W'] = df['Voltage_V'] * df['Current_A']
    else:
        df['Power_W'] = pd.to_numeric(df['Power_W'], errors='coerce')
        df['Power_W'] = df['Power_W'].fillna(df['Voltage_V'] * df['Current_A'])

    df = df.sort_values('Time_ms').reset_index(drop=True)
    return df


def validate_test_data(df: pd.DataFrame, expected_type: str) -> tuple:
    """
    Adaptive validation using the V_rms / I_rms ratio.
    Works for any transformer voltage rating (24V, 120V, 240V, 480V …).

    No-load:      high voltage, tiny current   → ratio >> 1000
    Short-circuit: low voltage, rated current  → ratio << 200

    Ambiguous zone (200–1000): accept with empty reason (warnings shown elsewhere).
    """
    v_rms = np.sqrt(np.mean(df['Voltage_V'].values ** 2))
    i_rms = np.sqrt(np.mean(df['Current_A'].values ** 2))

    if i_rms < 1e-9:
        return False, "Current signal is essentially zero — check your file."
    if v_rms < 1e-6:
        return False, "Voltage signal is essentially zero — check your file."

    ratio = v_rms / i_rms

    AMBIGUOUS_LOW  = 200
    AMBIGUOUS_HIGH = 1000

    if expected_type == 'no_load':
        if ratio >= AMBIGUOUS_LOW:
            return True, ''
        return False, (
            f'V/I ratio = {ratio:.1f} (V_rms={v_rms:.2f} V, I_rms={i_rms:.4f} A) — '
            f'expected ratio > {AMBIGUOUS_LOW} for a No-Load test. '
            'This looks like Short-Circuit data in the wrong slot.'
        )

    if expected_type == 'short_circuit':
        if ratio < AMBIGUOUS_HIGH:
            return True, ''
        return False, (
            f'V/I ratio = {ratio:.1f} (V_rms={v_rms:.2f} V, I_rms={i_rms:.4f} A) — '
            f'expected ratio < {AMBIGUOUS_HIGH} for a Short-Circuit test. '
            'This looks like No-Load data in the wrong slot.'
        )

    return False, f'Unknown expected type: {expected_type}'
