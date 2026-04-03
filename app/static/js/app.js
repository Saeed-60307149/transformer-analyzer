/* === TransformerIQ — App Logic === */

// Global state
let analysisResults = null;
let charts = {};

// ── File Upload Handling ──
['nl', 'sc'].forEach(prefix => {
    const dropZone = document.getElementById(`${prefix}DropZone`);
    const fileInput = document.getElementById(`${prefix}File`);
    
    // Drag and drop
    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('drag-over'); });
    });
    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length > 0) { fileInput.files = files; handleFileSelect(prefix); }
    });
    fileInput.addEventListener('change', () => handleFileSelect(prefix));
});

function handleFileSelect(prefix) {
    const input = document.getElementById(`${prefix}File`);
    const info = document.getElementById(`${prefix}FileInfo`);
    const name = document.getElementById(`${prefix}FileName`);
    const card = document.getElementById(`${prefix}Card`);
    const dropZone = document.getElementById(`${prefix}DropZone`);
    
    if (input.files.length > 0) {
        name.textContent = input.files[0].name;
        info.style.display = 'flex';
        dropZone.style.display = 'none';
        card.classList.add('has-file');
    }
}

function removeFile(prefix) {
    const input = document.getElementById(`${prefix}File`);
    const info = document.getElementById(`${prefix}FileInfo`);
    const card = document.getElementById(`${prefix}Card`);
    const dropZone = document.getElementById(`${prefix}DropZone`);
    
    input.value = '';
    info.style.display = 'none';
    dropZone.style.display = 'block';
    card.classList.remove('has-file');
}

// ── Form Submission ──
document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const btn = document.getElementById('analyzeBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-flex';
    clearAlerts();
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const data = await response.json();
        
        if (data.error) {
            showAlert(data.error, 'error');
            return;
        }
        
        // Show warnings
        if (data.warnings) data.warnings.forEach(w => showAlert(w, 'warning'));
        if (data.errors && data.errors.length > 0) data.errors.forEach(e => showAlert(e, 'error'));
        
        if (data.no_load || data.short_circuit) {
            analysisResults = data;
            renderResults(data);
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
            showAlert('Analysis complete!', 'success');
        }
    } catch (err) {
        showAlert('Connection error: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline-flex';
        btnLoader.style.display = 'none';
    }
});

// ── Alerts ──
function showAlert(message, type) {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `<span>${type === 'error' ? '⚠' : type === 'warning' ? '⚡' : '✓'}</span><span>${message}</span>`;
    container.appendChild(alert);
    setTimeout(() => alert.remove(), 8000);
}
function clearAlerts() { document.getElementById('alertContainer').innerHTML = ''; }

// ── Tab Switching ──
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tabName}`));
    // Resize charts after tab switch
    setTimeout(() => { Object.values(charts).forEach(c => { if(c) c.resize(); }); }, 100);
}

// ── Chart Defaults ──
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2a3548';
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'circle';

function destroyChart(id) { if(charts[id]) { charts[id].destroy(); delete charts[id]; } }

// Safe number formatter — returns '—' for null/undefined/NaN
function fmt(val, digits) {
    if (val === null || val === undefined || (typeof val === 'number' && isNaN(val))) return '—';
    return Number(val).toFixed(digits);
}

// ── Main Render ──
function renderResults(data) {
    renderKPIs(data);
    if (data.no_load) renderNoLoadTab(data);
    if (data.short_circuit) renderShortCircuitTab(data);
    if (data.combined) renderCombinedTab(data);
    renderWaveforms(data);
    renderCircuitDiagram(data);
    renderReportPreview(data);
    renderOverviewCharts(data);
}

// ── KPI Cards ──
function renderKPIs(data) {
    const grid = document.getElementById('kpiGrid');
    const kpis = [];
    
    if (data.no_load) {
        kpis.push({ label: 'Core Loss', value: fmt(data.no_load.P_core, 2), unit: 'W', sub: 'No-Load Test' });
        kpis.push({ label: 'Magnetizing Reactance', value: fmt(data.no_load.X_m, 1), unit: 'Ω', sub: `Rc = ${fmt(data.no_load.R_c, 1)} Ω` });
        kpis.push({ label: 'No-Load Current', value: fmt(data.no_load.I_o * 1000, 2), unit: 'mA', sub: `PF = ${fmt(data.no_load.PF_nl, 4)}` });
    }
    if (data.short_circuit) {
        kpis.push({ label: 'Copper Loss', value: fmt(data.short_circuit.P_cu, 2), unit: 'W', sub: 'Short-Circuit Test' });
        kpis.push({ label: 'Eq. Impedance', value: fmt(data.short_circuit.Z_eq, 2), unit: 'Ω', sub: `Req=${fmt(data.short_circuit.R_eq, 2)}, Xeq=${fmt(data.short_circuit.X_eq, 2)}` });
        kpis.push({ label: 'SC Current', value: fmt(data.short_circuit.I_sc * 1000, 1), unit: 'mA', sub: `PF = ${fmt(data.short_circuit.PF_sc, 4)}` });
    }
    if (data.combined) {
        kpis.push({ label: 'Max Efficiency', value: fmt(data.combined.max_efficiency, 1), unit: '%', sub: `at ${fmt(data.combined.x_max_efficiency * 100, 0)}% load` });
        kpis.push({ label: 'Rated VA', value: fmt(data.combined.S_rated, 1), unit: 'VA', sub: 'Apparent Power' });
    }
    
    grid.innerHTML = kpis.map(k => `
        <div class="kpi-card">
            <div class="kpi-label">${k.label}</div>
            <div class="kpi-value">${k.value}<span class="kpi-unit">${k.unit}</span></div>
            <div class="kpi-sub">${k.sub}</div>
        </div>
    `).join('');
}

// ── Overview Charts ──
function renderOverviewCharts(data) {
    const placeholder = '<div style="display:flex;align-items:center;justify-content:center;height:180px;color:#64748b;font-size:13px;">Upload both No-Load and Short-Circuit files to see this chart</div>';
    if (!data.combined) {
        document.getElementById('efficiencyChart').closest('.chart-card').innerHTML += placeholder;
        document.getElementById('vrChart').closest('.chart-card').innerHTML += placeholder;
        document.getElementById('efficiencyChart').style.display = 'none';
        document.getElementById('vrChart').style.display = 'none';
    }
    // Efficiency Chart
    if (data.combined) {
        destroyChart('efficiency');
        const ctx = document.getElementById('efficiencyChart').getContext('2d');
        const upf = data.combined.efficiency_data.filter(e => e.pf === 1.0);
        const pf8 = data.combined.efficiency_data.filter(e => e.pf === 0.8);
        charts['efficiency'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: upf.map(e => `${(e.load_fraction*100).toFixed(0)}%`),
                datasets: [
                    { label: 'UPF (1.0)', data: upf.map(e => e.efficiency), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', fill: true, tension: 0.4 },
                    { label: '0.8 PF Lag', data: pf8.map(e => e.efficiency), borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.1)', fill: true, tension: 0.4 },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'Efficiency (%)' } } } }
        });
        
        // VR Chart
        destroyChart('vr');
        const ctx2 = document.getElementById('vrChart').getContext('2d');
        const vr = data.combined.voltage_regulation;
        charts['vr'] = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: vr.map(v => v.pf),
                datasets: [
                    { label: 'Lagging', data: vr.map(v => v.vr_lagging), backgroundColor: 'rgba(56,189,248,0.6)' },
                    { label: 'Leading', data: vr.map(v => v.vr_leading), backgroundColor: 'rgba(244,114,182,0.6)' },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'VR (%)' } }, x: { title: { display: true, text: 'Power Factor' } } } }
        });
    }
    
    // Loss Distribution
    if (data.no_load && data.short_circuit) {
        destroyChart('loss');
        const ctx3 = document.getElementById('lossChart').getContext('2d');
        charts['loss'] = new Chart(ctx3, {
            type: 'doughnut',
            data: {
                labels: ['Core Loss (Pi)', 'Copper Loss (Pcu)'],
                datasets: [{ data: [data.no_load.P_core, data.short_circuit.P_cu], backgroundColor: ['#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 4 }]
            },
            options: { responsive: true, cutout: '60%', plugins: { legend: { position: 'bottom' } } }
        });
    }
    
    // Power Triangle (SC test)
    if (data.short_circuit) {
        destroyChart('power');
        const ctx4 = document.getElementById('powerChart').getContext('2d');
        const sc = data.short_circuit;
        charts['power'] = new Chart(ctx4, {
            type: 'bar',
            data: {
                labels: ['Apparent (S)', 'Real (P)', 'Reactive (Q)'],
                datasets: [{ data: [sc.S_sc, sc.P_cu, sc.Q_sc], backgroundColor: ['#818cf8', '#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 6 }]
            },
            options: { responsive: true, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: 'Power (W/VA/VAR)' } } } }
        });
    }
}

// ── No-Load Tab ──
function renderNoLoadTab(data) {
    const nl = data.no_load;
    const params = [
        { name: 'Open-Circuit Voltage', sym: 'V_OC', val: nl.V_oc.toFixed(2), unit: 'V' },
        { name: 'No-Load Current', sym: 'I_0', val: nl.I_o.toFixed(6), unit: 'A' },
        { name: 'Core Loss', sym: 'P_core', val: nl.P_core.toFixed(4), unit: 'W' },
        { name: 'Power Factor', sym: 'cos φ₀', val: nl.PF_nl.toFixed(6), unit: '' },
        { name: 'Core Loss Current', sym: 'I_c', val: nl.I_c.toFixed(6), unit: 'A' },
        { name: 'Magnetizing Current', sym: 'I_m', val: nl.I_m.toFixed(6), unit: 'A' },
        { name: 'Core Resistance', sym: 'R_c', val: nl.R_c.toFixed(2), unit: 'Ω' },
        { name: 'Magnetizing Reactance', sym: 'X_m', val: nl.X_m.toFixed(2), unit: 'Ω' },
        { name: 'Apparent Power', sym: 'S₀', val: nl.S_o.toFixed(4), unit: 'VA' },
        { name: 'Reactive Power', sym: 'Q₀', val: nl.Q_o.toFixed(4), unit: 'VAR' },
        { name: 'No-Load Angle', sym: 'φ₀', val: nl.theta_nl_deg.toFixed(2), unit: '°' },
        { name: 'Frequency', sym: 'f', val: nl.frequency_Hz.toFixed(1), unit: 'Hz' },
    ];
    
    document.getElementById('nlParamsGrid').innerHTML = params.map(p => `
        <div class="param-card">
            <div><div class="param-name">${p.name}</div><div class="param-symbol">${p.sym}</div></div>
            <div><span class="param-val">${p.val}</span><span class="param-unit">${p.unit}</span></div>
        </div>
    `).join('');
    
    // Harmonic chart
    if (data.harmonics && data.harmonics.no_load) {
        destroyChart('nlHarmonic');
        const h = data.harmonics.no_load;
        const ctx = document.getElementById('nlHarmonicChart').getContext('2d');
        charts['nlHarmonic'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: h.current_harmonics.map(x => `H${x.harmonic}`),
                datasets: [
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)' },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)' },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: `THD_V: ${h.thd_voltage}% | THD_I: ${h.thd_current}%` } }, scales: { y: { title: { display: true, text: '% of Fundamental' } } } }
        });
    }
    
    // Phasor chart (using polar area)
    destroyChart('nlPhasor');
    const pCtx = document.getElementById('nlPhasorChart').getContext('2d');
    charts['nlPhasor'] = new Chart(pCtx, {
        type: 'polarArea',
        data: {
            labels: ['I_c (Core Loss)', 'I_m (Magnetizing)', 'I_0 (Total)'],
            datasets: [{ data: [nl.I_c * 1000, nl.I_m * 1000, nl.I_o * 1000], backgroundColor: ['rgba(56,189,248,0.5)', 'rgba(129,140,248,0.5)', 'rgba(52,211,153,0.5)'] }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' }, title: { display: true, text: 'Current Components (mA)' } } }
    });
    
    // NL Power breakdown
    destroyChart('nlPowerBD');
    const pbCtx = document.getElementById('nlPowerBreakdown').getContext('2d');
    charts['nlPowerBD'] = new Chart(pbCtx, {
        type: 'doughnut',
        data: {
            labels: ['Real Power P₀', 'Reactive Power Q₀'],
            datasets: [{ data: [nl.P_core, nl.Q_o], backgroundColor: ['#38bdf8', '#818cf8'], borderWidth: 0 }]
        },
        options: { responsive: true, cutout: '55%', plugins: { legend: { position: 'bottom' } } }
    });
}

// ── Short-Circuit Tab ──
function renderShortCircuitTab(data) {
    const sc = data.short_circuit;
    const params = [
        { name: 'SC Voltage', sym: 'V_SC', val: sc.V_sc.toFixed(4), unit: 'V' },
        { name: 'SC Current', sym: 'I_SC', val: sc.I_sc.toFixed(6), unit: 'A' },
        { name: 'Copper Loss', sym: 'P_cu', val: sc.P_cu.toFixed(4), unit: 'W' },
        { name: 'Power Factor', sym: 'cos φ_SC', val: sc.PF_sc.toFixed(6), unit: '' },
        { name: 'Eq. Impedance', sym: 'Z_eq', val: sc.Z_eq.toFixed(4), unit: 'Ω' },
        { name: 'Eq. Resistance', sym: 'R_eq', val: sc.R_eq.toFixed(4), unit: 'Ω' },
        { name: 'Eq. Reactance', sym: 'X_eq', val: sc.X_eq.toFixed(4), unit: 'Ω' },
        { name: 'R₁ (approx)', sym: 'R₁', val: sc.R1_approx.toFixed(4), unit: 'Ω' },
        { name: 'X₁ (approx)', sym: 'X₁', val: sc.X1_approx.toFixed(4), unit: 'Ω' },
        { name: 'Apparent Power', sym: 'S_SC', val: sc.S_sc.toFixed(4), unit: 'VA' },
        { name: 'SC Angle', sym: 'φ_SC', val: sc.theta_sc_deg.toFixed(2), unit: '°' },
        { name: 'Frequency', sym: 'f', val: sc.frequency_Hz.toFixed(1), unit: 'Hz' },
    ];
    
    document.getElementById('scParamsGrid').innerHTML = params.map(p => `
        <div class="param-card">
            <div><div class="param-name">${p.name}</div><div class="param-symbol">${p.sym}</div></div>
            <div><span class="param-val">${p.val}</span><span class="param-unit">${p.unit}</span></div>
        </div>
    `).join('');
    
    // SC Harmonic chart
    if (data.harmonics && data.harmonics.short_circuit) {
        destroyChart('scHarmonic');
        const h = data.harmonics.short_circuit;
        const ctx = document.getElementById('scHarmonicChart').getContext('2d');
        charts['scHarmonic'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: h.current_harmonics.map(x => `H${x.harmonic}`),
                datasets: [
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)' },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)' },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: `THD_V: ${h.thd_voltage}% | THD_I: ${h.thd_current}%` } }, scales: { y: { title: { display: true, text: '% of Fundamental' } } } }
        });
    }
    
    // Impedance triangle
    destroyChart('scImpedance');
    const iCtx = document.getElementById('scImpedanceChart').getContext('2d');
    charts['scImpedance'] = new Chart(iCtx, {
        type: 'bar',
        data: {
            labels: ['Z_eq', 'R_eq', 'X_eq'],
            datasets: [{ data: [sc.Z_eq, sc.R_eq, sc.X_eq], backgroundColor: ['#818cf8', '#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 6 }]
        },
        options: { responsive: true, plugins: { legend: { display: false }, title: { display: true, text: 'Impedance Components (Ω)' } } }
    });
    
    // SC Power breakdown
    destroyChart('scPowerBD');
    const spCtx = document.getElementById('scPowerBreakdown').getContext('2d');
    charts['scPowerBD'] = new Chart(spCtx, {
        type: 'doughnut',
        data: {
            labels: ['Real (P_cu)', 'Reactive (Q_SC)'],
            datasets: [{ data: [sc.P_cu, sc.Q_sc], backgroundColor: ['#f472b6', '#818cf8'], borderWidth: 0 }]
        },
        options: { responsive: true, cutout: '55%', plugins: { legend: { position: 'bottom' } } }
    });
}

// ── Combined Tab ──
function renderCombinedTab(data) {
    const c = data.combined;
    const nl = data.no_load;
    const sc = data.short_circuit;
    
    document.getElementById('combinedSummary').innerHTML = `
        <h3>Equivalent Circuit Summary</h3>
        <div class="kpi-grid" style="margin-top:16px">
            <div class="kpi-card"><div class="kpi-label">Rated VA</div><div class="kpi-value">${c.S_rated.toFixed(1)}<span class="kpi-unit">VA</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Total FL Losses</div><div class="kpi-value">${c.total_loss_fl.toFixed(2)}<span class="kpi-unit">W</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency Load</div><div class="kpi-value">${(c.x_max_efficiency*100).toFixed(1)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency</div><div class="kpi-value">${c.max_efficiency.toFixed(2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%Z</div><div class="kpi-value">${c.Z_percent.toFixed(2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%R</div><div class="kpi-value">${c.R_percent.toFixed(2)}<span class="kpi-unit">%</span></div></div>
        </div>
    `;
    
    // Efficiency curves
    destroyChart('combinedEff');
    const ctx = document.getElementById('combinedEffChart').getContext('2d');
    const upf = c.efficiency_data.filter(e => e.pf === 1.0);
    const pf8 = c.efficiency_data.filter(e => e.pf === 0.8);
    
    // Generate smooth efficiency curve with more points
    const loadPoints = [];
    const effUPF = [];
    const effPF8 = [];
    for (let x = 0.1; x <= 1.3; x += 0.05) {
        loadPoints.push(`${(x*100).toFixed(0)}%`);
        const pcu = x*x * sc.P_cu;
        const p1 = x * c.S_rated * 1.0;
        const p2 = x * c.S_rated * 0.8;
        effUPF.push(p1 / (p1 + nl.P_core + pcu) * 100);
        effPF8.push(p2 / (p2 + nl.P_core + pcu) * 100);
    }
    
    charts['combinedEff'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: loadPoints,
            datasets: [
                { label: 'Unity PF', data: effUPF, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.08)', fill: true, tension: 0.4, pointRadius: 0 },
                { label: '0.8 PF Lagging', data: effPF8, borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.08)', fill: true, tension: 0.4, pointRadius: 0 },
            ]
        },
        options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'Efficiency (%)' }, min: 0 }, x: { title: { display: true, text: 'Load (% of Rated)' } } } }
    });
    
    // Tables
    let tables = '';
    
    // VR Table
    tables += `<div class="data-table-wrap"><h3>Voltage Regulation</h3><table>
        <tr><th>Power Factor</th><th>VR Lagging (%)</th><th>VR Leading (%)</th></tr>`;
    c.voltage_regulation.forEach(vr => {
        tables += `<tr><td>${vr.pf}</td><td>${vr.vr_lagging.toFixed(4)}</td><td>${vr.vr_leading.toFixed(4)}</td></tr>`;
    });
    tables += `</table></div>`;
    
    // Efficiency table
    tables += `<div class="data-table-wrap"><h3>Efficiency at Various Loads</h3><table>
        <tr><th>Load</th><th>PF</th><th>P_out (W)</th><th>P_cu (W)</th><th>P_core (W)</th><th>η (%)</th></tr>`;
    c.efficiency_data.forEach(e => {
        tables += `<tr><td>${(e.load_fraction*100).toFixed(0)}%</td><td>${e.pf}</td><td>${e.P_out.toFixed(2)}</td><td>${e.P_cu.toFixed(4)}</td><td>${e.P_core.toFixed(4)}</td><td>${e.efficiency.toFixed(2)}</td></tr>`;
    });
    tables += `</table></div>`;
    
    document.getElementById('combinedTables').innerHTML = tables;
}

// ── Waveforms Tab ──
function renderWaveforms(data) {
    if (data.waveforms) {
        if (data.waveforms.no_load) {
            destroyChart('nlWave');
            const w = data.waveforms.no_load;
            const ctx = document.getElementById('nlWaveformChart').getContext('2d');
            charts['nlWave'] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: w.time,
                    datasets: [
                        { label: 'Voltage (V)', data: w.voltage, borderColor: '#38bdf8', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y' },
                        { label: 'Current (A)', data: w.current, borderColor: '#f472b6', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y1' },
                    ]
                },
                options: {
                    responsive: true, interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { position: 'top' } },
                    scales: {
                        x: { title: { display: true, text: 'Time (ms)' }, ticks: { maxTicksLimit: 20 } },
                        y: { title: { display: true, text: 'Voltage (V)' }, position: 'left' },
                        y1: { title: { display: true, text: 'Current (A)' }, position: 'right', grid: { drawOnChartArea: false } },
                    }
                }
            });
        }
        
        if (data.waveforms.short_circuit) {
            destroyChart('scWave');
            const w = data.waveforms.short_circuit;
            const ctx = document.getElementById('scWaveformChart').getContext('2d');
            charts['scWave'] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: w.time,
                    datasets: [
                        { label: 'Voltage (V)', data: w.voltage, borderColor: '#38bdf8', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y' },
                        { label: 'Current (A)', data: w.current, borderColor: '#f472b6', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y1' },
                    ]
                },
                options: {
                    responsive: true, interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { position: 'top' } },
                    scales: {
                        x: { title: { display: true, text: 'Time (ms)' }, ticks: { maxTicksLimit: 20 } },
                        y: { title: { display: true, text: 'Voltage (V)' }, position: 'left' },
                        y1: { title: { display: true, text: 'Current (A)' }, position: 'right', grid: { drawOnChartArea: false } },
                    }
                }
            });
        }
    }
}

// ── Circuit Diagram (SVG) ──
function renderCircuitDiagram(data) {
    const nl = data.no_load || {};
    const sc = data.short_circuit || {};
    const R1 = sc.R1_approx ? sc.R1_approx.toFixed(2) : '?';
    const X1 = sc.X1_approx ? sc.X1_approx.toFixed(2) : '?';
    const R2 = sc.R2_approx ? sc.R2_approx.toFixed(2) : '?';
    const X2 = sc.X2_approx ? sc.X2_approx.toFixed(2) : '?';
    const Rc = nl.R_c ? nl.R_c.toFixed(1) : '?';
    const Xm = nl.X_m ? nl.X_m.toFixed(1) : '?';
    
    document.getElementById('circuitDiagram').innerHTML = `
        <h3 style="font-family:var(--font-display);font-size:22px;margin-bottom:24px;">Approximate Equivalent Circuit (Referred to Primary)</h3>
        <svg viewBox="0 0 800 340" xmlns="http://www.w3.org/2000/svg" style="max-width:750px;">
            <defs>
                <marker id="arrowR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#38bdf8"/></marker>
            </defs>
            <!-- Main line -->
            <line x1="40" y1="80" x2="120" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <!-- R1 -->
            <rect x="120" y="68" width="80" height="24" rx="3" fill="none" stroke="#38bdf8" stroke-width="2"/>
            <text x="160" y="84" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">R₁=${R1}Ω</text>
            <!-- X1 -->
            <line x1="200" y1="80" x2="240" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="240" y="68" width="80" height="24" rx="3" fill="none" stroke="#818cf8" stroke-width="2"/>
            <text x="280" y="84" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono" font-size="12">X₁=${X1}Ω</text>
            <!-- Junction A -->
            <line x1="320" y1="80" x2="380" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <circle cx="380" cy="80" r="3" fill="#94a3b8"/>
            <!-- Rc branch down -->
            <line x1="380" y1="80" x2="380" y2="120" stroke="#94a3b8" stroke-width="2"/>
            <rect x="355" y="120" width="50" height="60" rx="3" fill="none" stroke="#34d399" stroke-width="2"/>
            <text x="380" y="148" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono" font-size="11">Rc</text>
            <text x="380" y="164" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono" font-size="10">${Rc}Ω</text>
            <line x1="380" y1="180" x2="380" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <!-- Xm branch down -->
            <line x1="380" y1="80" x2="480" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <circle cx="480" cy="80" r="3" fill="#94a3b8"/>
            <line x1="480" y1="80" x2="480" y2="120" stroke="#94a3b8" stroke-width="2"/>
            <rect x="455" y="120" width="50" height="60" rx="3" fill="none" stroke="#fbbf24" stroke-width="2"/>
            <text x="480" y="148" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono" font-size="11">Xm</text>
            <text x="480" y="164" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono" font-size="10">${Xm}Ω</text>
            <line x1="480" y1="180" x2="480" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <!-- Continue main line -->
            <line x1="480" y1="80" x2="520" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <!-- R2 -->
            <rect x="520" y="68" width="80" height="24" rx="3" fill="none" stroke="#38bdf8" stroke-width="2"/>
            <text x="560" y="84" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">R₂'=${R2}Ω</text>
            <!-- X2 -->
            <line x1="600" y1="80" x2="620" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="620" y="68" width="80" height="24" rx="3" fill="none" stroke="#818cf8" stroke-width="2"/>
            <text x="660" y="84" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono" font-size="12">X₂'=${X2}Ω</text>
            <line x1="700" y1="80" x2="760" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <!-- Return path -->
            <line x1="40" y1="260" x2="760" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="40" y1="80" x2="40" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="760" y1="80" x2="760" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <!-- Labels -->
            <text x="20" y="170" text-anchor="middle" fill="#94a3b8" font-size="14" font-weight="600" transform="rotate(-90,20,170)">V₁ (Primary)</text>
            <text x="780" y="170" text-anchor="middle" fill="#94a3b8" font-size="14" font-weight="600" transform="rotate(90,780,170)">V₂' (Secondary)</text>
            <!-- Current arrows -->
            <line x1="60" y1="68" x2="100" y2="68" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arrowR)"/>
            <text x="80" y="62" text-anchor="middle" fill="#38bdf8" font-size="11">I₁</text>
            <line x1="720" y1="68" x2="740" y2="68" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arrowR)"/>
            <text x="730" y="62" text-anchor="middle" fill="#38bdf8" font-size="11">I₂'</text>
            <!-- Ic Im labels -->
            <text x="370" y="105" text-anchor="end" fill="#34d399" font-size="10">Ic↓</text>
            <text x="495" y="105" text-anchor="start" fill="#fbbf24" font-size="10">Im↓</text>
            <!-- Title box -->
            <rect x="160" y="290" width="480" height="35" rx="6" fill="rgba(56,189,248,0.08)" stroke="rgba(56,189,248,0.2)" stroke-width="1"/>
            <text x="400" y="312" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">
                Zeq = ${sc.Z_eq ? sc.Z_eq.toFixed(2) : '?'}Ω  |  Req = ${sc.R_eq ? sc.R_eq.toFixed(2) : '?'}Ω  |  Xeq = ${sc.X_eq ? sc.X_eq.toFixed(2) : '?'}Ω
            </text>
        </svg>
    `;
}

// ── Report Preview & Export ──
function renderReportPreview(data) {
    const preview = document.getElementById('reportPreview');
    let html = '<h2 style="color:#0f3460;margin-bottom:16px;">Transformer Analysis Report</h2>';
    
    if (data.no_load) {
        html += '<h3 style="color:#0f3460;margin:16px 0 8px;">No-Load Test Results</h3>';
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">';
        html += '<tr style="background:#0f3460;color:#fff;"><th style="padding:8px;text-align:left;">Parameter</th><th style="padding:8px;">Value</th><th style="padding:8px;">Unit</th></tr>';
        const nlParams = [
            ['V_OC', data.no_load.V_oc, 'V'], ['I_0', data.no_load.I_o, 'A'], ['P_core', data.no_load.P_core, 'W'],
            ['PF', data.no_load.PF_nl, ''], ['R_c', data.no_load.R_c, 'Ω'], ['X_m', data.no_load.X_m, 'Ω'],
            ['I_c', data.no_load.I_c, 'A'], ['I_m', data.no_load.I_m, 'A']
        ];
        nlParams.forEach(([n,v,u]) => html += `<tr style="border-bottom:1px solid #ddd;"><td style="padding:6px 8px;">${n}</td><td style="padding:6px 8px;font-family:monospace;font-weight:600;color:#0f3460;">${typeof v === 'number' ? v.toFixed(6) : v}</td><td style="padding:6px 8px;">${u}</td></tr>`);
        html += '</table>';
    }
    
    if (data.short_circuit) {
        html += '<h3 style="color:#0f3460;margin:16px 0 8px;">Short-Circuit Test Results</h3>';
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">';
        html += '<tr style="background:#0f3460;color:#fff;"><th style="padding:8px;text-align:left;">Parameter</th><th style="padding:8px;">Value</th><th style="padding:8px;">Unit</th></tr>';
        const scParams = [
            ['V_SC', data.short_circuit.V_sc, 'V'], ['I_SC', data.short_circuit.I_sc, 'A'], ['P_cu', data.short_circuit.P_cu, 'W'],
            ['PF_SC', data.short_circuit.PF_sc, ''], ['Z_eq', data.short_circuit.Z_eq, 'Ω'], ['R_eq', data.short_circuit.R_eq, 'Ω'],
            ['X_eq', data.short_circuit.X_eq, 'Ω']
        ];
        scParams.forEach(([n,v,u]) => html += `<tr style="border-bottom:1px solid #ddd;"><td style="padding:6px 8px;">${n}</td><td style="padding:6px 8px;font-family:monospace;font-weight:600;color:#0f3460;">${typeof v === 'number' ? v.toFixed(6) : v}</td><td style="padding:6px 8px;">${u}</td></tr>`);
        html += '</table>';
    }
    
    preview.innerHTML = html;
}

async function exportReport() {
    if (!analysisResults) return;
    try {
        const response = await fetch('/export-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                no_load: analysisResults.no_load,
                short_circuit: analysisResults.short_circuit,
                combined: analysisResults.combined,
                nl_harmonics: analysisResults.harmonics?.no_load,
                sc_harmonics: analysisResults.harmonics?.short_circuit,
            })
        });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transformer_report_${new Date().toISOString().slice(0,10)}.html`;
        a.click();
        window.URL.revokeObjectURL(url);
    } catch(err) { showAlert('Export failed: ' + err.message, 'error'); }
}

function printReport() { window.print(); }
