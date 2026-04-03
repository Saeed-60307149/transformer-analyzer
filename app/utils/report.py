"""
PDF Report Generator for Transformer Analysis
"""
from datetime import datetime


def generate_report_html(nl_results, sc_results, combined, nl_harmonics, sc_harmonics):
    """Generate a printable HTML report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Transformer Equivalent Circuit Analysis Report</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'DM Sans', sans-serif; color: #1a1a2e; padding: 40px; max-width: 900px; margin: 0 auto; line-height: 1.6; }}
.report-header {{ text-align: center; border-bottom: 3px solid #0f3460; padding-bottom: 20px; margin-bottom: 30px; }}
.report-header h1 {{ font-size: 28px; color: #0f3460; margin-bottom: 5px; }}
.report-header .subtitle {{ color: #666; font-size: 14px; }}
.section {{ margin-bottom: 30px; page-break-inside: avoid; }}
.section h2 {{ font-size: 20px; color: #0f3460; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px; margin-bottom: 15px; }}
.section h3 {{ font-size: 16px; color: #16213e; margin: 15px 0 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th, td {{ padding: 8px 12px; text-align: left; border: 1px solid #ddd; }}
th {{ background-color: #0f3460; color: white; font-weight: 600; }}
tr:nth-child(even) {{ background-color: #f8f9fa; }}
.param-value {{ font-family: 'IBM Plex Mono', monospace; font-weight: 600; color: #0f3460; }}
.footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 2px solid #e0e0e0; color: #888; font-size: 12px; }}
@media print {{
    body {{ padding: 20px; }}
    .no-print {{ display: none; }}
}}
</style>
</head>
<body>
<div class="report-header">
<h1>Transformer Equivalent Circuit Analysis</h1>
<p class="subtitle">Generated: {timestamp}</p>
<p class="subtitle">Transformer Equivalent Circuit Analysis</p>
</div>
"""

    if nl_results:
        html += f"""
<div class="section">
<h2>1. No-Load (Open Circuit) Test Results</h2>
<table>
<tr><th>Parameter</th><th>Symbol</th><th>Value</th><th>Unit</th></tr>
<tr><td>Open-Circuit Voltage (RMS)</td><td>V<sub>OC</sub></td><td class="param-value">{nl_results['V_oc']}</td><td>V</td></tr>
<tr><td>No-Load Current (RMS)</td><td>I<sub>0</sub></td><td class="param-value">{nl_results['I_o']}</td><td>A</td></tr>
<tr><td>Core Loss</td><td>P<sub>core</sub></td><td class="param-value">{nl_results['P_core']}</td><td>W</td></tr>
<tr><td>No-Load Power Factor</td><td>cos φ<sub>0</sub></td><td class="param-value">{nl_results['PF_nl']}</td><td>—</td></tr>
<tr><td>No-Load Angle</td><td>φ<sub>0</sub></td><td class="param-value">{nl_results['theta_nl_deg']}°</td><td>degrees</td></tr>
<tr><td>Core Loss Current</td><td>I<sub>c</sub></td><td class="param-value">{nl_results['I_c']}</td><td>A</td></tr>
<tr><td>Magnetizing Current</td><td>I<sub>m</sub></td><td class="param-value">{nl_results['I_m']}</td><td>A</td></tr>
<tr><td>Core Loss Resistance</td><td>R<sub>c</sub></td><td class="param-value">{nl_results['R_c']}</td><td>Ω</td></tr>
<tr><td>Magnetizing Reactance</td><td>X<sub>m</sub></td><td class="param-value">{nl_results['X_m']}</td><td>Ω</td></tr>
<tr><td>Frequency</td><td>f</td><td class="param-value">{nl_results['frequency_Hz']}</td><td>Hz</td></tr>
</table>
</div>
"""

    if sc_results:
        html += f"""
<div class="section">
<h2>2. Short-Circuit Test Results</h2>
<table>
<tr><th>Parameter</th><th>Symbol</th><th>Value</th><th>Unit</th></tr>
<tr><td>Short-Circuit Voltage (RMS)</td><td>V<sub>SC</sub></td><td class="param-value">{sc_results['V_sc']}</td><td>V</td></tr>
<tr><td>Short-Circuit Current (RMS)</td><td>I<sub>SC</sub></td><td class="param-value">{sc_results['I_sc']}</td><td>A</td></tr>
<tr><td>Copper Loss</td><td>P<sub>cu</sub></td><td class="param-value">{sc_results['P_cu']}</td><td>W</td></tr>
<tr><td>Short-Circuit Power Factor</td><td>cos φ<sub>SC</sub></td><td class="param-value">{sc_results['PF_sc']}</td><td>—</td></tr>
<tr><td>SC Angle</td><td>φ<sub>SC</sub></td><td class="param-value">{sc_results['theta_sc_deg']}°</td><td>degrees</td></tr>
<tr><td>Equivalent Impedance</td><td>Z<sub>eq</sub></td><td class="param-value">{sc_results['Z_eq']}</td><td>Ω</td></tr>
<tr><td>Equivalent Resistance</td><td>R<sub>eq</sub></td><td class="param-value">{sc_results['R_eq']}</td><td>Ω</td></tr>
<tr><td>Equivalent Reactance</td><td>X<sub>eq</sub></td><td class="param-value">{sc_results['X_eq']}</td><td>Ω</td></tr>
<tr><td>R₁ (approx)</td><td>R<sub>1</sub></td><td class="param-value">{sc_results['R1_approx']}</td><td>Ω</td></tr>
<tr><td>X₁ (approx)</td><td>X<sub>1</sub></td><td class="param-value">{sc_results['X1_approx']}</td><td>Ω</td></tr>
<tr><td>Frequency</td><td>f</td><td class="param-value">{sc_results['frequency_Hz']}</td><td>Hz</td></tr>
</table>
</div>
"""

    if combined:
        html += f"""
<div class="section">
<h2>3. Combined Analysis</h2>
<table>
<tr><th>Parameter</th><th>Value</th><th>Unit</th></tr>
<tr><td>Rated Apparent Power</td><td class="param-value">{combined['S_rated']}</td><td>VA</td></tr>
<tr><td>Total Full-Load Losses</td><td class="param-value">{combined['total_loss_fl']}</td><td>W</td></tr>
<tr><td>Load for Max Efficiency</td><td class="param-value">{combined['x_max_efficiency'] * 100:.1f}%</td><td>of rated</td></tr>
<tr><td>Maximum Efficiency (UPF)</td><td class="param-value">{combined['max_efficiency']:.2f}%</td><td>—</td></tr>
<tr><td>Percent Impedance</td><td class="param-value">{combined['Z_percent']:.2f}%</td><td>—</td></tr>
</table>

<h3>Voltage Regulation</h3>
<table>
<tr><th>Power Factor</th><th>VR (Lagging)</th><th>VR (Leading)</th></tr>
"""
        for vr in combined['voltage_regulation']:
            html += f'<tr><td>{vr["pf"]}</td><td class="param-value">{vr["vr_lagging"]:.4f}%</td><td class="param-value">{vr["vr_leading"]:.4f}%</td></tr>\n'

        html += """</table>

<h3>Efficiency at Various Loads</h3>
<table>
<tr><th>Load (%)</th><th>Power Factor</th><th>Output (W)</th><th>Cu Loss (W)</th><th>Core Loss (W)</th><th>Efficiency (%)</th></tr>
"""
        for e in combined['efficiency_data']:
            html += f'<tr><td>{e["load_fraction"] * 100:.0f}%</td><td>{e["pf"]}</td><td class="param-value">{e["P_out"]:.2f}</td><td>{e["P_cu"]:.4f}</td><td>{e["P_core"]:.4f}</td><td class="param-value">{e["efficiency"]:.2f}</td></tr>\n'

        html += "</table></div>"

    if nl_harmonics:
        html += f"""
<div class="section">
<h2>4. Harmonic Analysis - No-Load</h2>
<p>THD Voltage: <span class="param-value">{nl_harmonics['thd_voltage']}%</span> | THD Current: <span class="param-value">{nl_harmonics['thd_current']}%</span></p>
</div>
"""

    if sc_harmonics:
        html += f"""
<div class="section">
<h2>5. Harmonic Analysis - Short Circuit</h2>
<p>THD Voltage: <span class="param-value">{sc_harmonics['thd_voltage']}%</span> | THD Current: <span class="param-value">{sc_harmonics['thd_current']}%</span></p>
</div>
"""

    html += f"""
<div class="footer">
<p>Transformer Equivalent Circuit Analysis Report</p>
<p>{timestamp}</p>
</div>
</body>
</html>"""

    return html
