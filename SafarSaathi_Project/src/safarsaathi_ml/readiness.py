"""Read-only, bounded discovery of evidence for the four proposed capabilities."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from .pipeline import sha256, utc_now

IDS = {
    'tourism_demand': 'tourism_demand_forecaster',
    'disaster_risk': 'disaster_risk_predictor',
    'flood_segmentation': 'flood_segmentation_model',
    'destination_stress': 'destination_stress_predictor',
}
ARRIVALS = 'worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json'


def load_arrivals(raw: Path) -> tuple[pd.DataFrame, dict]:
    path = raw / ARRIVALS
    if not path.is_file():
        raise ValueError('India World Bank arrivals JSON is missing.')
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
        raise ValueError('Invalid World Bank response schema.')
    records = []
    for row in payload[1]:
        if not isinstance(row, dict):
            raise ValueError('Every World Bank observation must be an object.')
        if row.get('indicator', {}).get('id') != 'ST.INT.ARVL' or row.get('countryiso3code') != 'IND':
            raise ValueError('Only IND annual international-arrival observations are supported.')
        try:
            if isinstance(row.get('date'), bool) or not str(row.get('date', '')).isdigit() or len(str(row['date'])) != 4:
                raise ValueError('Expected four-digit calendar year.')
            year = int(row['date'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('Every observation needs an annual date.') from exc
        records.append({'destination': 'IND', 'year': year, 'arrivals': row.get('value')})
    frame = pd.DataFrame(records)
    if frame.empty or frame.duplicated(['destination', 'year']).any():
        raise ValueError('Empty series or duplicate destination/year keys.')
    frame['arrivals'] = pd.to_numeric(frame.arrivals, errors='raise')
    import numpy as np
    if not np.isfinite(frame.arrivals.dropna()).all():
        raise ValueError('Arrivals targets must be finite.')
    observed = frame.dropna(subset=['arrivals']).sort_values('year').reset_index(drop=True)
    if observed.empty or (observed.arrivals < 0).any() or observed.arrivals.mod(1).ne(0).any():
        raise ValueError('Observed non-negative arrivals targets are required.')
    if len(observed) > 1 and not observed.year.diff().dropna().eq(1).all():
        raise ValueError('Internal missing years require explicit resolution; no imputation is applied.')
    profile = {'path': ARRIVALS, 'format': 'World Bank JSON', 'sha256': sha256(path),
               'rows': len(frame), 'observed_rows': len(observed), 'duplicate_keys': 0,
               'columns': {'destination': 'ISO3 string', 'year': 'int', 'arrivals': 'float/count'},
               'missing_rates': {c: float(frame[c].isna().mean()) for c in frame},
               'missing_target_years': frame.loc[frame.arrivals.isna(), 'year'].tolist(),
               'observed_years': [int(observed.year.min()), int(observed.year.max())],
               'geography': 'India national total; not Uttarakhand or individual destinations',
               'units': 'international tourist arrivals per calendar year; annual dates have no time zone',
               'imputation': 'none; trailing null targets excluded, internal gaps rejected',
               'source_updated': payload[0].get('lastupdated')}
    return observed, profile


def imagery_inventory(raw: Path) -> dict:
    images, masks = [], []
    for category in ('sentinel1', 'sentinel2'):
        for path in sorted((raw / category).rglob('*')):
            if path.is_file() and path.suffix.lower() in {'.tif', '.tiff', '.jp2', '.png'}:
                item = {'path': path.relative_to(raw).as_posix(), 'bytes': path.stat().st_size}
                # Header inspection only: never materialize full satellite pixel arrays.
                if path.suffix.lower() in {'.tif', '.tiff'}:
                    try:
                        from PIL import Image
                        # Trusted local satellite sources; header-only inspection allocates no pixels.
                        limit = Image.MAX_IMAGE_PIXELS
                        try:
                            Image.MAX_IMAGE_PIXELS = None
                            with Image.open(path) as image:
                                item.update(width=image.width, height=image.height, channels=len(image.getbands()),
                                            mode=image.mode, geotiff_tags_present=bool(image.tag_v2.get(34735)),
                                            float32_full_scene_memory_bytes=image.width * image.height * len(image.getbands()) * 4)
                        finally:
                            Image.MAX_IMAGE_PIXELS = limit
                    except Exception as exc:
                        item['header_error'] = type(exc).__name__
                images.append(item)
                if any(token in path.stem.lower() for token in ('flood_mask', 'flood_label', 'ground_truth')):
                    masks.append(item['path'])
    return {'raster_or_preview_count': len(images), 'files': images, 'candidate_flood_masks': masks,
            'paired_label_count': 0, 'scene_count': len({p.parent.name for p in raw.rglob('manifest.safe')}),
            'alignment': 'No paired flood masks to validate; SCL/cloud/quality masks are not flood labels.',
            'positive_negative_pixels': None, 'split': 'Require event/scene/geography split before overlapping patches.',
            'georeferencing': 'GeoTIFF header tags inspected where readable; full CRS/transform validation requires rasterio.'}


def validate_flood_pair(image, mask, image_metadata: dict, mask_metadata: dict) -> dict:
    """Reusable array/metadata contract for future *labelled* imagery, not pseudo-labels."""
    import numpy as np
    if image.ndim != 3 or mask.ndim != 2 or image.shape[:2] != mask.shape:
        raise ValueError('Image HWC and mask HW must align exactly.')
    if not np.isfinite(image).all() or not set(np.unique(mask)).issubset({0, 1}):
        raise ValueError('Finite image values and binary observed flood masks are required.')
    for key in ('crs', 'transform', 'scene_id', 'event_id'):
        if key not in image_metadata or image_metadata[key] != mask_metadata.get(key):
            raise ValueError(f'Image and mask {key} must match.')
    if not image_metadata['scene_id'] or not image_metadata['event_id']:
        raise ValueError('Scene and event identifiers are required for leakage-safe splitting.')
    return {'height': mask.shape[0], 'width': mask.shape[1], 'flood_fraction': float(mask.mean())}


def validate_observed_table(frame: pd.DataFrame, task: str) -> pd.DataFrame:
    """Validate future event/stress tables without manufacturing outcomes or negative windows."""
    required = {'region_id', 'date', 'target', 'available_at'}
    if task not in {'disaster_risk', 'destination_stress'} or not required.issubset(frame.columns):
        raise ValueError('Expected region_id, date, target, available_at and a supported task.')
    data = frame.copy()
    if data.empty or data[list(required)].isna().any().any() or not data.region_id.map(lambda v: isinstance(v, str) and bool(v.strip())).all() or data.duplicated(['region_id', 'date']).any():
        raise ValueError('Missing observations or duplicate region/time keys.')
    data['date'] = pd.to_datetime(data.date, utc=True, errors='raise')
    data['available_at'] = pd.to_datetime(data.available_at, utc=True, errors='raise')
    if data.duplicated(['region_id', 'date']).any():
        raise ValueError('Duplicate region/time keys after UTC date normalization.')
    data['target'] = pd.to_numeric(data.target, errors='raise')
    import numpy as np
    if not np.isfinite(data.target).all():
        raise ValueError('Targets must be finite observations.')
    if not data.available_at.lt(data.date).all():
        raise ValueError('Feature availability must precede the target window/date.')
    if task == 'disaster_risk' and not set(data.target).issubset({0, 1}):
        raise ValueError('Event-window targets must be documented binary outcomes.')
    return data.sort_values(['date', 'region_id']).reset_index(drop=True)


def validate_group_splits(train_ids, validation_ids, test_ids):
    groups = [set(train_ids), set(validation_ids), set(test_ids)]
    if any(not group for group in groups) or any(groups[i] & groups[j] for i, j in ((0, 1), (0, 2), (1, 2))):
        raise ValueError('Non-empty event/scene groups must be disjoint across all splits.')
    return True


def auxiliary_profiles(raw: Path) -> dict:
    """Read each small JSON independently; never concatenate imagery or large tabular data."""
    bank, weather, sources = [], [], {}
    for path in sorted((raw / 'worldbank_un_tourism').glob('API_*.json')):
        payload = json.loads(path.read_text(encoding='utf-8'))
        rows = payload[1]
        keys = [(r.get('countryiso3code'), r.get('date')) for r in rows]
        bank.append({'path': path.relative_to(raw).as_posix(), 'rows': len(rows),
                     'indicator': rows[0]['indicator']['id'] if rows else None,
                     'missing_target_rate': sum(r.get('value') is None for r in rows) / len(rows) if rows else None,
                     'duplicate_country_years': len(keys) - len(set(keys)),
                     'country_count': len({k[0] for k in keys}),
                     'limitation': 'All-economy export may include aggregates; no pooled country model trained.'})
    for path in sorted((raw / 'weather_nasa_power').rglob('*.json')):
        payload = json.loads(path.read_text(encoding='utf-8'))
        features = payload.get('features', [])
        count = missing = 0; dates = []
        for feature in features:
            for series in feature.get('properties', {}).get('parameter', {}).values():
                values = pd.to_numeric(pd.Series(series.values()), errors='coerce')
                count += len(values); missing += int((values.isna() | values.eq(-999)).sum()); dates.extend(series.keys())
        weather.append({'path': path.relative_to(raw).as_posix(), 'grid_points': len(features), 'observations': count,
                        'missing_or_sentinel_rate': missing / count if count else None,
                        'date_min': min(dates) if dates else None, 'date_max': max(dates) if dates else None,
                        'usage': 'Not used: regional reanalysis does not align to national demand and future observed weather is unavailable.'})
    for path in sorted(raw.glob('*/SOURCE_INFO.txt')):
        sources[path.parent.name] = {'path': path.relative_to(raw).as_posix(), 'sha256': sha256(path),
                                    'documentation_read': True}
        path.read_text(encoding='utf-8')
    manifest = raw.parent / 'DATA_MANIFEST.csv'
    provenance = []
    if manifest.exists():
        table = pd.read_csv(manifest)
        for category, group in table.groupby('category'):
            provenance.append({'category': category, 'manifest_rows': len(group),
                               'coverage_start': sorted(group.coverage_start.dropna().astype(str).unique().tolist()),
                               'coverage_end': sorted(group.coverage_end.dropna().astype(str).unique().tolist()),
                               'geography': group.geographic_coverage.dropna().unique().tolist(),
                               'licenses': group.license.dropna().unique().tolist()})
    return {'worldbank_series': bank, 'weather_files': weather, 'source_documentation': sources, 'manifest_provenance': provenance}


def data_readiness(project: Path, raw: Path, write: bool = True) -> dict:
    files = sorted(p for p in raw.rglob('*') if p.is_file()) if raw.is_dir() else []
    categories = {}
    for category in sorted({p.relative_to(raw).parts[0] for p in files}):
        selected = [p for p in files if p.relative_to(raw).parts[0] == category]
        categories[category] = {'files': len(selected), 'bytes': sum(p.stat().st_size for p in selected),
                                'formats': dict(Counter(p.suffix.lower() for p in selected))}
    models = {}
    try:
        _, tourism = load_arrivals(raw)
        status = 'READY_FOR_TRAINING' if tourism['observed_rows'] >= 20 else 'NEEDS_MORE_DATA'
        reason = 'Annual India arrivals support a small historical baseline; no current or destination-level coverage.'
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        tourism, status, reason = {}, 'UNAVAILABLE', str(exc)
    models['tourism_demand'] = {'model_id': IDS['tourism_demand'], 'readiness': status,
        'task': 'annual count forecasting', 'target': 'Observed India international tourist arrivals (ST.INT.ARVL)',
        'reason': reason, 'data': tourism, 'supervised_training_suitable': status == 'READY_FOR_TRAINING',
        'alignment': 'Single national annual series; never join local weather to national totals.',
        'leakage': 'Use strictly prior annual lags; chronological train/validation/test; source vintage backtest only.'}
    hazard_path = raw / 'disaster_undrr/UNDRR_Datum_HIPs_hazards_v1.0.0_all.json'
    hazards = json.loads(hazard_path.read_text(encoding='utf-8')).get('data', []) if hazard_path.exists() else []
    hazard_frame = pd.DataFrame(hazards)
    models['disaster_risk'] = {'model_id': IDS['disaster_risk'], 'readiness': 'NEEDS_LABELS' if hazards else 'UNAVAILABLE',
        'task': 'future documented flood event by region/time (proposed, no trained target)',
        'target': None, 'reason': 'UNDRR HIPs are hazard definitions, not observed events. No event dates, region outcomes, verified negative windows or impact labels.',
        'data': {'path': 'disaster_undrr/UNDRR_Datum_HIPs_hazards_v1.0.0_all.json', 'rows': len(hazards),
                 'columns': {c: str(t) for c, t in hazard_frame.dtypes.items()},
                 'missing_rates': {c: float(v) for c, v in hazard_frame.isna().mean().items()},
                 'duplicate_ids': int(hazard_frame.uuid.duplicated().sum()) if 'uuid' in hazard_frame else None,
                 'temporal_coverage': 'publication timestamps only; no event history', 'geography': 'global taxonomy'},
        'alignment': 'Need region boundaries, event occurrence/completeness windows and features available before cutoff.',
        'leakage': 'Group shared events; future weather/reanalysis is unavailable at forecast cutoff.', 'supervised_training_suitable': False}
    imagery = imagery_inventory(raw)
    models['flood_segmentation'] = {'model_id': IDS['flood_segmentation'], 'readiness': 'NEEDS_LABELS' if imagery['files'] else 'UNAVAILABLE',
        'task': 'binary observed flooded-pixel segmentation', 'target': None,
        'reason': 'Sentinel scenes and quality/cloud masks exist; no verified paired observed flood masks or event-separated labelled splits.',
        'data': imagery, 'alignment': 'Require matching CRS, transform, footprint, acquisition and binary mask classes.',
        'leakage': 'Split events/geographies before patch extraction; never threshold imagery into claimed ground truth.',
        'supervised_training_suitable': False}
    models['destination_stress'] = {'model_id': IDS['destination_stress'], 'readiness': 'NEEDS_LABELS' if files else 'UNAVAILABLE',
        'task': 'observed capacity utilization/crowding prediction (requires target definition)', 'target': None,
        'reason': 'No observed stress, occupancy, crowd-density or aligned capacity time series. National arrivals and static OSM POIs do not establish destination stress.',
        'data': {'paths': ['tourism_india', 'osm_india', 'worldbank_un_tourism'], 'target_rows': 0,
                 'missing_rates': None, 'duplicates': None, 'geography': 'unaligned national series and regional snapshot',
                 'temporal_coverage': 'No measured destination/time stress series'},
        'alignment': 'Need common destination/time IDs, observed utilization units, capacities and pre-cutoff features.',
        'leakage': 'Future visitor totals cannot be prediction-time features. Arbitrary weighted scores are not labels.',
        'supervised_training_suitable': False}
    documents = [{'path': p.relative_to(raw).as_posix(), 'bytes': p.stat().st_size, 'format': p.suffix,
                  'status': 'READY_AFTER_PREPROCESSING', 'limitation': 'Binary DOC/PDF requires audited table extraction and unit/revision reconciliation before training.'}
                 for p in files if p.relative_to(raw).parts[0] == 'tourism_india' and p.suffix in {'.pdf', '.doc'}]
    report = {'generated_at': utc_now(), 'raw_root': 'SafarSaathi_Datasets/raw', 'file_count': len(files),
              'total_bytes': sum(p.stat().st_size for p in files), 'categories': categories,
              'models': models, 'tourism_documents': documents,
              'auxiliary_profiles': auxiliary_profiles(raw),
              'environment': {m: bool(importlib.util.find_spec(m)) for m in ('sklearn', 'torch', 'rasterio', 'PIL', 'pypdf')},
              'constraints': ['Raw sources read only; no uploads, downloads or pretrained weights.',
                  'Existing manifest and SOURCE_INFO provenance consulted; no legacy processed targets trusted.',
                  'Source: World Bank Open Data — World Development Indicators. Tourism indicators are compiled by the World Bank from UN Tourism (formerly UNWTO) source data.',
                  'World Bank CC BY 4.0; other source terms in SafarSaathi_Datasets/LICENSES_AND_ATTRIBUTION.md.',
                  'Full imagery pixel missingness/duplicates not computed: unlabelled 10 GB imagery; filenames/catalogues are not distinct training examples.',
                  'Weather 2000–2026 and OSM single 2026 snapshot are auxiliary inputs, not outcomes. NASA -999 sentinel requires explicit masking before any future join.']}
    if write:
        out = project / 'outputs/reports'; out.mkdir(parents=True, exist_ok=True)
        (out / 'ml_data_readiness.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        lines = ['# ML data readiness', '', '| Capability | Readiness | Evidence / limitation |', '|---|---|---|']
        lines += [f"| {k} | {v['readiness']} | {v['reason']} |" for k, v in models.items()]
        lines += ['', 'Machine-readable profiles, paths, missingness, split risks and image headers: `ml_data_readiness.json`.',
                  '', '## Scope and remediation', '', *['- ' + c for c in report['constraints']],
                  '', 'Tourism document extraction remains available as a future source improvement; the verified JSON series is used here.',
                  'Disaster needs a complete event/region/time outcome panel; flood needs observed aligned masks; stress needs measured destination/time pressure and units.',
                  'Risk support must follow official alerts; low scores cannot establish safety. No disaster model is operational.']
        (out / 'ml_data_readiness.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report
