"""Actual HTTP requests and frontend API-client round trip; uses only saved models."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer


@pytest.fixture
def endpoint():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        try:
            with urlopen(url + '/health', timeout=5) as response:
                assert response.status == 200
        except URLError as exc:
            if getattr(exc.reason, 'winerror', None) == 10013:
                pytest.skip('Sandbox blocks loopback; rerun this integration test outside sandbox.')
            raise
        yield url
    finally:
        server.shutdown(); thread.join()


def test_forecasting_and_unavailable_routes_over_http(endpoint):
    with urlopen(endpoint + '/capabilities') as response:
        items = json.loads(response.read())
    assert len(items) == 4
    tourism = next(x for x in items if x['model_id'] == 'tourism_demand_forecaster')
    if not tourism['inference_available']:
        pytest.skip('No real tourism artifact registered on this installation.')
    body = json.dumps({'destination': 'IND', 'horizon': 2}).encode()
    request = Request(endpoint + '/tourism/forecast', data=body, headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:3000'})
    with urlopen(request) as response:
        result = json.loads(response.read())
        assert len(result['forecasts']) == 2
        assert response.headers['Access-Control-Allow-Origin'] == 'http://localhost:3000'
    with urlopen(Request(endpoint + '/tourism/forecast', method='OPTIONS', headers={'Origin': 'http://localhost:3000'})) as response:
        assert response.status == 204
        assert 'POST' in response.headers['Access-Control-Allow-Methods']
    for route in ('/disaster/predict', '/flood/segment', '/stress/predict'):
        with pytest.raises(HTTPError) as error:
            urlopen(Request(endpoint + route, data=b'{}', headers={'Content-Type': 'application/json'}))
        if route=='/flood/segment' and any(x['model_id']=='flood_segmentation_model' and x['inference_available'] for x in items):
            assert error.value.code==422
        else:
            assert error.value.code == 503
            assert json.loads(error.value.read())['status'] == 'not_trained'
    with pytest.raises(HTTPError) as error:
        urlopen(Request(endpoint + '/tourism/forecast', data=b'{"destination":"IND","horizon":true}', headers={'Content-Type': 'application/json'}))
    assert error.value.code == 422


def test_frontend_client_with_real_backend(endpoint):
    frontend = Path(__file__).resolve().parents[1] / 'frontend'
    if not (frontend / 'tests/api.test.js').is_file():
        pytest.skip('Current protected frontend has no API client or client integration test; see integration_docs/FRONTEND_INTEGRATION_STATUS.md.')
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is unavailable.')
    result = subprocess.run([node, '--test', 'tests/api.test.js'], cwd=frontend,
                            env={**os.environ, 'SAFARSAATHI_TEST_API': endpoint},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '# skipped 0' in result.stdout or 'skipped 0' in result.stdout
