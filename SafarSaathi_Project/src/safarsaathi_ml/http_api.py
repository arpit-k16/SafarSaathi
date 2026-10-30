"""Dependency-light JSON HTTP backend; requests only read persisted artifacts."""
from __future__ import annotations
import json
import os
import socket
import logging
from urllib.parse import urlsplit
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as _ThreadingHTTPServer
from .inference import classify_reviews
from .persistence import list_models, model_metadata
from .config import settings
from .artifacts import ArtifactUnavailable
from .registry import RegistryError
from . import integration_api
from .integration_services import DataUnavailable, public_metadata

logger = logging.getLogger(__name__)

MAX_REQUEST_BYTES = 1_000_000
LOCAL_ORIGINS = {f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in (3000, 5173, 4173)}
POST_ROUTES = {'/reviews/classify', '/tourism/forecast', '/tourism/monthly-forecast', '/disaster/predict', '/flood/segment', '/stress/predict'}
GET_ROUTES = {'/health', '/models', '/system/summary', '/capabilities'}
SCOPED_ROUTES={'/disaster/cyclone-count':'cyclone_count','/environment/pm25-forecast':'pm25'}
POST_ROUTES.update(SCOPED_ROUTES)
POST_ROUTES.add('/stress/indicators')
GET_ROUTES.add('/stress/indicator-metadata')
GET_ROUTES.update(integration_api.GET_ROUTES)
POST_ROUTES.update(integration_api.POST_ROUTES)

class ThreadingHTTPServer(_ThreadingHTTPServer):
    # Windows SO_REUSEADDR can let a second instance bind an occupied port and route to stale code.
    allow_reuse_address = os.name != 'nt'
    def server_bind(self):
        if os.name == 'nt': self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

def model_capabilities():
    from .capabilities import capabilities
    return capabilities(settings().project_root)

def predict_capability(task: str, payload: object):
    from .readiness import IDS
    from .forecasting import forecast
    if task not in IDS:
        return HTTPStatus.NOT_FOUND, {'detail': 'Unknown capability.'}
    if not isinstance(payload, dict):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Request body must be an object.'}
    if task == 'flood_segmentation':
        from .flood_baseline import load_flood,segment
        try: load_flood(settings().project_root)
        except Exception: return HTTPStatus.SERVICE_UNAVAILABLE,{'status':'not_trained','model_id':IDS[task],'detail':'No validated flood-scene segmentation artifact is available.'}
        try:return HTTPStatus.OK,segment(settings().project_root,payload)
        except ValueError:return HTTPStatus.UNPROCESSABLE_ENTITY,{'detail':'Expected supported 128x128x2 STURM-preprocessed image and bounded metadata.'}
        except Exception:return HTTPStatus.SERVICE_UNAVAILABLE,{'status':'unavailable','detail':'Saved segmentation artifact is unavailable.'}
    if task != 'tourism_demand':
        item = next(i for i in model_capabilities() if i['model_id'] == IDS[task])
        return HTTPStatus.SERVICE_UNAVAILABLE, {'status': 'not_trained', 'model_id': IDS[task], 'detail': item['reason']}
    if set(payload) != {'destination', 'horizon'} or payload.get('destination') != 'IND' or type(payload.get('horizon')) is not int or not 1 <= payload['horizon'] <= 3:
        return HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Expected only destination=IND and integer horizon=1..3.'}
    try:
        return HTTPStatus.OK, forecast(settings().project_root, payload['destination'], payload['horizon'])
    except Exception:
        return HTTPStatus.SERVICE_UNAVAILABLE, {'status': 'unavailable', 'detail': 'No validated tourism artifact is available.'}

def health() -> dict[str, object]:
    return {"status": "ok", "trained_models": len(list_models()), "training_on_request": False,
            'service':'SafarSaathi','api_schema_version':'2026-10-25-completion'}

def models() -> list[dict[str, object]]:
    return [{"model_id": item.get("model_id"), "task": item.get("task"), "trained_at": item.get("trained_at"), "metrics": item.get("metrics"), "limitations": item.get("limitations"),
             'model_version': item.get('model_version', item['model_id']),
             'quality_status': item.get('quality_status', 'TRAINED_BUT_EXPERIMENTAL' if item['model_id'] == 'tourism_demand_forecaster' else 'TRAINED_AND_EVALUATED')} for item in list_models()]

def system_summary() -> dict[str, object]:
    project = settings().project_root
    audits = sorted((project / "outputs" / "metrics").glob("*_evaluation_audit.json"))
    evaluation = json.loads(audits[-1].read_text(encoding="utf-8")) if audits else None
    inventory_file = project / "release" / "dataset_inventory_summary.json"
    inventory = json.loads(inventory_file.read_text(encoding="utf-8")) if inventory_file.exists() else None
    return {"models": models(), "evaluation": evaluation, "dataset_inventory": inventory,
            "operational_data_status": "unavailable", "operational_data_note": "No validated live sensor, occupancy, routing, or emergency-dispatch feed is configured."}

def classify(payload: object) -> tuple[int, dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("model_id"), str) or not payload['model_id'].strip() or not isinstance(payload.get("reviews"), list):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "model_id and reviews[] are required."}
    if not 1 <= len(payload['reviews']) <= 100 or not all(isinstance(r, str) and r.strip() for r in payload['reviews']):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Expected 1 to 100 non-empty review strings.'}
    if model_metadata(payload["model_id"]) is None:
        return HTTPStatus.NOT_FOUND, {"detail": "Requested model is not available."}
    try:
        return HTTPStatus.OK, classify_reviews(payload["model_id"], payload["reviews"])
    except ArtifactUnavailable:
        return HTTPStatus.SERVICE_UNAVAILABLE, {'status': 'unavailable', 'detail': 'Saved review artifact is unavailable.'}
    except ValueError as exc:
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": str(exc)}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
        origin = self.headers.get('Origin')
        if origin in LOCAL_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin); self.send_header('Vary', 'Origin')
        if status == HTTPStatus.METHOD_NOT_ALLOWED:
            self.send_header('Allow', 'POST, OPTIONS' if self.path in POST_ROUTES else 'GET, OPTIONS')
        self.end_headers()
        if self.command != 'HEAD': self.wfile.write(body)
    def send_error(self, code, message=None, explain=None):
        self._send(code, {'detail': 'Unsupported HTTP request.'})
    def _wrong_method(self):
        route = urlsplit(self.path).path
        known = route in POST_ROUTES | GET_ROUTES or route.startswith(('/models/', '/destinations/'))
        self._send(HTTPStatus.METHOD_NOT_ALLOWED if known else HTTPStatus.NOT_FOUND, {'detail': 'Method not allowed.' if known else 'Endpoint not found.'})
    do_PUT = _wrong_method
    do_PATCH = _wrong_method
    do_DELETE = _wrong_method
    do_HEAD = _wrong_method
    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        origin = self.headers.get('Origin')
        if origin in LOCAL_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin); self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0'); self.end_headers()
    def log_message(self, *_: object) -> None: return
    def do_GET(self) -> None:
        try:
            self._get()
        except DataUnavailable as exc:
            logger.warning('Dataset adapter unavailable: %s', type(exc).__name__)
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {'status': 'unavailable', 'detail': str(exc)})
        except (RegistryError, ArtifactUnavailable, OSError, ValueError):
            logger.warning('Saved data unavailable for GET')
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, {'status': 'unavailable', 'detail': 'Saved model metadata is unavailable.'})
        except Exception:
            logger.error('Unhandled GET failure')
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {'detail': 'Request could not be completed.'})
    def _get(self) -> None:
        if urlsplit(self.path).path in POST_ROUTES: self._wrong_method(); return
        try:
            adapted = integration_api.get(settings().project_root, self.path)
        except ValueError as exc:
            self._send(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': str(exc)}); return
        if adapted is not None:
            self._send(*adapted); return
        if self.path == "/health": self._send(HTTPStatus.OK, health()); return
        if self.path == "/models": self._send(HTTPStatus.OK, models()); return
        if self.path == '/capabilities': self._send(HTTPStatus.OK, model_capabilities()); return
        if self.path == '/stress/indicator-metadata':
            from .pressure_indicators import load_indicators
            data=load_indicators(settings().project_root)
            geography_years = {}
            for record in data['records']:
                geography_years.setdefault(record['geography'], []).append(record['year'])
            geography_years = {key: sorted(set(years)) for key, years in geography_years.items()}
            self._send(HTTPStatus.OK,{**{k:data[k] for k in ['status','geographies','years','formulae','missing_data_rule','limitations']},'geography_years':geography_years});return
        if self.path == "/system/summary": self._send(HTTPStatus.OK, public_metadata(system_summary())); return
        if self.path.startswith("/models/"):
            metadata = model_metadata(self.path.removeprefix("/models/"))
            if metadata is None: self._send(HTTPStatus.NOT_FOUND, {"detail": "Requested model is not available."}); return
            self._send(HTTPStatus.OK, public_metadata(metadata)); return
        self._send(HTTPStatus.NOT_FOUND, {"detail": "Endpoint not found."})
    def do_POST(self) -> None:
        if urlsplit(self.path).path in GET_ROUTES or self.path.startswith(('/models/', '/destinations/')): self._wrong_method(); return
        routes = {'/tourism/forecast': 'tourism_demand', '/disaster/predict': 'disaster_risk', '/flood/segment': 'flood_segmentation', '/stress/predict': 'destination_stress'}
        if self.path not in POST_ROUTES: self._send(HTTPStatus.NOT_FOUND, {"detail": "Endpoint not found."}); return
        try:
            if self.headers.get('Transfer-Encoding'):
                self._send(HTTPStatus.BAD_REQUEST, {'detail': 'Transfer-Encoding is unsupported; send Content-Length.'}); return
            if 'Content-Length' not in self.headers:
                self._send(HTTPStatus.LENGTH_REQUIRED, {'detail': 'Content-Length is required.'}); return
            length = int(self.headers.get("Content-Length", "-1"))
            if length < 0:
                self._send(HTTPStatus.BAD_REQUEST, {'detail': 'Content-Length must be non-negative.'}); return
            if length > MAX_REQUEST_BYTES:
                # Drain only a narrowly oversized body before closing. On Windows,
                # closing with unread request bytes can reset the connection before
                # the client receives the intended 413 response.
                if length <= MAX_REQUEST_BYTES + 65536:
                    self.rfile.read(length)
                self.close_connection = True
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"detail": "Request body exceeds the configured limit."}); return
            if self.headers.get_content_type() != 'application/json':
                self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {'detail': 'Content-Type must be application/json.'}); return
            payload = json.loads(self.rfile.read(length), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError): self._send(HTTPStatus.BAD_REQUEST, {"detail": "Request body must be valid JSON."}); return
        try:
            if self.path in integration_api.POST_ROUTES:
                try: status, response = integration_api.post(settings().project_root, self.path, payload)
                except ValueError as exc:
                    status, response = HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': str(exc)}
            elif self.path in SCOPED_ROUTES:
                from .scoped_forecasts import load_scoped,predict_scoped
                kind=SCOPED_ROUTES[self.path]
                try:load_scoped(settings().project_root,kind)
                except Exception:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE,{'status':'unavailable','detail':'No validated scoped forecasting artifact is available.'});return
                try:status,response=HTTPStatus.OK,predict_scoped(settings().project_root,kind,payload)
                except ValueError:status,response=HTTPStatus.UNPROCESSABLE_ENTITY,{'detail':'Expected supported geography and integer horizon only; see capability metadata.'}
            elif self.path=='/stress/indicators':
                from .pressure_indicators import load_indicators,indicators
                try:load_indicators(settings().project_root)
                except Exception:
                    self._send(HTTPStatus.SERVICE_UNAVAILABLE,{'status':'unavailable','detail':'Historical indicator snapshot is unavailable.'});return
                try:status,response=HTTPStatus.OK,indicators(settings().project_root,payload)
                except ValueError:status,response=HTTPStatus.UNPROCESSABLE_ENTITY,{'detail':'Expected supported geography and observed year; national 2011–2024, State/UT 2023–2024.'}
            elif self.path == '/tourism/monthly-forecast':
                from .monthly_forecasting import forecast_monthly
                if not isinstance(payload, dict) or set(payload) != {'destination','horizon'} or payload.get('destination') != 'IND' or type(payload.get('horizon')) is not int or not 1 <= payload['horizon'] <= 6:
                    status,response = HTTPStatus.UNPROCESSABLE_ENTITY, {'detail':'Expected destination=IND and integer monthly horizon=1..6.'}
                else:
                    try: status,response = HTTPStatus.OK,forecast_monthly(settings().project_root,payload['destination'],payload['horizon'])
                    except Exception: status,response = HTTPStatus.SERVICE_UNAVAILABLE,{'detail':'No validated monthly FTA artifact is available.','status':'unavailable'}
            else:
                status, response = classify(payload) if self.path == '/reviews/classify' else predict_capability(routes[self.path], payload)
        except (RegistryError, ArtifactUnavailable, OSError, DataUnavailable):
            logger.warning('Saved data unavailable for POST')
            status, response = HTTPStatus.SERVICE_UNAVAILABLE, {'detail': 'Saved model is unavailable.'}
        except Exception:
            logger.error('Unhandled POST failure')
            status, response = HTTPStatus.INTERNAL_SERVER_ERROR, {'detail': 'Request could not be completed.'}
        self._send(status, response)

def serve(port: int = 8000) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
