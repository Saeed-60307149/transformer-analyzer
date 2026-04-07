/* === Transformer Equivalent Circuit Analyzer — App Logic === */

let analysisResults = null;
let charts = {};

// ── File Upload Handling ──────────────────────────────────────────────────────
['nl', 'sc'].forEach(prefix => {
    const dropZone = document.getElementById(`${prefix}DropZone`);
    const fileInput = document.getElementById(`${prefix}File`);

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
    const input    = document.getElementById(`${prefix}File`);
    const info     = document.getElementById(`${prefix}FileInfo`);
    const name     = document.getElementById(`${prefix}FileName`);
    const card     = document.getElementById(`${prefix}Card`);
    const dropZone = document.getElementById(`${prefix}DropZone`);

    if (input.files.length > 0) {
        name.textContent = input.files[0].name;
        info.style.display = 'flex';
        dropZone.style.display = 'none';
        card.classList.add('has-file');
    }
}

function removeFile(prefix) {
    const input    = document.getElementById(`${prefix}File`);
    const info     = document.getElementById(`${prefix}FileInfo`);
    const card     = document.getElementById(`${prefix}Card`);
    const dropZone = document.getElementById(`${prefix}DropZone`);

    input.value = '';
    info.style.display = 'none';
    dropZone.style.display = 'block';
    card.classList.remove('has-file');
}

// ── Form Submission ───────────────────────────────────────────────────────────
document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const btn      = document.getElementById('analyzeBtn');
    const btnText  = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');

    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-flex';
    clearAlerts();
    hideResults();

    const formData = new FormData(this);

    try {
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const data = await response.json();

        if (data.error) {
            showAlert(data.error, 'error');
            return;
        }

        // Show hard validation errors — do not proceed to render
        if (data.errors && data.errors.length > 0) {
            data.errors.forEach(err => showAlert(err, 'error'));
            const allErrors = (data.errors || []).join(' ').toLowerCase();
            if (allErrors.includes('wrong slot')) {
                showAlert('💡 Tip: Files may be in the wrong upload slots — try swapping them.', 'warning');
            }
            return;
        }

        if (data.warnings && data.warnings.length > 0) {
            data.warnings.forEach(w => showAlert(w, 'warning'));
        }

        if (data.no_load || data.short_circuit) {
            analysisResults = data;
            renderResults(data);
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
        }
    } catch (err) {
        showAlert('Connection error: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btnText.style.display = 'inline-flex';
        btnLoader.style.display = 'none';
    }
});

// ── Alerts ────────────────────────────────────────────────────────────────────
function showAlert(message, type) {
    const container = document.getElementById('alertContainer');
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    el.innerHTML = `<span>${type === 'error' ? '⚠' : '✓'}</span><span>${message}</span>`;
    container.appendChild(el);
    if (type !== 'error') setTimeout(() => el.remove(), 7000);
}
function clearAlerts() { document.getElementById('alertContainer').innerHTML = ''; }
function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
    // Destroy all existing charts so canvases are clean on next render
    Object.keys(charts).forEach(k => { if (charts[k]) { charts[k].destroy(); delete charts[k]; } });
}

// ── Chart Defaults ────────────────────────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2a3548';
Chart.defaults.font.family = "'DM Sans', sans-serif";
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function fmt(val, digits) {
    if (val === null || val === undefined || (typeof val === 'number' && isNaN(val))) return '—';
    return Number(val).toFixed(digits);
}

// ── Dynamic Tab Builder ───────────────────────────────────────────────────────
// Tabs are built entirely from scratch each render — nothing is shown unless
// the corresponding data actually exists.
function buildTabs(data) {
    const tabBar    = document.getElementById('tabBar');
    const panelWrap = document.getElementById('panelWrap');
    tabBar.innerHTML    = '';
    panelWrap.innerHTML = '';

    const defs = [
        { id: 'overview',      label: 'Overview',           show: !!(data.no_load || data.short_circuit) },
        { id: 'noload',        label: 'No-Load',            show: !!data.no_load },
        { id: 'shortcircuit',  label: 'Short-Circuit',      show: !!data.short_circuit },
        { id: 'combined',      label: 'Combined',           show: !!data.combined },
        { id: 'waveforms',     label: 'Waveforms',          show: !!(data.waveforms && (data.waveforms.no_load || data.waveforms.short_circuit)) },
        { id: 'circuit',       label: 'Circuit',            show: !!(data.no_load || data.short_circuit) },
        { id: 'phasors',       label: '⚡ Phasors',         show: !!(data.no_load || data.short_circuit) },
        { id: 'report',        label: 'Report',             show: !!(data.no_load || data.short_circuit) },
    ];

    const visible = defs.filter(d => d.show);
    visible.forEach((def, idx) => {
        // Tab button
        const btn = document.createElement('button');
        btn.className = 'tab' + (idx === 0 ? ' active' : '');
        btn.dataset.tab = def.id;
        btn.textContent = def.label;
        btn.onclick = () => switchTab(def.id);
        tabBar.appendChild(btn);

        // Panel
        const panel = document.createElement('div');
        panel.className = 'tab-panel' + (idx === 0 ? ' active' : '');
        panel.id = `panel-${def.id}`;
        panelWrap.appendChild(panel);
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === `panel-${tabName}`));
    setTimeout(() => Object.values(charts).forEach(c => { if (c) c.resize(); }), 100);
}

// ── Main Render ───────────────────────────────────────────────────────────────
function renderResults(data) {
    if (!document.getElementById('resetBtn')) {
        const resetBtn = document.createElement('button');
        resetBtn.id = 'resetBtn';
        resetBtn.className = 'btn-analyze';
        resetBtn.style.cssText = 'margin:0 0 24px 0;background:var(--surface);border:1px solid var(--border);color:var(--text);box-shadow:none;';
        resetBtn.textContent = '↩ Analyze Another File';
        resetBtn.onclick = () => {
            hideResults();
            clearAlerts();
            removeFile('nl');
            removeFile('sc');
            document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
            resetBtn.remove();
        };
        document.getElementById('resultsSection').prepend(resetBtn);
    }

    buildTabs(data);
    renderOverview(data);
    if (data.no_load)       renderNoLoadTab(data);
    if (data.short_circuit) renderShortCircuitTab(data);
    if (data.combined)      renderCombinedTab(data);
    renderWaveforms(data);
    if (data.no_load || data.short_circuit) renderCircuitDiagram(data);
    if (data.no_load || data.short_circuit) renderReportPreview(data);
    renderPhasorDiagram(data);
}

// ── Helper: inject HTML into a panel ─────────────────────────────────────────
function panel(id) { return document.getElementById(`panel-${id}`); }

function chartCard(title, canvasId, extraClass) {
    return `<div class="chart-card${extraClass ? ' ' + extraClass : ''}">
                <h3>${title}</h3>
                <canvas id="${canvasId}"></canvas>
            </div>`;
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function renderOverview(data) {
    const el = panel('overview');
    if (!el) return;

    // KPI cards
    const kpis = [];
    if (data.no_load) {
        kpis.push({ label: 'Core Loss',           value: fmt(data.no_load.P_core, 2),          unit: 'W',  sub: 'No-Load Test' });
        kpis.push({ label: 'Magnetizing Reactance', value: fmt(data.no_load.X_m, 1),             unit: 'Ω',  sub: `Rc = ${fmt(data.no_load.R_c, 1)} Ω` });
        kpis.push({ label: 'No-Load Current',      value: fmt(data.no_load.I_o * 1000, 2),       unit: 'mA', sub: `PF = ${fmt(data.no_load.PF_nl, 4)}` });
    }
    if (data.short_circuit) {
        kpis.push({ label: 'Copper Loss',    value: fmt(data.short_circuit.P_cu, 2),   unit: 'W',  sub: 'Short-Circuit Test' });
        kpis.push({ label: 'Eq. Impedance',  value: fmt(data.short_circuit.Z_eq, 2),   unit: 'Ω',  sub: `Req=${fmt(data.short_circuit.R_eq, 2)}, Xeq=${fmt(data.short_circuit.X_eq, 2)}` });
        kpis.push({ label: 'SC Current',     value: fmt(data.short_circuit.I_sc * 1000, 1), unit: 'mA', sub: `PF = ${fmt(data.short_circuit.PF_sc, 4)}` });
    }
    if (data.combined) {
        kpis.push({ label: 'Max Efficiency', value: fmt(data.combined.max_efficiency, 1), unit: '%',  sub: `at ${fmt(data.combined.x_max_efficiency * 100, 0)}% load` });
        kpis.push({ label: 'Rated VA',       value: fmt(data.combined.S_rated, 1),         unit: 'VA', sub: 'Apparent Power' });
    }

    let html = `<div class="kpi-grid">${kpis.map(k => `
        <div class="kpi-card">
            <div class="kpi-label">${k.label}</div>
            <div class="kpi-value">${k.value}<span class="kpi-unit">${k.unit}</span></div>
            <div class="kpi-sub">${k.sub}</div>
        </div>`).join('')}</div><div class="charts-row">`;

    // Only include chart cards for data that exists
    if (data.combined) {
        html += chartCard('Efficiency vs Load', 'efficiencyChart') +
                chartCard('Voltage Regulation vs Power Factor', 'vrChart');
    }
    html += '</div><div class="charts-row">';
    if (data.no_load && data.short_circuit) {
        html += chartCard('Loss Distribution', 'lossChart');
    }
    if (data.short_circuit) {
        html += chartCard('Power Triangle', 'powerChart');
    }
    html += '</div>';

    el.innerHTML = html;

    // Now draw into the freshly created canvases
    if (data.combined) {
        const upf = data.combined.efficiency_data.filter(e => e.pf === 1.0);
        const pf8 = data.combined.efficiency_data.filter(e => e.pf === 0.8);
        charts['efficiency'] = new Chart(document.getElementById('efficiencyChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: upf.map(e => `${(e.load_fraction * 100).toFixed(0)}%`),
                datasets: [
                    { label: 'UPF (1.0)',   data: upf.map(e => e.efficiency), borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                    { label: '0.8 PF Lag', data: pf8.map(e => e.efficiency), borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'Efficiency (%)' } } } },
        });

        const vr = data.combined.voltage_regulation;
        charts['vr'] = new Chart(document.getElementById('vrChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: vr.map(v => v.pf),
                datasets: [
                    { label: 'Lagging', data: vr.map(v => v.vr_lagging), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Leading', data: vr.map(v => v.vr_leading), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'VR (%)' } }, x: { title: { display: true, text: 'Power Factor' } } } },
        });
    }

    if (data.no_load && data.short_circuit) {
        charts['loss'] = new Chart(document.getElementById('lossChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Core Loss (Pi)', 'Copper Loss (Pcu)'],
                datasets: [{ data: [data.no_load.P_core, data.short_circuit.P_cu], backgroundColor: ['#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 4 }],
            },
            options: { responsive: true, cutout: '60%', plugins: { legend: { position: 'bottom' } } },
        });
    }

    if (data.short_circuit) {
        const sc = data.short_circuit;
        charts['power'] = new Chart(document.getElementById('powerChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Apparent (S)', 'Real (P)', 'Reactive (Q)'],
                datasets: [{ data: [sc.S_sc, sc.P_cu, sc.Q_sc], backgroundColor: ['#818cf8', '#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 6 }],
            },
            options: { responsive: true, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: 'Power (W/VA/VAR)' } } } },
        });
    }
}

// ── No-Load Tab ───────────────────────────────────────────────────────────────
function renderNoLoadTab(data) {
    const el = panel('noload');
    if (!el) return;
    const nl = data.no_load;

    const params = [
        { name: 'Open-Circuit Voltage',  sym: 'V_OC',    val: fmt(nl.V_oc,          2), unit: 'V'   },
        { name: 'No-Load Current',       sym: 'I_0',     val: fmt(nl.I_o,           6), unit: 'A'   },
        { name: 'Core Loss',             sym: 'P_core',  val: fmt(nl.P_core,        4), unit: 'W'   },
        { name: 'Power Factor',          sym: 'cos φ₀',  val: fmt(nl.PF_nl,         6), unit: ''    },
        { name: 'Core Loss Current',     sym: 'I_c',     val: fmt(nl.I_c,           6), unit: 'A'   },
        { name: 'Magnetizing Current',   sym: 'I_m',     val: fmt(nl.I_m,           6), unit: 'A'   },
        { name: 'Core Resistance',       sym: 'R_c',     val: fmt(nl.R_c,           2), unit: 'Ω'   },
        { name: 'Magnetizing Reactance', sym: 'X_m',     val: fmt(nl.X_m,           2), unit: 'Ω'   },
        { name: 'Apparent Power',        sym: 'S₀',      val: fmt(nl.S_o,           4), unit: 'VA'  },
        { name: 'Reactive Power',        sym: 'Q₀',      val: fmt(nl.Q_o,           4), unit: 'VAR' },
        { name: 'No-Load Angle',         sym: 'φ₀',      val: fmt(nl.theta_nl_deg,  2), unit: '°'   },
        { name: 'Frequency',             sym: 'f',       val: fmt(nl.frequency_Hz,  1), unit: 'Hz'  },
    ];

    const nlConf = (nl.confidence) ? confidenceBadge(nl.confidence) : '';
    let html = `<h2 style="margin-bottom:20px;font-family:var(--font-display);font-size:28px;">No-Load Test Results ${nlConf}</h2>
    <div class="params-grid">${params.map(p => `
        <div class="param-card">
            <div><div class="param-name">${p.name}</div><div class="param-symbol">${p.sym}</div></div>
            <div><span class="param-val">${p.val}</span><span class="param-unit">${p.unit}</span></div>
        </div>`).join('')}</div>`;

    // Charts — only inject the cards we can actually fill
    const hasHarmonics = data.harmonics && data.harmonics.no_load;
    html += '<div class="charts-row">';
    if (hasHarmonics) html += chartCard('No-Load Voltage & Current Harmonics', 'nlHarmonicChart', 'full-width');
    html += '</div><div class="charts-row">';
    html += chartCard('No-Load Current Phasor', 'nlPhasorChart');
    html += chartCard('No-Load Power Breakdown', 'nlPowerBreakdown');
    html += '</div>';

    el.innerHTML = html;

    if (hasHarmonics) {
        const h = data.harmonics.no_load;
        charts['nlHarmonic'] = new Chart(document.getElementById('nlHarmonicChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: h.current_harmonics.map(x => `H${x.harmonic}`),
                datasets: [
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: `THD_V: ${h.thd_voltage}%  |  THD_I: ${h.thd_current}%` } }, scales: { y: { title: { display: true, text: '% of Fundamental' } } } },
        });
    }

    charts['nlPhasor'] = new Chart(document.getElementById('nlPhasorChart').getContext('2d'), {
        type: 'polarArea',
        data: {
            labels: ['I_c (Core Loss)', 'I_m (Magnetizing)', 'I_0 (Total)'],
            datasets: [{ data: [nl.I_c * 1000, nl.I_m * 1000, nl.I_o * 1000], backgroundColor: ['rgba(56,189,248,0.5)', 'rgba(129,140,248,0.5)', 'rgba(52,211,153,0.5)'] }],
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' }, title: { display: true, text: 'Current Components (mA)' } } },
    });

    charts['nlPowerBD'] = new Chart(document.getElementById('nlPowerBreakdown').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Real Power P₀', 'Reactive Power Q₀'],
            datasets: [{ data: [nl.P_core, nl.Q_o], backgroundColor: ['#38bdf8', '#818cf8'], borderWidth: 0 }],
        },
        options: { responsive: true, cutout: '55%', plugins: { legend: { position: 'bottom' } } },
    });
}

// ── Short-Circuit Tab ─────────────────────────────────────────────────────────
function renderShortCircuitTab(data) {
    const el = panel('shortcircuit');
    if (!el) return;
    const sc = data.short_circuit;

    const params = [
        { name: 'SC Voltage',           sym: 'V_SC',      val: fmt(sc.V_sc,         4), unit: 'V'   },
        { name: 'SC Current',           sym: 'I_SC',      val: fmt(sc.I_sc,         6), unit: 'A'   },
        { name: 'Copper Loss',          sym: 'P_cu',      val: fmt(sc.P_cu,         4), unit: 'W'   },
        { name: 'Power Factor',         sym: 'cos φ_SC',  val: fmt(sc.PF_sc,        6), unit: ''    },
        { name: 'Eq. Impedance',        sym: 'Z_eq',      val: fmt(sc.Z_eq,         4), unit: 'Ω'   },
        { name: 'Eq. Resistance',       sym: 'R_eq',      val: fmt(sc.R_eq,         4), unit: 'Ω'   },
        { name: 'Eq. Reactance',        sym: 'X_eq',      val: fmt(sc.X_eq,         4), unit: 'Ω'   },
        { name: 'R₁ (approx)',          sym: 'R₁',        val: fmt(sc.R1_approx,    4), unit: 'Ω'   },
        { name: 'X₁ (approx)',          sym: 'X₁',        val: fmt(sc.X1_approx,    4), unit: 'Ω'   },
        { name: 'Apparent Power',       sym: 'S_SC',      val: fmt(sc.S_sc,         4), unit: 'VA'  },
        { name: 'SC Angle',             sym: 'φ_SC',      val: fmt(sc.theta_sc_deg, 2), unit: '°'   },
        { name: 'Frequency',            sym: 'f',         val: fmt(sc.frequency_Hz, 1), unit: 'Hz'  },
    ];

    const scConf = (sc.confidence) ? confidenceBadge(sc.confidence) : '';
    let html = `<h2 style="margin-bottom:20px;font-family:var(--font-display);font-size:28px;">Short-Circuit Test Results ${scConf}</h2>
    <div class="params-grid">${params.map(p => `
        <div class="param-card">
            <div><div class="param-name">${p.name}</div><div class="param-symbol">${p.sym}</div></div>
            <div><span class="param-val">${p.val}</span><span class="param-unit">${p.unit}</span></div>
        </div>`).join('')}</div>`;

    const hasHarmonics = data.harmonics && data.harmonics.short_circuit;
    html += '<div class="charts-row">';
    if (hasHarmonics) html += chartCard('Short-Circuit Voltage & Current Harmonics', 'scHarmonicChart', 'full-width');
    html += '</div><div class="charts-row">';
    html += chartCard('Impedance Triangle', 'scImpedanceChart');
    html += chartCard('SC Power Breakdown', 'scPowerBreakdown');
    html += '</div>';

    el.innerHTML = html;

    if (hasHarmonics) {
        const h = data.harmonics.short_circuit;
        charts['scHarmonic'] = new Chart(document.getElementById('scHarmonicChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: h.current_harmonics.map(x => `H${x.harmonic}`),
                datasets: [
                    { label: 'Voltage (%)', data: h.voltage_harmonics.map(x => x.percent), backgroundColor: 'rgba(56,189,248,0.6)', borderRadius: 4 },
                    { label: 'Current (%)', data: h.current_harmonics.map(x => x.percent), backgroundColor: 'rgba(244,114,182,0.6)', borderRadius: 4 },
                ],
            },
            options: { responsive: true, plugins: { legend: { position: 'top' }, title: { display: true, text: `THD_V: ${h.thd_voltage}%  |  THD_I: ${h.thd_current}%` } }, scales: { y: { title: { display: true, text: '% of Fundamental' } } } },
        });
    }

    charts['scImpedance'] = new Chart(document.getElementById('scImpedanceChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Z_eq', 'R_eq', 'X_eq'],
            datasets: [{ data: [sc.Z_eq, sc.R_eq, sc.X_eq], backgroundColor: ['#818cf8', '#38bdf8', '#f472b6'], borderWidth: 0, borderRadius: 6 }],
        },
        options: { responsive: true, plugins: { legend: { display: false }, title: { display: true, text: 'Impedance Components (Ω)' } } },
    });

    charts['scPowerBD'] = new Chart(document.getElementById('scPowerBreakdown').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Real (P_cu)', 'Reactive (Q_SC)'],
            datasets: [{ data: [sc.P_cu, sc.Q_sc], backgroundColor: ['#f472b6', '#818cf8'], borderWidth: 0 }],
        },
        options: { responsive: true, cutout: '55%', plugins: { legend: { position: 'bottom' } } },
    });
}

// ── Combined Tab ──────────────────────────────────────────────────────────────
function renderCombinedTab(data) {
    const el = panel('combined');
    if (!el) return;
    const c  = data.combined;
    const nl = data.no_load;
    const sc = data.short_circuit;

    let html = `<div class="combined-summary">
        <h3>Equivalent Circuit Summary</h3>
        <div class="kpi-grid" style="margin-top:16px">
            <div class="kpi-card"><div class="kpi-label">Rated VA</div><div class="kpi-value">${fmt(c.S_rated, 1)}<span class="kpi-unit">VA</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Total FL Losses</div><div class="kpi-value">${fmt(c.total_loss_fl, 2)}<span class="kpi-unit">W</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency Load</div><div class="kpi-value">${fmt(c.x_max_efficiency * 100, 1)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">Max Efficiency</div><div class="kpi-value">${fmt(c.max_efficiency, 2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%Z</div><div class="kpi-value">${fmt(c.Z_percent, 2)}<span class="kpi-unit">%</span></div></div>
            <div class="kpi-card"><div class="kpi-label">%R</div><div class="kpi-value">${fmt(c.R_percent, 2)}<span class="kpi-unit">%</span></div></div>
        </div>
    </div>`;
    html += '<div class="charts-row">' + chartCard('Efficiency Curves (UPF & 0.8 PF)', 'combinedEffChart', 'full-width') + '</div>';
    html += '<div class="data-tables" id="combinedTables"></div>';
    el.innerHTML = html;

    // Smooth efficiency curve
    const loadPoints = [], effUPF = [], effPF8 = [];
    for (let x = 0.1; x <= 1.3; x += 0.05) {
        loadPoints.push(`${(x * 100).toFixed(0)}%`);
        const pcu = x * x * sc.P_cu;
        const p1  = x * c.S_rated * 1.0;
        const p2  = x * c.S_rated * 0.8;
        effUPF.push(p1 / (p1 + nl.P_core + pcu) * 100);
        effPF8.push(p2 / (p2 + nl.P_core + pcu) * 100);
    }
    charts['combinedEff'] = new Chart(document.getElementById('combinedEffChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: loadPoints,
            datasets: [
                { label: 'Unity PF',       data: effUPF, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.08)', fill: true, tension: 0.4, pointRadius: 0 },
                { label: '0.8 PF Lagging', data: effPF8, borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.08)', fill: true, tension: 0.4, pointRadius: 0 },
            ],
        },
        options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { title: { display: true, text: 'Efficiency (%)' }, min: 0 }, x: { title: { display: true, text: 'Load (% of Rated)' } } } },
    });

    let tables = `<div class="data-table-wrap"><h3>Voltage Regulation</h3><table>
        <tr><th>Power Factor</th><th>VR Lagging (%)</th><th>VR Leading (%)</th></tr>`;
    c.voltage_regulation.forEach(vr => {
        tables += `<tr><td>${vr.pf}</td><td>${fmt(vr.vr_lagging, 4)}</td><td>${fmt(vr.vr_leading, 4)}</td></tr>`;
    });
    tables += `</table></div><div class="data-table-wrap"><h3>Efficiency at Various Loads</h3><table>
        <tr><th>Load</th><th>PF</th><th>P_out (W)</th><th>P_cu (W)</th><th>P_core (W)</th><th>η (%)</th></tr>`;
    c.efficiency_data.forEach(e => {
        tables += `<tr><td>${fmt(e.load_fraction * 100, 0)}%</td><td>${e.pf}</td><td>${fmt(e.P_out, 2)}</td><td>${fmt(e.P_cu, 4)}</td><td>${fmt(e.P_core, 4)}</td><td>${fmt(e.efficiency, 2)}</td></tr>`;
    });
    tables += '</table></div>';
    document.getElementById('combinedTables').innerHTML = tables;
}

// ── Waveforms Tab ─────────────────────────────────────────────────────────────
function renderWaveforms(data) {
    const el = panel('waveforms');
    if (!el || !data.waveforms) return;

    let html = '';
    if (data.waveforms.no_load)       html += '<div class="charts-row">' + chartCard('No-Load Waveforms',       'nlWaveformChart',  'full-width') + '</div>';
    if (data.waveforms.short_circuit) html += '<div class="charts-row">' + chartCard('Short-Circuit Waveforms', 'scWaveformChart', 'full-width') + '</div>';
    el.innerHTML = html;

    function waveChart(id, w, key) {
        charts[key] = new Chart(document.getElementById(id).getContext('2d'), {
            type: 'line',
            data: {
                labels: w.time,
                datasets: [
                    { label: 'Voltage (V)', data: w.voltage, borderColor: '#38bdf8', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y' },
                    { label: 'Current (A)', data: w.current, borderColor: '#f472b6', borderWidth: 1.5, pointRadius: 0, yAxisID: 'y1' },
                ],
            },
            options: {
                responsive: true, interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top' } },
                scales: {
                    x:  { title: { display: true, text: 'Time (ms)' }, ticks: { maxTicksLimit: 20 } },
                    y:  { title: { display: true, text: 'Voltage (V)' }, position: 'left' },
                    y1: { title: { display: true, text: 'Current (A)' }, position: 'right', grid: { drawOnChartArea: false } },
                },
            },
        });
    }

    if (data.waveforms.no_load)       waveChart('nlWaveformChart',  data.waveforms.no_load,       'nlWave');
    if (data.waveforms.short_circuit) waveChart('scWaveformChart', data.waveforms.short_circuit, 'scWave');
}

// ── Circuit Diagram ───────────────────────────────────────────────────────────
function renderCircuitDiagram(data) {
    const el = panel('circuit');
    if (!el) return;
    const nl = data.no_load     || {};
    const sc = data.short_circuit || {};

    const R1  = sc.R1_approx != null ? fmt(sc.R1_approx, 2) : '?';
    const X1  = sc.X1_approx != null ? fmt(sc.X1_approx, 2) : '?';
    const R2  = sc.R2_approx != null ? fmt(sc.R2_approx, 2) : '?';
    const X2  = sc.X2_approx != null ? fmt(sc.X2_approx, 2) : '?';
    const Rc  = nl.R_c  != null ? fmt(nl.R_c,  1) : '?';
    const Xm  = nl.X_m  != null ? fmt(nl.X_m,  1) : '?';

    el.innerHTML = `
        <h3 style="font-family:var(--font-display);font-size:22px;margin-bottom:24px;">Approximate Equivalent Circuit (Referred to Primary)</h3>
        <svg viewBox="0 0 800 340" xmlns="http://www.w3.org/2000/svg" style="max-width:750px;">
            <defs><marker id="arrC" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#38bdf8"/></marker></defs>
            <line x1="40" y1="80" x2="120" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="120" y="68" width="80" height="24" rx="3" fill="none" stroke="#38bdf8" stroke-width="2"/>
            <text x="160" y="84" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">R₁=${R1}Ω</text>
            <line x1="200" y1="80" x2="240" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="240" y="68" width="80" height="24" rx="3" fill="none" stroke="#818cf8" stroke-width="2"/>
            <text x="280" y="84" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono" font-size="12">X₁=${X1}Ω</text>
            <line x1="320" y1="80" x2="380" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <circle cx="380" cy="80" r="3" fill="#94a3b8"/>
            <line x1="380" y1="80" x2="380" y2="120" stroke="#94a3b8" stroke-width="2"/>
            <rect x="355" y="120" width="50" height="60" rx="3" fill="none" stroke="#34d399" stroke-width="2"/>
            <text x="380" y="148" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono" font-size="11">Rc</text>
            <text x="380" y="164" text-anchor="middle" fill="#34d399" font-family="IBM Plex Mono" font-size="10">${Rc}Ω</text>
            <line x1="380" y1="180" x2="380" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="380" y1="80" x2="480" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <circle cx="480" cy="80" r="3" fill="#94a3b8"/>
            <line x1="480" y1="80" x2="480" y2="120" stroke="#94a3b8" stroke-width="2"/>
            <rect x="455" y="120" width="50" height="60" rx="3" fill="none" stroke="#fbbf24" stroke-width="2"/>
            <text x="480" y="148" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono" font-size="11">Xm</text>
            <text x="480" y="164" text-anchor="middle" fill="#fbbf24" font-family="IBM Plex Mono" font-size="10">${Xm}Ω</text>
            <line x1="480" y1="180" x2="480" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="480" y1="80" x2="520" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="520" y="68" width="80" height="24" rx="3" fill="none" stroke="#38bdf8" stroke-width="2"/>
            <text x="560" y="84" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">R₂'=${R2}Ω</text>
            <line x1="600" y1="80" x2="620" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <rect x="620" y="68" width="80" height="24" rx="3" fill="none" stroke="#818cf8" stroke-width="2"/>
            <text x="660" y="84" text-anchor="middle" fill="#818cf8" font-family="IBM Plex Mono" font-size="12">X₂'=${X2}Ω</text>
            <line x1="700" y1="80" x2="760" y2="80" stroke="#94a3b8" stroke-width="2"/>
            <line x1="40" y1="260" x2="760" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="40" y1="80" x2="40" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <line x1="760" y1="80" x2="760" y2="260" stroke="#94a3b8" stroke-width="2"/>
            <text x="20" y="170" text-anchor="middle" fill="#94a3b8" font-size="14" font-weight="600" transform="rotate(-90,20,170)">V₁ (Primary)</text>
            <text x="780" y="170" text-anchor="middle" fill="#94a3b8" font-size="14" font-weight="600" transform="rotate(90,780,170)">V₂' (Secondary)</text>
            <line x1="60" y1="68" x2="100" y2="68" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arrC)"/>
            <text x="80" y="62" text-anchor="middle" fill="#38bdf8" font-size="11">I₁</text>
            <line x1="720" y1="68" x2="740" y2="68" stroke="#38bdf8" stroke-width="1.5" marker-end="url(#arrC)"/>
            <text x="730" y="62" text-anchor="middle" fill="#38bdf8" font-size="11">I₂'</text>
            <text x="370" y="105" text-anchor="end" fill="#34d399" font-size="10">Ic↓</text>
            <text x="495" y="105" text-anchor="start" fill="#fbbf24" font-size="10">Im↓</text>
            <rect x="160" y="290" width="480" height="35" rx="6" fill="rgba(56,189,248,0.08)" stroke="rgba(56,189,248,0.2)" stroke-width="1"/>
            <text x="400" y="312" text-anchor="middle" fill="#38bdf8" font-family="IBM Plex Mono" font-size="12">
                Zeq = ${sc.Z_eq != null ? fmt(sc.Z_eq, 2) : '?'}Ω  |  Req = ${sc.R_eq != null ? fmt(sc.R_eq, 2) : '?'}Ω  |  Xeq = ${sc.X_eq != null ? fmt(sc.X_eq, 2) : '?'}Ω
            </text>
        </svg>`;
}

// ── Report Preview ────────────────────────────────────────────────────────────
function renderReportPreview(data) {
    const el = panel('report');
    if (!el) return;

    const nl  = data.no_load       || {};
    const sc  = data.short_circuit || {};
    const c   = data.combined      || {};
    const har = data.harmonics     || {};

    // Helper: render a compact param row
    const row = (label, value, unit = '') => `
        <div class="rp-row">
            <span class="rp-label">${label}</span>
            <span class="rp-value">${value}${unit ? '<span class="rp-unit"> '+unit+'</span>' : ''}</span>
        </div>`;

    // Build section blocks
    let sections = '';

    if (data.no_load) {
        const nlConf = data.no_load.confidence;
        const badge  = nlConf ? `<span class="rp-conf" style="background:${nlConf.color}22;border-color:${nlConf.color}55;color:${nlConf.color}">${nlConf.icon} ${nlConf.label}</span>` : '';
        sections += `<div class="rp-section">
            <div class="rp-section-head"><span class="rp-section-tag nl">OC</span> No-Load Test ${badge}</div>
            ${row('V<sub>OC</sub>', fmt(nl.V_oc, 3), 'V')}
            ${row('I₀', fmt(nl.I_o, 4), 'A')}
            ${row('P<sub>core</sub>', fmt(nl.P_core, 3), 'W')}
            ${row('cos φ₀', fmt(nl.PF_nl, 4))}
            ${row('R<sub>c</sub>', fmt(nl.R_c, 2), 'Ω')}
            ${row('X<sub>m</sub>', fmt(nl.X_m, 2), 'Ω')}
            ${row('f', fmt(nl.frequency_Hz, 1), 'Hz')}
        </div>`;
    }

    if (data.short_circuit) {
        const scConf = data.short_circuit.confidence;
        const badge  = scConf ? `<span class="rp-conf" style="background:${scConf.color}22;border-color:${scConf.color}55;color:${scConf.color}">${scConf.icon} ${scConf.label}</span>` : '';
        sections += `<div class="rp-section">
            <div class="rp-section-head"><span class="rp-section-tag sc">SC</span> Short-Circuit Test ${badge}</div>
            ${row('V<sub>SC</sub>', fmt(sc.V_sc, 3), 'V')}
            ${row('I<sub>SC</sub>', fmt(sc.I_sc, 4), 'A')}
            ${row('P<sub>cu</sub>', fmt(sc.P_cu, 3), 'W')}
            ${row('cos φ<sub>SC</sub>', fmt(sc.PF_sc, 4))}
            ${row('Z<sub>eq</sub>', fmt(sc.Z_eq, 4), 'Ω')}
            ${row('R<sub>eq</sub>', fmt(sc.R_eq, 4), 'Ω')}
            ${row('X<sub>eq</sub>', fmt(sc.X_eq, 4), 'Ω')}
        </div>`;
    }

    if (data.combined) {
        const eff  = c.max_efficiency   != null ? fmt(c.max_efficiency, 2) + '%' : '—';
        const xmax = c.x_max_efficiency != null ? fmt(c.x_max_efficiency * 100, 1) + '%' : '—';
        const zp   = c.Z_percent        != null ? fmt(c.Z_percent, 2) + '%'       : '—';
        sections += `<div class="rp-section">
            <div class="rp-section-head"><span class="rp-section-tag comb">∑</span> Combined Analysis</div>
            ${row('S<sub>rated</sub>', fmt(c.S_rated, 1), 'VA')}
            ${row('η<sub>max</sub> (UPF)', eff)}
            ${row('Load @ η<sub>max</sub>', xmax)}
            ${row('%Z', zp)}
            ${row('Total losses (FL)', fmt(c.total_loss_fl, 3), 'W')}
        </div>`;
    }

    if (har.no_load || har.short_circuit) {
        let hrows = '';
        if (har.no_load)       hrows += row('THD<sub>V</sub> (OC)', har.no_load.thd_voltage + '%') + row('THD<sub>I</sub> (OC)', har.no_load.thd_current + '%');
        if (har.short_circuit) hrows += row('THD<sub>V</sub> (SC)', har.short_circuit.thd_voltage + '%') + row('THD<sub>I</sub> (SC)', har.short_circuit.thd_current + '%');
        sections += `<div class="rp-section">
            <div class="rp-section-head"><span class="rp-section-tag har">∿</span> Harmonic Analysis</div>
            ${hrows}
        </div>`;
    }

    el.innerHTML = `
        <div class="rp-hero">
            <div class="rp-hero-text">
                <p class="rp-hero-title">Analysis Report</p>
                <p class="rp-hero-sub">IEEE-standard parameter extraction · ${new Date().toLocaleDateString()}</p>
            </div>
            <button class="btn-export rp-export-btn" onclick="exportReport()">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18"><path d="M12 3v12m0 0l-4-4m4 4l4-4M5 17v2a2 2 0 002 2h10a2 2 0 002-2v-2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                Export PDF
            </button>
        </div>
        <div class="rp-grid">${sections}</div>`;
}

// ── Export / Print ────────────────────────────────────────────────────────────
async function exportReport() {
    if (!analysisResults) return;
    try {
        const response = await fetch('/export-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                no_load:       analysisResults.no_load,
                short_circuit: analysisResults.short_circuit,
                combined:      analysisResults.combined,
                nl_harmonics:  analysisResults.harmonics?.no_load,
                sc_harmonics:  analysisResults.harmonics?.short_circuit,
            }),
        });
        const html = await response.text();
        const win  = window.open('', '_blank');
        win.document.write(html);
        win.document.close();
        win.focus();
        setTimeout(() => win.print(), 600);
    } catch (err) { showAlert('Export failed: ' + err.message, 'error'); }
}

// ── Confidence Badge ──────────────────────────────────────────────────────────
function confidenceBadge(conf) {
    if (!conf) return '';
    const tip = conf.reasons && conf.reasons.length
        ? conf.reasons.join('; ')
        : 'All quality checks passed';
    return `<span class="conf-badge" style="
        display:inline-flex;align-items:center;gap:5px;
        background:${conf.color}22;border:1px solid ${conf.color}55;
        color:${conf.color};border-radius:20px;
        padding:3px 10px;font-size:11px;font-weight:600;
        cursor:help;margin-left:8px;"
        title="${tip}">
        ${conf.icon} ${conf.label} (${conf.score}%)
    </span>`;
}


// ── Animated Phasor Diagram ───────────────────────────────────────────────────
function renderPhasorDiagram(data) {
    const el = panel('phasors');
    if (!el) return;

    const datasets = [];
    if (data.no_load) {
        datasets.push({
            label: 'No-Load',
            pf: data.no_load.PF_nl,
            vMag: Math.min(data.no_load.V_oc || 1, 9999),
            iMag: (data.no_load.I_o || 0.001) * 1000,
        });
    }
    if (data.short_circuit) {
        datasets.push({
            label: 'Short-Circuit',
            pf: data.short_circuit.PF_sc,
            vMag: data.short_circuit.V_sc || 1,
            iMag: (data.short_circuit.I_sc || 0.001) * 10,
        });
    }

    let activeIdx = 0;
    let animating = true;
    let animFrame = null;
    let t = 0;

    el.innerHTML = `
        <div style="text-align:center;padding:20px;">
            <h3 style="margin-bottom:16px;font-family:var(--font-display);font-size:22px;">
                Animated Phasor Diagram
            </h3>
            ${datasets.length > 1 ? `
            <div style="display:flex;justify-content:center;gap:10px;margin-bottom:16px;">
                ${datasets.map((d,i) => `
                <button class="phasor-toggle ${i===0?'active':''}" data-idx="${i}"
                    style="padding:6px 18px;border-radius:8px;border:1px solid var(--border);
                    background:${i===0?'var(--accent)':'var(--surface)'};
                    color:${i===0?'#fff':'var(--text-dim)'};cursor:pointer;font-size:13px;">
                    ${d.label}
                </button>`).join('')}
            </div>` : ''}
            <canvas id="phasorCanvas" width="480" height="480"
                style="border-radius:50%;background:#0a0e1a;max-width:100%;"></canvas>
            <div style="margin-top:16px;display:flex;justify-content:center;gap:12px;align-items:center;">
                <button id="phasorPlayPause"
                    style="padding:8px 24px;border-radius:8px;
                    background:var(--accent);color:#fff;border:none;
                    font-size:14px;cursor:pointer;">⏸ Pause</button>
                <span style="font-size:13px;color:var(--text-muted);" id="phasorAngleDisplay"></span>
            </div>
        </div>`;

    const canvas = document.getElementById('phasorCanvas');
    const ctx = canvas.getContext('2d');
    const cx = 240, cy = 240, R = 170;

    el.querySelectorAll('.phasor-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            activeIdx = parseInt(btn.dataset.idx);
            el.querySelectorAll('.phasor-toggle').forEach((b, i) => {
                b.style.background = i === activeIdx ? 'var(--accent)' : 'var(--surface)';
                b.style.color = i === activeIdx ? '#fff' : 'var(--text-dim)';
            });
        });
    });

    document.getElementById('phasorPlayPause').onclick = () => {
        animating = !animating;
        document.getElementById('phasorPlayPause').textContent = animating ? '⏸ Pause' : '▶ Play';
        if (animating) draw();
    };

    function draw() {
        if (!animating) return;
        const ds = datasets[activeIdx];
        const phiV = t;
        const phi  = Math.acos(Math.max(-1, Math.min(1, ds.pf)));
        const phiI = t - phi;

        ctx.clearRect(0, 0, 480, 480);

        ctx.fillStyle = '#0a0e1a';
        ctx.beginPath();
        ctx.arc(cx, cy, R + 30, 0, Math.PI * 2);
        ctx.fill();

        [0.33, 0.66, 1.0].forEach(f => {
            ctx.beginPath();
            ctx.arc(cx, cy, R * f, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(255,255,255,0.06)';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        ctx.strokeStyle = 'rgba(255,255,255,0.15)';
        ctx.setLineDash([4, 6]);
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(cx - R - 20, cy); ctx.lineTo(cx + R + 20, cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx, cy - R - 20); ctx.lineTo(cx, cy + R + 20); ctx.stroke();
        ctx.setLineDash([]);

        // Voltage phasor
        const vx = cx + R * Math.cos(phiV);
        const vy = cy - R * Math.sin(phiV);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(vx, vy);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 3;
        ctx.stroke();
        const avAngle = Math.atan2(cy - vy, vx - cx);
        ctx.beginPath();
        ctx.moveTo(vx, vy);
        ctx.lineTo(vx - 14 * Math.cos(avAngle - 0.4), vy + 14 * Math.sin(avAngle - 0.4));
        ctx.lineTo(vx - 14 * Math.cos(avAngle + 0.4), vy + 14 * Math.sin(avAngle + 0.4));
        ctx.closePath();
        ctx.fillStyle = '#38bdf8';
        ctx.fill();
        ctx.fillStyle = '#38bdf8';
        ctx.font = 'bold 14px DM Sans, sans-serif';
        ctx.fillText('V', vx + 10, vy - 6);

        // Current phasor
        const iScale = 0.65;
        const ix = cx + R * iScale * Math.cos(phiI);
        const iy = cy - R * iScale * Math.sin(phiI);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(ix, iy);
        ctx.strokeStyle = '#f472b6';
        ctx.lineWidth = 3;
        ctx.stroke();
        const aiAngle = Math.atan2(cy - iy, ix - cx);
        ctx.beginPath();
        ctx.moveTo(ix, iy);
        ctx.lineTo(ix - 14 * Math.cos(aiAngle - 0.4), iy + 14 * Math.sin(aiAngle - 0.4));
        ctx.lineTo(ix - 14 * Math.cos(aiAngle + 0.4), iy + 14 * Math.sin(aiAngle + 0.4));
        ctx.closePath();
        ctx.fillStyle = '#f472b6';
        ctx.fill();
        ctx.fillStyle = '#f472b6';
        ctx.font = 'bold 14px DM Sans, sans-serif';
        ctx.fillText('I', ix + 10, iy - 6);

        // Phase angle arc
        ctx.beginPath();
        ctx.arc(cx, cy, 50, -phiI, -phiV, phiI > phiV);
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#fbbf24';
        ctx.font = '12px DM Sans, sans-serif';
        ctx.fillText(`φ=${(phi * 180 / Math.PI).toFixed(1)}°`,
            cx + 60 * Math.cos(-(phiV + phiI) / 2) - 10,
            cy - 60 * Math.sin(-(phiV + phiI) / 2)
        );

        ctx.fillStyle = 'rgba(255,255,255,0.6)';
        ctx.font = '13px DM Sans, sans-serif';
        ctx.fillText(`PF = ${ds.pf.toFixed(4)}  |  ${ds.label}`, cx - 70, 30);

        const angleEl = document.getElementById('phasorAngleDisplay');
        if (angleEl) angleEl.textContent = `Phase angle: ${(phi * 180 / Math.PI).toFixed(2)}°`;

        t += 0.025;
        animFrame = requestAnimationFrame(draw);
    }

    draw();

    const observer = new MutationObserver(() => {
        const isActive = el.classList.contains('active');
        if (!isActive && animFrame) {
            cancelAnimationFrame(animFrame);
            animating = false;
            const btn = document.getElementById('phasorPlayPause');
            if (btn) btn.textContent = '▶ Play';
        }
    });
    observer.observe(el, { attributes: true, attributeFilter: ['class'] });
}

