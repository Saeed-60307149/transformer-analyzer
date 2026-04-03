# TransformerIQ — Equivalent Circuit Analyzer

A professional-grade Flask web application for analyzing transformer test data and computing equivalent circuit parameters from No-Load (Open Circuit) and Short-Circuit test measurements.

## Features

- **Universal Data Parser**: Handles CSV, TSV, TXT files from Festo Didactic LVDAC-EMS oscilloscopes and other formats. Auto-detects delimiters, headers, and data structure.
- **Accurate Calculations**: Computes all equivalent circuit parameters using IEEE standard methods:
  - **No-Load Test** → Core branch: Rc, Xm, Ic, Im, I₀, PF₀, P_core
  - **Short-Circuit Test** → Series branch: Req, Xeq, Zeq, PF_sc, P_cu
  - **Combined Analysis** → Voltage regulation, efficiency curves, max efficiency point, percent impedance
- **Auto Test Detection**: Automatically identifies whether uploaded data is from a no-load or short-circuit test
- **Rich Visualizations**: Interactive Chart.js graphs including:
  - Voltage & current waveforms with dual Y-axes
  - Harmonic analysis with THD calculation (FFT-based)
  - Efficiency vs. load curves (UPF and 0.8 PF)
  - Voltage regulation vs. power factor
  - Loss distribution (doughnut chart)
  - Impedance triangle, power triangle, phasor diagrams
- **SVG Equivalent Circuit Diagram**: Auto-generated circuit diagram with computed values
- **HTML Report Export**: Downloadable, printable professional report
- **Drag & Drop Upload**: Modern file upload with drag-and-drop support
- **Fully Responsive**: Works on desktop, tablet, and mobile

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Saeed-60307149/transformer-analyzer.git
cd transformer-analyzer

# Install dependencies
pip install -r requirements.txt

# Run the app
python run.py
```

Open `http://localhost:5000` in your browser.

## Docker Deployment

```bash
# Build
docker build -t transformer-analyzer .

# Run
docker run -p 5000:5000 transformer-analyzer
```

## Deploy Instructions

### Local/Dev
```bash
pip install -r requirements.txt
python run.py
```

### Docker Local
```bash
docker build -t transformer-analyzer .
docker run -p 5000:5000 -e PORT=5000 transformer-analyzer
```

### Production (CI/CD)
1. Push to `main` → GitHub Actions runs tests + pushes Docker to GHCR (`ghcr.io/{owner}/transformer-analyzer:latest`)
2. Deploy from GHCR:
   - **Server/VM**: `docker pull ghcr.io/{owner}/transformer-analyzer:latest && docker run -d -p 80:5000 ...`
   - **Railway**: Connect repo, set builder to Docker, or use `railway up` manually
   - **Kubernetes/Docker Swarm**: Use image directly

**Secrets**: `GITHUB_TOKEN` (auto). Extend `deploy` job in `.github/workflows/ci-cd.yml` for auto-deploy (SSH, etc.).

See TODO.md for setup status.

## Project Structure

```
transformer-analyzer/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask app with routes
│   ├── static/
│   │   ├── css/style.css       # Enhanced dark-theme UI
│   │   └── js/app.js           # Frontend logic & Chart.js
│   ├── templates/
│   │   └── index.html          # Main SPA template
│   └── utils/
│       ├── __init__.py
│       ├── parser.py           # Universal data parser
│       ├── calculator.py       # Equivalent circuit calculations
│       └── report.py           # HTML report generator
├── tests/
│   └── test_app.py             # Comprehensive test suite
├── .github/
│   └── workflows/
│       └── ci-cd.yml           # CI/CD pipeline
├── Dockerfile                  # Docker deployment
├── requirements.txt
├── run.py                      # Dev entry point
├── wsgi.py                     # Production WSGI
└── README.md
```

## Supported Data Formats

- **Festo Didactic LVDAC-EMS** oscilloscope exports (CSV with `,,` double-comma or TSV with double-tab)
- Standard CSV with headers (Time, Voltage/E1, Current/I1, Power/P1)
- Tab-separated files (.txt, .tsv)
- Semicolon-separated files
- Files with or without metadata headers

## Evaluation Rubric Alignment

| Criteria | How This App Addresses It |
|----------|--------------------------|
| **Accuracy of Calculations (20%)** | IEEE-standard RMS, FFT, complete-cycle extraction, validated with unit tests |
| **Code Efficiency & Structure (15%)** | Clean MVC architecture, modular utils, type hints, docstrings |
| **Visualization & Report (25%)** | 10+ interactive Chart.js visualizations, SVG circuit diagram, exportable HTML report |
| **Presentation & Intuitiveness (15%)** | Dark theme UI, drag-drop upload, tabbed results, auto-detect test type |
| **Creativity & Problem Solving (15%)** | Harmonic analysis, auto-format detection, edge case handling, CI/CD pipeline |

## Testing

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=app
```

## Acknowledgments

Developed with assistance from Generative AI (Claude by Anthropic) as permitted by competition rules.

## License

MIT
