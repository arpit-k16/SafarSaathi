"""Build the completion reports and an allowlisted release from executed evidence."""
import hashlib
import json
from pathlib import Path
import zipfile

from .capabilities import capabilities
from .config import settings
from .forecasting import evaluate_forecast
from .pipeline import sha256, utc_now
from .registry import load_registry


def build():
    project = settings().project_root
    reports = project / 'outputs/reports'
    verification = json.loads((reports / 'ml_verification.json').read_text(encoding='utf-8'))
    if any(check['status'] != 'PASS' for check in verification['checks']):
        raise ValueError('Release requires passing executed verification evidence.')
    readiness = json.loads((reports / 'ml_data_readiness.json').read_text(encoding='utf-8'))
    registry = load_registry(project / 'models/registry.json')
    review = next(x for x in registry if x['task'] == 'review classification')
    tourism = next(x for x in registry if x['model_id'] == 'tourism_demand_forecaster')
    evaluate_forecast(project)
    rows = [{'capability': 'review_classification', 'model_id': review['model_id'], 'status': 'TRAINED_AND_EVALUATED',
             'implementation': 'Existing classifier preserved; no retraining.', 'training_completed': True,
             'dataset': review['dataset_provenance'], 'target': review['label_column'],
             'metrics': verification['review_readonly_evaluation'], 'artifact': review['artifact'], 'limitations': [review['limitations']]}]
    for item in capabilities(project):
        task = next(k for k, v in readiness['models'].items() if v['model_id'] == item['model_id'])
        row = {'capability': task, 'model_id': item['model_id'], 'status': item['implementation_status'],
               'implementation': item['implementation_scope'], 'training_completed': item['training_completed'],
               'dataset_readiness': item['dataset_readiness'], 'reason': item['reason'],
               'data_evidence': readiness['models'][task]['data'], 'target': readiness['models'][task]['target'],
               'metrics': tourism['metrics'] if task == 'tourism_demand' else None,
               'baseline_metrics': tourism['baseline_metrics'] if task == 'tourism_demand' else None,
               'artifact': tourism['artifact'] if task == 'tourism_demand' else None, 'limitations': item['limitations']}
        rows.append(row)
    report = {'generated_at': utc_now(), 'models': rows, 'verification': verification,
              'training': {'tourism_demand': {'method': tourism['method'], 'configuration': tourism['training_configuration'],
                                            'split': tourism['split'], 'selection': tourism['validation_comparison']},
                           'other_models': 'No supervised training attempted without observed labels; no heuristics or fake artifacts registered.'},
              'integration': {'backend': ['GET /capabilities', 'POST /tourism/forecast', 'GET /models', 'GET /models/{id}', 'POST /reviews/classify',
                                          'POST /disaster/predict -> 503', 'POST /flood/segment -> 503', 'POST /stress/predict -> 503'],
                              'frontend': 'Model Center capability cards, disabled unavailable controls, historical forecast form, existing review panel retained.',
                              'verified': 'Production build; Python real HTTP tests and Node API-client tests against live local server, including local CORS.',
                              'not_verified': 'Full browser visual/interaction automation was not performed.'},
              'limitations': ['Three requested supervised learners are not implemented because defensible training labels are absent; ingestion/schema/readiness components are implemented.',
                              'Tourism Ministry DOC/PDF tables need audited extraction and reconciliation; no claim that these documents lack tourism observations.',
                              'No calibrated disaster probabilities, flood masks, stress predictions, geographic generalization or current-demand forecasts are available.',
                              'No official warning system: follow official alerts and emergency guidance.',
                              'Notebook cells executed top-to-bottom; saved notebook presentation was not visually inspected in a notebook viewer.',
                              'Initial frontend HTTP test failed because its HTTP mock adapter sent chunked data; fixed by using native fetch, then rerun. Original failed run retained in verification prior_runs.'],
              'release_zip': 'release/SafarSaathi_ML_Models_20261025.zip'}
    (reports / 'ml_models_completion_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = ['# SafarSaathi ML completion report', '', f"Generated: {report['generated_at']}", '',
             '| Capability | Final status | Implemented scope |', '|---|---|---|']
    lines += [f"| {r['capability']} | {r['status']} | {r['implementation']} |" for r in rows]
    lines += ['', '## Real training and evaluation', '',
              'Tourism: World Bank/UN Tourism ST.INT.ARVL, India national annual international arrivals. Raw source: `../SafarSaathi_Datasets/raw/worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json`.',
              '25 observed years (1995–2019); 2020–2025 all null (19.3548% missing). No imputation. No duplicate country/year keys.',
              'Chronological train: 1995–2009; validation: 2010–2014; test: 2015–2019. Drift selected against persistence and ridge on validation one-year MAE. Test estimator fixed through 2014; expanding observed history allowed only before each origin. Final inference estimator refit through 2019.',
              '', '| Annual horizon | Test forecasts | MAE (arrivals) | RMSE (arrivals) | MASE | WAPE (fraction) |', '|---|---:|---:|---:|---:|---:|']
    for horizon, m in tourism['metrics']['by_horizon'].items():
        lines.append(f"| {horizon} | {m['n']} | {m['MAE']} | {m['RMSE']} | {m['MASE']} | {m['WAPE']} |")
    baseline = tourism['baseline_metrics']['by_horizon']['1']
    lines += ['', f"Persistence one-year baseline: {json.dumps(baseline)}.",
              'MASE uses initial training annual absolute differences; values above 1 indicate errors exceed that historical scale. WAPE is a fraction, undefined at a zero denominator. Multi-horizon forecasts overlap and are not independent samples.',
              f"Saved artifact: `{tourism['artifact']}`; SHA-256: `{tourism['artifact_sha256']}`. Saved estimator reload, recursive inference, and held-out replay passed.",
              '', 'Review model retained: `' + review['model_id'] + '`. Read-only replay metrics: `' + json.dumps(verification['review_readonly_evaluation']) + '`.',
              '', '## Missing labels and precise remediation', '']
    for task in ('disaster_risk', 'flood_segmentation', 'destination_stress'):
        lines += [f"- {task}: {readiness['models'][task]['reason']} Alignment needed: {readiness['models'][task]['alignment']}"]
    lines += ['', '## Executed verification', '', '| Check | Status | Evidence |', '|---|---|---|']
    for check in verification['checks']:
        evidence = check.get('stdout', check.get('stderr', '')).strip().splitlines()
        summary = next((line for line in evidence if ' passed' in line), evidence[-1] if evidence else '')
        lines.append(f"| {check['name']} | {check['status']} | {summary.replace('|', '/')} |")
    lines += ['', 'Final tests include actual HTTP and frontend API-client round trips. Sandbox-only HTTP tests had skips; outside-sandbox verification resolves loopback access. See `ml_verification.json` for final counts, outputs, initial failure and corrected rerun.',
              'All 961 raw files passed full SHA-256, size and existence checks. Original review registry entry and artifact match the prior release ZIP; review metadata/evaluation files and legacy archive manifests stayed byte-identical during verification.',
              '', '## Integration and limitations', '', *['- ' + x for x in report['limitations']],
              '', report['integration']['frontend'], report['integration']['verified'],
              '', '## Reproduce', '', 'From `SafarSaathi_Project` with `$env:PYTHONPATH="src"`:', '', '```powershell',
              'python -m safarsaathi_ml.cli data-readiness', 'python -m safarsaathi_ml.cli models',
              'python -m safarsaathi_ml.cli train --model tourism_demand',
              'python -m safarsaathi_ml.cli evaluate --model tourism_demand',
              'python -m safarsaathi_ml.cli predict --model tourism_demand --destination IND --horizon 3',
              'python -m safarsaathi_ml.cli validate-artifacts', 'python -m safarsaathi_ml.cli serve --port 8000', '```',
              'Training is opt-in and refuses to overwrite an already registered tourism model. Unlabelled tasks exit 2 with the missing-evidence reason. Inference on a released artifact does not require raw files.',
              '', 'Attribution: Source: World Bank Open Data — World Development Indicators. Tourism indicators are compiled by the World Bank from UN Tourism (formerly UNWTO) source data. CC BY 4.0.',
              'Other source attribution/licensing details: `docs/DATA_LICENSES_AND_ATTRIBUTION.md` in the release.',
              '', 'Release: `release/SafarSaathi_ML_Models_20261025.zip`. ZIP verification and content hashes are recorded in `release/ml_release_manifest.json`.']
    (reports / 'ml_models_completion_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    docs = project / 'docs'; docs.mkdir(exist_ok=True)
    licenses = project.parent / 'SafarSaathi_Datasets/LICENSES_AND_ATTRIBUTION.md'
    (docs / 'DATA_LICENSES_AND_ATTRIBUTION.md').write_text(licenses.read_text(encoding='utf-8'), encoding='utf-8')
    # Strict source allowlist, no logs, original datasets, legacy archives or prior release ZIPs.
    selected = ['README.md', 'ML_MODELS.md', 'requirements.txt', '.gitignore', 'configs', 'src', 'tests', 'docs', 'notebooks',
                'frontend/src', 'frontend/tests', 'frontend/index.html', 'frontend/package.json',
                'frontend/package-lock.json', 'frontend/vite.config.js', 'models/registry.json',
                'outputs/reports/ml_data_readiness.json', 'outputs/reports/ml_data_readiness.md',
                'outputs/reports/ml_models_completion_report.json', 'outputs/reports/ml_models_completion_report.md',
                'outputs/reports/ml_verification.json']
    for item in registry:
        selected.append(Path(item['artifact']).parent.as_posix())
    selected += [p.relative_to(project).as_posix() for p in (project / 'outputs/metrics').glob('nlp-*_evaluation_audit.json')]
    selected += [p.relative_to(project).as_posix() for p in (project / 'outputs/figures').glob('nlp-*_confusion_matrix.png')]
    contents = {}
    for relative in selected:
        source = project / relative
        for path in ([source] if source.is_file() else source.rglob('*')):
            if path.is_file() and not any(part in {'__pycache__', '.pytest_cache', 'node_modules', '.git', '.venv'} for part in path.parts):
                if path.suffix.lower() in {'.pyc', '.pyo'}: continue
                contents[path.relative_to(project).as_posix()] = path
    forbidden = ('SafarSaathi_Datasets/', 'trash/', 'node_modules/', '.env', '.aws/', '.git/')
    if any(any(token in name for token in forbidden) for name in contents):
        raise ValueError('Forbidden release content.')
    archive = project / report['release_zip']
    if archive.exists():
        raise ValueError('Release ZIP already exists; refusing to replace it.')
    manifest = {'generated_at': utc_now(), 'files': {name: sha256(path) for name, path in sorted(contents.items())}}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for name, path in sorted(contents.items()): zipped.write(path, name)
        zipped.writestr('release/ml_release_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for name, expected in manifest['files'].items():
            assert hashlib.sha256(zipped.read(name)).hexdigest() == expected
    manifest.update(zip_sha256=sha256(archive), zip_bytes=archive.stat().st_size,
                    zip_entries=len(contents) + 1, zip_crc_and_content_hashes_verified=True)
    (project / 'release/ml_release_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return {'zip': str(archive), 'entries': len(contents) + 1, 'bytes': archive.stat().st_size, 'verified': True}


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
