"""Production ASGI adapter for the existing SafarSaathi HTTP route logic."""
from __future__ import annotations

import logging
import os
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import integration_api
from .artifacts import ArtifactUnavailable
from .config import settings
from .http_api import (GET_ROUTES, POST_ROUTES, SCOPED_ROUTES, classify,
                       health, model_capabilities, model_metadata, models,
                       predict_capability, system_summary)
from .integration_services import DataUnavailable, public_metadata
from .registry import RegistryError

logger = logging.getLogger(__name__)
MAX_REQUEST_BYTES = 1_000_000


def allowed_origins() -> list[str]:
    """Use explicit production origins; local Vite origins remain useful in development."""
    configured = os.getenv("SAFARSAATHI_CORS_ORIGINS", "")
    origins = [value.strip().rstrip("/") for value in configured.split(",") if value.strip()]
    local = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"]
    return list(dict.fromkeys(origins + local))


app = FastAPI(title="SafarSaathi API", version="2026-11-render")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def response(status: int | HTTPStatus, payload: object) -> JSONResponse:
    return JSONResponse(status_code=int(status), content=payload)


def get_route(target: str):
    route = target.split("?", 1)[0]
    adapted = integration_api.get(settings().project_root, target)
    if adapted is not None:
        return adapted
    if route == "/health": return HTTPStatus.OK, health()
    if route == "/models": return HTTPStatus.OK, models()
    if route == "/capabilities": return HTTPStatus.OK, model_capabilities()
    if route == "/system/summary": return HTTPStatus.OK, public_metadata(system_summary())
    if route == "/stress/indicator-metadata":
        from .pressure_indicators import load_indicators
        data = load_indicators(settings().project_root)
        years = {}
        for row in data["records"]: years.setdefault(row["geography"], []).append(row["year"])
        return HTTPStatus.OK, {**{key: data[key] for key in ["status", "geographies", "years", "formulae", "missing_data_rule", "limitations"]}, "geography_years": {key: sorted(set(value)) for key, value in years.items()}}
    if route.startswith("/models/"):
        metadata = model_metadata(route.removeprefix("/models/"))
        return (HTTPStatus.OK, public_metadata(metadata)) if metadata else (HTTPStatus.NOT_FOUND, {"detail": "Requested model is not available."})
    return HTTPStatus.NOT_FOUND, {"detail": "Endpoint not found."}


def post_route(route: str, payload: object):
    if route in integration_api.POST_ROUTES:
        result = integration_api.post(settings().project_root, route, payload)
        return result or (HTTPStatus.NOT_FOUND, {"detail": "Endpoint not found."})
    if route in SCOPED_ROUTES:
        from .scoped_forecasts import load_scoped, predict_scoped
        try: load_scoped(settings().project_root, SCOPED_ROUTES[route])
        except Exception: return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable", "detail": "No validated scoped forecasting artifact is available."}
        try: return HTTPStatus.OK, predict_scoped(settings().project_root, SCOPED_ROUTES[route], payload)
        except ValueError: return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Expected supported geography and integer horizon only; see capability metadata."}
    if route == "/stress/indicators":
        from .pressure_indicators import indicators, load_indicators
        try: load_indicators(settings().project_root); return HTTPStatus.OK, indicators(settings().project_root, payload)
        except ValueError: return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Expected supported geography and observed year; national 2011–2024, State/UT 2023–2024."}
        except Exception: return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable", "detail": "Historical indicator snapshot is unavailable."}
    if route == "/tourism/monthly-forecast":
        from .monthly_forecasting import forecast_monthly
        if not isinstance(payload, dict) or set(payload) != {"destination", "horizon"} or payload.get("destination") != "IND" or type(payload.get("horizon")) is not int or not 1 <= payload["horizon"] <= 6:
            return HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Expected destination=IND and integer monthly horizon=1..6."}
        try: return HTTPStatus.OK, forecast_monthly(settings().project_root, payload["destination"], payload["horizon"])
        except Exception: return HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable", "detail": "No validated monthly FTA artifact is available."}
    routes = {"/tourism/forecast": "tourism_demand", "/disaster/predict": "disaster_risk", "/flood/segment": "flood_segmentation", "/stress/predict": "destination_stress"}
    return classify(payload) if route == "/reviews/classify" else predict_capability(routes[route], payload)


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def api(request: Request, path: str):
    route = "/" + path
    target = route + (f"?{request.url.query}" if request.url.query else "")
    try:
        if request.method == "GET":
            if route in POST_ROUTES: return response(HTTPStatus.METHOD_NOT_ALLOWED, {"detail": "Method not allowed."})
            return response(*get_route(target))
        if route not in POST_ROUTES: return response(HTTPStatus.NOT_FOUND, {"detail": "Endpoint not found."})
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            return response(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"detail": "Content-Type must be application/json."})
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES: return response(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"detail": "Request body exceeds the configured limit."})
        try: payload = await request.json()
        except Exception: return response(HTTPStatus.BAD_REQUEST, {"detail": "Request body must be valid JSON."})
        return response(*post_route(route, payload))
    except ValueError as exc:
        return response(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": str(exc)})
    except (RegistryError, ArtifactUnavailable, OSError, DataUnavailable):
        logger.warning("Saved data unavailable for %s", route)
        return response(HTTPStatus.SERVICE_UNAVAILABLE, {"detail": "Saved model or data is unavailable."})
    except Exception:
        logger.exception("Unhandled API failure for %s", route)
        return response(HTTPStatus.INTERNAL_SERVER_ERROR, {"detail": "Request could not be completed."})
