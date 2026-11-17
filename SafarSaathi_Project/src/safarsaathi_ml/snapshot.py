"""Build-time snapshots of read-only adapter outputs for deployments without raw data.

Hosted services (Render, Docker) do not ship the multi-gigabyte raw collection or
the gitignored ``data/`` tree. ``build_snapshot`` runs the *same* adapter code
against the local files on a machine that has them and stores the results under
``deploy_snapshot/`` with SHA-256 checksums. At runtime the adapters read live
files when present and otherwise fall back to the checksum-verified snapshot,
labelling every response with ``data_origin`` so a snapshot is never presented
as a live local scan. Nothing here trains, edits raw files or invents values.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

SNAPSHOT_DIRNAME = 'deploy_snapshot'
SECTIONS = ('dataset_files', 'destinations', 'climate', 'tourism_history')
LIVE = 'LIVE_LOCAL_FILES'
SNAPSHOT = 'BUILD_SNAPSHOT'

CLIMATE_PARAMETERS = {
    'T2M': 'mean', 'T2M_MAX': 'mean', 'T2M_MIN': 'mean', 'RH2M': 'mean',
    'WS2M': 'mean', 'PRECTOTCORR': 'sum',
}
CLIMATE_LIMITATIONS = [
    'NASA POWER daily values are grid-scale reanalysis (MERRA-2/satellite blend), not rain-gauge or station observations.',
    'Grid cells do not resolve valley-scale or orographic rainfall; high-altitude shrines can differ substantially from these values.',
    'Climatology describes 2000–2024 history only. It is not a weather forecast, warning or hazard probability.',
    'Monthly precipitation is the mean of per-year monthly totals; temperature, humidity and wind are means of daily values.',
]


class SnapshotUnavailable(RuntimeError):
    """No verified snapshot section exists for this installation."""


def snapshot_dir(project: Path) -> Path:
    return project / SNAPSHOT_DIRNAME


def data_mode() -> str:
    mode = os.getenv('SAFARSAATHI_DATA_MODE', 'auto').strip().lower()
    return mode if mode in {'auto', 'live', 'snapshot'} else 'auto'


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=8)
def _load_section(directory: str, name: str):
    root = Path(directory)
    manifest_path = root / 'manifest.json'
    if not manifest_path.is_file():
        raise SnapshotUnavailable('Deployment snapshot manifest is missing.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entry = manifest.get('sections', {}).get(name)
    if not entry:
        raise SnapshotUnavailable(f'Deployment snapshot does not include {name}.')
    raw = (root / entry['file']).read_bytes()
    if _sha256_bytes(raw) != entry['sha256']:
        raise SnapshotUnavailable(f'Deployment snapshot checksum failed for {name}.')
    return json.loads(raw.decode('utf-8')), manifest['generated_utc']


def load_section(project: Path, name: str):
    """Return ``(payload, generated_utc)`` for a verified snapshot section."""
    if name not in SECTIONS:
        raise SnapshotUnavailable('Unknown snapshot section.')
    try:
        return _load_section(str(snapshot_dir(project)), name)
    except SnapshotUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SnapshotUnavailable('Deployment snapshot is unreadable.') from exc


def snapshot_status(project: Path) -> dict:
    root = snapshot_dir(project)
    try:
        manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'available': False, 'sections': [], 'generated_utc': None, 'mode': data_mode()}
    return {'available': True, 'generated_utc': manifest.get('generated_utc'), 'mode': data_mode(),
            'sections': sorted(manifest.get('sections', {})),
            'omitted': manifest.get('omitted', {})}


# --------------------------------------------------------------------------- climate

def _finite(value, fill):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value != fill


def climate_from_power(data: dict) -> dict:
    """Summarise one NASA POWER daily point file into a monthly climatology."""
    fill = data.get('header', {}).get('fill_value', -999.0)
    series = data['properties']['parameter']
    units = {key: data.get('parameters', {}).get(key, {}).get('units') for key in CLIMATE_PARAMETERS}
    units['PRECTOTCORR'] = 'mm/month'  # monthly rows hold totals of the source mm/day values
    monthly_values = {key: {m: [] for m in range(1, 13)} for key in CLIMATE_PARAMETERS}
    annual_precip, annual_temp = {}, {}
    wettest = None
    daily_precip = []
    for key, how in CLIMATE_PARAMETERS.items():
        per_year_month = {}
        for stamp, value in series.get(key, {}).items():
            if len(stamp) != 8 or not stamp.isdigit() or not _finite(value, fill):
                continue
            year, month = int(stamp[:4]), int(stamp[4:6])
            bucket = per_year_month.setdefault((year, month), [])
            bucket.append(float(value))
            if key == 'PRECTOTCORR':
                daily_precip.append(float(value))
                annual_precip[year] = annual_precip.get(year, 0.0) + float(value)
                if wettest is None or value > wettest['mm']:
                    wettest = {'date': f'{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}', 'mm': float(value)}
            if key == 'T2M':
                annual_temp.setdefault(year, []).append(float(value))
        for (year, month), values in per_year_month.items():
            monthly_values[key][month].append(sum(values) if how == 'sum' else sum(values) / len(values))
    months = []
    for month in range(1, 13):
        row = {'month': month}
        for key in CLIMATE_PARAMETERS:
            values = monthly_values[key][month]
            row[key] = round(sum(values) / len(values), 3) if values else None
        row['years_observed'] = len(monthly_values['PRECTOTCORR'][month])
        months.append(row)
    daily_precip.sort()
    p95 = daily_precip[int(0.95 * (len(daily_precip) - 1))] if daily_precip else None
    years = sorted(annual_precip)
    return {
        'units': units,
        'monthly_climatology': months,
        'annual': [{'year': y, 'precip_total_mm': round(annual_precip[y], 2),
                    'T2M_mean': round(sum(annual_temp[y]) / len(annual_temp[y]), 3) if annual_temp.get(y) else None}
                   for y in years],
        'extremes': {'wettest_day': wettest, 'daily_precip_p95_mm': round(p95, 3) if p95 is not None else None,
                     'days_with_precip_data': len(daily_precip)},
        'period': {'start': data.get('header', {}).get('start'), 'end': data.get('header', {}).get('end')},
    }


def live_climate(project: Path) -> dict:
    """Compute climatology for every live POWER point file (id -> summary)."""
    import re
    root = project / 'data/raw_v2/weather_power'
    result = {}
    for file in sorted(root.glob('POWER_*.json')):
        data = json.loads(file.read_text(encoding='utf-8'))
        name = data['_safarsaathi_query']['destination']
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        result[slug] = {'id': slug, 'name': name, **climate_from_power(data)}
    return result


# --------------------------------------------------------------------------- builder

def build_snapshot(project: Path, sections_wanted=None) -> dict:
    """Run the real adapters locally and persist their outputs with checksums."""
    from .integration_services import (DataUnavailable, _dataset_files, _live_destinations,
                                       _live_tourism_history)
    out = snapshot_dir(project)
    out.mkdir(parents=True, exist_ok=True)
    sections, omitted = {}, {}
    builders = {
        'dataset_files': lambda: _dataset_files(project),
        'destinations': lambda: _live_destinations(project),
        'climate': lambda: live_climate(project),
        'tourism_history': lambda: _live_tourism_history(project),
    }
    previous = {}
    try:
        previous = json.loads((out / 'manifest.json').read_text(encoding='utf-8')).get('sections', {})
    except (OSError, ValueError):
        pass
    for name, build in builders.items():
        if sections_wanted and name not in sections_wanted:
            if name in previous and (out / previous[name]['file']).is_file():
                sections[name] = previous[name]  # keep an earlier verified section untouched
            else:
                omitted[name] = 'Not requested in this build; run build-snapshot on the machine holding the datasets.'
            continue
        try:
            payload = build()
            if not payload:
                raise DataUnavailable('empty')
        except Exception as exc:  # noqa: BLE001 - recorded, never silently replaced
            omitted[name] = f'{type(exc).__name__}: source files unavailable on the build machine.'
            continue
        raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        filename = f'{name}.json'
        (out / filename).write_bytes(raw)
        sections[name] = {'file': filename, 'sha256': _sha256_bytes(raw), 'bytes': len(raw)}
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'sections': sections, 'omitted': omitted,
                'note': 'Outputs of the SafarSaathi read-only adapters captured on the machine holding the local datasets.'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    _load_section.cache_clear()
    return manifest
