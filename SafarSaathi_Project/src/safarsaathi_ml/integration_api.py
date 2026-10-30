"""Read-only API adapters and the scope of verified frontend client bindings."""
from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

from .integration_services import (DataUnavailable, capacity_scenario, dataset_inventory,
                                   destinations, map_layers, report, satellite_metadata,
                                   tourism_history)

GET_ROUTES = {'/datasets', '/destinations', '/map/layers', '/tourism/history',
              '/satellite/metadata', '/integration/status'}
POST_ROUTES = {'/scenarios/simulate', '/reports/generate', '/optimization/solve'}

PAGE_STATUS = {
    'landing': 'DEMO DATA', 'overview': 'PARTIALLY CONNECTED', 'destination-twin': 'PARTIALLY CONNECTED',
    'tourism-intelligence': 'CONNECTED', 'crowd-destination-stress': 'PARTIALLY CONNECTED',
    'risk-resilience': 'PARTIALLY CONNECTED', 'disaster-mode': 'PARTIALLY CONNECTED',
    'live-geospatial-map': 'PARTIALLY CONNECTED', 'satellite-intelligence': 'CONNECTED',
    'what-if-simulator': 'PARTIALLY CONNECTED', 'simulation-results': 'CONNECTED',
    'intervention-optimizer': 'NOT IMPLEMENTED', 'optimization-explanation': 'NOT IMPLEMENTED',
    'ai-model-center': 'CONNECTED', 'tourist-community-insights': 'CONNECTED',
    'data-hub': 'CONNECTED', 'reports-briefs': 'CONNECTED', 'notifications': 'NOT IMPLEMENTED',
    'settings': 'NOT IMPLEMENTED', 'help-architecture': 'PARTIALLY CONNECTED',
}


def get(project, target):
    parsed = urlsplit(target)
    route = parsed.path
    if route not in GET_ROUTES and not route.startswith('/destinations/'):
        return None
    if parsed.query and route != '/datasets':
        raise ValueError('This endpoint does not accept query parameters.')
    if route == '/datasets':
        query = parse_qs(parsed.query, keep_blank_values=True)
        if set(query) - {'offset', 'limit', 'category'} or any(len(v) != 1 for v in query.values()):
            raise ValueError('Expected offset, limit and optional category once each.')
        offset, limit = query.get('offset', ['0'])[0], query.get('limit', ['100'])[0]
        if not offset.isascii() or not offset.isdigit() or not limit.isascii() or not limit.isdigit():
            raise ValueError('offset and limit must be integers.')
        return HTTPStatus.OK, dataset_inventory(project, int(offset), int(limit), query.get('category', [None])[0])
    if route == '/integration/status':
        return HTTPStatus.OK, {'frontend_connected': True, 'pages': PAGE_STATUS,
                               'verification_date': '2026-10-30',
                               'reason': 'Client bindings implemented and browser-verified for the listed scope. This metadata is not a live browser heartbeat; runtime failures remain visible in the UI.'}
    if route == '/destinations':
        return HTTPStatus.OK, destinations(project)
    if route.startswith('/destinations/'):
        selected = next((r for r in destinations(project)['destinations'] if r['id'] == route.removeprefix('/destinations/')), None)
        if selected is None:
            return HTTPStatus.NOT_FOUND, {'detail': 'Destination not found.'}
        return HTTPStatus.OK, {'status': 'STATIC_SOURCE_LOCATION', 'destination': selected,
                               'limitations': destinations(project)['limitations']}
    service = {'/map/layers': map_layers, '/tourism/history': tourism_history,
               '/satellite/metadata': satellite_metadata}[route]
    return HTTPStatus.OK, service(project)


def post(project, route, payload):
    if route == '/scenarios/simulate':
        return HTTPStatus.OK, capacity_scenario(payload)
    if route == '/reports/generate':
        return HTTPStatus.OK, report(project, payload)
    if route == '/optimization/solve':
        if not isinstance(payload, dict) or payload:
            raise ValueError('No optimization input schema is supported; only an empty object can request availability.')
        return HTTPStatus.NOT_IMPLEMENTED, {'status': 'NOT_IMPLEMENTED',
                'detail': 'No verified intervention cost/benefit data, objective, constraints or optimizer implementation exists.',
                'requirements': ['Specify decision variables, intervention costs, feasible bounds and budget.',
                                 'Validate benefit estimates, objective and baseline before implementing GA/PSO.']}
    return None
