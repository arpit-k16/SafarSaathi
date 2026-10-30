"""Start the real CLI on a temporary loopback port and record HTTP evidence."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def main():
    project = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    opener = build_opener(ProxyHandler({}))
    results = []
    with (project / 'integration_docs/startup_server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'safarsaathi_ml.cli', 'serve', '--port', str(port)],
                                   cwd=project, env={**os.environ, 'PYTHONPATH': str(project / 'src')},
                                   stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            base = f'http://127.0.0.1:{port}'
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('CLI server exited before becoming ready.')
                try:
                    with opener.open(base + '/health', timeout=1):
                        break
                except URLError:
                    time.sleep(.1)
            else:
                raise RuntimeError('CLI server did not become ready.')

            def call(route, payload=None, expected=200):
                body = json.dumps(payload).encode() if payload is not None else None
                request = Request(base + route, data=body, headers={'Content-Type': 'application/json'})
                try:
                    response = opener.open(request, timeout=30)
                except HTTPError as exc:
                    response = exc
                with response:
                    data = json.loads(response.read())
                    if response.status != expected:
                        raise RuntimeError(f'{route} returned {response.status}, expected {expected}')
                    results.append({'route': route, 'method': request.get_method(), 'http_status': response.status,
                                    'response': data})
                    return data

            for route in ('/health', '/models', '/capabilities', '/system/summary', '/integration/status',
                          '/tourism/history', '/datasets?limit=2', '/destinations', '/destinations/rishikesh',
                          '/map/layers', '/satellite/metadata', '/stress/indicator-metadata'):
                call(route)
            call('/models/tourism_demand_forecaster')
            call('/reviews/classify', {'model_id': 'nlp-20261024T182952Z', 'reviews': ['Comfortable hotel with friendly staff.']})
            call('/tourism/forecast', {'destination': 'IND', 'horizon': 3})
            call('/tourism/monthly-forecast', {'destination': 'IND', 'horizon': 6})
            call('/disaster/cyclone-count', {'geography': 'NI', 'horizon': 2})
            call('/environment/pm25-forecast', {'geography': 'IND', 'horizon': 1})
            call('/stress/indicators', {'geography': 'IND', 'year': 2024})
            # Format-valid zeros verify inference mechanics, not raw-scene scientific accuracy.
            flood = call('/flood/segment', {'image': [[[0., 0.] for _ in range(128)] for _ in range(128)],
                                           'metadata': {'source_format': 'STURM-S1-preprocessed', 'geo_tags': {}}})
            assert flood['dimensions'] == [128, 128]
            # Avoid storing a large zero-input response as misleading analytical evidence.
            results[-1]['response'] = {k: v for k, v in flood.items() if k not in {'mask', 'confidence_map'}}
            results[-1]['input_note'] = 'Schema-valid zero tile; inference smoke only, not scientific validation.'
            scenario = {'baseline_visitors': 100, 'capacity': 120,
                        'demand_change_percent': 50, 'available_capacity_percent': 50}
            call('/scenarios/simulate', scenario)
            call('/reports/generate', {'scenario': scenario})
            call('/disaster/predict', {}, 503)
            call('/stress/predict', {}, 503)
            call('/optimization/solve', {}, 501)
            call('/scenarios/simulate', {'capacity': True}, 422)
        finally:
            process.terminate()
            process.wait(timeout=10)
    evidence = {'cli_startup_verified': True, 'loopback_only': True, 'requests': results,
                'external_services_tested': False, 'frontend_executed': False}
    (project / 'integration_docs/startup_smoke.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f'CLI startup and {len(results)} HTTP requests verified; process stopped.')


if __name__ == '__main__':
    main()
