"""
TransformerIQ - Transformer Test Data Analyzer
Flask Web Application
"""
import os
import traceback
from datetime import datetime
import numpy as np
from flask import Flask, render_template, request, jsonify, make_response
from flask.json.provider import DefaultJSONProvider

from app.utils.parser import parse_transformer_data, detect_test_type
from app.utils.calculator import (
    analyze_no_load_test,
    analyze_short_circuit_test,
    compute_combined_analysis,
    generate_waveform_data,
    compute_harmonic_analysis,
)
from app.utils.report import generate_report_html


class NumpyJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.json_provider_class = NumpyJSONProvider
    app.json = NumpyJSONProvider(app)

    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
    app.config['SECRET_KEY'] = os.urandom(32)

    ALLOWED_EXTENSIONS = {'csv', 'tsv', 'txt', 'dat'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Main analysis endpoint - handles file uploads and returns results."""
        try:
            results = {
                'no_load': None,
                'short_circuit': None,
                'combined': None,
                'waveforms': {},
                'harmonics': {},
                'errors': [],
                'warnings': [],
            }

            nl_file = request.files.get('no_load_file')
            sc_file = request.files.get('short_circuit_file')

            if not nl_file and not sc_file:
                return jsonify({'error': 'Please upload at least one test data file.'}), 400

            nl_df = None
            sc_df = None

            if nl_file and nl_file.filename:
                if not allowed_file(nl_file.filename):
                    results['errors'].append(f'Invalid file type for no-load: {nl_file.filename}')
                else:
                    try:
                        content = nl_file.read().decode('utf-8', errors='replace')
                        nl_df = parse_transformer_data(content, nl_file.filename)

                        detected_type = detect_test_type(nl_df)
                        if detected_type != 'no_load':
                            results['warnings'].append(
                                f'No-load file "{nl_file.filename}" appears to contain '
                                f'{detected_type.replace("_", " ")} data. '
                                'Processing as no-load test as specified.'
                            )

                        results['no_load'] = analyze_no_load_test(nl_df)
                        results['waveforms']['no_load'] = generate_waveform_data(nl_df)
                        results['harmonics']['no_load'] = compute_harmonic_analysis(nl_df)
                    except Exception as e:
                        results['errors'].append(f'Error parsing no-load file: {str(e)}')
                        traceback.print_exc()

            if sc_file and sc_file.filename:
                if not allowed_file(sc_file.filename):
                    results['errors'].append(f'Invalid file type for short-circuit: {sc_file.filename}')
                else:
                    try:
                        content = sc_file.read().decode('utf-8', errors='replace')
                        sc_df = parse_transformer_data(content, sc_file.filename)

                        detected_type = detect_test_type(sc_df)
                        if detected_type != 'short_circuit':
                            results['warnings'].append(
                                f'Short-circuit file "{sc_file.filename}" appears to contain '
                                f'{detected_type.replace("_", " ")} data. '
                                'Processing as short-circuit test as specified.'
                            )

                        results['short_circuit'] = analyze_short_circuit_test(sc_df)
                        results['waveforms']['short_circuit'] = generate_waveform_data(sc_df)
                        results['harmonics']['short_circuit'] = compute_harmonic_analysis(sc_df)
                    except Exception as e:
                        results['errors'].append(f'Error parsing short-circuit file: {str(e)}')
                        traceback.print_exc()

            if results['no_load'] and results['short_circuit']:
                try:
                    results['combined'] = compute_combined_analysis(
                        results['no_load'], results['short_circuit']
                    )
                except Exception as e:
                    results['errors'].append(f'Error in combined analysis: {str(e)}')
                    traceback.print_exc()

            return jsonify(results)

        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/export-report', methods=['POST'])
    def export_report():
        """Generate and return HTML report for download."""
        try:
            data = request.get_json()
            html = generate_report_html(
                data.get('no_load'),
                data.get('short_circuit'),
                data.get('combined'),
                data.get('nl_harmonics'),
                data.get('sc_harmonics'),
            )
            response = make_response(html)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = (
                f'attachment; filename=transformer_report_'
                f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
            )
            return response
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

    return app
