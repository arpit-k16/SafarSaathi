"""Start a fresh API process, make real HTTP requests, then stop only that child."""
import json
import os
import subprocess
import sys
import time
from urllib.request import Request, urlopen

from .config import settings

CHILD = '''from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
'''


def main():
    process = subprocess.Popen([sys.executable, '-u', '-c', CHILD], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env={**os.environ, 'PYTHONPATH': str(settings().project_root / 'src')})
    try:
        # Child only prints its bound local port; startup is bounded by the outer verification timeout.
        port = int(process.stdout.readline().strip())
        base = f'http://127.0.0.1:{port}'
        with urlopen(base + '/health', timeout=10) as response:
            assert json.loads(response.read())['training_on_request'] is False
        with urlopen(base + '/models', timeout=10) as response:
            models = json.loads(response.read())
        review = next(m for m in models if m['task'] == 'review classification')
        requests = [('/reviews/classify', {'model_id': review['model_id'], 'reviews': ['The hotel staff were helpful.']}),
                    ('/tourism/forecast', {'destination': 'IND', 'horizon': 1})]
        for path, body in requests:
            request = Request(base + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=10) as response:
                assert response.status == 200
        print(json.dumps({'fresh_process_startup': 'PASS', 'review_inference': 'PASS', 'forecast_inference': 'PASS'}))
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == '__main__':
    main()
