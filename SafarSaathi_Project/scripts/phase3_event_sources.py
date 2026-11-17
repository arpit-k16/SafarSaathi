"""Read-only inventory check for the Rasuwagadhi case; no event skill is invented.

Run from SafarSaathi_Project: python scripts/phase3_event_sources.py
Web source verification is recorded separately in event_sources.json. This script
does not re-fetch the web or treat a source URL as a locally loaded dataset.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(project):
    raw = project.parent / 'SafarSaathi_Datasets'
    manifest = raw / 'DATA_MANIFEST.csv'
    with manifest.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    scenes = [r for r in rows if r['category'] in {'sentinel1', 'sentinel2'}]
    products = sorted({r['local_path'].split('/')[2] for r in scenes
                       if len(r['local_path'].split('/')) > 3
                       and r['local_path'].split('/')[2].startswith(('S1', 'S2'))})
    result = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'event_date_under_review': '2026-08-26',
        'inventory_method': 'Local manifest and benchmark metadata, not pixel/ground-truth validation.',
        'collection_manifest_sha256': digest(manifest),
        'raw_satellite_manifest_rows': len(scenes),
        'raw_satellite_geographic_coverage': sorted({r['geographic_coverage'] for r in scenes}),
        'raw_satellite_product_ids': products,
        'raw_satellite_product_ids_in_2026': [name for name in products if '2026' in name],
        'sturm_metadata': [],
    }
    for name, date_field in [('Sentinel1_metadata.csv', 'sentinel_date'),
                             ('Sentinel2_metadata.csv', 'sentinel_timestamp')]:
        path = project / 'data/external/sturm_flood/12748983' / name
        with path.open(encoding='utf-8-sig', newline='') as stream:
            records = list(csv.DictReader(stream))
        dates = [datetime.fromisoformat(r[date_field]) for r in records]
        result['sturm_metadata'].append({
            'file': path.relative_to(project).as_posix(), 'sha256': digest(path),
            'rows': len(records), 'countries': sorted({r['country'] for r in records}),
            'nepal_country_rows': sum(r['country'].strip().casefold() == 'nepal' for r in records),
            'sentinel_start': min(dates).isoformat(), 'sentinel_end': max(dates).isoformat(),
            'sentinel_rows_on_event_date': sum(d.date().isoformat() == '2026-08-26' for d in dates),
        })
    snapshot = project / 'research/_baseline/dataset_inventory.json'
    if snapshot.is_file():
        local = json.loads(snapshot.read_text(encoding='utf-8'))
        result['dedicated_nepal_named_inventory_paths'] = [r['path'] for r in local if any(
            term in r['path'].lower() for term in ('nepal', 'rasuwa', 'rasuwag', 'bhotekoshi', 'lende'))]
    result['nepal_event_model_validation'] = 'NOT_EVALUATED_MISSING_ALIGNED_INPUTS_AND_REFERENCE'
    result['limitations'] = [
        'Filename checks are discovery only, not proof that all files lack Nepal content.',
        'The all-country World Bank collection can contain Nepal national statistics; it is not an event-level exposure panel.',
        'Northern India OSM coverage is not certified as Nepal event infrastructure data.',
        'Authoritative report links are remote leads, not loaded local imagery/vector/gauge data.',
    ]
    return result


def main():
    project = Path(__file__).resolve().parents[1]
    result = inventory(project)
    target = project / 'research/flood_case_study'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'local_event_inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({
        'sturm_nepal_rows': [r['nepal_country_rows'] for r in result['sturm_metadata']],
        'event_date_sturm_rows': [r['sentinel_rows_on_event_date'] for r in result['sturm_metadata']],
        'product_ids_in_2026': len(result['raw_satellite_product_ids_in_2026']),
        'status': result['nepal_event_model_validation'],
    }, indent=2))


if __name__ == '__main__':
    main()
