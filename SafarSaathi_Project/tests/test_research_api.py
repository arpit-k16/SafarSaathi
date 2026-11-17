import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest
from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer
from safarsaathi_ml.integration_api import get
from test_research_optimization import payload


@pytest.fixture
def endpoint():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}'
    finally: server.shutdown(); thread.join(); server.server_close()


def call(base, path, body=None):
    request = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Content-Type': 'application/json'})
    try: response = urlopen(request, timeout=20)
    except HTTPError as exc: response = exc
    with response: return response.status, json.loads(response.read())


def test_new_optimizer_http_and_report_recomputation(endpoint):
    assert call(endpoint, '/optimization/metadata')[1]['algorithms'] == ['ga', 'pso']
    request = payload('pso')
    status, result = call(endpoint, '/optimization/allocate', request)
    assert status == 200 and result['status'] == 'EXPERIMENTAL_HYPOTHETICAL_ALLOCATION'
    assert result['conservation_error'] < 1e-6
    assert not result['globally_optimal']
    status, report = call(endpoint, '/reports/generate', {'optimization': request})
    assert status == 200
    assert report['optimization']['allocations'] == result['allocations']
    assert call(endpoint, '/reports/generate', {'optimization': result})[0] == 422
    bad = payload(); bad['problem']['demand'] = 10000
    assert call(endpoint, '/optimization/allocate', bad)[0] == 422
    # Original unavailable operational endpoint and its tests remain intact.
    assert call(endpoint, '/optimization/solve', {})[0] == 501


def test_missing_research_evidence_not_fabricated(tmp_path):
    status, result = get(tmp_path, '/research/status')
    assert status == 503 and result['status'] == 'unavailable'
