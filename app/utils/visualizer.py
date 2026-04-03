"""
Plotly-based visualization functions for transformer analysis.
Returns plotly.graph_objects.Figure objects for use in Streamlit.
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional

# ── Color palette ──
NL_BLUE   = '#0ea5e9'   # sky-500  — no-load data
SC_PINK   = '#e879f9'   # fuchsia-400 — short-circuit data
INDIGO    = '#6366f1'   # indigo-500 — combined / reactance
EMERALD   = '#10b981'   # emerald-500 — efficiency / core
AMBER     = '#f59e0b'   # amber-400  — magnetizing
GRAY      = '#94a3b8'   # slate-400


def _layout(**overrides) -> dict:
    """Shared base layout for every chart."""
    base = dict(
        template='plotly_white',
        font=dict(family='Inter, system-ui, sans-serif', size=12, color='#334155'),
        margin=dict(l=16, r=16, t=44, b=16),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', y=1.10, x=0, font_size=11),
        height=290,
    )
    base.update(overrides)
    return base


def _axis(title: str, **kw) -> dict:
    return dict(title_text=title, gridcolor='#f1f5f9', zerolinecolor='#e2e8f0', **kw)


# ── Waveforms ────────────────────────────────────────────────────────────────

def waveform_chart(waveform: Dict, title: str) -> go.Figure:
    """Time-domain voltage and current waveform with dual y-axis."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=waveform['time'], y=waveform['voltage'],
            name='Voltage (V)', line=dict(color=NL_BLUE, width=1.5),
            hovertemplate='%{x:.3f} ms  %{y:.3f} V<extra></extra>',
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=waveform['time'], y=waveform['current'],
            name='Current (A)', line=dict(color=SC_PINK, width=1.5),
            hovertemplate='%{x:.3f} ms  %{y:.5f} A<extra></extra>',
        ),
        secondary_y=True,
    )
    fig.update_layout(title_text=title, **_layout(height=300))
    fig.update_xaxes(**_axis('Time (ms)'), tickformat='.1f')
    fig.update_yaxes(**_axis('Voltage (V)'), secondary_y=False)
    fig.update_yaxes(title_text='Current (A)', showgrid=False,
                     zerolinecolor='#e2e8f0', secondary_y=True)
    return fig


# ── Harmonics ─────────────────────────────────────────────────────────────────

def harmonic_chart(harmonics: Dict, title: str) -> go.Figure:
    """Grouped bar chart of voltage and current harmonics."""
    v_harm = harmonics.get('voltage_harmonics', [])
    i_harm = harmonics.get('current_harmonics', [])
    if not v_harm or not i_harm:
        return go.Figure()

    labels = [f"H{h['harmonic']}" for h in v_harm]
    thd_v  = harmonics.get('thd_voltage', 0)
    thd_i  = harmonics.get('thd_current', 0)

    fig = go.Figure([
        go.Bar(
            name=f'Voltage  (THD {thd_v}%)',
            x=labels, y=[h['percent'] for h in v_harm],
            marker_color=NL_BLUE, marker_opacity=0.85,
        ),
        go.Bar(
            name=f'Current  (THD {thd_i}%)',
            x=labels, y=[h['percent'] for h in i_harm],
            marker_color=SC_PINK, marker_opacity=0.85,
        ),
    ])
    fig.update_layout(
        title_text=title, barmode='group',
        **_layout(),
        xaxis=_axis('Harmonic Order'),
        yaxis=_axis('% of Fundamental'),
    )
    return fig


# ── Efficiency ────────────────────────────────────────────────────────────────

def efficiency_overview_chart(combined: Dict) -> go.Figure:
    """Discrete efficiency vs load from combined analysis data."""
    upf = [e for e in combined['efficiency_data'] if e['pf'] == 1.0]
    pf8 = [e for e in combined['efficiency_data'] if e['pf'] == 0.8]

    fig = go.Figure([
        go.Scatter(
            x=[e['load_fraction'] * 100 for e in upf],
            y=[e['efficiency'] for e in upf],
            name='Unity PF', mode='lines+markers',
            line=dict(color=NL_BLUE, width=2),
            marker=dict(size=7),
        ),
        go.Scatter(
            x=[e['load_fraction'] * 100 for e in pf8],
            y=[e['efficiency'] for e in pf8],
            name='0.8 PF Lagging', mode='lines+markers',
            line=dict(color=SC_PINK, width=2),
            marker=dict(size=7),
        ),
    ])
    fig.update_layout(
        title_text='Efficiency vs Load',
        **_layout(),
        xaxis=_axis('Load (%)'),
        yaxis=_axis('Efficiency (%)'),
    )
    return fig


def efficiency_curve_chart(combined: Dict, nl: Dict, sc: Dict) -> go.Figure:
    """Smooth, dense efficiency curves with max-efficiency marker."""
    S_rated = combined['S_rated']
    P_core  = nl['P_core']
    P_cu_fl = sc['P_cu']
    x_vals  = np.arange(0.05, 1.35, 0.02)

    def eff(x, pf):
        p_out = x * S_rated * pf
        p_cu  = x**2 * P_cu_fl
        denom = p_out + P_core + p_cu
        return (p_out / denom * 100) if denom > 0 else 0

    eff_upf = [eff(x, 1.0) for x in x_vals]
    eff_pf8 = [eff(x, 0.8) for x in x_vals]

    x_max  = combined['x_max_efficiency']
    eta_max = combined['max_efficiency']

    fig = go.Figure([
        go.Scatter(
            x=x_vals * 100, y=eff_upf,
            name='Unity PF', mode='lines',
            line=dict(color=NL_BLUE, width=2.5),
            fill='tozeroy', fillcolor='rgba(14,165,233,0.07)',
        ),
        go.Scatter(
            x=x_vals * 100, y=eff_pf8,
            name='0.8 PF Lagging', mode='lines',
            line=dict(color=SC_PINK, width=2.5),
            fill='tozeroy', fillcolor='rgba(232,121,249,0.07)',
        ),
        go.Scatter(
            x=[x_max * 100], y=[eta_max],
            name=f'η_max = {eta_max:.2f}%',
            mode='markers',
            marker=dict(color=EMERALD, size=13, symbol='star',
                        line=dict(color='white', width=1.5)),
            hovertemplate=f'Max η = {eta_max:.2f}%  @  {x_max*100:.1f}% load<extra></extra>',
        ),
    ])
    fig.update_layout(
        title_text='Efficiency Curves',
        **_layout(height=320),
        xaxis=_axis('Load (% of Rated)'),
        yaxis=_axis('Efficiency (%)', range=[0, 102]),
    )
    return fig


# ── Voltage Regulation ────────────────────────────────────────────────────────

def vr_chart(vr_data: List[Dict]) -> go.Figure:
    """Grouped bar: VR lagging vs leading for each PF."""
    labels = [str(v['pf']) for v in vr_data]
    fig = go.Figure([
        go.Bar(
            name='Lagging',
            x=labels, y=[v['vr_lagging'] for v in vr_data],
            marker_color=NL_BLUE, marker_opacity=0.85,
        ),
        go.Bar(
            name='Leading',
            x=labels, y=[v['vr_leading'] for v in vr_data],
            marker_color=SC_PINK, marker_opacity=0.85,
        ),
    ])
    fig.update_layout(
        title_text='Voltage Regulation vs Power Factor',
        barmode='group',
        **_layout(),
        xaxis=_axis('Power Factor'),
        yaxis=_axis('VR (%)'),
    )
    return fig


# ── Loss / Power ──────────────────────────────────────────────────────────────

def loss_donut(nl: Dict, sc: Dict) -> go.Figure:
    """Core loss vs copper loss donut."""
    fig = go.Figure(go.Pie(
        labels=['Core Loss (Pᵢ)', 'Copper Loss (Pcu)'],
        values=[nl['P_core'], sc['P_cu']],
        hole=0.58,
        marker_colors=[NL_BLUE, SC_PINK],
        textinfo='label+percent',
        hovertemplate='%{label}: %{value:.4f} W<extra></extra>',
    ))
    fig.update_layout(title_text='Loss Distribution', **_layout(showlegend=False))
    return fig


def nl_current_components(nl: Dict) -> go.Figure:
    """No-load current breakdown donut: Ic vs Im."""
    ic = nl.get('I_c') or 0
    im = nl.get('I_m') or 0
    io = nl.get('I_o') or 0
    fig = go.Figure(go.Pie(
        labels=['I_c (Core Loss)', 'I_m (Magnetizing)'],
        values=[ic, im],
        hole=0.55,
        marker_colors=[NL_BLUE, INDIGO],
        textinfo='label+percent',
        hovertemplate='%{label}: %{value:.6f} A<extra></extra>',
    ))
    fig.update_layout(
        title_text=f'No-Load Current Components  (I₀ = {io:.6f} A)',
        **_layout(showlegend=False),
    )
    return fig


def nl_power_breakdown(nl: Dict) -> go.Figure:
    """No-load active vs reactive power donut."""
    fig = go.Figure(go.Pie(
        labels=['Active Power (P_core)', 'Reactive Power (Q₀)'],
        values=[abs(nl.get('P_core') or 0), abs(nl.get('Q_o') or 0)],
        hole=0.55,
        marker_colors=[EMERALD, INDIGO],
        textinfo='label+percent',
        hovertemplate='%{label}: %{value:.4f}<extra></extra>',
    ))
    fig.update_layout(title_text='No-Load Power Breakdown', **_layout(showlegend=False))
    return fig


def sc_power_breakdown(sc: Dict) -> go.Figure:
    """Short-circuit active vs reactive power donut."""
    fig = go.Figure(go.Pie(
        labels=['Real Power (P_cu)', 'Reactive Power (Q_SC)'],
        values=[abs(sc.get('P_cu') or 0), abs(sc.get('Q_sc') or 0)],
        hole=0.55,
        marker_colors=[SC_PINK, INDIGO],
        textinfo='label+percent',
        hovertemplate='%{label}: %{value:.4f}<extra></extra>',
    ))
    fig.update_layout(title_text='SC Power Breakdown', **_layout(showlegend=False))
    return fig


def sc_power_bar(sc: Dict) -> go.Figure:
    """Horizontal bar: apparent, real, reactive power from SC test."""
    vals   = [sc.get('S_sc') or 0, sc.get('P_cu') or 0, sc.get('Q_sc') or 0]
    labels = ['Apparent S', 'Real P (Pcu)', 'Reactive Q']
    fig = go.Figure(go.Bar(
        y=labels, x=vals,
        orientation='h',
        marker_color=[INDIGO, NL_BLUE, SC_PINK],
        text=[f'{v:.4f}' for v in vals],
        textposition='outside',
    ))
    fig.update_layout(
        title_text='Power Triangle (SC Test)',
        **_layout(showlegend=False),
        xaxis=_axis('Power (VA / W / VAR)'),
        yaxis=dict(autorange='reversed'),
    )
    return fig


def impedance_chart(sc: Dict) -> go.Figure:
    """Bar chart of impedance components."""
    vals   = [sc.get('Z_eq') or 0, sc.get('R_eq') or 0, sc.get('X_eq') or 0]
    labels = ['Z_eq', 'R_eq', 'X_eq']
    fig = go.Figure(go.Bar(
        x=labels, y=vals,
        marker_color=[INDIGO, NL_BLUE, SC_PINK],
        text=[f'{v:.4f} Ω' for v in vals],
        textposition='outside',
    ))
    fig.update_layout(
        title_text='Impedance Components',
        **_layout(showlegend=False),
        yaxis=_axis('Impedance (Ω)'),
    )
    return fig


# ── Equivalent Circuit SVG ────────────────────────────────────────────────────

def circuit_svg(nl: Optional[Dict], sc: Optional[Dict]) -> str:
    """Return an SVG string of the approximate equivalent circuit."""

    def fv(d, k, digits=3):
        if d is None:
            return '?'
        v = d.get(k)
        if v is None:
            return '?'
        try:
            return f'{float(v):.{digits}f}'
        except (TypeError, ValueError):
            return '?'

    R1  = fv(sc, 'R1_approx', 3)
    X1  = fv(sc, 'X1_approx', 3)
    R2  = fv(sc, 'R2_approx', 3)
    X2  = fv(sc, 'X2_approx', 3)
    Rc  = fv(nl, 'R_c', 1)
    Xm  = fv(nl, 'X_m', 1)
    Zeq = fv(sc, 'Z_eq', 3)
    Req = fv(sc, 'R_eq', 3)
    Xeq = fv(sc, 'X_eq', 3)

    return f"""
<svg viewBox="0 0 860 350" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:820px;display:block;margin:auto;border-radius:12px;">
  <defs>
    <marker id="arrC" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="{NL_BLUE}"/>
    </marker>
  </defs>
  <rect width="860" height="350" fill="#f8fafc" rx="12"/>

  <!-- Title -->
  <text x="430" y="38" text-anchor="middle" fill="#0f172a"
        font-family="Inter,system-ui,sans-serif" font-size="14" font-weight="700">
    Approximate Equivalent Circuit — Referred to Primary
  </text>

  <!-- Top rail -->
  <line x1="40"  y1="90" x2="130" y2="90" stroke="{GRAY}" stroke-width="2"/>

  <!-- R1 -->
  <rect x="130" y="76" width="88" height="28" rx="4" fill="none"
        stroke="{NL_BLUE}" stroke-width="2"/>
  <text x="174" y="94" text-anchor="middle" fill="{NL_BLUE}"
        font-family="monospace" font-size="12" font-weight="600">R₁={R1}Ω</text>

  <!-- X1 -->
  <line x1="218" y1="90" x2="258" y2="90" stroke="{GRAY}" stroke-width="2"/>
  <rect x="258" y="76" width="88" height="28" rx="4" fill="none"
        stroke="{INDIGO}" stroke-width="2"/>
  <text x="302" y="94" text-anchor="middle" fill="{INDIGO}"
        font-family="monospace" font-size="12" font-weight="600">X₁={X1}Ω</text>

  <!-- to junction A -->
  <line x1="346" y1="90" x2="420" y2="90" stroke="{GRAY}" stroke-width="2"/>
  <circle cx="420" cy="90" r="4" fill="{GRAY}"/>

  <!-- Rc branch -->
  <line x1="420" y1="90"  x2="420" y2="128" stroke="{GRAY}" stroke-width="2"/>
  <rect x="393" y="128" width="54" height="68" rx="4" fill="none"
        stroke="{EMERALD}" stroke-width="2"/>
  <text x="420" y="158" text-anchor="middle" fill="{EMERALD}"
        font-family="monospace" font-size="11" font-weight="600">Rc</text>
  <text x="420" y="174" text-anchor="middle" fill="{EMERALD}"
        font-family="monospace" font-size="10">{Rc} Ω</text>
  <line x1="420" y1="196" x2="420" y2="272" stroke="{GRAY}" stroke-width="2"/>

  <!-- Xm branch -->
  <line x1="420" y1="90"  x2="520" y2="90" stroke="{GRAY}" stroke-width="2"/>
  <circle cx="520" cy="90" r="4" fill="{GRAY}"/>
  <line x1="520" y1="90"  x2="520" y2="128" stroke="{GRAY}" stroke-width="2"/>
  <rect x="493" y="128" width="54" height="68" rx="4" fill="none"
        stroke="{AMBER}" stroke-width="2"/>
  <text x="520" y="158" text-anchor="middle" fill="{AMBER}"
        font-family="monospace" font-size="11" font-weight="600">Xm</text>
  <text x="520" y="174" text-anchor="middle" fill="{AMBER}"
        font-family="monospace" font-size="10">{Xm} Ω</text>
  <line x1="520" y1="196" x2="520" y2="272" stroke="{GRAY}" stroke-width="2"/>

  <!-- Continue top rail -->
  <line x1="520" y1="90" x2="566" y2="90" stroke="{GRAY}" stroke-width="2"/>

  <!-- R2 -->
  <rect x="566" y="76" width="88" height="28" rx="4" fill="none"
        stroke="{NL_BLUE}" stroke-width="2"/>
  <text x="610" y="94" text-anchor="middle" fill="{NL_BLUE}"
        font-family="monospace" font-size="12" font-weight="600">R₂'={R2}Ω</text>

  <!-- X2 -->
  <line x1="654" y1="90" x2="686" y2="90" stroke="{GRAY}" stroke-width="2"/>
  <rect x="686" y="76" width="88" height="28" rx="4" fill="none"
        stroke="{INDIGO}" stroke-width="2"/>
  <text x="730" y="94" text-anchor="middle" fill="{INDIGO}"
        font-family="monospace" font-size="12" font-weight="600">X₂'={X2}Ω</text>
  <line x1="774" y1="90" x2="820" y2="90" stroke="{GRAY}" stroke-width="2"/>

  <!-- Bottom rail + verticals -->
  <line x1="40"  y1="272" x2="820" y2="272" stroke="{GRAY}" stroke-width="2"/>
  <line x1="40"  y1="90"  x2="40"  y2="272" stroke="{GRAY}" stroke-width="2"/>
  <line x1="820" y1="90"  x2="820" y2="272" stroke="{GRAY}" stroke-width="2"/>

  <!-- V1 / V2' labels -->
  <text x="20" y="185" text-anchor="middle" fill="{GRAY}"
        font-size="13" font-weight="600"
        transform="rotate(-90,20,185)">V₁</text>
  <text x="842" y="185" text-anchor="middle" fill="{GRAY}"
        font-size="13" font-weight="600"
        transform="rotate(90,842,185)">V₂'</text>

  <!-- Current arrows -->
  <line x1="58" y1="78" x2="100" y2="78" stroke="{NL_BLUE}"
        stroke-width="1.5" marker-end="url(#arrC)"/>
  <text x="79" y="73" text-anchor="middle" fill="{NL_BLUE}" font-size="11">I₁</text>
  <line x1="783" y1="78" x2="807" y2="78" stroke="{NL_BLUE}"
        stroke-width="1.5" marker-end="url(#arrC)"/>
  <text x="795" y="73" text-anchor="middle" fill="{NL_BLUE}" font-size="11">I₂'</text>

  <!-- Branch current labels -->
  <text x="408" y="118" text-anchor="end" fill="{EMERALD}" font-size="10">Ic ↓</text>
  <text x="534" y="118" text-anchor="start" fill="{AMBER}"  font-size="10">Im ↓</text>

  <!-- Summary strip -->
  <rect x="210" y="298" width="440" height="32" rx="6"
        fill="rgba(14,165,233,0.07)" stroke="rgba(14,165,233,0.22)" stroke-width="1"/>
  <text x="430" y="318" text-anchor="middle" fill="{NL_BLUE}"
        font-family="monospace" font-size="12" font-weight="600">
    Zeq = {Zeq} Ω  ·  Req = {Req} Ω  ·  Xeq = {Xeq} Ω
  </text>
</svg>"""
