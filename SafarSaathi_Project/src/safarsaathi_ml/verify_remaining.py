"""Execute checks and record their actual outputs. Never train or rewrite review audits."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from .config import settings
from .pipeline import sha256, utc_now
from .registry import load_registry, resolve_artifact_path


def verify():
    project = settings().project_root
    registry = load_registry(project / 'models/registry.json')
    review = next(x for x in registry if x['task'] == 'review classification')
    artifact = resolve_artifact_path(project, review['artifact'])
    protected = list(artifact.parent.glob('*')) + list((project / 'outputs/metrics').glob('nlp-*_evaluation_audit.json'))
    protected += list((project.parent / 'trash').glob('*/archive_manifest.json'))
    before = {str(p.relative_to(project.parent)): sha256(p) for p in protected if p.is_file()}
    checks = []
    env = {**os.environ, 'PYTHONPATH': str(project / 'src'), 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONIOENCODING': 'utf-8'}
    with tempfile.TemporaryDirectory(prefix='safarsaathi-ml-tests-') as isolated:
        commands = [
            ('python_tests', [sys.executable, '-m', 'pytest', '-q', '--basetemp', str(Path(isolated) / 'pytest')], project),
            ('artifact_validation', [sys.executable, '-m', 'safarsaathi_ml.cli', 'validate-artifacts'], project),
            ('package_compile', [sys.executable, '-m', 'compileall', '-q', 'src/safarsaathi_ml'], project),
            ('frontend_build', [shutil.which('node'), str(project / 'frontend/node_modules/vite/bin/vite.js'), 'build'], project / 'frontend'),
            ('full_raw_checksums', [sys.executable, 'verify_checksums.py'], project.parent / 'SafarSaathi_Datasets'),
        ]
        for name, command, cwd in commands:
            started = time.monotonic()
            result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
            checks.append({'name': name, 'command': command, 'exit_code': result.returncode,
                           'status': 'PASS' if result.returncode == 0 else 'FAIL', 'seconds': time.monotonic() - started,
                           'stdout': result.stdout, 'stderr': result.stderr})
            print(f'{name}: {checks[-1]["status"]}', flush=True)
        # Explicit refusal commands are successful checks only when they fail clearly with no artifact writes.
        for task in ('disaster_risk', 'flood_segmentation', 'destination_stress'):
            result = subprocess.run([sys.executable, '-m', 'safarsaathi_ml.cli', 'train', '--model', task], cwd=project,
                                    env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
            checks.append({'name': f'{task}_training_refused', 'status': 'PASS' if result.returncode == 2 and 'unavailable' in result.stderr else 'FAIL',
                           'exit_code': result.returncode, 'stderr': result.stderr})
    # Reproduce review metrics read-only; preserve its existing evaluation files byte-for-byte.
    metadata = json.loads((artifact.parent / 'metadata.json').read_text(encoding='utf-8'))
    source = project.parent / Path(metadata['dataset_provenance']['repository_relative_path'])
    text, label = metadata['text_column'], metadata['label_column']
    frame = pd.read_csv(source)[[text, label]].dropna().drop_duplicates()
    frame[text] = frame[text].astype(str).str.strip(); frame = frame[frame[text].str.len() > 0]
    _, test = train_test_split(frame, test_size=.2, random_state=metadata['random_seed'], stratify=frame[label])
    predictions = joblib.load(artifact).predict(test[text])
    review_metrics = {'accuracy': float(accuracy_score(test[label], predictions)),
                      'macro_f1': float(f1_score(test[label], predictions, average='macro')),
                      'weighted_f1': float(f1_score(test[label], predictions, average='weighted'))}
    assert review_metrics['accuracy'] == review['metrics']['accuracy']
    prior_zip = project / 'release/SafarSaathi_Final.zip'
    comparison = 'prior release unavailable'
    if prior_zip.exists():
        with zipfile.ZipFile(prior_zip) as archived:
            prior_registry = json.loads(archived.read('models/registry.json'))
            prior_review = next(x for x in prior_registry if x['task'] == 'review classification')
            assert prior_review == review, 'Original review registry entry changed.'
            import hashlib
            assert hashlib.sha256(archived.read(review['artifact'])).hexdigest() == sha256(artifact)
        comparison = 'Review registry entry and artifact byte-identical to prior release ZIP.'
    after = {str(p.relative_to(project.parent)): sha256(p) for p in protected if p.is_file()}
    assert before == after, 'Protected review or archive evidence changed.'
    assert registry == load_registry(project / 'models/registry.json'), 'Verification mutated registry.'
    output = project / 'outputs/reports/ml_verification.json'
    history = []
    if output.exists():
        prior = json.loads(output.read_text(encoding='utf-8'))
        history = prior.get('prior_runs', []) + [{'generated_at': prior['generated_at'], 'checks': prior['checks']}]
    report = {'generated_at': utc_now(), 'checks': checks, 'prior_runs': history, 'review_readonly_evaluation': review_metrics,
              'preservation': {'protected_sha256': after, 'before_after_equal': True, 'prior_release_comparison': comparison,
                               'registry_unchanged_during_verification': True,
                               'registered_models': [m['model_id'] for m in registry]},
              'verification_scope': 'Python suite includes actual HTTP endpoints, local CORS, and Node frontend API client against a running backend. Browser rendering/interaction not automated.',
              'repository': 'No .git directory in workspace or project; no reset, checkout or commits performed.'}
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if any(c['status'] != 'PASS' for c in checks):
        raise SystemExit('One or more checks failed; inspect ml_verification.json.')
    return report


if __name__ == '__main__':
    verify()
