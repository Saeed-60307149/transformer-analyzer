"""
Premium HTML Report Generator for TransformerIQ
Self-contained, null-safe, zero-dependency exported report.
"""
from datetime import datetime


# ── Null-safe formatting ──────────────────────────────────────────────────────

def _f(value, digits=4, suffix=''):
    """Format a value safely; return em-dash for None/NaN."""
    if value is None:
        return '—'
    try:
        v = float(value)
        import math
        if math.isnan(v) or math.isinf(v):
            return '—'
        return f'{v:.{digits}f}{suffix}'
    except (TypeError, ValueError):
        return '—'


# ── Inline SVG helpers ────────────────────────────────────────────────────────

def _svg_bar(data_points, width=520, height=220, color='#38bdf8', bg='#0d1a32'):
    """Premium dark-theme bar chart as inline SVG."""
    if not data_points:
        return ''
    labels = [str(d['label']) for d in data_points]
    values = [float(d['value']) if d['value'] is not None else 0.0 for d in data_points]
    max_val = max(values) if any(v > 0 for v in values) else 1.0
    pad_l, pad_b, pad_t, pad_r = 50, 40, 20, 20
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    bar_gap = 12
    bar_w = max(10, (chart_w - bar_gap * (len(values) + 1)) // len(values))

    parts = [
        f'<rect width="{width}" height="{height}" rx="10" fill="{bg}"/>',
        # Y-axis line
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+chart_h}" '
        f'stroke="rgba(255,255,255,0.1)" stroke-width="1"/>',
        # X-axis line
        f'<line x1="{pad_l}" y1="{pad_t+chart_h}" x2="{width-pad_r}" y2="{pad_t+chart_h}" '
        f'stroke="rgba(255,255,255,0.1)" stroke-width="1"/>',
    ]

    # Grid lines
    for step in [0.25, 0.5, 0.75, 1.0]:
        gy = pad_t + chart_h - int(step * chart_h)
        gv = max_val * step
        parts.append(
            f'<line x1="{pad_l}" y1="{gy}" x2="{width-pad_r}" y2="{gy}" '
            f'stroke="rgba(255,255,255,0.05)" stroke-width="1" stroke-dasharray="4 4"/>'
            f'<text x="{pad_l-6}" y="{gy+4}" text-anchor="end" '
            f'fill="rgba(255,255,255,0.35)" font-size="10" font-family="IBM Plex Mono,monospace">'
            f'{gv:.1f}</text>'
        )

    for i, (lbl, val) in enumerate(zip(labels, values)):
        bh = int((val / max_val) * chart_h)
        bh = max(bh, 2)
        x = pad_l + bar_gap + i * (bar_w + bar_gap)
        y = pad_t + chart_h - bh

        # Bar with gradient effect
        gid = f'bg{i}'
        parts.append(
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="1"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0.4"/>'
            f'</linearGradient></defs>'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" rx="4" fill="url(#{gid})"/>'
        )
        # Value label above bar
        parts.append(
            f'<text x="{x + bar_w/2:.0f}" y="{y-5}" text-anchor="middle" '
            f'fill="{color}" font-size="10" font-weight="600" font-family="IBM Plex Mono,monospace">'
            f'{val:.2f}</text>'
        )
        # X label
        parts.append(
            f'<text x="{x + bar_w/2:.0f}" y="{pad_t+chart_h+18}" text-anchor="middle" '
            f'fill="rgba(255,255,255,0.5)" font-size="10" font-family="DM Sans,sans-serif">'
            f'{lbl}</text>'
        )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;margin:16px auto;border-radius:10px;">'
        + ''.join(parts) + '</svg>'
    )


def _svg_donut(slices, width=260, height=260, bg='#0d1a32'):
    """Premium donut chart as inline SVG."""
    if not slices or sum(s['value'] for s in slices if s['value']) == 0:
        return ''
    total = sum(float(s['value']) for s in slices if s['value'])
    colors = ['#38bdf8', '#f472b6', '#818cf8', '#34d399', '#fbbf24']
    cx, cy, r, r_inner = width // 2, height // 2, 90, 54

    parts = [f'<rect width="{width}" height="{height}" rx="10" fill="{bg}"/>']
    angle = -90.0

    for i, s in enumerate(slices):
        val = float(s['value']) if s['value'] else 0
        frac = val / total
        sweep = frac * 360
        color = colors[i % len(colors)]

        start_rad = angle * 3.14159265 / 180
        end_rad = (angle + sweep) * 3.14159265 / 180

        x1 = cx + r * __import__('math').cos(start_rad)
        y1 = cy + r * __import__('math').sin(start_rad)
        x2 = cx + r * __import__('math').cos(end_rad)
        y2 = cy + r * __import__('math').sin(end_rad)
        ix1 = cx + r_inner * __import__('math').cos(start_rad)
        iy1 = cy + r_inner * __import__('math').sin(start_rad)
        ix2 = cx + r_inner * __import__('math').cos(end_rad)
        iy2 = cy + r_inner * __import__('math').sin(end_rad)

        large = 1 if sweep > 180 else 0
        parts.append(
            f'<path d="M {x1:.2f} {y1:.2f} A {r} {r} 0 {large} 1 {x2:.2f} {y2:.2f} '
            f'L {ix2:.2f} {iy2:.2f} A {r_inner} {r_inner} 0 {large} 0 {ix1:.2f} {iy1:.2f} Z" '
            f'fill="{color}" opacity="0.9"/>'
        )
        angle += sweep

    # Center text
    parts.append(
        f'<text x="{cx}" y="{cy-6}" text-anchor="middle" fill="white" '
        f'font-size="13" font-weight="700" font-family="DM Sans,sans-serif">Loss</text>'
        f'<text x="{cx}" y="{cy+12}" text-anchor="middle" fill="rgba(255,255,255,0.5)" '
        f'font-size="11" font-family="DM Sans,sans-serif">Split</text>'
    )

    # Legend
    legend_y = height - 10 - len(slices) * 18
    for i, s in enumerate(slices):
        color = colors[i % len(colors)]
        val = float(s['value']) if s['value'] else 0
        pct = val / total * 100
        ly = legend_y + i * 18
        parts.append(
            f'<rect x="10" y="{ly}" width="10" height="10" rx="2" fill="{color}"/>'
            f'<text x="26" y="{ly+9}" fill="rgba(255,255,255,0.7)" '
            f'font-size="10" font-family="DM Sans,sans-serif">'
            f'{s["label"]}: {pct:.1f}%</text>'
        )

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:inline-block;border-radius:10px;">'
        + ''.join(parts) + '</svg>'
    )


def _svg_circuit(nl, sc):
    """Premium inline SVG equivalent circuit diagram."""
    R1  = _f(sc.get('R1_approx'), 2) if sc else '?'
    X1  = _f(sc.get('X1_approx'), 2) if sc else '?'
    R2  = _f(sc.get('R2_approx'), 2) if sc else '?'
    X2  = _f(sc.get('X2_approx'), 2) if sc else '?'
    Rc  = _f(nl.get('R_c'),  1) if nl else '?'
    Xm  = _f(nl.get('X_m'),  1) if nl else '?'
    Zeq = _f(sc.get('Z_eq'), 2) if sc else '?'
    Req = _f(sc.get('R_eq'), 2) if sc else '?'
    Xeq = _f(sc.get('X_eq'), 2) if sc else '?'

    return f'''<svg viewBox="0 0 820 350" xmlns="http://www.w3.org/2000/svg"
  style="width:100%;max-width:800px;display:block;margin:16px auto;">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#38bdf8"/>
    </marker>
    <filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <!-- Background -->
  <rect width="820" height="350" rx="12" fill="#0a1628"/>
  <!-- Main conductors -->
  <line x1="40" y1="90" x2="120" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- R1 -->
  <rect x="120" y="76" width="72" height="28" rx="4" fill="none" stroke="#38bdf8" stroke-width="2" filter="url(#glow)"/>
  <text x="156" y="93" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono,monospace" font-size="11" font-weight="600">R₁={R1}Ω</text>
  <line x1="192" y1="90" x2="232" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- X1 -->
  <rect x="232" y="76" width="72" height="28" rx="4" fill="none" stroke="#818cf8" stroke-width="2" filter="url(#glow)"/>
  <text x="268" y="93" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono,monospace" font-size="11" font-weight="600">X₁={X1}Ω</text>
  <line x1="304" y1="90" x2="370" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- Node dot -->
  <circle cx="370" cy="90" r="4" fill="#38bdf8" filter="url(#glow)"/>
  <!-- Shunt branch Rc -->
  <line x1="370" y1="90" x2="370" y2="128" stroke="#4a5a7a" stroke-width="2"/>
  <rect x="342" y="128" width="56" height="68" rx="4" fill="none" stroke="#34d399" stroke-width="2" filter="url(#glow)"/>
  <text x="370" y="158" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono,monospace" font-size="10" font-weight="600">Rc</text>
  <text x="370" y="174" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono,monospace" font-size="9">{Rc}Ω</text>
  <line x1="370" y1="196" x2="370" y2="275" stroke="#4a5a7a" stroke-width="2"/>
  <!-- Shunt branch Xm -->
  <line x1="370" y1="90" x2="470" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <circle cx="470" cy="90" r="4" fill="#38bdf8" filter="url(#glow)"/>
  <line x1="470" y1="90" x2="470" y2="128" stroke="#4a5a7a" stroke-width="2"/>
  <rect x="442" y="128" width="56" height="68" rx="4" fill="none" stroke="#fbbf24" stroke-width="2" filter="url(#glow)"/>
  <text x="470" y="158" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono,monospace" font-size="10" font-weight="600">Xm</text>
  <text x="470" y="174" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono,monospace" font-size="9">{Xm}Ω</text>
  <line x1="470" y1="196" x2="470" y2="275" stroke="#4a5a7a" stroke-width="2"/>
  <!-- Connect nodes -->
  <line x1="470" y1="90" x2="510" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- R2 -->
  <rect x="510" y="76" width="72" height="28" rx="4" fill="none" stroke="#38bdf8" stroke-width="2" filter="url(#glow)"/>
  <text x="546" y="93" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono,monospace" font-size="11" font-weight="600">R₂'={R2}Ω</text>
  <line x1="582" y1="90" x2="610" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- X2 -->
  <rect x="610" y="76" width="72" height="28" rx="4" fill="none" stroke="#818cf8" stroke-width="2" filter="url(#glow)"/>
  <text x="646" y="93" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono,monospace" font-size="11" font-weight="600">X₂'={X2}Ω</text>
  <line x1="682" y1="90" x2="780" y2="90" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- Return conductor -->
  <line x1="40" y1="275" x2="780" y2="275" stroke="#4a5a7a" stroke-width="2.5"/>
  <line x1="40" y1="90" x2="40" y2="275" stroke="#4a5a7a" stroke-width="2.5"/>
  <line x1="780" y1="90" x2="780" y2="275" stroke="#4a5a7a" stroke-width="2.5"/>
  <!-- Labels -->
  <text x="22" y="185" text-anchor="middle" fill="#8ba3c7" font-size="12" font-weight="600"
    transform="rotate(-90,22,185)">V₁</text>
  <text x="798" y="185" text-anchor="middle" fill="#8ba3c7" font-size="12" font-weight="600"
    transform="rotate(90,798,185)">V₂'</text>
  <!-- Current arrows -->
  <line x1="55" y1="78" x2="90" y2="78" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arr)"/>
  <text x="72" y="72" text-anchor="middle" fill="#38bdf8" font-size="10">I₁</text>
  <line x1="720" y1="78" x2="755" y2="78" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arr)"/>
  <text x="737" y="72" text-anchor="middle" fill="#38bdf8" font-size="10">I₂'</text>
  <!-- Ic Im labels -->
  <text x="362" y="115" text-anchor="end" fill="#34d399" font-size="10">Ic↓</text>
  <text x="482" y="115" text-anchor="start" fill="#fbbf24" font-size="10">Im↓</text>
  <!-- Summary bar -->
  <rect x="200" y="305" width="420" height="30" rx="6" fill="rgba(56,189,248,0.08)" stroke="rgba(56,189,248,0.2)" stroke-width="1"/>
  <text x="410" y="325" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono,monospace" font-size="11">
    Zeq = {Zeq}Ω  |  Req = {Req}Ω  |  Xeq = {Xeq}Ω
  </text>
</svg>'''


# ── Main report generator ─────────────────────────────────────────────────────

def generate_report_html(nl_results, sc_results, combined, nl_harmonics, sc_harmonics):
    """Generate a premium, self-contained HTML report. All values null-safe."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nl = nl_results or {}
    sc = sc_results or {}
    cb = combined or {}

    # ── CSS ──────────────────────────────────────────────────────────────────
    css = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600;700&family=Instrument+Serif&display=swap');
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#040c1a;--bg2:#08142a;--card:rgba(13,26,50,0.95);
  --border:rgba(56,189,248,0.15);--border2:rgba(56,189,248,0.35);
  --cyan:#38bdf8;--purple:#818cf8;--pink:#f472b6;
  --green:#34d399;--amber:#fbbf24;--text:#e2eeff;--muted:#6a88b0;
}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);
  min-height:100vh;line-height:1.7;-webkit-font-smoothing:antialiased;padding:0}

/* ── Cover / Header ── */
.cover{
  background:linear-gradient(135deg,#010a1a 0%,#061428 40%,#0a1e38 100%);
  padding:64px 48px 56px;text-align:center;position:relative;overflow:hidden;
  border-bottom:1px solid rgba(56,189,248,0.2);
}
.cover::before{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(56,189,248,0.15),transparent),
             radial-gradient(ellipse 50% 40% at 80% 100%,rgba(129,140,248,0.1),transparent);
}
.cover-logo{
  display:inline-flex;align-items:center;gap:16px;margin-bottom:32px;
  background:rgba(56,189,248,0.06);border:1px solid rgba(56,189,248,0.2);
  padding:12px 24px;border-radius:50px;
}
.cover-icon{width:36px;height:36px;color:#38bdf8}
.cover-brand{font-family:'Instrument Serif',Georgia,serif;font-size:22px;
  background:linear-gradient(135deg,#e2eeff,#38bdf8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.cover h1{font-family:'Instrument Serif',Georgia,serif;font-size:48px;font-weight:400;
  line-height:1.1;margin-bottom:12px;
  background:linear-gradient(135deg,#fff 0%,#38bdf8 60%,#818cf8 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.cover-sub{font-size:16px;color:var(--muted);letter-spacing:0.5px}
.cover-meta{
  display:inline-flex;gap:32px;margin-top:32px;
  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
  padding:16px 32px;border-radius:12px;
}
.meta-item{text-align:center}
.meta-label{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:4px}
.meta-value{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--cyan)}

/* ── Content ── */
.content{max-width:960px;margin:0 auto;padding:48px 40px}

/* ── Section ── */
.section{margin-bottom:48px;page-break-inside:avoid}
.section-title{
  display:flex;align-items:center;gap:12px;margin-bottom:24px;
  padding-bottom:12px;border-bottom:1px solid var(--border);
}
.section-title .num{
  width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:700;font-family:'IBM Plex Mono',monospace;flex-shrink:0;
}
.num-cyan{background:rgba(56,189,248,0.15);color:var(--cyan);border:1px solid rgba(56,189,248,0.3)}
.num-pink{background:rgba(244,114,182,0.15);color:var(--pink);border:1px solid rgba(244,114,182,0.3)}
.num-purple{background:rgba(129,140,248,0.15);color:var(--purple);border:1px solid rgba(129,140,248,0.3)}
.num-green{background:rgba(52,211,153,0.15);color:var(--green);border:1px solid rgba(52,211,153,0.3)}
.num-amber{background:rgba(251,191,36,0.15);color:var(--amber);border:1px solid rgba(251,191,36,0.3)}
.section-title h2{font-size:22px;font-weight:600;letter-spacing:-0.3px}

/* ── KPI Row ── */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:28px}
.kpi{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:18px 16px;text-align:center;position:relative;overflow:hidden;
}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.kpi-cyan::before{background:linear-gradient(90deg,var(--cyan),var(--purple))}
.kpi-pink::before{background:linear-gradient(90deg,var(--pink),var(--purple))}
.kpi-green::before{background:var(--green)}
.kpi-amber::before{background:var(--amber)}
.kpi-label{font-size:10px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin-bottom:8px}
.kpi-val{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600}
.kpi-cyan .kpi-val{color:var(--cyan)}
.kpi-pink .kpi-val{color:var(--pink)}
.kpi-green .kpi-val{color:var(--green)}
.kpi-amber .kpi-val{color:var(--amber)}
.kpi-unit{font-size:12px;color:var(--muted);margin-top:2px}

/* ── Table ── */
.tbl-wrap{
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  overflow:hidden;margin-bottom:24px;
}
table{width:100%;border-collapse:collapse}
thead th{
  background:rgba(56,189,248,0.08);padding:11px 16px;text-align:left;
  font-size:10px;text-transform:uppercase;letter-spacing:1px;
  color:var(--muted);font-weight:600;border-bottom:1px solid var(--border);
}
tbody td{
  padding:10px 16px;font-size:13px;border-bottom:1px solid rgba(56,189,248,0.06);
}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even) td{background:rgba(56,189,248,0.025)}
.td-sym{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--muted)}
.td-val{font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:600;color:var(--cyan);text-align:right}
.td-val-pink{color:var(--pink)}
.td-val-green{color:var(--green)}
.td-unit{font-size:12px;color:var(--muted);text-align:center}
.sub-h{font-size:15px;font-weight:600;margin:24px 0 12px;color:var(--text)}

/* ── Chart section ── */
.charts-row{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:24px 0}
.chart-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;text-align:center}
.chart-box h4{font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px}

/* ── Circuit ── */
.circuit-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px;margin:24px 0;text-align:center}
.circuit-box h4{font-size:13px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:16px}

/* ── Nameplate ── */
.nameplate{
  background:linear-gradient(135deg,#1a2236,#0f1729);
  border:2px solid var(--amber);border-radius:14px;
  padding:28px 36px;margin:24px 0;position:relative;overflow:hidden;
}
.nameplate::before{
  content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(45deg,transparent,transparent 10px,
    rgba(251,191,36,0.02) 10px,rgba(251,191,36,0.02) 11px);
}
.np-title{font-size:11px;letter-spacing:3px;color:var(--amber);text-transform:uppercase;text-align:center;margin-bottom:8px}
.np-kva{font-family:'Instrument Serif',Georgia,serif;font-size:36px;text-align:center;color:#fff;margin-bottom:4px}
.np-computed{font-size:11px;color:var(--muted);text-align:center;margin-bottom:20px}
.np-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.np-cell{text-align:center}
.np-cell-label{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#475569}
.np-cell-val{font-family:'IBM Plex Mono',monospace;font-size:15px;color:var(--amber);font-weight:600;margin-top:2px}
.np-footer{text-align:center;margin-top:18px;padding-top:12px;border-top:1px solid rgba(251,191,36,0.2);
  font-size:10px;color:#475569;letter-spacing:1px;text-transform:uppercase}

/* ── Harmonic ── */
.thd-row{display:flex;gap:20px;margin-bottom:16px;flex-wrap:wrap}
.thd-badge{
  display:flex;flex-direction:column;align-items:center;
  background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 24px;
}
.thd-val{font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600;color:var(--cyan)}
.thd-label{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Footer ── */
.report-footer{
  background:var(--bg2);border-top:1px solid var(--border);
  padding:28px 40px;display:flex;justify-content:space-between;align-items:center;
  font-size:12px;color:var(--muted);
}

/* ── Print ── */
@media print{
  body{background:#fff!important;color:#000!important}
  .cover{background:#f0f4f8!important;border-color:#ccc!important}
  .cover h1,.cover-brand{-webkit-text-fill-color:#0f3460!important}
  .kpi,.tbl-wrap,.circuit-box,.nameplate,.chart-box{background:#fff!important;border-color:#ddd!important}
  td,th{color:#000!important}
  .td-val,.kpi-val,.np-cell-val{color:#0f3460!important}
}
"""

    # ── Compute summary values ───────────────────────────────────────────────
    has_nl = bool(nl)
    has_sc = bool(sc)
    has_cb = bool(cb)

    V_oc    = nl.get('V_oc')
    I_o     = nl.get('I_o')
    P_core  = nl.get('P_core')
    PF_nl   = nl.get('PF_nl')
    V_sc    = sc.get('V_sc')
    I_sc    = sc.get('I_sc')
    P_cu    = sc.get('P_cu')
    PF_sc   = sc.get('PF_sc')
    S_rated = cb.get('S_rated')
    max_eff = cb.get('max_efficiency')
    Z_pct   = cb.get('Z_percent')

    # Nameplate snap
    sRaw = float(S_rated) if S_rated else 0
    stdKVA = [0.05, 0.1, 0.15, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 25, 50, 75, 100]
    kvaRaw = sRaw / 1000
    snapKVA = min(stdKVA, key=lambda x: abs(x - kvaRaw)) if sRaw > 0 else '—'

    freq = nl.get('frequency_Hz') or sc.get('frequency_Hz') or 50

    # ── Nameplate HTML ───────────────────────────────────────────────────────
    np_html = ''
    if has_nl or has_sc:
        np_html = f'''
<div class="nameplate">
  <div class="np-title">Estimated Nameplate</div>
  <div class="np-kva">{snapKVA} kVA</div>
  <div class="np-computed">Computed: {_f(sRaw/1000, 4)} kVA &nbsp;|&nbsp; {_f(S_rated, 2)} VA</div>
  <div class="np-grid">
    <div class="np-cell"><div class="np-cell-label">Primary V</div><div class="np-cell-val">{_f(V_oc, 1)} V</div></div>
    <div class="np-cell"><div class="np-cell-label">Frequency</div><div class="np-cell-val">{_f(freq, 0)} Hz</div></div>
    <div class="np-cell"><div class="np-cell-label">Rated I</div><div class="np-cell-val">{_f((float(I_sc)*1000) if I_sc else None, 1)} mA</div></div>
    <div class="np-cell"><div class="np-cell-label">%Z</div><div class="np-cell-val">{_f(Z_pct, 2)}%</div></div>
    <div class="np-cell"><div class="np-cell-label">Max η</div><div class="np-cell-val">{_f(max_eff, 1)}%</div></div>
    <div class="np-cell"><div class="np-cell-label">Temp Rise</div><div class="np-cell-val">~40°C</div></div>
  </div>
  <div class="np-footer">Estimated From Test Data · TransformerIQ Analyzer</div>
</div>'''

    # ── No-Load Table ────────────────────────────────────────────────────────
    nl_table = ''
    if has_nl:
        nl_rows = [
            ('Open-Circuit Voltage', 'V<sub>OC</sub>', _f(nl.get('V_oc'), 4), 'V', 'cyan'),
            ('No-Load Current', 'I<sub>0</sub>', _f(nl.get('I_o'), 6), 'A', 'cyan'),
            ('Core Loss (P<sub>core</sub>)', 'P<sub>core</sub>', _f(nl.get('P_core'), 4), 'W', 'green'),
            ('No-Load Power Factor', 'cos φ₀', _f(nl.get('PF_nl'), 6), '—', 'cyan'),
            ('No-Load Angle', 'φ₀', _f(nl.get('theta_nl_deg'), 2) + '°', 'deg', 'cyan'),
            ('Core Loss Current', 'I<sub>c</sub>', _f(nl.get('I_c'), 6), 'A', 'cyan'),
            ('Magnetizing Current', 'I<sub>m</sub>', _f(nl.get('I_m'), 6), 'A', 'purple'),
            ('Core Loss Resistance', 'R<sub>c</sub>', _f(nl.get('R_c'), 2), 'Ω', 'cyan'),
            ('Magnetizing Reactance', 'X<sub>m</sub>', _f(nl.get('X_m'), 2), 'Ω', 'purple'),
            ('Apparent Power', 'S₀', _f(nl.get('S_o'), 4), 'VA', 'cyan'),
            ('Reactive Power', 'Q₀', _f(nl.get('Q_o'), 4), 'VAR', 'purple'),
            ('Frequency', 'f', _f(nl.get('frequency_Hz'), 1), 'Hz', 'cyan'),
        ]
        rows_html = ''.join(
            f'<tr><td>{n}</td><td class="td-sym">{s}</td>'
            f'<td class="td-val td-val-{"pink" if c=="pink" else "green" if c=="green" else "cyan" if c=="cyan" else ""}">{v}</td>'
            f'<td class="td-unit">{u}</td></tr>'
            for n, s, v, u, c in nl_rows
        )
        nl_table = f'''<div class="tbl-wrap"><table>
<thead><tr><th>Parameter</th><th>Symbol</th><th style="text-align:right">Value</th><th style="text-align:center">Unit</th></tr></thead>
<tbody>{rows_html}</tbody></table></div>'''

    # ── SC Table ─────────────────────────────────────────────────────────────
    sc_table = ''
    if has_sc:
        sc_rows = [
            ('Short-Circuit Voltage', 'V<sub>SC</sub>', _f(sc.get('V_sc'), 4), 'V', 'pink'),
            ('Short-Circuit Current', 'I<sub>SC</sub>', _f(sc.get('I_sc'), 6), 'A', 'pink'),
            ('Copper Loss', 'P<sub>cu</sub>', _f(sc.get('P_cu'), 4), 'W', 'pink'),
            ('Short-Circuit Power Factor', 'cos φ<sub>SC</sub>', _f(sc.get('PF_sc'), 6), '—', 'pink'),
            ('SC Angle', 'φ<sub>SC</sub>', _f(sc.get('theta_sc_deg'), 2) + '°', 'deg', 'pink'),
            ('Equivalent Impedance', 'Z<sub>eq</sub>', _f(sc.get('Z_eq'), 4), 'Ω', 'pink'),
            ('Equivalent Resistance', 'R<sub>eq</sub>', _f(sc.get('R_eq'), 4), 'Ω', 'pink'),
            ('Equivalent Reactance', 'X<sub>eq</sub>', _f(sc.get('X_eq'), 4), 'Ω', 'purple'),
            ('R₁ (approx)', 'R₁', _f(sc.get('R1_approx'), 4), 'Ω', 'cyan'),
            ('X₁ (approx)', 'X₁', _f(sc.get('X1_approx'), 4), 'Ω', 'purple'),
            ('Apparent Power', 'S<sub>SC</sub>', _f(sc.get('S_sc'), 4), 'VA', 'pink'),
            ('Frequency', 'f', _f(sc.get('frequency_Hz'), 1), 'Hz', 'cyan'),
        ]
        rows_html = ''.join(
            f'<tr><td>{n}</td><td class="td-sym">{s}</td>'
            f'<td class="td-val td-val-{"pink" if c=="pink" else "green" if c=="green" else ""}">{v}</td>'
            f'<td class="td-unit">{u}</td></tr>'
            for n, s, v, u, c in sc_rows
        )
        sc_table = f'''<div class="tbl-wrap"><table>
<thead><tr><th>Parameter</th><th>Symbol</th><th style="text-align:right">Value</th><th style="text-align:center">Unit</th></tr></thead>
<tbody>{rows_html}</tbody></table></div>'''

    # ── Combined ─────────────────────────────────────────────────────────────
    cb_html = ''
    vr_table = ''
    eff_table = ''
    eff_chart = ''
    if has_cb:
        x_max = cb.get('x_max_efficiency')
        x_max_pct = _f(float(x_max) * 100 if x_max is not None else None, 1)
        cb_rows = [
            ('Rated Apparent Power', _f(cb.get('S_rated'), 2), 'VA'),
            ('Total Full-Load Losses', _f(cb.get('total_loss_fl'), 4), 'W'),
            ('Load at Max Efficiency', x_max_pct + '%', 'of rated'),
            ('Maximum Efficiency (UPF)', _f(cb.get('max_efficiency'), 2) + '%', '—'),
            ('Percent Impedance (%Z)', _f(cb.get('Z_percent'), 2) + '%', '—'),
            ('Percent Resistance (%R)', _f(cb.get('R_percent'), 2) + '%', '—'),
        ]
        cb_rows_html = ''.join(
            f'<tr><td>{n}</td><td class="td-val">{v}</td><td class="td-unit">{u}</td></tr>'
            for n, v, u in cb_rows
        )
        cb_html = f'''<div class="tbl-wrap"><table>
<thead><tr><th>Parameter</th><th style="text-align:right">Value</th><th>Unit</th></tr></thead>
<tbody>{cb_rows_html}</tbody></table></div>'''

        # VR table
        vr_data = cb.get('voltage_regulation', [])
        if vr_data:
            vr_rows = ''.join(
                f'<tr><td>{vr.get("pf","—")}</td>'
                f'<td class="td-val">{_f(vr.get("vr_lagging"), 4)}%</td>'
                f'<td class="td-val td-val-pink">{_f(vr.get("vr_leading"), 4)}%</td></tr>'
                for vr in vr_data
            )
            vr_table = f'''<div class="sub-h">Voltage Regulation</div>
<div class="tbl-wrap"><table>
<thead><tr><th>Power Factor</th><th style="text-align:right">VR Lagging</th><th style="text-align:right">VR Leading</th></tr></thead>
<tbody>{vr_rows}</tbody></table></div>'''

        # Efficiency table
        eff_data = cb.get('efficiency_data', [])
        if eff_data:
            eff_rows = ''.join(
                f'<tr><td>{_f(e.get("load_fraction",0)*100, 0)}%</td>'
                f'<td>{e.get("pf","—")}</td>'
                f'<td class="td-val">{_f(e.get("P_out"), 2)}</td>'
                f'<td>{_f(e.get("P_cu"), 4)}</td>'
                f'<td>{_f(e.get("P_core"), 4)}</td>'
                f'<td class="td-val td-val-green">{_f(e.get("efficiency"), 2)}%</td></tr>'
                for e in eff_data
            )
            eff_table = f'''<div class="sub-h">Efficiency at Various Loads</div>
<div class="tbl-wrap"><table>
<thead><tr><th>Load</th><th>PF</th><th style="text-align:right">P_out (W)</th>
<th>Cu Loss (W)</th><th>Core Loss (W)</th><th style="text-align:right">η (%)</th></tr></thead>
<tbody>{eff_rows}</tbody></table></div>'''

            # Efficiency SVG chart
            upf_pts = [{'label': f'{int(e["load_fraction"]*100)}%', 'value': e['efficiency']}
                       for e in eff_data if e.get('pf') == 1.0]
            eff_chart = _svg_bar(upf_pts, width=520, height=200, color='#38bdf8')

    # ── Loss charts ──────────────────────────────────────────────────────────
    loss_html = ''
    if has_nl and has_sc and P_core is not None and P_cu is not None:
        p_c = float(P_core)
        p_cu_v = float(P_cu)
        total = p_c + p_cu_v
        if total > 0:
            loss_html = f'''
<div class="charts-row">
  <div class="chart-box">
    <h4>Loss Distribution</h4>
    {_svg_donut([{'label':'Core Loss','value':p_c},{'label':'Copper Loss','value':p_cu_v}])}
    <div style="font-size:12px;color:var(--muted);margin-top:8px;">
      Core: <b style="color:#38bdf8">{p_c:.4f} W ({p_c/total*100:.1f}%)</b>
      &nbsp;|&nbsp; Copper: <b style="color:#f472b6">{p_cu_v:.4f} W ({p_cu_v/total*100:.1f}%)</b>
    </div>
  </div>
  <div class="chart-box">
    <h4>Loss Comparison</h4>
    {_svg_bar([{'label':'Core Loss','value':p_c},{'label':'Copper Loss','value':p_cu_v}],
              width=240,height=200,color='#38bdf8')}
  </div>
</div>'''

    # ── Harmonic HTML ────────────────────────────────────────────────────────
    harm_html = ''
    if nl_harmonics:
        h = nl_harmonics
        harm_html += f'''
<div class="section">
  <div class="section-title"><div class="num num-amber">H</div><h2>Harmonic Analysis — No-Load</h2></div>
  <div class="thd-row">
    <div class="thd-badge"><div class="thd-val">{_f(h.get("thd_voltage"), 2)}%</div><div class="thd-label">THD Voltage</div></div>
    <div class="thd-badge"><div class="thd-val" style="color:var(--pink)">{_f(h.get("thd_current"), 2)}%</div><div class="thd-label">THD Current</div></div>
    <div class="thd-badge"><div class="thd-val" style="color:var(--green)">{_f(h.get("fundamental_frequency"), 1)} Hz</div><div class="thd-label">Fundamental</div></div>
  </div>
</div>'''
    if sc_harmonics:
        h = sc_harmonics
        harm_html += f'''
<div class="section">
  <div class="section-title"><div class="num num-amber">H</div><h2>Harmonic Analysis — Short-Circuit</h2></div>
  <div class="thd-row">
    <div class="thd-badge"><div class="thd-val">{_f(h.get("thd_voltage"), 2)}%</div><div class="thd-label">THD Voltage</div></div>
    <div class="thd-badge"><div class="thd-val" style="color:var(--pink)">{_f(h.get("thd_current"), 2)}%</div><div class="thd-label">THD Current</div></div>
    <div class="thd-badge"><div class="thd-val" style="color:var(--green)">{_f(h.get("fundamental_frequency"), 1)} Hz</div><div class="thd-label">Fundamental</div></div>
  </div>
</div>'''

    # ── NL KPI row ───────────────────────────────────────────────────────────
    nl_kpis = ''
    if has_nl:
        nl_kpis = f'''<div class="kpi-row">
  <div class="kpi kpi-cyan"><div class="kpi-label">V_OC</div><div class="kpi-val">{_f(V_oc, 2)}</div><div class="kpi-unit">V</div></div>
  <div class="kpi kpi-green"><div class="kpi-label">P_core</div><div class="kpi-val">{_f(P_core, 4)}</div><div class="kpi-unit">W</div></div>
  <div class="kpi kpi-cyan"><div class="kpi-label">I₀</div><div class="kpi-val">{_f(float(I_o)*1000 if I_o else None, 2)}</div><div class="kpi-unit">mA</div></div>
  <div class="kpi kpi-cyan"><div class="kpi-label">PF_NL</div><div class="kpi-val">{_f(PF_nl, 4)}</div><div class="kpi-unit">—</div></div>
</div>'''

    sc_kpis = ''
    if has_sc:
        sc_kpis = f'''<div class="kpi-row">
  <div class="kpi kpi-pink"><div class="kpi-label">V_SC</div><div class="kpi-val">{_f(V_sc, 4)}</div><div class="kpi-unit">V</div></div>
  <div class="kpi kpi-pink"><div class="kpi-label">P_cu</div><div class="kpi-val">{_f(P_cu, 4)}</div><div class="kpi-unit">W</div></div>
  <div class="kpi kpi-pink"><div class="kpi-label">I_SC</div><div class="kpi-val">{_f(float(I_sc)*1000 if I_sc else None, 1)}</div><div class="kpi-unit">mA</div></div>
  <div class="kpi kpi-pink"><div class="kpi-label">PF_SC</div><div class="kpi-val">{_f(PF_sc, 4)}</div><div class="kpi-unit">—</div></div>
</div>'''

    cb_kpis = ''
    if has_cb:
        cb_kpis = f'''<div class="kpi-row">
  <div class="kpi kpi-green"><div class="kpi-label">Rated VA</div><div class="kpi-val">{_f(S_rated, 1)}</div><div class="kpi-unit">VA</div></div>
  <div class="kpi kpi-green"><div class="kpi-label">Max Efficiency</div><div class="kpi-val">{_f(max_eff, 2)}</div><div class="kpi-unit">%</div></div>
  <div class="kpi kpi-amber"><div class="kpi-label">%Z</div><div class="kpi-val">{_f(Z_pct, 2)}</div><div class="kpi-unit">%</div></div>
</div>'''

    # ── Circuit diagram ───────────────────────────────────────────────────────
    circ_html = ''
    if has_nl or has_sc:
        circ_html = f'''
<div class="section">
  <div class="section-title"><div class="num num-purple">≈</div><h2>Equivalent Circuit (Referred to Primary)</h2></div>
  <div class="circuit-box">
    <h4>T-Model Approximate Circuit</h4>
    {_svg_circuit(nl if has_nl else None, sc if has_sc else None)}
  </div>
</div>'''

    # ── Efficiency chart ──────────────────────────────────────────────────────
    eff_chart_section = ''
    if eff_chart:
        eff_chart_section = f'''
<div class="chart-box" style="margin-bottom:24px">
  <h4>Efficiency at Unity Power Factor</h4>
  {eff_chart}
</div>'''

    # ── Assemble HTML ─────────────────────────────────────────────────────────
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TransformerIQ — Analysis Report</title>
<style>{css}</style>
</head>
<body>

<!-- ── Cover ── -->
<div class="cover">
  <div class="cover-logo">
    <svg class="cover-icon" viewBox="0 0 40 40" fill="none">
      <rect x="4" y="8" width="12" height="24" rx="2" stroke="currentColor" stroke-width="2.5"/>
      <rect x="24" y="8" width="12" height="24" rx="2" stroke="currentColor" stroke-width="2.5"/>
      <path d="M16 16 L24 16M16 20 L24 20M16 24 L24 24" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 2"/>
    </svg>
    <span class="cover-brand">TransformerIQ</span>
  </div>
  <h1>Equivalent Circuit<br>Analysis Report</h1>
  <p class="cover-sub">IEEE Standard Transformer Parameter Extraction</p>
  <div class="cover-meta">
    <div class="meta-item"><div class="meta-label">Generated</div><div class="meta-value">{ts}</div></div>
    {'<div class="meta-item"><div class="meta-label">V_OC</div><div class="meta-value">' + _f(V_oc, 2) + ' V</div></div>' if has_nl else ''}
    {'<div class="meta-item"><div class="meta-label">Freq</div><div class="meta-value">' + _f(freq, 0) + ' Hz</div></div>' if True else ''}
    {'<div class="meta-item"><div class="meta-label">Max η</div><div class="meta-value">' + _f(max_eff, 2) + ' %</div></div>' if has_cb else ''}
  </div>
</div>

<!-- ── Content ── -->
<div class="content">

{np_html}

{'<!-- NL Section -->' if has_nl else ''}
{f"""<div class="section">
  <div class="section-title"><div class="num num-cyan">1</div><h2>No-Load (Open Circuit) Test Results</h2></div>
  {nl_kpis}
  {nl_table}
</div>""" if has_nl else ''}

{'<!-- SC Section -->' if has_sc else ''}
{f"""<div class="section">
  <div class="section-title"><div class="num num-pink">2</div><h2>Short-Circuit Test Results</h2></div>
  {sc_kpis}
  {sc_table}
</div>""" if has_sc else ''}

{'<!-- Combined Section -->' if has_cb else ''}
{f"""<div class="section">
  <div class="section-title"><div class="num num-green">3</div><h2>Combined Analysis</h2></div>
  {cb_kpis}
  {cb_html}
  {vr_table}
  {eff_table}
  {eff_chart_section}
</div>""" if has_cb else ''}

{loss_html}

{circ_html}

{harm_html}

</div><!-- /content -->

<!-- ── Footer ── -->
<div class="report-footer">
  <span>TransformerIQ Equivalent Circuit Analyzer</span>
  <span>{ts}</span>
</div>

</body>
</html>'''
