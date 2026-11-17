"""Deployment snapshot fallback, climate endpoint and single-origin hosting."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from safarsaathi_ml import snapshot
from safarsaathi_ml.asgi import app
from safarsaathi_ml.config import settings

PROJECT = settings().project_root
POWER = PROJECT / 'data/raw_v2/weather_power'


def test_climate_summary_uses_source_values_and_skips_fill():
    data = {'header': {'fill_value': -999.0, 'start': '20000101', 'end': '20000229'},
            'parameters': {'PRECTOTCORR': {'units': 'mm/day'}, 'T2M': {'units': 'C'}},
            'properties': {'parameter': {
                'PRECTOTCORR': {'20000101': 1.0, '20000102': 3.0, '20000201': -999.0, '20000202': 5.0},
                'T2M': {'20000101': 2.0, '20000102': 4.0, '20000201': 6.0}}}}
    result = snapshot.climate_from_power(data)
    january, february = result['monthly_climatology'][:2]
    assert january['PRECTOTCORR'] == 4.0 and january['T2M'] == 3.0
    assert february['PRECTOTCORR'] == 5.0  # fill value excluded, not treated as rain
    assert result['units']['PRECTOTCORR'] == 'mm/month'
    assert result['extremes']['wettest_day'] == {'date': '2000-02-02', 'mm': 5.0}
    assert result['annual'] == [{'year': 2000, 'precip_total_mm': 9.0, 'T2M_mean': 4.0}]


def test_snapshot_checksum_is_enforced(tmp_path, monkeypatch):
    (tmp_path / 'deploy_snapshot').mkdir()
    (tmp_path / 'deploy_snapshot/destinations.json').write_text('{"tampered":true}')
    (tmp_path / 'deploy_snapshot/manifest.json').write_text(json.dumps({
        'generated_utc': 'x', 'sections': {'destinations': {'file': 'destinations.json', 'sha256': '0' * 64}}}))
    snapshot._load_section.cache_clear()
    with pytest.raises(snapshot.SnapshotUnavailable):
        snapshot.load_section(tmp_path, 'destinations')
    snapshot._load_section.cache_clear()


def test_snapshot_mode_serves_labelled_snapshot(monkeypatch):
    if not (PROJECT / 'deploy_snapshot/manifest.json').is_file():
        pytest.skip('No deployment snapshot has been built on this installation.')
    monkeypatch.setenv('SAFARSAATHI_DATA_MODE', 'snapshot')
    client = TestClient(app)
    body = client.get('/destinations').json()
    assert body['data_origin'] == snapshot.SNAPSHOT and len(body['destinations']) >= 1
    first = body['destinations'][0]['id']
    climate = client.get(f'/destinations/{first}/climate')
    assert climate.status_code == 200
    assert climate.json()['is_forecast'] is False and len(climate.json()['monthly_climatology']) == 12
    assert client.get('/destinations/not-a-place/climate').status_code == 404
    status = client.get('/deployment/status').json()
    assert status['snapshot']['mode'] == 'snapshot'


def test_live_and_snapshot_climate_agree(monkeypatch):
    if not any(POWER.glob('POWER_*.json')) or not (PROJECT / 'deploy_snapshot/manifest.json').is_file():
        pytest.skip('Needs both live POWER files and a built snapshot.')
    client = TestClient(app)
    monkeypatch.setenv('SAFARSAATHI_DATA_MODE', 'live')
    live = client.get('/destinations/kedarnath/climate').json()
    monkeypatch.setenv('SAFARSAATHI_DATA_MODE', 'snapshot')
    snap = client.get('/destinations/kedarnath/climate').json()
    assert live['data_origin'] == snapshot.LIVE and snap['data_origin'] == snapshot.SNAPSHOT
    assert live['monthly_climatology'] == snap['monthly_climatology']


def test_api_prefix_and_static_spa(tmp_path, monkeypatch):
    client = TestClient(app)
    assert client.get('/api/health').json()['status'] == 'ok'
    assert client.post('/api/scenarios/simulate', json={'baseline_visitors': 10, 'capacity': 10,
                       'demand_change_percent': 0, 'available_capacity_percent': 100}).status_code == 200
    dist = tmp_path / 'dist'
    (dist / 'assets').mkdir(parents=True)
    (dist / 'index.html').write_text('<!doctype html><div id="root"></div>')
    (dist / 'assets/app.js').write_text('console.log(1)')
    monkeypatch.setenv('SAFARSAATHI_STATIC_DIR', str(dist))
    assert 'id="root"' in client.get('/').text
    assert client.get('/assets/app.js').headers['cache-control'].endswith('immutable')
    assert client.get('/assets/missing.js').status_code == 404
    assert client.get('/health').json()['status'] == 'ok'  # API routes still win over the SPA
    from safarsaathi_ml.asgi import static_response
    escaped = static_response('/../../../etc/passwd')  # resolved outside dist: never served
    assert escaped is None or str(escaped.path).endswith('index.html')


def test_data_unavailable_detail_is_actionable(monkeypatch, tmp_path):
    monkeypatch.setenv('SAFARSAATHI_DATA_MODE', 'snapshot')
    monkeypatch.setattr(snapshot, 'snapshot_dir', lambda project: tmp_path / 'absent')
    snapshot._load_section.cache_clear()
    response = TestClient(app).get('/datasets')
    assert response.status_code == 503
    assert 'build-snapshot' in response.json()['detail']
    snapshot._load_section.cache_clear()


def test_report_survives_missing_inventory(monkeypatch, tmp_path):
    monkeypatch.setenv('SAFARSAATHI_DATA_MODE', 'snapshot')
    monkeypatch.setattr(snapshot, 'snapshot_dir', lambda project: tmp_path / 'absent')
    snapshot._load_section.cache_clear()
    response = TestClient(app).post('/reports/generate', json={})
    assert response.status_code == 200
    assert response.json()['dataset_inventory'] is None and 'build-snapshot' in response.json()['dataset_inventory_note']
    snapshot._load_section.cache_clear()
