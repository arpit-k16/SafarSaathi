"""Regression coverage for defects found in the final audit; all fault writes isolated."""
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import pytest

from safarsaathi_ml.baseline_comparison import compare, predict_at_origin
from safarsaathi_ml.config import Settings, settings
from safarsaathi_ml.forecasting import AnnualForecaster, metrics
from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer
from safarsaathi_ml.readiness import validate_observed_table
from safarsaathi_ml.registry import RegistryError, atomic_write_registry, load_registry, normalize_artifact_path, registry_lock


@contextmanager
def server():
    service = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=service.serve_forever, daemon=True); thread.start()
    try:
        yield f'http://127.0.0.1:{service.server_port}'
    finally:
        service.shutdown(); thread.join(); service.server_close()


def call(url, path, payload=None, method=None, body=None, content_type='application/json'):
    data = body if body is not None else (json.dumps(payload).encode() if payload is not None else None)
    request = Request(url + path, data=data, method=method, headers={'Content-Type': content_type})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as exc:
        response = exc
    except URLError as exc:
        if getattr(exc.reason, 'winerror', None) == 10013:
            pytest.skip('Sandbox blocks real HTTP; rerun with loopback access.')
        raise
    with response:
        encoded = response.read()
        assert response.headers.get_content_type() == 'application/json'
        decoded = json.loads(encoded) if encoded else {}
        if response.status >= 400:
            assert 'detail' in decoded and 'Traceback' not in str(decoded)
            assert ':\\' not in str(decoded) and 'pipeline.joblib' not in str(decoded)
        return response.status, decoded, response.headers


@pytest.fixture
def endpoint():
    with server() as url:
        yield url


@pytest.mark.parametrize('payload', [[], {}, {'model_id': None, 'reviews': ['a']}, {'model_id': 1, 'reviews': ['a']},
    {'model_id': '', 'reviews': ['a']}, {'model_id': 'x', 'reviews': None}, {'model_id': 'x', 'reviews': []},
    {'model_id': 'x', 'reviews': ['']}, {'model_id': 'x', 'reviews': [None]}, {'model_id': 'x', 'reviews': [3]},
    {'model_id': 'x', 'reviews': ['a'] * 101}])
def test_review_request_schema(endpoint, payload):
    assert call(endpoint, '/reviews/classify', payload)[0] == 422


@pytest.mark.parametrize('payload', [[], {}, {'destination': None, 'horizon': 1}, {'destination': 4, 'horizon': 1},
    {'destination': '', 'horizon': 1}, {'destination': 'Uttarakhand', 'horizon': 1}, {'destination': 'IND', 'horizon': None},
    {'destination': 'IND', 'horizon': 0}, {'destination': 'IND', 'horizon': 4}, {'destination': 'IND', 'horizon': 1.5},
    {'destination': 'IND', 'horizon': True}, {'destination': 'IND', 'horizon': '1'}, {'destination': 'IND', 'horizon': 1, 'path': '../secret'}])
def test_forecast_request_schema(endpoint, payload):
    assert call(endpoint, '/tourism/forecast', payload)[0] == 422


@pytest.mark.parametrize('path', ['/reviews/classify', '/tourism/forecast'])
@pytest.mark.parametrize('body,status,content_type', [(b'{broken', 400, 'application/json'), (b'\xff', 400, 'application/json'),
    (b'{"value":NaN}', 400, 'application/json'), (b'x' * 1000001, 413, 'application/json'),
    (b'{}', 415, 'text/plain'), (b'{}', 415, 'application/x-www-form-urlencoded')],
    ids=['malformed-json', 'invalid-utf8', 'nonfinite-json', 'oversized-body', 'plain-text', 'form-content'])
def test_http_body_validation(endpoint, path, body, status, content_type):
    assert call(endpoint, path, body=body, content_type=content_type)[0] == status


@pytest.mark.parametrize('path,method', [('/tourism/forecast', 'GET'), ('/reviews/classify', 'GET'),
    ('/health', 'POST'), ('/models', 'PUT'), ('/tourism/forecast', 'DELETE'), ('/tourism/forecast', 'PATCH')])
def test_wrong_methods_are_json(endpoint, path, method):
    assert call(endpoint, path, payload={} if method != 'GET' else None, method=method)[0] == 405


def test_valid_requests_and_unknown_models(endpoint):
    model_id = next(m['model_id'] for m in load_registry(settings().models_root / 'registry.json') if m['task'] == 'review classification')
    status, result, _ = call(endpoint, '/reviews/classify', {'model_id': model_id, 'reviews': ['A clean room with helpful staff.']})
    assert status == 200 and result['predictions'][0] in {'NEGATIVE', 'POSITIVE'}
    assert result['model_version'] == model_id
    status, result, _ = call(endpoint, '/tourism/forecast', {'destination': 'IND', 'horizon': 3})
    assert status == 200 and result['forecast_origin_year'] == result['latest_observed_year'] == 2019
    assert result['horizon'] == 3 and result['quality_status'] == 'TRAINED_BUT_EXPERIMENTAL'
    assert [r['year'] for r in result['forecasts']] == [2020, 2021, 2022]
    assert call(endpoint, '/reviews/classify', {'model_id': 'unknown', 'reviews': ['a']})[0] == 404
    assert call(endpoint, '/models/unknown')[0] == 404


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    real = settings().project_root
    shutil.copytree(real / 'models', tmp_path / 'models')
    cfg = Settings(tmp_path, tmp_path / 'models', tmp_path / 'outputs')
    import safarsaathi_ml.config as config
    import safarsaathi_ml.persistence as persistence
    import safarsaathi_ml.http_api as api
    for module in (config, persistence, api): monkeypatch.setattr(module, 'settings', lambda: cfg)
    return tmp_path


@pytest.mark.parametrize('fault', ['missing_review', 'corrupt_review', 'missing_forecast', 'corrupt_forecast', 'bad_registry', 'invalid_utf8_registry'])
def test_artifact_and_registry_failures_are_safe(isolated_project, fault):
    registry = isolated_project / 'models/registry.json'
    entries = load_registry(registry)
    if fault in {'bad_registry', 'invalid_utf8_registry'}:
        registry.write_bytes(b'not json' if fault == 'bad_registry' else b'\xff')
    else:
        entry = entries[0] if 'review' in fault else entries[1]
        artifact = isolated_project / entry['artifact']
        if fault.startswith('missing'): artifact.unlink()
        else: artifact.write_bytes(b'corrupt isolated test artifact')
    with server() as url:
        path, payload = ('/reviews/classify', {'model_id': entries[0]['model_id'], 'reviews': ['clean']}) if 'review' in fault else ('/tourism/forecast', {'destination': 'IND', 'horizon': 1})
        assert call(url, path, payload)[0] == 503
        if 'registry' in fault:
            assert call(url, '/models')[0] == 503
            assert call(url, '/health')[0] == 503


def test_unexpected_error_does_not_expose_exception(endpoint, monkeypatch):
    import safarsaathi_ml.http_api as api
    monkeypatch.setattr(api, 'classify', lambda _: (_ for _ in ()).throw(RuntimeError('C:\\private\\secret token=do-not-expose')))
    status, body, _ = call(endpoint, '/reviews/classify', {'model_id': 'any', 'reviews': ['a']})
    assert status == 500 and 'secret' not in str(body)


def test_baselines_align_origins_and_never_use_future_targets():
    values = np.arange(25, dtype=float) * 20 + 100
    years = np.arange(1995, 2020)
    saved = AnnualForecaster('drift').fit(values[:20])
    a = compare(values, years, 15, 20, saved)
    changed = values.copy(); changed[20:] += 100000
    b = compare(changed, years, 15, 20, saved)
    for method in a['methods']:
        first = [r for r in a['methods'][method]['predictions'] if r['forecast_origin_year'] == 2014]
        other = [r for r in b['methods'][method]['predictions'] if r['forecast_origin_year'] == 2014]
        assert [r['prediction'] for r in first] == [r['prediction'] for r in other]
        assert [v['n'] for v in a['methods'][method]['by_horizon'].values()] == [5, 4, 3]
        assert a['methods'][method]['by_horizon']['1']['origins'] == [2014, 2015, 2016, 2017, 2018]
    assert a['mase_denominator'] == 20


def test_metric_denominators_and_invalid_arrays():
    score = metrics([0, 0], [1, 1], 0)
    assert score['WAPE'] is None and score['MASE'] is None
    assert metrics([0, 2], [1, 1], 2)['WAPE'] == 1
    for actual, predicted, scale in [([], [], 1), ([1], [1, 2], 1), ([np.nan], [1], 1), ([1], [1], -1)]:
        with pytest.raises(ValueError): metrics(actual, predicted, scale)


@pytest.mark.parametrize('value', ['models/foo:stream', 'models/a\x00b', '//server/share/file', 'C:/foo'])
def test_windows_path_edge_cases(value):
    with pytest.raises(RegistryError): normalize_artifact_path(value)


def test_atomic_duplicate_ids_and_unverified_entry_are_rejected(tmp_path):
    artifact = tmp_path / 'models/a.bin'; artifact.parent.mkdir(); artifact.write_bytes(b'fixture')
    entry = {'model_id': 'test', 'task': 'fixture', 'artifact': 'models/a.bin', 'persistence_test_passed': True}
    path = tmp_path / 'models/registry.json'
    with pytest.raises(RegistryError): atomic_write_registry(path, [entry, entry])
    with pytest.raises(RegistryError): atomic_write_registry(path, [{**entry, 'persistence_test_passed': False}])
    with registry_lock(path):
        with pytest.raises(RegistryError, match='locked'):
            with registry_lock(path, timeout_seconds=0): pass
    assert not path.with_suffix('.json.lock').exists()


def test_normalized_time_duplicates_and_empty_labels_rejected():
    frame = pd.DataFrame({'region_id': ['A', 'A'], 'date': ['2020-01-01T00:00:00Z', '2019-12-31T19:00:00-05:00'],
                          'target': [1, 1], 'available_at': ['2019-01-01', '2019-01-01']})
    with pytest.raises(ValueError, match='normalization'): validate_observed_table(frame, 'disaster_risk')
    with pytest.raises(ValueError): validate_observed_table(frame.iloc[:0], 'destination_stress')
