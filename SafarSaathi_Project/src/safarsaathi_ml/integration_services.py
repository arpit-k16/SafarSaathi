"""Read-only dataset adapters. No raw writes, training, or operational claims."""
from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


class DataUnavailable(RuntimeError):
    """Required local source is absent or invalid."""


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def public_metadata(value):
    """Exclude local paths and source URLs that may contain credentials."""
    private = {'source', 'artifact', 'derived_source', 'source_file', 'source_path',
               'local_path', 'raw_root', 'path', 'official_url', 'url'}
    if isinstance(value, dict):
        return {k: public_metadata(v) for k, v in value.items() if k not in private}
    if isinstance(value, list):
        return [public_metadata(v) for v in value]
    if isinstance(value, str) and (re.search(r'[A-Za-z]:[\\/]', value) or value.startswith(('/', '\\\\'))):
        return '[local path omitted]'
    return value


def dataset_roots(project):
    return {
        'raw_collection': project.parent / 'SafarSaathi_Datasets/raw',
        'project_raw': project / 'data/raw_v2',
        'project_external': project / 'data/external',
        'project_derived': project / 'data/processed',
        'indicators': project / 'outputs/indicators',
    }


def dataset_files(project):
    """Join actual file stats with declared provenance; existence is not validation."""
    try:
        return _dataset_files(project)
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        raise DataUnavailable('Local dataset inventory or provenance manifest is invalid.') from exc


def _dataset_files(project):
    manifest = project.parent / 'SafarSaathi_Datasets/DATA_MANIFEST.csv'
    provenance = {}
    if manifest.is_file():
        with manifest.open(encoding='utf-8-sig', newline='') as stream:
            provenance = {r['local_path'].replace('\\', '/'): r for r in csv.DictReader(stream)}
    records = []
    for label, root in dataset_roots(project).items():
        if not root.is_dir():
            continue
        for file in sorted(root.rglob('*')):
            # Do not follow links into arbitrary machine directories.
            if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
                continue
            relative = file.relative_to(root).as_posix()
            meta = provenance.get('raw/' + relative, {}) if label == 'raw_collection' else {}
            stat = file.stat()
            records.append({
                'root': label, 'relative_path': relative, 'filename': file.name,
                'category': relative.split('/')[0], 'format': file.suffix.lower() or None,
                'size_bytes': stat.st_size,
                'modified_utc': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                'source': meta.get('source') or None,
                'coverage_start': meta.get('coverage_start') or None,
                'coverage_end': meta.get('coverage_end') or None,
                'geographic_coverage': meta.get('geographic_coverage') or None,
                'license': meta.get('license') or None,
                'declared_sha256': meta.get('checksum') or None,
                'declared_size_matches': stat.st_size == int(meta['file_size_bytes']) if meta.get('file_size_bytes') else None,
                'checksum_verified_this_request': False,
                'availability': 'LOCAL_FILE', 'remote_connection_tested': False,
            })
    if not records:
        raise DataUnavailable('No local dataset files are available.')
    return records


def dataset_inventory(project, offset=0, limit=100, category=None):
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('offset must be non-negative; limit must be 1..200.')
    rows = dataset_files(project)
    if category is not None:
        rows = [r for r in rows if r['category'] == category]
    groups = {}
    for row in rows:
        key = row['root'] + '/' + row['category']
        group = groups.setdefault(key, {'files': 0, 'size_bytes': 0})
        group['files'] += 1
        group['size_bytes'] += row['size_bytes']
    return {'status': 'LOCAL_INVENTORY', 'generated_utc': timestamp(), 'total': len(rows),
            'offset': offset, 'limit': limit, 'groups': groups, 'files': rows[offset:offset + limit],
            'limitations': ['File presence is not an ingestion, integrity, inference or live-connection test.',
                            'Coverage and license are null when no per-file source manifest is available.',
                            'Original raw files are never modified; interim test fixtures are excluded.']}


def tourism_history(project):
    # These are the exact source readers used in training, not invented UI values.
    from .readiness import load_arrivals
    import pandas as pd
    from .monthly_forecasting import validate_series
    from .pipeline import sha256
    try:
        annual, provenance = load_arrivals(project.parent / 'SafarSaathi_Datasets/raw')
        derived = project / 'data/processed/tourism_monthly_fta/20261025'
        monthly_provenance = json.loads((derived / 'provenance.json').read_text(encoding='utf-8'))
        source = derived / 'monthly_fta.csv'
        if sha256(source) != monthly_provenance['derived_csv_sha256']:
            raise ValueError('Monthly source integrity mismatch.')
        monthly = pd.read_csv(source)
        validate_series(monthly)
        return {'status': 'HISTORICAL_ONLY', 'destination': 'IND', 'is_forecast': False,
                'series': [
                    {'frequency': 'annual', 'units': 'international tourist arrivals/year',
                     'source': public_metadata(provenance),
                     'observations': [{'year': int(r.year), 'arrivals': float(r.arrivals)} for r in annual.itertuples()]},
                    {'frequency': 'monthly', 'units': 'foreign tourist arrivals/month',
                     'source': public_metadata(monthly_provenance),
                     'observations': [{'date': str(r.date), 'arrivals': float(r.arrivals)} for r in monthly.itertuples()]},
                ], 'limitations': ['National series have different definitions and must not be combined.',
                                    'These records do not measure current destination footfall.']}
    except (OSError, ValueError, KeyError) as exc:
        raise DataUnavailable('Tourism history source is missing or invalid.') from exc


def destinations(project):
    root = project / 'data/raw_v2/weather_power'
    records = []
    try:
        for file in sorted(root.glob('POWER_*.json')):
            data = json.loads(file.read_text(encoding='utf-8'))
            query = data['_safarsaathi_query']
            coordinates = data['geometry']['coordinates']
            if data['geometry']['type'] != 'Point' or not 2 <= len(coordinates) <= 3:
                raise ValueError('Invalid source point.')
            if not all(type(x) in (int, float) and math.isfinite(x) for x in coordinates):
                raise ValueError('Non-finite source coordinates.')
            if not -180 <= coordinates[0] <= 180 or not -90 <= coordinates[1] <= 90:
                raise ValueError('Source coordinates out of range.')
            name = query['destination']
            if not isinstance(name, str) or not name.strip() or not isinstance(data['parameters'], dict):
                raise ValueError('Invalid source location metadata.')
            records.append({'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'),
                            'name': name, 'geometry': data['geometry'],
                            'query_coordinates': {'latitude': query['lat'], 'longitude': query['lon']},
                            'coverage_start': data['header']['start'], 'coverage_end': data['header']['end'],
                            'parameters': data['parameters'], 'source_file': file.name,
                            'source': 'NASA POWER archived reanalysis', 'live': False})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DataUnavailable('Location metadata is missing or invalid.') from exc
    if not records:
        raise DataUnavailable('Location metadata is unavailable.')
    return {'status': 'STATIC_SOURCE_LOCATIONS', 'destinations': records,
            'limitations': ['Points are NASA POWER grid locations, not destination boundaries or tourist clusters.',
                            'Requested query coordinates are separate from returned grid coordinates.',
                            'The source JSON does not declare an EPSG code. No live synchronization is configured.']}


def map_layers(project):
    data = destinations(project)
    return {'type': 'FeatureCollection', 'status': data['status'], 'live': False,
            'coordinate_metadata': 'Source-native geographic longitude/latitude; no EPSG code supplied in source JSON.',
            'features': [{'type': 'Feature', 'id': r['id'], 'geometry': r['geometry'],
                          'properties': {k: v for k, v in r.items() if k != 'geometry'}} for r in data['destinations']],
            'limitations': data['limitations'] + ['Roads, hazards, occupancy and infrastructure layers are not implemented.']}


def satellite_metadata(project):
    rows = [r for r in dataset_files(project) if r['root'] == 'raw_collection' and r['category'] in {'sentinel1', 'sentinel2'}]
    scenes = {}
    for row in rows:
        parts = row['relative_path'].split('/')
        if len(parts) < 3 or not parts[1].startswith(('S1', 'S2')):
            continue
        key = '/'.join(parts[:2])
        scene = scenes.setdefault(key, {'mission': parts[0], 'product_id': parts[1], 'files': 0, 'size_bytes': 0,
                                       'acquisition_from_product_id': None, 'geographic_coverage': row['geographic_coverage'],
                                       'source': row['source'], 'license': row['license']})
        match = re.search(r'(\d{8}T\d{6})', parts[1])
        if match:
            scene['acquisition_from_product_id'] = datetime.strptime(match[1], '%Y%m%dT%H%M%S').isoformat() + 'Z'
        scene['files'] += 1
        scene['size_bytes'] += row['size_bytes']
    if not scenes:
        raise DataUnavailable('Local Sentinel scene metadata is unavailable.')
    return {'status': 'RAW_IMAGERY_METADATA_ONLY', 'scenes': list(scenes.values()),
            'flood_analysis_available_for_these_scenes': False,
            'limitations': ['Acquisition times are parsed from product identifiers; files are inventoried, not image-validated.',
                            'No raw-scene preprocessing into the STURM benchmark input is implemented.',
                            'Sentinel-2 catalogue names can differ from AWS processing baselines; see raw SOURCE_INFO.txt.',
                            'No live overpasses, NDVI, InSAR, GLOF or local flood detections are inferred.']}


def capacity_scenario(payload):
    """One-period conservation accounting with explicit hypothetical denominators."""
    required = {'baseline_visitors', 'capacity', 'demand_change_percent', 'available_capacity_percent'}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError('Expected baseline_visitors, capacity, demand_change_percent and available_capacity_percent only.')
    bounds = {'baseline_visitors': (0, 1e9), 'capacity': (1, 1e9),
              'demand_change_percent': (-100, 1000), 'available_capacity_percent': (0, 100)}
    for key, (low, high) in bounds.items():
        value = payload[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} must be a finite number in [{low:g}, {high:g}].')
    demand = payload['baseline_visitors'] * (1 + payload['demand_change_percent'] / 100)
    capacity = payload['capacity'] * payload['available_capacity_percent'] / 100

    def outcomes(demand, capacity):
        return {'visitors': demand, 'available_capacity': capacity,
                'served_visitors': min(demand, capacity), 'unserved_visitors': max(0, demand - capacity),
                'utilization_ratio': demand / capacity if capacity else None}

    baseline = outcomes(payload['baseline_visitors'], payload['capacity'])
    scenario = outcomes(demand, capacity)
    return {'status': 'HYPOTHETICAL_CAPACITY_ACCOUNTING', 'parameters': dict(payload),
            'model_version': 'capacity-accounting-v1', 'baseline': baseline, 'scenario': scenario,
            'delta_unserved_visitors': scenario['unserved_visitors'] - baseline['unserved_visitors'],
            'units': 'visitors and visitor places in the same user-selected period', 'is_prediction': False,
            'assumptions': ['Inputs are user-supplied hypothetical values, not observed local capacity.',
                            'One period; no queue dynamics, road routing, rainfall effects or causal stress weights.',
                            'Served = min(demand, available capacity); unserved = max(0, demand - capacity).',
                            'Zero available capacity gives null utilization, not infinity.'],
            'limitations': ['This is a capacity arithmetic scenario, not a validated stress, evacuation, delay or hazard model.']}


def report(project, payload):
    """Recompute evidence server-side; never accept purported results from clients."""
    if not isinstance(payload, dict) or set(payload) - {'scenario'}:
        raise ValueError('Expected an object with optional scenario parameters only.')
    scenario = capacity_scenario(payload['scenario']) if 'scenario' in payload else None
    from .http_api import models
    return {'report_type': 'safarsaathi_evidence_json', 'generated_utc': timestamp(),
            'models': models(), 'dataset_inventory': dataset_inventory(project, limit=1)['groups'],
            'scenario': scenario,
            'sources': ['Local model registry and pinned artifacts', 'Local dataset file stats and collection manifest'],
            'limitations': ['Registry metrics are recorded evaluations, not a new evaluation run.',
                            'No live telemetry is included. PDF export is not implemented.',
                            'Scenarios, when present, are recomputed from explicit hypothetical inputs.']}
