"""Versioned quality audit/release. Earlier artifacts and evaluation evidence stay immutable."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET

from .baseline_comparison import build_comparison
from .config import settings
from .pipeline import sha256, utc_now
from .registry import load_registry

RELEASE_NAME = 'final_ml_quality_20261025_01'


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)


def protected_state(project):
    roots = [project / 'models', project / 'outputs', project.parent / 'trash']
    selected = [p for root in roots for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    selected += [p for p in (project / 'release').iterdir() if p.is_file()]
    selected += [p for p in (project.parent / 'SafarSaathi_Datasets').iterdir() if p.is_file()]
    return {p.relative_to(project.parent).as_posix(): sha256(p) for p in sorted(selected)}


def prepare(project, destination):
    if destination.exists():
        raise ValueError('Quality release directory already exists; do not overwrite prior evidence.')
    destination.mkdir(parents=True)
    # Snapshot all existing evidence/model files and the complete legacy archive before audit commands.
    protected = protected_state(project)
    raw = project.parent / 'SafarSaathi_Datasets/raw'
    stats = {p.relative_to(raw).as_posix(): {'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns}
             for p in sorted(raw.rglob('*')) if p.is_file()}
    prior = project / 'release/SafarSaathi_ML_Models_20261025.zip'
    registry = load_registry(project / 'models/registry.json')
    with zipfile.ZipFile(prior) as zipped:
        if zipped.testzip() is not None or json.loads(zipped.read('models/registry.json')) != registry:
            raise ValueError('Prior release integrity or registry comparison failed.')
        for entry in registry:
            if hashlib.sha256(zipped.read(entry['artifact'])).hexdigest() != sha256(project / entry['artifact']):
                raise ValueError('Registered artifact differs from prior working release.')
    save(destination / 'initial_state.json', {'generated_at': utc_now(), 'protected_sha256': protected,
         'raw_file_stats': stats, 'raw_file_count': len(stats), 'prior_release_crc_and_artifacts_verified': True,
         'git': 'No .git in workspace/project; no Git operations performed.'})
    integrity = project / 'models/artifact_integrity.json'
    pins = {'schema_version': 1, 'provenance': 'Artifacts matched the prior verified release ZIP before pinning.',
            'artifacts': {entry['artifact']: sha256(project / entry['artifact']) for entry in registry}}
    if integrity.exists():
        if json.loads(integrity.read_text(encoding='utf-8')) != pins:
            raise ValueError('Existing checksum pins conflict; refusing replacement.')
    else:
        save(integrity, pins)
    comparison = build_comparison(project, raw)
    # Reports contain scores, origins and generated forecasts, never raw target series or review text.
    for item in comparison['methods'].values():
        item['forecast_errors'] = [{'forecast_origin_year': r['forecast_origin_year'], 'target_year': r['target_year'],
                                    'horizon': r['horizon'], 'absolute_error': abs(r['actual'] - r['prediction'])}
                                   for r in item.pop('predictions')]
    save(destination / 'tourism_baseline_comparison.json', comparison)
    return comparison


def run_check(destination, name, command, cwd, expected=0, extra_env=None, timeout=180):
    started = time.monotonic()
    env = {**os.environ, 'PYTHONPATH': str(settings().project_root / 'src'), 'PYTHONIOENCODING': 'utf-8',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', **(extra_env or {})}
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        stdout = result.stdout
        if result.returncode == expected and 'safarsaathi_ml.cli' in command:
            try:
                def without_raw_targets(value):
                    if isinstance(value, dict): return {k: without_raw_targets(v) for k, v in value.items() if k not in {'actual', 'text', 'review_text'}}
                    if isinstance(value, list): return [without_raw_targets(v) for v in value]
                    return value
                stdout = json.dumps(without_raw_targets(json.loads(stdout)), indent=2)
            except json.JSONDecodeError:
                pass
        output = {'name': name, 'status': 'PASS' if result.returncode == expected else 'FAIL', 'command': command,
                  'exit_code': result.returncode, 'expected_exit_code': expected,
                  'stdout': stdout, 'stderr': result.stderr, 'seconds': time.monotonic() - started}
    except (OSError, subprocess.TimeoutExpired) as exc:
        output = {'name': name, 'status': 'BLOCKED', 'command': command, 'reason': type(exc).__name__, 'seconds': time.monotonic() - started}
    save(destination / f'{name}.json', output)
    print(name + ': ' + output['status'], flush=True)
    return output


def check_preservation(project, destination):
    initial = json.loads((destination / 'initial_state.json').read_text(encoding='utf-8'))
    mismatches = [relative for relative, digest in initial['protected_sha256'].items()
                  if not (project.parent / relative).is_file() or sha256(project.parent / relative) != digest]
    raw = project.parent / 'SafarSaathi_Datasets/raw'
    current = {p.relative_to(raw).as_posix(): {'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns}
               for p in raw.rglob('*') if p.is_file()}
    if mismatches or current != initial['raw_file_stats']:
        raise ValueError('Protected files or raw inventory changed: ' + ', '.join(mismatches))
    result = {'status': 'PASS', 'protected_file_count': len(initial['protected_sha256']),
              'raw_inventory_stat_count': len(current), 'registry_models_evaluations_archives_and_prior_releases_unchanged': True,
              'raw_inventory_sizes_mtimes_and_paths_unchanged': True}
    return result


def review_audit(project):
    import joblib
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from .artifacts import load_artifact
    registry = load_registry(project / 'models/registry.json')
    entry = next(m for m in registry if m['task'] == 'review classification')
    metadata = json.loads((project / Path(entry['artifact']).parent / 'metadata.json').read_text(encoding='utf-8'))
    source = project.parent / Path(entry['dataset_provenance']['repository_relative_path'])
    if sha256(source) != entry['dataset_provenance']['sha256']:
        raise ValueError('Review source checksum differs from registered provenance.')
    frame = pd.read_csv(source)
    text, label = metadata['text_column'], metadata['label_column']
    cleaned = frame[[text, label]].dropna().drop_duplicates().copy()
    cleaned[text] = cleaned[text].astype(str).str.strip(); cleaned = cleaned[cleaned[text].str.len() > 0]
    train, test = train_test_split(cleaned, test_size=0.2, random_state=metadata['random_seed'], stratify=cleaned[label])
    model = load_artifact(project, entry)
    predictions = model.predict(test[text])
    scores = {'accuracy': float(accuracy_score(test[label], predictions)),
              'macro_f1': float(f1_score(test[label], predictions, average='macro')),
              'weighted_f1': float(f1_score(test[label], predictions, average='weighted'))}
    prior = json.loads((project / f"outputs/metrics/{entry['model_id']}_evaluation_audit.json").read_text(encoding='utf-8'))
    labels = model.classes_.tolist()
    matrix = confusion_matrix(test[label], predictions, labels=labels).tolist()
    if any(scores[k] != prior[k] for k in scores) or matrix != prior['confusion_matrix']:
        raise ValueError('Read-only review evaluation does not match existing audit.')
    return {'generated_at': utc_now(), 'status': 'PASS', 'training_performed': False, 'evaluation_freshly_reproduced': True,
            'model_id': entry['model_id'], 'artifact': entry['artifact'], 'artifact_sha256': sha256(project / entry['artifact']),
            'source': {**entry['dataset_provenance'], 'bytes': source.stat().st_size},
            'preprocessing': {'steps': list(model.named_steps), 'tfidf_ngram_range': list(model.named_steps['tfidf'].ngram_range),
                              'scope': 'Source-defined hotel-review label classification; no destination/language generalization claim.'},
            'classes': labels, 'metrics': scores, 'confusion_matrix': matrix,
            'classification_report': classification_report(test[label], predictions, labels=labels, output_dict=True),
            'split': {'seed': metadata['random_seed'], 'strategy': 'stratified 80/20 documented split replay', 'train_rows': len(train), 'test_rows': len(test)},
            'software_versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                                  'sklearn': sklearn.__version__, 'joblib': joblib.__version__},
            'stored_metrics_and_confusion_matrix_match': True,
            'limitations': [entry['limitations'], 'Exact split replay is not independent validation on new hotels or languages.']}


def verify(project, destination):
    from .forecasting import evaluate_forecast
    from .readiness import data_readiness
    if not (destination / 'initial_state.json').exists():
        raise ValueError('Run prepare before verification.')
    checks = []
    temporary = destination / 'temporary'
    temporary.mkdir(exist_ok=True)
    test_temporary = project / 'data/interim/test_runs'
    test_temporary.mkdir(parents=True, exist_ok=True)
    commands = [
        ('python_tests', [sys.executable, '-m', 'pytest', 'tests', '-q', '--tb=short', '--basetemp', str(test_temporary / destination.name), '--junitxml', str(destination / 'python_tests.xml')], project),
        ('artifact_validation', [sys.executable, '-m', 'safarsaathi_ml.cli', 'validate-artifacts'], project),
        ('tourism_saved_evaluation', [sys.executable, '-m', 'safarsaathi_ml.cli', 'evaluate', '--model', 'tourism_demand'], project),
        ('tourism_saved_inference', [sys.executable, '-m', 'safarsaathi_ml.cli', 'predict', '--model', 'tourism_demand', '--destination', 'IND', '--horizon', '3'], project),
        ('model_listing', [sys.executable, '-m', 'safarsaathi_ml.cli', 'models'], project),
        ('package_compile', [sys.executable, '-m', 'compileall', '-q', 'src/safarsaathi_ml'], project),
        ('frontend_build', [shutil.which('node'), str(project / 'frontend/node_modules/vite/bin/vite.js'), 'build'], project / 'frontend'),
        ('raw_checksums', [sys.executable, 'verify_checksums.py'], project.parent / 'SafarSaathi_Datasets'),
    ]
    for name, command, cwd in commands:
        checks.append(run_check(destination, name, command, cwd))
    # Standalone Node tests run against an actual server, so no optional live test is skipped.
    import threading
    from .http_api import Handler, ThreadingHTTPServer
    service = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=service.serve_forever, daemon=True); thread.start()
    try:
        checks.append(run_check(destination, 'frontend_all_tests', [shutil.which('node'), '--test', '--test-reporter=tap', 'tests/api.test.js', 'tests/routes.test.js'], project / 'frontend',
                                extra_env={'SAFARSAATHI_TEST_API': f'http://127.0.0.1:{service.server_port}'}))
    finally:
        service.shutdown(); thread.join(); service.server_close()
    for task in ('disaster_risk', 'flood_segmentation', 'destination_stress'):
        checks.append(run_check(destination, task + '_training_refusal', [sys.executable, '-m', 'safarsaathi_ml.cli', 'train', '--model', task], project, expected=2))
    checks.append(run_check(destination, 'registered_tourism_overwrite_refusal', [sys.executable, '-m', 'safarsaathi_ml.cli', 'train', '--model', 'tourism_demand'], project, expected=2))
    # Fresh process startup uses port 0; exercise an external request, then terminate only our child.
    checks.append(run_check(destination, 'clean_process_startup', [sys.executable, '-m', 'safarsaathi_ml.startup_check'], project))
    review = review_audit(project)
    save(destination / 'review_evaluation.json', review)
    tourism = evaluate_forecast(project)
    tourism['metrics'].pop('predictions', None)
    tourism.update(status='TRAINED_BUT_EXPERIMENTAL', no_training_performed=True)
    save(destination / 'tourism_evaluation.json', tourism)
    readiness = data_readiness(project, project.parent / 'SafarSaathi_Datasets/raw', write=False)
    compact = {'generated_at': utc_now(), 'file_count': readiness['file_count'], 'total_bytes': readiness['total_bytes'],
               'categories': readiness['categories'], 'tourism_source': readiness['models']['tourism_demand']['data'],
               'proposed_models': {k: {'readiness': v['readiness'], 'reason': v['reason'], 'alignment': v['alignment']} for k, v in readiness['models'].items()},
               'flood_mask_inventory': {k: v for k, v in readiness['models']['flood_segmentation']['data'].items() if k != 'files'},
               'minimum_additional_data': {
                   'disaster_risk': 'Proposed target: any verified flood onset in each Uttarakhand district during the next 7 days. Need dated event IDs/coordinates mapped to versioned district boundaries, documented observation completeness and confirmed no-event windows, plus rainfall/features available before each cutoff. This is a proposed definition, not existing labels.',
                   'flood_segmentation': 'Observed binary flood masks paired with acquisition-scene imagery; matching CRS/transform/footprint/time, documented event IDs and independent event/geography splits before patches. Cloud/SCL masks are not flood outcomes.',
                   'destination_stress': 'Measured destination/day crowd density or occupied/available capacity with units, sampling coverage and timestamped capacity; agree on one observed outcome and prediction lead time before training.'},
               'source_improvement': 'Local ministry DOC/PDF reports exist but require audited extraction and definition reconciliation. No newer verified observations of the exact World Bank target series were found; no claim that all documents lack newer tourism statistics.'}
    save(destination / 'dataset_readiness_summary.json', compact)
    preservation = check_preservation(project, destination)
    save(destination / 'preservation_check.json', preservation)
    suite = ET.parse(destination / 'python_tests.xml').getroot().find('testsuite')
    counts = {key: int(suite.attrib.get(key, 0)) for key in ('tests', 'failures', 'errors', 'skipped')}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    save(destination / 'verification_checks.json', {'generated_at': utc_now(), 'checks': checks, 'python_counts': counts,
         'development_checks': [{'status': 'FAIL', 'result': '74 passed, 4 setup errors',
                                 'reason': 'Oversized-request parameter values created test IDs exceeding Windows filename limits. Explicit bounded IDs fixed the harness; affected rerun: 58 passed.'}],
         'review_metrics': review['metrics'], 'preservation': preservation})
    if any(c['status'] != 'PASS' for c in checks):
        raise ValueError('Verification has failures/blocks; inspect per-check outputs before packaging.')


def package(project, destination):
    verification = json.loads((destination / 'verification_checks.json').read_text(encoding='utf-8'))
    browser = json.loads((destination / 'browser_verification.json').read_text(encoding='utf-8'))
    comparison = json.loads((destination / 'tourism_baseline_comparison.json').read_text(encoding='utf-8'))
    readiness = json.loads((destination / 'dataset_readiness_summary.json').read_text(encoding='utf-8'))
    review = json.loads((destination / 'review_evaluation.json').read_text(encoding='utf-8'))
    # Optional extra checks are recorded separately without replacing completed evidence.
    frontend_name = 'frontend_all_tests_rerun' if (destination / 'frontend_all_tests_rerun.json').exists() else 'frontend_all_tests'
    for name in (frontend_name, 'frontend_final_build'):
        check_path = destination / (name + '.json')
        if check_path.exists() and not any(c['name'] == name for c in verification['checks']):
            verification['checks'].append(json.loads(check_path.read_text(encoding='utf-8')))
    if any(check['status'] != 'PASS' for check in verification['checks']):
        raise ValueError('Resolve failed non-browser checks before packaging; browser block must remain explicit.')
    registry = load_registry(project / 'models/registry.json')
    comparison_now = build_comparison(project, project.parent / 'SafarSaathi_Datasets/raw')
    if comparison_now['mase_denominator'] != comparison['mase_denominator'] or comparison_now['artifact'] != comparison['artifact']:
        raise ValueError('Comparison or artifact identity changed after verification.')
    preserve = check_preservation(project, destination)
    statuses = [{'capability': 'review_classification', 'status': 'TRAINED_AND_EVALUATED', 'model_id': review['model_id'],
                 'evidence': 'Artifact integrity, fresh-process inference and documented holdout evaluation reproduced without training.'},
                {'capability': 'tourism_demand', 'status': 'TRAINED_BUT_EXPERIMENTAL', 'model_id': 'tourism_demand_forecaster',
                 'evidence': comparison['decision']}]
    from .readiness import IDS
    statuses += [{'capability': name, 'status': 'LABELS_INSUFFICIENT', 'model_id': IDS[name],
                  'evidence': readiness['proposed_models'][name]['reason'], 'minimum_additional_data': requirement}
                 for name, requirement in readiness['minimum_additional_data'].items()]
    counts = verification['python_counts']
    report = {'generated_at': utc_now(), 'overall_status': 'VERIFIED_WITH_BROWSER_CHECK_BLOCKED',
              'model_status': statuses, 'checks': verification['checks'], 'python_counts': counts,
              'frontend_counts': {'tests': 13, 'passed': 13, 'failed': 0, 'skipped': 0,
                                  'scope': '4 API-client tests against a real backend plus 9 server-rendering tests; verify TAP counts in ' + frontend_name + '.json'},
              'browser_verification': browser, 'tourism_comparison': 'tourism_baseline_comparison.json',
              'review_evaluation': 'review_evaluation.json', 'dataset_integrity': readiness,
              'preservation': preserve, 'development_checks': verification['development_checks'],
              'changes': [
                  'Preserved both registered estimators, registry bytes, prior metrics, legacy archive and previous releases.',
                  'Added like-for-like persistence, expanding drift, historical mean and ridge comparisons on original horizons/origins; no test-selected replacement.',
                  'Pinned artifact checksums against prior working ZIP; hardened registry validation and Windows path checks.',
                  'Added JSON errors for wrong HTTP methods/content types, malformed/nonfinite/oversized bodies, missing/corrupt artifacts, registry errors and internal failures.',
                  'Derived last observation from saved metadata; displayed origin, horizon, version, units and limitations; reject malformed successful API responses.',
                  'Marked demonstration views and removed unsupported uptime/live-feed/compliance claims.'
              ],
              'limitations': [
                  'Tourism uses 25 annual India national observations ending in 2019. Extrapolations do not estimate current 2026 demand or individual Uttarakhand destinations.',
                  '5/4/3 overlapping test forecasts and revised-source vintages do not establish reliable generalization or superiority; no uncertainty calibration or pandemic outcomes.',
                  'Ministry tourism documents may contain newer statistics but have not been extracted and reconciled to this exact target definition; no source series was silently merged.',
                  'Disaster, flood and stress learners remain untrained pending observed labels; follow official alerts and emergency guidance.',
                  'Actual browser form journeys, responsive layout and route navigation remain BLOCKED. Server rendering, HTTP and client tests are not visual validation.',
                  'Tailwind and fonts remain externally loaded as in the existing design; offline visual styling is not verified.',
                  'Review scores apply to the documented held-out source split, not every destination, language or review domain.'
              ], 'release': {'zip': 'SafarSaathi_Final.zip', 'content_manifest': 'release_content_manifest.json',
                              'post_extract_validation': 'release_validation.json'}}
    # Derive Node counts from actual TAP output rather than declaring fixed successful counts.
    all_node = next((c for c in verification['checks'] if c['name'] in {'frontend_all_tests', 'frontend_all_tests_rerun'}), None)
    if all_node is None: raise ValueError('Run the complete frontend suite with the real API before packaging.')
    for label, field in [('tests', 'tests'), ('pass', 'passed'), ('fail', 'failed'), ('skipped', 'skipped')]:
        match = re.search(r'^# ' + label + r' (\d+)$', all_node['stdout'], re.MULTILINE)
        if not match: raise ValueError('Missing frontend TAP count: ' + label)
        report['frontend_counts'][field] = int(match.group(1))
    if report['frontend_counts']['failed'] or report['frontend_counts']['skipped']:
        raise ValueError('Frontend suite has failures/skips; cannot report complete API coverage.')
    if frontend_name.endswith('_rerun'):
        prior_frontend = json.loads((destination / 'frontend_all_tests.json').read_text(encoding='utf-8'))
        report['development_checks'].append({'status': prior_frontend['status'], 'result': '12 passed, 1 failed; 0 skipped',
            'evidence': 'frontend_all_tests.json', 'reason': 'Fixed-port 8000 returned 404 for /capabilities. Repeated against an explicitly created fresh server on its returned ephemeral port, avoiding a stale or different service.'})
    save(destination / 'verification_report.json', report)
    lines = ['# SafarSaathi final verification', '', 'Status: VERIFIED_WITH_BROWSER_CHECK_BLOCKED',
             '', '## Model status', '', '| Capability | Status | Evidence |', '|---|---|---|']
    lines += [f"| {row['capability']} | {row['status']} | {row['evidence']} |" for row in statuses]
    lines += ['', '## Tourism quality', '', comparison['decision'], comparison['mase_resolution'],
              f"The unchanged MASE denominator is {comparison['mase_denominator']} arrivals (mean absolute annual changes, 1995–2009).",
              'Splits remain train 1995–2009, validation 2010–2014, test 2015–2019. All methods use identical origins/targets/missingness treatment. Expanding methods fit only past prefixes; the original evaluation estimator stays fixed through 2014. No future external features are used.',
              '', '| Method | Horizon | Origin years | n | MAE | RMSE | MASE | WAPE fraction |', '|---|---:|---|---:|---:|---:|---:|---:|']
    for name, method in comparison['methods'].items():
        for h, score in method['by_horizon'].items():
            lines.append(f"| {name} | {h} | {score['origins'][0]}–{score['origins'][-1]} | {score['n']} | {score['MAE']} | {score['RMSE']} | {score['MASE']} | {score['WAPE']} |")
    lines += ['', 'Absolute/relative differences versus persistence for every metric/horizon and validation-only results are in `tourism_baseline_comparison.json`. Negative differences mean lower error. WAPE allows individual zero actuals; all-zero denominator produces null. MASE is null for a zero training scale. Annual seasonal-naive is NOT_APPLICABLE because no defensible seasonal period is established.',
              '', '## Verification', '',
              f"Python: {counts['passed']} passed, {counts['failures']} failed, {counts['errors']} errors, {counts['skipped']} skipped.",
              f"Frontend: {report['frontend_counts']['passed']} passed, {report['frontend_counts']['failed']} failed, {report['frontend_counts']['skipped']} skipped. API and server-rendering tests are separate from browser validation.",
              '', '| Check | Status | Exit code |', '|---|---|---:|']
    lines += [f"| {c['name']} | {c['status']} | {c.get('exit_code', '')} |" for c in verification['checks']]
    lines += ['| Browser visual journeys / navigation | BLOCKED | |',
              '| Annual seasonal-naive | NOT_APPLICABLE | |', '',
              'Commands, timings, stdout and stderr: per-check JSON files and `verification_report.json`. The three untrained-model commands and registered-model overwrite attempt intentionally exit 2; successful checks confirm refusal without mutation.',
              'Development run: 74 passed with 4 setup errors caused by oversized parameter identifiers exceeding Windows filename limits. Explicit bounded IDs fixed the test harness; affected rerun passed 58 tests. A separate fixed-port frontend run had 12 passes and 1 failure (404 for /capabilities); an explicitly created fresh-server rerun resolved that target-instance issue. Failed-run evidence is retained. Final counts above describe the verified reruns.',
              '', '## Review validation', '', f"Fresh read-only reproduction: {json.dumps(review['metrics'])}.",
              f"Classes: {review['classes']}; split seed: {review['split']['seed']}; train/test rows: {review['split']['train_rows']}/{review['split']['test_rows']}.",
              'Existing confusion matrix and audit metrics match exactly; no new confusion-matrix image is needed. Fresh evidence is in `review_evaluation.json`; prior artifacts remain byte-identical.',
              '', '## Data integrity and readiness', '',
              f"Raw files inventoried: {readiness['file_count']}; total bytes: {readiness['total_bytes']}. Fresh streaming verifier output is in `raw_checksums.json`.",
              f"World Bank source identity: {json.dumps(readiness['tourism_source'])}.",
              f"{preserve['protected_file_count']} pre-existing protected files, registry entries, evaluation files, archive files and prior releases remain unchanged. Raw paths/sizes/mtimes also match the initial snapshot.",
              '', *[f"- {name}: {requirement}" for name, requirement in readiness['minimum_additional_data'].items()],
              '', '## Unresolved limitations', '', *['- ' + item for item in report['limitations']],
              '', 'Browser tool reason: ' + browser['reason'],
              'Computer-use policy ended browser control; no alternative browser automation was attempted.',
              '', '## Release and reproduction', '',
              'See root `README.md` and `ML_MODELS.md` for verified setup/evaluation/inference commands. `SafarSaathi_Final.zip` contains source, tests, documentation, config, reports and both preserved model artifacts. It excludes raw collections, review text, the legacy archive, secrets, environments and caches.',
              'ZIP CRC, content hashes, extracted fresh-process review and tourism inference, explicit unavailable capabilities and raw-free operation are verified by `release_validation.json` after packaging.',
              'Source: World Bank Open Data — World Development Indicators. Tourism indicators are compiled by the World Bank from UN Tourism (formerly UNWTO) source data. CC BY 4.0. See `docs/DATA_LICENSES_AND_ATTRIBUTION.md`.']
    with (destination / 'FINAL_VERIFICATION_REPORT.md').open('x', encoding='utf-8') as handle: handle.write('\n'.join(lines) + '\n')
    # Explicit allowlist; package no old output directories or raw reviews.
    selected = ['README.md', 'ML_MODELS.md', 'requirements.txt', '.gitignore', 'configs', 'src', 'tests', 'docs',
                'frontend/src', 'frontend/tests', 'frontend/index.html', 'frontend/package.json', 'frontend/package-lock.json', 'frontend/vite.config.js',
                'models/registry.json', 'models/artifact_integrity.json',
                'outputs/reports/ml_data_readiness.json', 'outputs/reports/ml_data_readiness.md']
    for entry in registry: selected.append(Path(entry['artifact']).parent.as_posix())
    selected += [p.relative_to(project).as_posix() for p in (project / 'outputs/metrics').glob('nlp-*_evaluation_audit.json')]
    selected += [p.relative_to(project).as_posix() for p in (project / 'outputs/figures').glob('nlp-*_confusion_matrix.png')]
    files = {}
    for relative in selected:
        root = project / relative
        for path in ([root] if root.is_file() else root.rglob('*')):
            if path.is_file() and not any(p in {'node_modules', '__pycache__', '.git', '.pytest_cache', '.venv'} for p in path.parts) and path.suffix not in {'.pyc', '.pyo'}:
                files[path.relative_to(project).as_posix()] = path
    # Compact current release evidence only; initial snapshots and temporary test files stay outside ZIP.
    evidence = ['FINAL_VERIFICATION_REPORT.md', 'verification_report.json', 'tourism_baseline_comparison.json', 'tourism_evaluation.json',
                'review_evaluation.json', 'dataset_readiness_summary.json', 'browser_verification.json', 'preservation_check.json',
                'verification_checks.json', 'python_tests.xml']
    evidence += [c['name'] + '.json' for c in verification['checks']]
    if (destination / 'frontend_all_tests.json').exists(): evidence.append('frontend_all_tests.json')
    for name in set(evidence): files[f'release/{destination.name}/{name}'] = destination / name
    manifest = {name: sha256(path) for name, path in sorted(files.items())}
    archive = destination / 'SafarSaathi_Final.zip'
    if archive.exists(): raise ValueError('Refusing to overwrite an existing release ZIP.')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipped:
        for name, path in sorted(files.items()): zipped.write(path, name)
        zipped.writestr('release_content_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None: raise ValueError('ZIP CRC verification failed.')
        for name, digest in manifest.items():
            if hashlib.sha256(zipped.read(name)).hexdigest() != digest: raise ValueError('ZIP content checksum mismatch.')
            if Path(name).is_absolute() or '..' in Path(name).parts or any(token in Path(name).parts for token in ('SafarSaathi_Datasets', 'trash', 'node_modules', '.git', '.venv')):
                raise ValueError('Unsafe release structure.')
    save(destination / 'release_content_manifest.json', {'files': manifest, 'zip_sha256': sha256(archive), 'zip_bytes': archive.stat().st_size})
    result = extracted_validation(project, destination, archive)
    result['preservation_after_extract'] = check_preservation(project, destination)
    save(destination / 'release_validation.json', result)
    if result['status'] != 'PASS': raise ValueError('Extracted release validation did not pass.')
    print(json.dumps({'status': 'PASS', 'zip': str(archive), 'bytes': archive.stat().st_size, 'entries': len(manifest) + 1,
                      'browser_visual_check': 'BLOCKED'}, indent=2))


def extracted_validation(project, destination, archive):
    from .registry import resolve_artifact_path
    extracted = destination / 'temporary/extracted_release'
    if extracted.exists(): raise ValueError('Extraction target already exists; refusing to overwrite.')
    extracted.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped: zipped.extractall(extracted)
    if (extracted.parent / 'SafarSaathi_Datasets').exists(): raise ValueError('Extraction unexpectedly has sibling raw data.')
    # PYTHONPATH contains only the extracted source. config/project roots resolve to the extracted checkout.
    child = '''import json
from pathlib import Path
from safarsaathi_ml.config import settings
from safarsaathi_ml.validation import validate_artifacts
from safarsaathi_ml.inference import classify_reviews
from safarsaathi_ml.forecasting import forecast
from safarsaathi_ml.capabilities import capabilities
from safarsaathi_ml.registry import load_registry
p=settings().project_root
assert not (p.parent/'SafarSaathi_Datasets').exists()
entries=load_registry(p/'models/registry.json')
review=next(m for m in entries if m['task']=='review classification')
assert validate_artifacts(p)
assert classify_reviews(review['model_id'],['A clean hotel with helpful staff.'])['predictions'][0] in {'NEGATIVE','POSITIVE'}
f=forecast(p,'IND',3)
assert f['forecast_origin_year']==2019 and len(f['forecasts'])==3
unavailable=[m for m in capabilities(p) if m['model_id']!='tourism_demand_forecaster']
assert len(unavailable)==3 and all(not m['inference_available'] for m in unavailable)
print(json.dumps({'status':'PASS','review_inference':True,'tourism_inference':True,'unavailable_models_disabled':True,'raw_dataset_directory_absent':True,'loaded_from_extracted_source':str(p)}))
'''
    env = {**os.environ, 'PYTHONPATH': str(extracted / 'src'), 'PYTHONIOENCODING': 'utf-8'}
    result = subprocess.run([sys.executable, '-c', child], cwd=extracted, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
    if result.returncode:
        return {'status': 'FAIL', 'exit_code': result.returncode, 'stderr': result.stderr}
    return {**json.loads(result.stdout), 'zip_crc_and_every_content_sha256_verified': True,
            'zip_sha256': sha256(archive), 'zip_bytes': archive.stat().st_size, 'exit_code': result.returncode}


def frontend_verification(project, destination):
    import threading
    from .http_api import Handler, ThreadingHTTPServer
    service = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=service.serve_forever, daemon=True); thread.start()
    name = 'frontend_all_tests_rerun' if (destination / 'frontend_all_tests.json').exists() else 'frontend_all_tests'
    try:
        result = run_check(destination, name, [shutil.which('node'), '--test', '--test-reporter=tap', 'tests/api.test.js', 'tests/routes.test.js'], project / 'frontend',
                           extra_env={'SAFARSAATHI_TEST_API': f'http://127.0.0.1:{service.server_port}'})
        if result['status'] != 'PASS': raise ValueError('Frontend test suite failed; inspect retained output.')
    finally:
        service.shutdown(); thread.join(); service.server_close()
    result = run_check(destination, 'frontend_final_build', [shutil.which('node'), str(project / 'frontend/node_modules/vite/bin/vite.js'), 'build'], project / 'frontend')
    if result['status'] != 'PASS': raise ValueError('Final production build failed.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('prepare', 'verify', 'frontend', 'package'))
    parser.add_argument('--release-name', default=RELEASE_NAME)
    args = parser.parse_args()
    project = settings().project_root
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.release_name):
        parser.error('release-name must contain only letters, digits, underscores or hyphens.')
    destination = project / 'release' / args.release_name
    if args.stage == 'prepare':
        comparison = prepare(project, destination)
        print(json.dumps({name: item['by_horizon']['1']['MAE'] for name, item in comparison['methods'].items()}, indent=2))
    elif args.stage == 'verify':
        verify(project, destination)
    elif args.stage == 'frontend':
        frontend_verification(project, destination)
    else:
        package(project, destination)


if __name__ == '__main__':
    main()
