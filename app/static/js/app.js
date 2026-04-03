/* === Transformer Equivalent Circuit Analyzer — App Logic === */

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
Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;

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

// ── Chart placeholder helpers (never destroy canvas DOM elements) ──
function showNoData(chartId) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    canvas.style.display = 'none';
    if (!canvas.nextElementSibling || !canvas.nextElementSibling.classList.contains('no-data-msg')) {
        const div = document.createElement('div');
        div.className = 'no-data-msg';
        div.style.cssText = 'display:flex;align-items:center;justify-content:center;height:180px;color:#64748b;font-size:13px;';
        div.textContent = 'Upload both test files to see this chart';
        canvas.parentNode.insertBefore(div, canvas.nextSibling);
    }
}
function clearNoData(chartId) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    canvas.style.display = '';
    const sibling = canvas.nextElementSibling;
    if (sibling && sibling.classList.contains('no-data-msg')) sibling.remove();
}

// ── Overview Charts ──
function renderOverviewCharts(data) {
    // Efficiency + VR charts need combined data
    if (!data.combined) {
        showNoData('efficiencyChart');
        showNoData('vrChart');
    } else {
        clearNoData('efficiencyChart');
        clearNoData('vrChart');
        // Efficiency Chart
        destroyChart('efficiency');
        const ctx = document.getElementById('efficiencyChart').getContext('2d');
        const upf = data.combined.efficiency_data.filter(e => e.pf === 1.0);
        const pf8 = data.combined.efficiency_data.filter(e => e.pf === 0.8);
        charts['efficiency'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: upf.map(e => `${(e.load_fraction*100).toFixed(0)}%`),
                datasets: [
                    { label: 'UPF (1.0)', data: upf.map(e => e.efficiency), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                    { label: '0.8 PF Lag', data: pf8.map(e => e.efficiency), borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
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
                    { label: 'Lagging', data: vr.map(v => v.vr_lagging), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Leading', data: vr.map(v => v.vr_leading), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'VR (%)' } }, x: { title: { display: true, text: 'Power Factor' } } } }
        });
    }

    // Loss Distribution — needs both tests
    if (data.no_load && data.short_circuit) {
        clearNoData('lossChart');
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
    } else {
        showNoData('lossChart');
    }

    // Power Triangle — needs SC
    if (data.short_circuit) {
        clearNoData('powerChart');
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
    } else {
        showNoData('powerChart');
    }
}

// ── No-Load Tab ──
function renderNoLoadTab(data) {
    const nl = data.no_load;
    const params = [
        { name: 'Open-Circuit Voltage', sym: 'V_OC', val: fmt(nl.V_oc, 2), unit: 'V' },
        { name: 'No-Load Current', sym: 'I_0', val: fmt(nl.I_o, 6), unit: 'A' },
        { name: 'Core Loss', sym: 'P_core', val: fmt(nl.P_core, 4), unit: 'W' },
        { name: 'Power Factor', sym: 'cos φ₀', val: fmt(nl.PF_nl, 6), unit: '' },
        { name: 'Core Loss Current', sym: 'I_c', val: fmt(nl.I_c, 6), unit: 'A' },
        { name: 'Magnetizing Current', sym: 'I_m', val: fmt(nl.I_m, 6), unit: 'A' },
        { name: 'Core Resistance', sym: 'R_c', val: fmt(nl.R_c, 2), unit: 'Ω' },
        { name: 'Magnetizing Reactance', sym: 'X_m', val: fmt(nl.X_m, 2), unit: 'Ω' },
        { name: 'Apparent Power', sym: 'S₀', val: fmt(nl.S_o, 4), unit: 'VA' },
        { name: 'Reactive Power', sym: 'Q₀', val: fmt(nl.Q_o, 4), unit: 'VAR' },
        { name: 'No-Load Angle', sym: 'φ₀', val: fmt(nl.theta_nl_deg, 2), unit: '°' },
        { name: 'Frequency', sym: 'f', val: fmt(nl.frequency_Hz, 1), unit: 'Hz' },
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
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: `THD_V: ${h.thd_voltage}% | THD_I: ${h.thd_current}%` } }, scales: { y: { title: { display: true, text: '% of Fundamental' } } } }
        });
    }

    // Phasor chart
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
        { name: 'SC Voltage', sym: 'V_SC', val: fmt(sc.V_sc, 4), unit: 'V' },
        { name: 'SC Current', sym: 'I_SC', val: fmt(sc.I_sc, 6), unit: 'A' },
        { name: 'Copper Loss', sym: 'P_cu', val: fmt(sc.P_cu, 4), unit: 'W' },
        { name: 'Power Factor', sym: 'cos φ_SC', val: fmt(sc.PF_sc, 6), unit: '' },
        { name: 'Eq. Impedance', sym: 'Z_eq', val: fmt(sc.Z_eq, 4), unit: 'Ω' },
        { name: 'Eq. Resistance', sym: 'R_eq', val: fmt(sc.R_eq, 4), unit: 'Ω' },
        { name: 'Eq. Reactance', sym: 'X_eq', val: fmt(sc.X_eq, 4), unit: 'Ω' },
        { name: 'R₁ (approx)', sym: 'R₁', val: fmt(sc.R1_approx, 4), unit: 'Ω' },
        { name: 'X₁ (approx)', sym: 'X₁', val: fmt(sc.X1_approx, 4), unit: 'Ω' },
        { name: 'Apparent Power', sym: 'S_SC', val: fmt(sc.S_sc, 4), unit: 'VA' },
        { name: 'SC Angle', sym: 'φ_SC', val: fmt(sc.theta_sc_deg, 2), unit: '°' },
        { name: 'Frequency', sym: 'f', val: fmt(sc.frequency_Hz, 1), unit: 'Hz' },
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
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
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
            <div class="kpi-card"><div class="kpi-label">Rated VA</div><div class="kpi-value">${fmt(c.S_rated, 1)}<span class="kpi-unit">VA</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Total FL Losses</div><div class="kpi-value">${fmt(c.total_loss_fl, 2)}<span class="kpi-unit">W</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency Load</div><div class="kpi-value">${fmt(c.x_max_efficiency * 100, 1)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency</div><div class="kpi-value">${fmt(c.max_efficiency, 2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%Z</div><div class="kpi-value">${fmt(c.Z_percent, 2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%R</div><div class="kpi-value">${fmt(c.R_percent, 2)}<span class="kpi-unit">%</span></div></div>
        </div>
    `;

    // Efficiency curves
    destroyChart('combinedEff');
    const ctx = document.getElementById('combinedEffChart').getContext('2d');

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
        tables += `<tr><td>${vr.pf}</td><td>${fmt(vr.vr_lagging, 4)}</td><td>${fmt(vr.vr_leading, 4)}</td></tr>`;
    });
    tables += `</table></div>`;

    // Efficiency table
    tables += `<div class="data-table-wrap"><h3>Efficiency at Various Loads</h3><table>
        <tr><th>Load</th><th>PF</th><th>P_out (W)</th><th>P_cu (W)</th><th>P_core (W)</th><th>η (%)</th></tr>`;
    c.efficiency_data.forEach(e => {
        tables += `<tr><td>${fmt(e.load_fraction * 100, 0)}%</td><td>${e.pf}</td><td>${fmt(e.P_out, 2)}</td><td>${fmt(e.P_cu, 4)}</td><td>${fmt(e.P_core, 4)}</td><td>${fmt(e.efficiency, 2)}</td></tr>`;
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
    const R1 = sc.R1_approx != null ? fmt(sc.R1_approx, 2) : '?';
    const X1 = sc.X1_approx != null ? fmt(sc.X1_approx, 2) : '?';
    const R2 = sc.R2_approx != null ? fmt(sc.R2_approx, 2) : '?';
    const X2 = sc.X2_approx != null ? fmt(sc.X2_approx, 2) : '?';
    const Rc = nl.R_c != null ? fmt(nl.R_c, 1) : '?';
    const Xm = nl.X_m != null ? fmt(nl.X_m, 1) : '?';

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
                Zeq = ${sc.Z_eq != null ? fmt(sc.Z_eq, 2) : '?'}Ω  |  Req = ${sc.R_eq != null ? fmt(sc.R_eq, 2) : '?'}Ω  |  Xeq = ${sc.X_eq != null ? fmt(sc.X_eq, 2) : '?'}Ω
            </text>
        </svg>
    `;
}

// ── Report Preview ──
function renderReportPreview(data) {
    const preview = document.getElementById('reportPreview');
    const ts = new Date().toLocaleString();
    let html = `
        <div style="text-align:center;border-bottom:3px solid #0f3460;padding-bottom:16px;margin-bottom:24px;">
            <h2 style="color:#0f3460;font-size:22px;margin-bottom:4px;">Transformer Equivalent Circuit Analysis</h2>
            <p style="color:#666;font-size:13px;">${ts}</p>
        </div>`;

    if (data.no_load) {
        const nl = data.no_load;
        html += `<h3 style="color:#0f3460;margin:20px 0 10px;">1. No-Load (Open Circuit) Test Results</h3>`;
        html += `<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr style="background:#0f3460;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Parameter</th>
                <th style="padding:8px 12px;text-align:left;">Symbol</th>
                <th style="padding:8px 12px;text-align:right;">Value</th>
                <th style="padding:8px 12px;">Unit</th>
            </tr>`;
        const nlRows = [
            ['Open-Circuit Voltage', 'V_OC', fmt(nl.V_oc, 4), 'V'],
            ['No-Load Current', 'I_0', fmt(nl.I_o, 6), 'A'],
            ['Core Loss', 'P_core', fmt(nl.P_core, 4), 'W'],
            ['No-Load Power Factor', 'cos φ₀', fmt(nl.PF_nl, 6), '—'],
            ['No-Load Angle', 'φ₀', fmt(nl.theta_nl_deg, 2), '°'],
            ['Core Loss Current', 'I_c', fmt(nl.I_c, 6), 'A'],
            ['Magnetizing Current', 'I_m', fmt(nl.I_m, 6), 'A'],
            ['Core Loss Resistance', 'R_c', fmt(nl.R_c, 2), 'Ω'],
            ['Magnetizing Reactance', 'X_m', fmt(nl.X_m, 2), 'Ω'],
            ['Apparent Power', 'S₀', fmt(nl.S_o, 4), 'VA'],
            ['Reactive Power', 'Q₀', fmt(nl.Q_o, 4), 'VAR'],
            ['Frequency', 'f', fmt(nl.frequency_Hz, 1), 'Hz'],
        ];
        nlRows.forEach(([name, sym, val, unit], i) => {
            const bg = i % 2 === 0 ? '#f8f9fa' : '#fff';
            html += `<tr style="background:${bg};border-bottom:1px solid #ddd;">
                <td style="padding:7px 12px;">${name}</td>
                <td style="padding:7px 12px;font-family:monospace;color:#555;">${sym}</td>
                <td style="padding:7px 12px;text-align:right;font-family:monospace;font-weight:600;color:#0f3460;">${val}</td>
                <td style="padding:7px 12px;color:#777;">${unit}</td>
            </tr>`;
        });
        html += `</table>`;
    }

    if (data.short_circuit) {
        const sc = data.short_circuit;
        html += `<h3 style="color:#0f3460;margin:20px 0 10px;">2. Short-Circuit Test Results</h3>`;
        html += `<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr style="background:#0f3460;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Parameter</th>
                <th style="padding:8px 12px;text-align:left;">Symbol</th>
                <th style="padding:8px 12px;text-align:right;">Value</th>
                <th style="padding:8px 12px;">Unit</th>
            </tr>`;
        const scRows = [
            ['Short-Circuit Voltage', 'V_SC', fmt(sc.V_sc, 4), 'V'],
            ['Short-Circuit Current', 'I_SC', fmt(sc.I_sc, 6), 'A'],
            ['Copper Loss', 'P_cu', fmt(sc.P_cu, 4), 'W'],
            ['SC Power Factor', 'cos φ_SC', fmt(sc.PF_sc, 6), '—'],
            ['SC Angle', 'φ_SC', fmt(sc.theta_sc_deg, 2), '°'],
            ['Equivalent Impedance', 'Z_eq', fmt(sc.Z_eq, 4), 'Ω'],
            ['Equivalent Resistance', 'R_eq', fmt(sc.R_eq, 4), 'Ω'],
            ['Equivalent Reactance', 'X_eq', fmt(sc.X_eq, 4), 'Ω'],
            ['R₁ (approx)', 'R₁', fmt(sc.R1_approx, 4), 'Ω'],
            ['X₁ (approx)', 'X₁', fmt(sc.X1_approx, 4), 'Ω'],
            ['Apparent Power', 'S_SC', fmt(sc.S_sc, 4), 'VA'],
            ['Frequency', 'f', fmt(sc.frequency_Hz, 1), 'Hz'],
        ];
        scRows.forEach(([name, sym, val, unit], i) => {
            const bg = i % 2 === 0 ? '#f8f9fa' : '#fff';
            html += `<tr style="background:${bg};border-bottom:1px solid #ddd;">
                <td style="padding:7px 12px;">${name}</td>
                <td style="padding:7px 12px;font-family:monospace;color:#555;">${sym}</td>
                <td style="padding:7px 12px;text-align:right;font-family:monospace;font-weight:600;color:#0f3460;">${val}</td>
                <td style="padding:7px 12px;color:#777;">${unit}</td>
            </tr>`;
        });
        html += `</table>`;
    }

    if (data.combined) {
        const c = data.combined;
        html += `<h3 style="color:#0f3460;margin:20px 0 10px;">3. Combined Analysis</h3>`;
        html += `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
            <tr style="background:#0f3460;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Parameter</th>
                <th style="padding:8px 12px;text-align:right;">Value</th>
                <th style="padding:8px 12px;">Unit</th>
            </tr>`;
        const cRows = [
            ['Rated Apparent Power', fmt(c.S_rated, 1), 'VA'],
            ['Total Full-Load Losses', fmt(c.total_loss_fl, 2), 'W'],
            ['Load for Max Efficiency', fmt(c.x_max_efficiency * 100, 1) + '%', 'of rated'],
            ['Maximum Efficiency (UPF)', fmt(c.max_efficiency, 2) + '%', '—'],
            ['Percent Impedance (%Z)', fmt(c.Z_percent, 2) + '%', '—'],
            ['Percent Resistance (%R)', fmt(c.R_percent, 2) + '%', '—'],
        ];
        cRows.forEach(([name, val, unit], i) => {
            const bg = i % 2 === 0 ? '#f8f9fa' : '#fff';
            html += `<tr style="background:${bg};border-bottom:1px solid #ddd;">
                <td style="padding:7px 12px;">${name}</td>
                <td style="padding:7px 12px;text-align:right;font-family:monospace;font-weight:600;color:#0f3460;">${val}</td>
                <td style="padding:7px 12px;color:#777;">${unit}</td>
            </tr>`;
        });
        html += `</table>`;

        // VR table in report preview
        html += `<h4 style="color:#0f3460;margin:16px 0 8px;">Voltage Regulation</h4>
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
            <tr style="background:#0f3460;color:#fff;">
                <th style="padding:8px 12px;">Power Factor</th>
                <th style="padding:8px 12px;text-align:right;">VR Lagging (%)</th>
                <th style="padding:8px 12px;text-align:right;">VR Leading (%)</th>
            </tr>`;
        c.voltage_regulation.forEach((vr, i) => {
            const bg = i % 2 === 0 ? '#f8f9fa' : '#fff';
            html += `<tr style="background:${bg};border-bottom:1px solid #ddd;">
                <td style="padding:7px 12px;">${vr.pf}</td>
                <td style="padding:7px 12px;text-align:right;font-family:monospace;font-weight:600;color:#0f3460;">${fmt(vr.vr_lagging, 4)}</td>
                <td style="padding:7px 12px;text-align:right;font-family:monospace;font-weight:600;color:#0f3460;">${fmt(vr.vr_leading, 4)}</td>
            </tr>`;
        });
        html += `</table>`;
    }

    if (data.harmonics) {
        if (data.harmonics.no_load) {
            const h = data.harmonics.no_load;
            html += `<h3 style="color:#0f3460;margin:20px 0 10px;">4. Harmonic Analysis — No-Load</h3>
                <p style="margin-bottom:8px;">THD Voltage: <strong>${h.thd_voltage}%</strong> &nbsp;|&nbsp; THD Current: <strong>${h.thd_current}%</strong></p>`;
        }
        if (data.harmonics.short_circuit) {
            const h = data.harmonics.short_circuit;
            html += `<h3 style="color:#0f3460;margin:20px 0 10px;">5. Harmonic Analysis — Short-Circuit</h3>
                <p style="margin-bottom:8px;">THD Voltage: <strong>${h.thd_voltage}%</strong> &nbsp;|&nbsp; THD Current: <strong>${h.thd_current}%</strong></p>`;
        }
    }

    preview.innerHTML = html;
}

// ── Export PDF (open in new window + print) ──
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
        const html = await response.text();
        const win = window.open('', '_blank');
        win.document.write(html);
        win.document.close();
        win.focus();
        setTimeout(() => win.print(), 600);
    } catch(err) { showAlert('Export failed: ' + err.message, 'error'); }
}

function printReport() { window.print(); }
