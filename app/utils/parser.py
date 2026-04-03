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


def parse_transformer_data(file_content: str, filename: str = '') -> pd.DataFrame:
    """
    Universal parser that handles any transformer test data format.

    Supports:
    - Festo Didactic LVDAC-EMS oscilloscope exports (CSV, TSV, TXT)
    - Simple CSV/TSV with headers
    - Tab-separated data with double-tab separators
    - Files with metadata headers before data

    Returns DataFrame with standardized columns: Time_ms, Voltage_V, Current_A, Power_W
    """
    content = clean_content(file_content)

    if not content.strip():
        raise ValueError("File is empty")

    sep = detect_separator(content)

    # Check if it's a Festo format (has metadata header)
    lower_content = content[:500].lower()
    is_festo = 'festo' in lower_content or 'oscilloscope' in lower_content or 'lvdac' in lower_content

    try:
        if is_festo:
            df = parse_festo_format(content, sep)
        else:
            # Try Festo format first (might not have Festo header but same structure)
            try:
                df = parse_festo_format(content, sep)
            except (ValueError, IndexError):
                df = parse_simple_csv(content, sep)
    except Exception as e:
        # Last resort: try simple CSV
        try:
            df = parse_simple_csv(content, sep)
        except Exception:
            raise ValueError(f"Could not parse file: {str(e)}")

    # Validate we have the required columns
    required = ['Time_ms', 'Voltage_V', 'Current_A']
    missing = [col for col in required if col not in df.columns]

    if missing:
        # Try to auto-assign columns based on position
        if len(df.columns) >= 3:
            new_names = ['Time_ms', 'Voltage_V', 'Current_A']
            if len(df.columns) >= 4:
                new_names.append('Power_W')
            for i in range(4, len(df.columns)):
                new_names.append(f'Extra_{i}')
            df.columns = new_names[:len(df.columns)]
        else:
            raise ValueError(f"File must contain at least Time, Voltage, and Current columns. Found: {list(df.columns)}")

    # Drop rows with NaN in critical columns
    df = df.dropna(subset=['Time_ms', 'Voltage_V', 'Current_A'])

    # Calculate Power if not present
    if 'Power_W' not in df.columns:
        df['Power_W'] = df['Voltage_V'] * df['Current_A']

    # Sort by time
    df = df.sort_values('Time_ms').reset_index(drop=True)

    return df


def detect_test_type(df: pd.DataFrame) -> str:
    """
    Auto-detect whether data is from a No-Load or Short-Circuit test.

    No-Load: Full rated voltage applied to primary (typically >50 V RMS)
    Short-Circuit: Reduced voltage applied (~5-15% of rated, typically <50 V RMS)

    The voltage magnitude is the most reliable physical indicator:
    - No-load test always applies full line voltage to the primary
    - Short-circuit test uses a small fraction to limit current
    """
    v_rms = np.sqrt(np.mean(df['Voltage_V'].values ** 2))
    i_rms = np.sqrt(np.mean(df['Current_A'].values ** 2))
    impedance_magnitude = v_rms / i_rms if i_rms > 0 else float('inf')

    # Primary heuristic: voltage level
    # No-load: full primary voltage (>50 V for typical lab transformers)
    # Short-circuit: reduced voltage (<50 V)
    if v_rms > 50:
        return 'no_load'
    # Fallback: impedance ratio for edge cases (e.g. very small transformers)
    if impedance_magnitude > 100:
        return 'no_load'
    return 'short_circuit'
