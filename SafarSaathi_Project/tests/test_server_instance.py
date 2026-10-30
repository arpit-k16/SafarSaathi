import os
import pytest
from safarsaathi_ml.http_api import ThreadingHTTPServer,Handler,health


def test_health_identifies_current_api_schema():
    assert health()['service']=='SafarSaathi'
    assert health()['api_schema_version']=='2026-10-25-completion'


def test_duplicate_port_binding_cannot_silently_start_stale_instance():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    try:
        with pytest.raises(OSError):
            second=ThreadingHTTPServer(('127.0.0.1',server.server_port),Handler)
            second.server_close()
    finally:server.server_close()
