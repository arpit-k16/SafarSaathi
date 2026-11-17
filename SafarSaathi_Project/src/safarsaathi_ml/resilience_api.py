"""HTTP adapter for the digital twin, anomaly, hotspot and routing features."""
from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qsl

GET_ROUTES = {"/twin/metadata", "/anomalies", "/hotspots", "/routing/metadata", "/release"}
POST_ROUTES = {"/twin/state", "/routing/route", "/twin/interventions"}


def get(project: Path, target: str):
    route, _, query = target.partition("?")
    if route not in GET_ROUTES:
        return None
    from . import resilience, routing
    if route == "/twin/metadata": return HTTPStatus.OK, resilience.metadata(project)
    if route == "/anomalies": return HTTPStatus.OK, resilience.anomalies(project)
    if route == "/hotspots": return HTTPStatus.OK, resilience.hotspots(project, dict(parse_qsl(query)))
    if route == "/routing/metadata": return HTTPStatus.OK, routing.metadata(project)
    if route == "/release":
        from .release_gate import release
        data = release(project)
        return (HTTPStatus.OK, data) if data else (HTTPStatus.NOT_FOUND, {"detail": "No release has been frozen; run python -m safarsaathi_ml.release_gate."})
    return None


def post(project: Path, route: str, payload: object):
    from . import resilience, routing
    if route == "/twin/state": return HTTPStatus.OK, resilience.twin_state(project, payload)
    if route == "/routing/route": return HTTPStatus.OK, routing.route(project, payload)
    if route == "/twin/interventions": return HTTPStatus.OK, resilience.interventions(project, payload)
    return None
