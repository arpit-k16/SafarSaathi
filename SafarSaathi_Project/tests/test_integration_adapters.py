"""Real local adapters, bounded HTTP contracts and isolated failure injection."""
import json
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import joblib
import pytest

from safarsaathi_ml import integration_api, integration_services as service
from safarsaathi_ml.artifacts import ArtifactUnavailable, load_artifact
from safarsaathi_ml.config import settings
from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer
from safarsaathi_ml.pipeline import sha256


PARAMETERS = {'baseline_visitors': 100, 'capacity': 120,
              'demand_change_percent': 50, 'available_capacity_percent': 50}


@pytest.fixture
def endpoint():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/health', timeout=5) as response:
                assert response.status == 200
        except URLError as exc:
            if getattr(exc.reason, 'winerror', None) == 10013:
                pytest.skip('Loopback is blocked by sandbox permissions.')
            raise
        yield base
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def call(endpoint, route, payload=None, method=None, origin='http://localhost:5173'):
    request = Request(endpoint + route,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      method=method, headers={'Content-Type': 'application/json', 'Origin': origin})
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as exc:
        response = exc
    with response:
        return response.status, json.loads(response.read()), response.headers


def test_real_data_adapters():
    project = settings().project_root
    data = service.tourism_history(project)
    assert data['is_forecast'] is False
    annual, monthly = data['series']
    assert len(annual['observations']) == 25
    assert annual['observations'][-1]['year'] == 2019
    assert len(monthly['observations']) == 72
    assert monthly['observations'][-1]['date'] == '2024-12'
    locations = service.destinations(project)['destinations']
    rishikesh = next(r for r in locations if r['id'] == 'rishikesh')
    assert rishikesh['query_coordinates']['latitude'] == 30.10865
    assert rishikesh['geometry']['coordinates'][:2] == [78.292, 30.109]
    assert len(service.map_layers(project)['features']) == len(locations)
    satellite = service.satellite_metadata(project)
    assert len(satellite['scenes']) == 12
    assert all(r['acquisition_from_product_id'] for r in satellite['scenes'])
    assert satellite['flood_analysis_available_for_these_scenes'] is False


def test_catalog_actual_files_and_pagination():
    project = settings().project_root
    first = service.dataset_inventory(project, limit=2)
    second = service.dataset_inventory(project, offset=2, limit=2)
    assert first['total'] > 900
    assert first['files'] != second['files']
    roots = service.dataset_roots(project)
    for record in first['files'] + second['files']:
        assert (roots[record['root']] / record['relative_path']).stat().st_size == record['size_bytes']
        assert not record['checksum_verified_this_request']
    assert not any(str(project) in str(r) for r in first['files'])


def test_hypothetical_scenario_conserves_visitors():
    result = service.capacity_scenario(PARAMETERS)
    assert result['baseline']['unserved_visitors'] == 0
    assert result['scenario']['visitors'] == 150
    assert result['scenario']['available_capacity'] == 60
    assert result['scenario']['served_visitors'] == 60
    assert result['scenario']['unserved_visitors'] == 90
    assert result['delta_unserved_visitors'] == 90
    assert result['is_prediction'] is False
    for availability in (0, 25, 100):
        result = service.capacity_scenario({**PARAMETERS, 'available_capacity_percent': availability})
        scenario = result['scenario']
        assert scenario['served_visitors'] + scenario['unserved_visitors'] == scenario['visitors']
        assert scenario['served_visitors'] <= scenario['available_capacity']
        assert (scenario['utilization_ratio'] is None) == (availability == 0)


@pytest.mark.parametrize('field,value', [('capacity', 0), ('capacity', True), ('baseline_visitors', -1),
    ('demand_change_percent', -101), ('demand_change_percent', float('nan')),
    ('available_capacity_percent', 101), ('available_capacity_percent', float('inf'))])
def test_scenario_rejects_invalid_inputs(field, value):
    with pytest.raises(ValueError):
        service.capacity_scenario({**PARAMETERS, field: value})


@pytest.mark.parametrize('function', [service.dataset_inventory, service.tourism_history,
                                    service.destinations, service.map_layers, service.satellite_metadata])
def test_missing_sources_are_explicit(function, tmp_path):
    with pytest.raises(service.DataUnavailable):
        function(tmp_path / 'empty_project')


def test_malformed_geospatial_data(tmp_path):
    root = tmp_path / 'data/raw_v2/weather_power'
    root.mkdir(parents=True)
    (root / 'POWER_bad.json').write_text('{"geometry": null}', encoding='utf-8')
    with pytest.raises(service.DataUnavailable):
        service.destinations(tmp_path)


def test_artifact_cache_rechecks_integrity_and_reuses_deserialization(tmp_path, monkeypatch):
    artifact = tmp_path / 'pipeline.joblib'
    joblib.dump({'stable': [1, 2]}, artifact)
    entry = {'artifact': 'pipeline.joblib', 'artifact_sha256': sha256(artifact)}
    import safarsaathi_ml.artifacts as artifacts
    original = artifacts.joblib.load
    calls = []

    def tracked(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(artifacts.joblib, 'load', tracked)
    assert load_artifact(tmp_path, entry) == {'stable': [1, 2]}
    assert load_artifact(tmp_path, entry) == {'stable': [1, 2]}
    assert len(calls) == 1
    artifact.write_bytes(b'corrupted after first inference')
    with pytest.raises(ArtifactUnavailable):
        load_artifact(tmp_path, entry)


def test_public_metadata_strips_nested_private_paths():
    result = service.public_metadata({'artifact': 'models/x', 'provenance': {'source_file': 'private',
                                    'file': 'C:\\private\\raw.csv'}, 'model_id': 'example'})
    assert result == {'model_id': 'example', 'provenance': {'file': '[local path omitted]'}}


@pytest.mark.parametrize('route,expected', [('/datasets?limit=2', 'LOCAL_INVENTORY'),
    ('/tourism/history', 'HISTORICAL_ONLY'), ('/destinations', 'STATIC_SOURCE_LOCATIONS'),
    ('/destinations/rishikesh', 'STATIC_SOURCE_LOCATION'), ('/map/layers', 'STATIC_SOURCE_LOCATIONS'),
    ('/satellite/metadata', 'RAW_IMAGERY_METADATA_ONLY')])
def test_http_get_contracts(endpoint, route, expected):
    status, result, headers = call(endpoint, route)
    assert status == 200
    assert result['status'] == expected
    assert headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'
    assert str(settings().project_root) not in str(result)


def test_http_scenario_report_and_blocked_optimizer(endpoint):
    status, result, _ = call(endpoint, '/scenarios/simulate', PARAMETERS)
    assert status == 200 and result['scenario']['unserved_visitors'] == 90
    status, result, _ = call(endpoint, '/reports/generate', {'scenario': PARAMETERS})
    assert status == 200 and result['generated_utc']
    assert result['report_type'] == 'safarsaathi_evidence_json'
    assert result['scenario']['scenario']['unserved_visitors'] == 90
    assert len(result['models']) == 6
    assert call(endpoint, '/reports/generate', {'results': 'invented'})[0] == 422
    assert call(endpoint, '/scenarios/simulate', {'capacity': 1})[0] == 422
    status, result, _ = call(endpoint, '/optimization/solve', {})
    assert status == 501 and result['status'] == 'NOT_IMPLEMENTED'
    assert call(endpoint, '/optimization/solve', {'budget': 100})[0] == 422


@pytest.mark.parametrize('route', ['/datasets?limit=201', '/datasets?offset=-1', '/datasets?limit=true',
    '/datasets?limit=1&limit=2', '/datasets?path=../../private', '/destinations?unknown=1'])
def test_invalid_query_contract(endpoint, route):
    assert call(endpoint, route)[0] == 422


def test_methods_unknown_location_cors_and_frontend_status(endpoint):
    assert call(endpoint, '/destinations/absent')[0] == 404
    assert call(endpoint, '/datasets?limit=1', {}, method='POST')[0] == 405
    assert call(endpoint, '/scenarios/simulate')[0] == 405
    assert call(endpoint, '/datasets', method='PUT')[0] == 405
    status, result, headers = call(endpoint, '/integration/status', origin='https://untrusted.example')
    assert status == 200
    assert 'Access-Control-Allow-Origin' not in headers
    assert result['frontend_connected'] is True
    assert result['pages']['tourism-intelligence'] == 'CONNECTED'
    assert result['pages']['intervention-optimizer'] == 'NOT IMPLEMENTED'
    assert set(result['pages'].values()) <= {'CONNECTED', 'PARTIALLY CONNECTED', 'DEMO DATA', 'BACKEND UNAVAILABLE', 'NOT IMPLEMENTED'}


def test_http_source_failure_is_safe(endpoint, monkeypatch):
    def missing(*args, **kwargs):
        raise service.DataUnavailable('Tourism history source is missing or invalid.')

    monkeypatch.setattr(integration_api, 'tourism_history', missing)
    status, result, _ = call(endpoint, '/tourism/history')
    assert status == 503 and result['status'] == 'unavailable'
    assert 'Traceback' not in str(result)
