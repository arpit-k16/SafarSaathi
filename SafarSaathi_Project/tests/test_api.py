from http import HTTPStatus
import json
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import pytest

from safarsaathi_ml.http_api import Handler, ThreadingHTTPServer, classify, health, models, system_summary
from safarsaathi_ml.persistence import list_models


def test_health_and_model_listing_are_read_only():
    assert health()["status"] == "ok"
    assert len(models()) == len(list_models())
    assert system_summary()["operational_data_status"] == "unavailable"


def test_review_endpoint_rejects_unknown_model():
    status, response = classify({"model_id": "not-a-model", "reviews": ["test"]})
    assert status == HTTPStatus.NOT_FOUND
    assert response["detail"]


def test_http_round_trip_health_and_malformed_request():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/health") as response:
                assert json.loads(response.read())["status"] == "ok"
        except URLError as error:
            if getattr(error.reason, "winerror", None) == 10013:
                pytest.skip("Sandbox blocks loopback sockets; exercised in the unsandboxed integration check.")
            raise
        request = Request(f"http://127.0.0.1:{server.server_port}/reviews/classify", data=b"not-json", method="POST", headers={'Content-Type': 'application/json'})
        try:
            urlopen(request)
        except HTTPError as error:
            assert error.code == 400
        oversized = Request(f"http://127.0.0.1:{server.server_port}/reviews/classify", data=b"x" * 1_000_001, method="POST")
        try:
            urlopen(oversized)
        except HTTPError as error:
            assert error.code == 413
    finally:
        server.shutdown(); thread.join()
