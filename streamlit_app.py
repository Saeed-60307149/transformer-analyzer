"""
Transformer Equivalent Circuit Analyzer
Streamlit application — main entry point.

Flow:
  1. Upload no-load and/or short-circuit CSV test files
  2. Validate and preview the parsed data
  3. Click Analyze to compute equivalent circuit parameters
  4. Explore results across tabbed sections
  5. Download a printable PDF report
"""
import numpy as np
import pandas as pd
import streamlit as st

from app.utils.parser import parse_transformer_data, detect_test_type
from app.utils.calculator import (
    analyze_no_load_test,
    analyze_short_circuit_test,
    compute_combined_analysis,
    generate_waveform_data,
    compute_harmonic_analysis,
)
from app.utils import visualizer
from app.utils.report import generate_report_html

# ═══════════════════════════════════════════════════════════════════════════════
# Page configuration — must be the first Streamlit call
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Transformer Equivalent Circuit Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
# Global CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Layout ── */
[data-testid="stAppViewContainer"] > .main { background: #f0f4f8; }
[data-testid="stHeader"] { background: transparent !important; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; }

/* ── App header ── */
.app-header { padding-bottom: 1.25rem; margin-bottom: 0.5rem; }
.app-header h1 {
    font-size: 1.9rem; font-weight: 800;
    color: #0f172a; margin: 0; letter-spacing: -0.6px;
}
.app-header p { color: #475569; margin: 0.4rem 0 0; font-size: 0.95rem; line-height: 1.5; }

/* ── Section labels ── */
.section-label {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.8px; color: #94a3b8; margin-bottom: 0.5rem;
}

/* ── Parameter table ── */
.param-table {
    width: 100%; border-collapse: collapse;
    border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    font-size: 0.88rem;
}
.param-table thead tr { background: #f1f5f9; }
.param-table thead th {
    padding: 9px 14px; text-align: left; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 1px; color: #64748b;
    font-weight: 700; border-bottom: 2px solid #e2e8f0;
}
.param-table tbody tr:nth-child(even) { background: #f8fafc; }
.param-table tbody tr:nth-child(odd)  { background: #ffffff; }
.param-table tbody td { padding: 8px 14px; color: #334155; }
.param-table tbody td.val {
    text-align: right; font-family: 'JetBrains Mono', monospace;
    font-weight: 700; color: #0f172a; font-size: 0.92rem;
}
.param-table tbody td.unit { color: #94a3b8; }
.param-table tbody td.sym { font-family: monospace; color: #64748b; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #e8edf3; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important; padding: 6px 18px !important;
    font-weight: 500; font-size: 0.88rem;
}
.stTabs [aria-selected="true"] { background: white !important; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Session state initialisation
# ═══════════════════════════════════════════════════════════════════════════════
_DEFAULTS: dict = {
    'nl_df': None, 'sc_df': None,
    'nl_filename': '', 'sc_filename': '',
    'nl_result': None, 'sc_result': None, 'combined': None,
    'nl_waveform': None, 'sc_waveform': None,
    'nl_harmonics': None, 'sc_harmonics': None,
    'analyzed': False,
    'errors': [],
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def fmt(v, d: int = 4) -> str:
    """Format a numeric value. Returns '—' for None / NaN / Inf."""
    if v is None:
        return '—'
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return '—'
        return f'{f:.{d}f}'
    except (TypeError, ValueError):
        return '—'


def param_table(rows: list) -> None:
    """
    Render a clean HTML parameter table.
    rows: list of (label, symbol, value_string, unit)
    """
    body = ''
    for label, sym, val, unit in rows:
        body += (
            f'<tr>'
            f'<td>{label}</td>'
            f'<td class="sym">{sym}</td>'
            f'<td class="val">{val}</td>'
            f'<td class="unit">{unit}</td>'
            f'</tr>'
        )
    html = f"""
    <table class="param-table">
      <thead>
        <tr>
          <th>Parameter</th><th>Symbol</th><th style="text-align:right">Value</th><th>Unit</th>
        </tr>
      </thead>
      <tbody>{body}</tbody>
    </table>"""
    st.markdown(html, unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f'<p class="section-label">{text}</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
  <h1>⚡ Transformer Equivalent Circuit Analyzer</h1>
  <p>
    Upload oscilloscope CSV files from no-load and short-circuit tests.
    The app computes equivalent circuit parameters, efficiency curves, voltage
    regulation, and harmonic distortion — then generates a printable report.
  </p>
</div>
""", unsafe_allow_html=True)

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — File upload
# ═══════════════════════════════════════════════════════════════════════════════
up_l, up_r = st.columns(2, gap='large')


def _parse_upload(uploaded, expected_type: str, col) -> pd.DataFrame | None:
    """Parse an UploadedFile, show feedback in col, return DataFrame or None."""
    if uploaded is None:
        return None
    try:
        content = uploaded.read().decode('utf-8', errors='replace')
        df = parse_transformer_data(content, uploaded.name)
        detected = detect_test_type(df)
        label = 'no-load' if expected_type == 'no_load' else 'short-circuit'
        with col:
            if detected != expected_type:
                st.warning(
                    f"This file appears to contain **{detected.replace('_', '-')}** data. "
                    f"Processing as **{label}** as specified."
                )
            else:
                st.success(f"✓  {uploaded.name}  ·  {len(df):,} rows  ·  {len(df.columns)} columns")
        return df
    except Exception as exc:
        with col:
            st.error(f"Could not parse file: {exc}")
        return None


with up_l:
    st.markdown('<p class="section-label">No-Load (Open Circuit) Test</p>', unsafe_allow_html=True)
    nl_file = st.file_uploader(
        'No-Load CSV', type=['csv', 'tsv', 'txt', 'dat'],
        key='nl_upload', label_visibility='collapsed',
        help='Full rated voltage on primary, secondary open-circuited.',
    )

with up_r:
    st.markdown('<p class="section-label">Short-Circuit Test</p>', unsafe_allow_html=True)
    sc_file = st.file_uploader(
        'SC CSV', type=['csv', 'tsv', 'txt', 'dat'],
        key='sc_upload', label_visibility='collapsed',
        help='Reduced primary voltage until rated current flows; secondary shorted.',
    )

# Parse uploads and update state
nl_df_new = _parse_upload(nl_file, 'no_load', up_l)
sc_df_new = _parse_upload(sc_file, 'short_circuit', up_r)

if nl_file is not None:
    if nl_file.name != st.session_state['nl_filename']:
        st.session_state['analyzed'] = False   # new file → reset results
    if nl_df_new is not None:
        st.session_state['nl_df'] = nl_df_new
        st.session_state['nl_filename'] = nl_file.name
else:
    st.session_state['nl_df'] = None
    st.session_state['nl_filename'] = ''

if sc_file is not None:
    if sc_file.name != st.session_state['sc_filename']:
        st.session_state['analyzed'] = False
    if sc_df_new is not None:
        st.session_state['sc_df'] = sc_df_new
        st.session_state['sc_filename'] = sc_file.name
else:
    st.session_state['sc_df'] = None
    st.session_state['sc_filename'] = ''

nl_df: pd.DataFrame | None = st.session_state['nl_df']
sc_df: pd.DataFrame | None = st.session_state['sc_df']


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Data preview
# ═══════════════════════════════════════════════════════════════════════════════
if nl_df is not None or sc_df is not None:
    with st.expander('Data Preview', expanded=False):
        prev_l, prev_r = st.columns(2)
        if nl_df is not None:
            with prev_l:
                st.caption(f"No-Load — {st.session_state['nl_filename']}  ({len(nl_df):,} rows)")
                st.dataframe(
                    nl_df.head(30).style.format('{:.5f}'),
                    use_container_width=True, height=280,
                )
        if sc_df is not None:
            with prev_r:
                st.caption(f"Short-Circuit — {st.session_state['sc_filename']}  ({len(sc_df):,} rows)")
                st.dataframe(
                    sc_df.head(30).style.format('{:.5f}'),
                    use_container_width=True, height=280,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Analyze button
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('')
btn_col, _ = st.columns([2, 5])
with btn_col:
    do_analyze = st.button(
        '⚙  Analyze Data',
        type='primary',
        disabled=(nl_df is None and sc_df is None),
        use_container_width=True,
    )

if do_analyze:
    errors: list[str] = []
    with st.spinner('Computing equivalent circuit parameters…'):
        nl_result = sc_result = combined = None
        nl_waveform = sc_waveform = None
        nl_harmonics = sc_harmonics = None

        if nl_df is not None:
            try:
                nl_result   = analyze_no_load_test(nl_df)
                nl_waveform = generate_waveform_data(nl_df)
                nl_harmonics = compute_harmonic_analysis(nl_df)
            except Exception as exc:
                errors.append(f'No-Load analysis failed: {exc}')

        if sc_df is not None:
            try:
                sc_result   = analyze_short_circuit_test(sc_df)
                sc_waveform = generate_waveform_data(sc_df)
                sc_harmonics = compute_harmonic_analysis(sc_df)
            except Exception as exc:
                errors.append(f'Short-Circuit analysis failed: {exc}')

        if nl_result and sc_result:
            try:
                combined = compute_combined_analysis(nl_result, sc_result)
            except Exception as exc:
                errors.append(f'Combined analysis failed: {exc}')

    st.session_state.update({
        'nl_result': nl_result, 'sc_result': sc_result, 'combined': combined,
        'nl_waveform': nl_waveform, 'sc_waveform': sc_waveform,
        'nl_harmonics': nl_harmonics, 'sc_harmonics': sc_harmonics,
        'analyzed': True, 'errors': errors,
    })
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Results
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state['analyzed']:
    st.stop()

nl        = st.session_state['nl_result']
sc        = st.session_state['sc_result']
combined  = st.session_state['combined']
nl_wave   = st.session_state['nl_waveform']
sc_wave   = st.session_state['sc_waveform']
nl_harm   = st.session_state['nl_harmonics']
sc_harm   = st.session_state['sc_harmonics']
errors    = st.session_state['errors']

for err in errors:
    st.error(err)

if not nl and not sc:
    st.error('No results could be computed. Verify your uploaded files.')
    st.stop()

st.divider()
st.markdown('## Results')

# Build tabs dynamically — only include sections with data
_tab_defs = [
    ('Overview',           True),
    ('No-Load',            bool(nl)),
    ('Short-Circuit',      bool(sc)),
    ('Combined',           bool(combined)),
    ('Waveforms',          bool(nl_wave or sc_wave)),
    ('Equivalent Circuit', bool(nl or sc)),
    ('Report',             True),
]
_tab_labels = [label for label, show in _tab_defs if show]
_tab_objs   = st.tabs(_tab_labels)
TAB = dict(zip(_tab_labels, _tab_objs))


# ─── Tab: Overview ────────────────────────────────────────────────────────────
with TAB['Overview']:

    # KPI row — primary measurements
    kpi_count = (3 if nl else 0) + (3 if sc else 0)
    if kpi_count > 0:
        kpi_cols = st.columns(kpi_count)
        ci = 0
        if nl:
            kpi_cols[ci].metric('Core Loss', f"{fmt(nl['P_core'], 4)} W")
            ci += 1
            kpi_cols[ci].metric('No-Load PF', fmt(nl['PF_nl'], 4))
            ci += 1
            kpi_cols[ci].metric(
                'Xm  /  Rc',
                f"{fmt(nl['X_m'], 2)} Ω",
                f"Rc = {fmt(nl['R_c'], 2)} Ω",
            )
            ci += 1
        if sc:
            kpi_cols[ci].metric('Copper Loss', f"{fmt(sc['P_cu'], 4)} W")
            ci += 1
            kpi_cols[ci].metric('Zeq', f"{fmt(sc['Z_eq'], 4)} Ω")
            ci += 1
            kpi_cols[ci].metric('SC Power Factor', fmt(sc['PF_sc'], 4))

    # Combined summary KPIs
    if combined:
        st.markdown('')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Max Efficiency',
                  f"{fmt(combined['max_efficiency'], 2)} %",
                  f"at {fmt(combined['x_max_efficiency'] * 100, 1)}% load")
        c2.metric('Rated Apparent Power', f"{fmt(combined['S_rated'], 1)} VA")
        c3.metric('Percent Impedance',    f"{fmt(combined['Z_percent'], 2)} %")
        c4.metric('Full-Load Losses',     f"{fmt(combined['total_loss_fl'], 4)} W")

    st.markdown('')

    # Charts — only render combinations that have the required data
    if combined:
        r1a, r1b = st.columns(2)
        with r1a:
            st.plotly_chart(
                visualizer.efficiency_overview_chart(combined),
                use_container_width=True,
            )
        with r1b:
            st.plotly_chart(
                visualizer.vr_chart(combined['voltage_regulation']),
                use_container_width=True,
            )

    if nl and sc:
        r2a, r2b = st.columns(2)
        with r2a:
            st.plotly_chart(visualizer.loss_donut(nl, sc), use_container_width=True)
        with r2b:
            st.plotly_chart(visualizer.sc_power_bar(sc), use_container_width=True)
    elif sc:
        _, r2b = st.columns(2)
        with r2b:
            st.plotly_chart(visualizer.sc_power_bar(sc), use_container_width=True)


# ─── Tab: No-Load ─────────────────────────────────────────────────────────────
if 'No-Load' in TAB:
    with TAB['No-Load']:
        section_label('Core Branch Parameters')
        param_table([
            ('Open-Circuit Voltage',  'V_OC',  fmt(nl['V_oc'],          4), 'V'),
            ('No-Load Current',       'I₀',    fmt(nl['I_o'],           6), 'A'),
            ('Core Loss',             'P_core',fmt(nl['P_core'],        4), 'W'),
            ('Apparent Power',        'S₀',    fmt(nl['S_o'],           4), 'VA'),
            ('Reactive Power',        'Q₀',    fmt(nl['Q_o'],           4), 'VAR'),
            ('Power Factor',          'cos φ₀',fmt(nl['PF_nl'],        6), '—'),
            ('No-Load Angle',         'φ₀',    fmt(nl['theta_nl_deg'],  2), '°'),
            ('Core Loss Current',     'I_c',   fmt(nl['I_c'],           6), 'A'),
            ('Magnetizing Current',   'I_m',   fmt(nl['I_m'],           6), 'A'),
            ('Core Loss Resistance',  'R_c',   fmt(nl['R_c'],           2), 'Ω'),
            ('Magnetizing Reactance', 'X_m',   fmt(nl['X_m'],           2), 'Ω'),
            ('Frequency',             'f',     fmt(nl['frequency_Hz'],  1), 'Hz'),
        ])

        st.markdown('')
        ch1, ch2 = st.columns(2)
        with ch1:
            st.plotly_chart(visualizer.nl_current_components(nl), use_container_width=True)
        with ch2:
            st.plotly_chart(visualizer.nl_power_breakdown(nl), use_container_width=True)

        if nl_harm:
            st.plotly_chart(
                visualizer.harmonic_chart(nl_harm, 'No-Load Harmonic Analysis'),
                use_container_width=True,
            )

        if nl_wave:
            st.plotly_chart(
                visualizer.waveform_chart(nl_wave, 'No-Load Waveforms'),
                use_container_width=True,
            )


# ─── Tab: Short-Circuit ───────────────────────────────────────────────────────
if 'Short-Circuit' in TAB:
    with TAB['Short-Circuit']:
        section_label('Series Branch Parameters')
        param_table([
            ('Short-Circuit Voltage', 'V_SC',     fmt(sc['V_sc'],         4), 'V'),
            ('Short-Circuit Current', 'I_SC',     fmt(sc['I_sc'],         6), 'A'),
            ('Copper Loss',           'P_cu',     fmt(sc['P_cu'],         4), 'W'),
            ('Apparent Power',        'S_SC',     fmt(sc['S_sc'],         4), 'VA'),
            ('Power Factor',          'cos φ_SC', fmt(sc['PF_sc'],        6), '—'),
            ('SC Angle',              'φ_SC',     fmt(sc['theta_sc_deg'], 2), '°'),
            ('Equivalent Impedance',  'Z_eq',     fmt(sc['Z_eq'],         4), 'Ω'),
            ('Equivalent Resistance', 'R_eq',     fmt(sc['R_eq'],         4), 'Ω'),
            ('Equivalent Reactance',  'X_eq',     fmt(sc['X_eq'],         4), 'Ω'),
            ('R₁ (approx)',           'R₁',       fmt(sc['R1_approx'],    4), 'Ω'),
            ('X₁ (approx)',           'X₁',       fmt(sc['X1_approx'],    4), 'Ω'),
            ('Frequency',             'f',        fmt(sc['frequency_Hz'], 1), 'Hz'),
        ])

        st.markdown('')
        ch1, ch2 = st.columns(2)
        with ch1:
            st.plotly_chart(visualizer.impedance_chart(sc), use_container_width=True)
        with ch2:
            st.plotly_chart(visualizer.sc_power_breakdown(sc), use_container_width=True)

        if sc_harm:
            st.plotly_chart(
                visualizer.harmonic_chart(sc_harm, 'Short-Circuit Harmonic Analysis'),
                use_container_width=True,
            )

        if sc_wave:
            st.plotly_chart(
                visualizer.waveform_chart(sc_wave, 'Short-Circuit Waveforms'),
                use_container_width=True,
            )


# ─── Tab: Combined ────────────────────────────────────────────────────────────
if 'Combined' in TAB:
    with TAB['Combined']:
        c = combined

        section_label('Equivalent Circuit Summary')
        k1, k2, k3, k4 = st.columns(4)
        k1.metric('Rated VA',          f"{fmt(c['S_rated'], 1)} VA")
        k2.metric('Full-Load Losses',  f"{fmt(c['total_loss_fl'], 4)} W")
        k3.metric('Max Efficiency',
                  f"{fmt(c['max_efficiency'], 2)} %",
                  f"at {fmt(c['x_max_efficiency'] * 100, 1)}% load")
        k4.metric('% Impedance',       f"{fmt(c['Z_percent'], 2)} %")

        st.markdown('')
        st.plotly_chart(
            visualizer.efficiency_curve_chart(c, nl, sc),
            use_container_width=True,
        )

        st.markdown('')
        section_label('Voltage Regulation')
        vr_df = pd.DataFrame(c['voltage_regulation'])
        vr_df.columns = ['Power Factor', 'VR Lagging (%)', 'VR Leading (%)']
        st.dataframe(
            vr_df.style.format({'VR Lagging (%)': '{:.4f}', 'VR Leading (%)': '{:.4f}'}),
            use_container_width=True, hide_index=True,
        )

        st.markdown('')
        section_label('Efficiency at Various Loads')
        eff_df = pd.DataFrame(c['efficiency_data'])
        eff_df['Load (%)'] = (eff_df['load_fraction'] * 100).round(0).astype(int)
        eff_df = eff_df[['Load (%)', 'pf', 'P_out', 'P_cu', 'P_core', 'efficiency']].copy()
        eff_df.columns = ['Load (%)', 'PF', 'P_out (W)', 'P_cu (W)', 'P_core (W)', 'η (%)']
        st.dataframe(
            eff_df.style.format({
                'P_out (W)': '{:.4f}', 'P_cu (W)': '{:.5f}',
                'P_core (W)': '{:.5f}', 'η (%)': '{:.4f}',
            }),
            use_container_width=True, hide_index=True,
        )


# ─── Tab: Waveforms ───────────────────────────────────────────────────────────
if 'Waveforms' in TAB:
    with TAB['Waveforms']:
        if nl_wave:
            st.plotly_chart(
                visualizer.waveform_chart(nl_wave, 'No-Load Test — Voltage & Current'),
                use_container_width=True,
            )
        if sc_wave:
            st.plotly_chart(
                visualizer.waveform_chart(sc_wave, 'Short-Circuit Test — Voltage & Current'),
                use_container_width=True,
            )


# ─── Tab: Equivalent Circuit ──────────────────────────────────────────────────
if 'Equivalent Circuit' in TAB:
    with TAB['Equivalent Circuit']:
        st.markdown(
            visualizer.circuit_svg(nl, sc),
            unsafe_allow_html=True,
        )
        st.markdown('')
        if nl and sc:
            section_label('Component Values')
            param_table([
                ('Core Loss Resistance',      'R_c',  fmt(nl['R_c'],       2), 'Ω'),
                ('Magnetizing Reactance',     'X_m',  fmt(nl['X_m'],       2), 'Ω'),
                ('Equivalent Resistance',     'R_eq', fmt(sc['R_eq'],      4), 'Ω'),
                ('Equivalent Reactance',      'X_eq', fmt(sc['X_eq'],      4), 'Ω'),
                ('Equivalent Impedance',      'Z_eq', fmt(sc['Z_eq'],      4), 'Ω'),
                ('Primary Resistance (est.)', 'R₁',   fmt(sc['R1_approx'], 4), 'Ω'),
                ('Primary Reactance (est.)',  'X₁',   fmt(sc['X1_approx'], 4), 'Ω'),
            ])


# ─── Tab: Report ──────────────────────────────────────────────────────────────
with TAB['Report']:
    section_label('Download Report')
    st.markdown(
        'The report is a self-contained HTML file. '
        'Open it in any browser and use **File → Print → Save as PDF** '
        'to produce a high-quality PDF.'
    )
    st.markdown('')

    report_html = generate_report_html(
        nl, sc, combined,
        nl_harm, sc_harm,
    )

    dl_col, _ = st.columns([2, 5])
    with dl_col:
        st.download_button(
            label='⬇  Download Report (HTML → PDF)',
            data=report_html.encode('utf-8'),
            file_name='transformer_analysis_report.html',
            mime='text/html',
            use_container_width=True,
            type='primary',
        )

    st.markdown('')
    section_label('Report Preview')
    st.markdown(
        f'<div style="background:white;border-radius:10px;padding:2rem 2.5rem;'
        f'border:1px solid #e2e8f0;max-height:600px;overflow:auto;">'
        f'{report_html}</div>',
        unsafe_allow_html=True,
    )
