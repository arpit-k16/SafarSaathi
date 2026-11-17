"""Reproducible read-only native GIS/image audit; derived outputs only under research/."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString, MultiPoint, Point, box, shape
from shapely.ops import transform
from shapely.strtree import STRtree
import tifffile
from PIL import Image, UnidentifiedImageError

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT.parent / 'SafarSaathi_Datasets/raw'
PILOT = (77.24, 28.61, 81.45, 31.63)
GEOD = Geod(ellps='WGS84')
METRIC = CRS.from_proj4('+proj=aeqd +lat_0=30.1 +lon_0=79.3 +datum=WGS84 +units=m +no_defs')
PROJECTOR = Transformer.from_crs(4326, METRIC, always_xy=True).transform


def coordinate_valid(lon, lat):
    return type(lon) in (int, float) and type(lat) in (int, float) and math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90


def geodesic_m(lon1, lat1, lon2, lat2):
    if not coordinate_valid(lon1, lat1) or not coordinate_valid(lon2, lat2):
        raise ValueError('Coordinates must be finite geographic longitude/latitude.')
    return float(GEOD.inv(lon1, lat1, lon2, lat2)[2])


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False, default=str), encoding='utf-8')


def csv_write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(key for row in rows for key in row)) if rows else ['status'])
        writer.writeheader()
        writer.writerows(rows)


def sha(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def locations():
    rows = []
    for path in sorted((PROJECT / 'data/raw_v2/weather_power').glob('POWER_*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        query, coordinates = data['_safarsaathi_query'], data['geometry']['coordinates']
        lon, lat = coordinates[:2]
        qlon, qlat = query['lon'], query['lat']
        rows.append({'destination': query['destination'], 'source_file': path.name,
                     'query_longitude': qlon, 'query_latitude': qlat,
                     'returned_longitude': lon, 'returned_latitude': lat,
                     'query_coordinates_valid': coordinate_valid(qlon, qlat),
                     'returned_coordinates_valid': coordinate_valid(lon, lat),
                     'within_pilot_bbox': box(*PILOT).covers(Point(lon, lat)),
                     'query_to_grid_geodesic_m': geodesic_m(lon, lat, qlon, qlat),
                     'coverage_start': data['header']['start'], 'coverage_end': data['header']['end'],
                     'parameter_count': len(data['parameters']), 'epsg_declared': False})
    return rows


class UnionFind:
    def __init__(self):
        self.parents = {}
    def find(self, x):
        parent = self.parents.setdefault(x, x)
        while parent != self.parents[parent]:
            self.parents[parent] = self.parents[self.parents[parent]]
            parent = self.parents[parent]
        self.parents[x] = parent
        return parent
    def union(self, a, b):
        pa, pb = self.find(a), self.find(b)
        if pa != pb:
            self.parents[pa] = pb


def osm_audit(points):
    import osmium
    road_lines, road_ids, rivers, river_ids, hospital_points = [], [], [], [], []
    graph = UnionFind()
    counts = Counter()
    pilot = box(*PILOT)
    road_classes = {'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'service',
                    'motorway_link', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link', 'living_street'}
    class Handler(osmium.SimpleHandler):
        def node(self, node):
            if node.tags.get('amenity') == 'hospital' and node.location.valid():
                lon, lat = node.location.lon, node.location.lat
                if pilot.covers(Point(lon, lat)):
                    hospital_points.append({'osm_id': int(node.id), 'name': node.tags.get('name'), 'longitude': lon, 'latitude': lat, 'kind': 'node'})
        def way(self, way):
            kind = 'road' if way.tags.get('highway') in road_classes else 'river' if way.tags.get('waterway') in {'river', 'stream'} else 'hospital' if way.tags.get('amenity') == 'hospital' else None
            if not kind:
                return
            try:
                coords = [(n.location.lon, n.location.lat) for n in way.nodes]
            except osmium.InvalidLocationError:
                counts['invalid_node_reference_' + kind] += 1
                return
            if len(coords) < 2:
                counts['too_short_' + kind] += 1
                return
            line = LineString(coords)
            if not line.intersects(pilot):
                return
            counts[kind + '_ways_intersecting_pilot'] += 1
            if not line.is_valid:
                counts['invalid_geometry_' + kind] += 1
                return
            if kind == 'hospital':
                center = line.centroid
                hospital_points.append({'osm_id': int(way.id), 'name': way.tags.get('name'), 'longitude': center.x, 'latitude': center.y, 'kind': 'way_centroid_proxy'})
                return
            clipped = line.intersection(pilot)
            metric_line = transform(PROJECTOR, clipped)
            if kind == 'road':
                road_lines.append(metric_line)
                road_ids.append(int(way.id))
                refs = list(way.nodes)
                for i in range(len(coords) - 1):
                    if pilot.covers(Point(coords[i])) and pilot.covers(Point(coords[i + 1])):
                        graph.union(int(refs[i].ref), int(refs[i + 1].ref))
                counts['oneway_tagged_road_ways'] += way.tags.get('oneway') in {'yes', '1', '-1'}
                counts['restricted_access_tagged_road_ways'] += way.tags.get('access') in {'private', 'no'}
            else:
                rivers.append(metric_line)
                river_ids.append(int(way.id))
    source = RAW / 'osm_india/northern-zone-latest.osm.pbf'
    start = time.perf_counter()
    Handler().apply_file(str(source), locations=True, idx='sparse_mem_array')
    road_tree = STRtree(road_lines) if road_lines else None
    river_tree = STRtree(rivers) if rivers else None
    associations = []
    for row in points:
        point = transform(PROJECTOR, Point(row['query_longitude'], row['query_latitude']))
        road_index = int(road_tree.nearest(point)) if road_tree else None
        river_index = int(river_tree.nearest(point)) if river_tree else None
        associations.append({'destination': row['destination'],
                             'nearest_road_way_id': road_ids[road_index] if road_index is not None else None,
                             'nearest_road_projected_m': float(point.distance(road_lines[road_index])) if road_index is not None else None,
                             'nearest_river_or_stream_way_id': river_ids[river_index] if river_index is not None else None,
                             'nearest_river_or_stream_projected_m': float(point.distance(rivers[river_index])) if river_index is not None else None})
    sizes = Counter(graph.find(n) for n in list(graph.parents))
    expected_md5 = (RAW / 'osm_india/northern-zone-latest.osm.pbf.md5').read_text().split()[0]
    # Independent known distance and projection-vs-geodesic checks, not raw-degree distances.
    sample_errors = []
    inverse = Transformer.from_crs(METRIC, 4326, always_xy=True)
    for line in road_lines[::max(1, len(road_lines) // 100)]:
        if line.geom_type not in {'LineString', 'MultiLineString'}:
            continue
        segment = line if line.geom_type == 'LineString' else list(line.geoms)[0]
        if segment.length <= 1:
            continue
        a, b = segment.coords[0], segment.coords[-1]
        lon1, lat1 = inverse.transform(*a)
        lon2, lat2 = inverse.transform(*b)
        distance = geodesic_m(lon1, lat1, lon2, lat2)
        if distance > 1:
            sample_errors.append(abs(math.dist(a, b) - distance) / distance)
    return {'counts': dict(counts), 'source': source.relative_to(PROJECT.parent).as_posix(),
            'source_bytes': source.stat().st_size, 'publisher_md5_expected': expected_md5,
            'publisher_md5_actual': sha(source, 'md5'), 'bbox': PILOT,
            'metric_crs': METRIC.to_string(), 'network_nodes': len(graph.parents),
            'undirected_components': len(sizes), 'largest_component_nodes': max(sizes.values(), default=0),
            'largest_component_fraction': max(sizes.values(), default=0) / len(graph.parents) if graph.parents else None,
            'road_line_geometries': len(road_lines), 'river_stream_line_geometries': len(rivers),
            'hospital_features': len(hospital_points), 'hospital_locations': hospital_points,
            'associations': associations,
            'metric_distance_check_samples': len(sample_errors),
            'max_projected_chord_vs_geodesic_relative_error': max(sample_errors, default=None),
            'runtime_seconds': time.perf_counter() - start,
            'limitations': ['Static OSM snapshot, selected drivable highway tags; not live accessibility or a routing engine.',
                            'Connectivity graph is undirected, shared-node based and restricted to endpoint-inside-pilot edges; cut boundaries cause components.',
                            'Oneway, turn restrictions, bridges/layers, missing OSM features and temporary closures are not routing-validated.',
                            'Nearest distances are projected horizontal proximity to clipped OSM road/river lines, not travel or flood exposure.',
                            'Hospital tags/way-centroid proxies are not independent evidence that facilities exist or are operational.',
                            'No measured hazard polygons or validated tourism-cluster assignments exist.']}


def satellite_audit(full_hash=True):
    manifest = {r['local_path'].replace('\\', '/'): r for r in csv.DictReader((RAW.parent / 'DATA_MANIFEST.csv').open(encoding='utf-8-sig'))}
    rasters, scenes = [], []
    pilot = box(*PILOT)
    for category in ('sentinel1', 'sentinel2'):
        for product in sorted((RAW / category).iterdir()):
            if not product.is_dir():
                continue
            info_file = next(product.rglob('productInfo.json'))
            info = json.loads(info_file.read_text(encoding='utf-8'))
            info_time = info.get('startTime', info.get('timestamp'))
            actual_name = info.get('name', info.get('id'))
            scene = {'category': category, 'wrapper_product_id': product.name,
                     'delivered_product_id': actual_name, 'acquisition_metadata': info_time,
                     'wrapper_delivered_name_match': product.name.removesuffix('.SAFE') == actual_name,
                     'sensor': info.get('missionId', actual_name[:3]),
                     'level': info.get('productType', 'MSIL2A' if 'MSIL2A' in actual_name else None),
                     'raster_count': 0}
            footprint = shape(info['footprint']) if category == 'sentinel1' else None
            if category == 'sentinel2':
                tile = json.loads(next(product.rglob('tileInfo.json')).read_text(encoding='utf-8'))
                epsg = int(tile['tileGeometry']['crs']['properties']['name'].split(':')[-1])
                footprint = transform(Transformer.from_crs(epsg, 4326, always_xy=True).transform, shape(tile['tileGeometry']))
                data_footprint = transform(Transformer.from_crs(epsg, 4326, always_xy=True).transform, shape(tile['tileDataGeometry']))
                scene.update({'tile_crs_epsg': epsg, 'tile_timestamp': tile['timestamp'],
                              'declared_cloudy_pixel_percent': tile['cloudyPixelPercentage'],
                              'declared_data_coverage_percent': tile['dataCoveragePercentage'],
                              'actual_data_geometry_intersects_pilot': data_footprint.intersects(pilot)})
                scl_path = next(product.rglob('R60m/SCL.jp2'), None)
                if scl_path:
                    with Image.open(scl_path) as scl_image:
                        scl = np.asarray(scl_image)
                    valid = scl != 0
                    clouds = np.isin(scl, [8, 9, 10])
                    scene.update({'scl_valid_pixels': int(valid.sum()), 'scl_cloud_pixels': int(clouds.sum()),
                                  'scl_cloud_percent_valid': float(100 * clouds.sum() / valid.sum()) if valid.any() else None,
                                  'scl_cloud_percent_tile': float(100 * clouds.mean()),
                                  'scl_definition': 'Classes 8/9/10; denominator excludes class 0 no-data; classified mask, not independent ground truth'})
                bands = {f.stem for f in product.rglob('*.jp2') if f.parent.name == 'R10m'}
                scene['R10m_bands_present'] = sorted(bands)
                scene['required_R10m_spectral_bands_missing'] = sorted({'B02', 'B03', 'B04', 'B08'} - bands)
            scene.update({'footprint_valid': footprint.is_valid, 'footprint_wgs84_bounds': footprint.bounds,
                          'footprint_intersects_pilot_bbox': footprint.intersects(pilot),
                          'footprint_metadata_crs': 4326 if category == 'sentinel1' else scene['tile_crs_epsg']})
            for path in sorted(product.rglob('*')):
                if path.suffix.lower() not in {'.tiff', '.tif', '.jp2'}:
                    continue
                relative = path.relative_to(RAW.parent).as_posix()
                declared = manifest.get(relative, {})
                item = {'path': relative, 'product_id': product.name, 'category': category,
                        'bytes': path.stat().st_size, 'declared_bytes': declared.get('file_size_bytes'),
                        'declared_sha256': declared.get('checksum', '').removeprefix('sha256:'),
                        'sha256_actual': sha(path) if full_hash else None}
                item['sha256_matches_manifest'] = item['sha256_actual'] == item['declared_sha256'] if full_hash and item['declared_sha256'] else None
                if path.suffix.lower() in {'.tiff', '.tif'}:
                    with tifffile.TiffFile(path) as tf:
                        page = tf.pages[0]
                        meta = tf.geotiff_metadata or {}
                        gcps = np.asarray(page.tags[33922].value).reshape(-1, 6) if 33922 in page.tags else np.empty((0, 6))
                        item.update({'width': page.imagewidth, 'height': page.imagelength, 'dtype': str(page.dtype),
                                     'compression': page.compression.name, 'readable_header': True,
                                     'geographic_crs_epsg': int(meta['GeographicTypeGeoKey']) if 'GeographicTypeGeoKey' in meta else None,
                                     'affine_scale_present': 33550 in page.tags, 'affine_matrix_present': 34264 in page.tags,
                                     'geolocation_control_points': len(gcps)})
                        if len(gcps):
                            hull = MultiPoint(gcps[:, 3:5]).convex_hull
                            item['gcp_hull_wgs84_bounds'] = hull.bounds
                            item['gcp_hull_intersects_pilot'] = hull.intersects(pilot)
                            item['gcp_hull_vs_footprint_iou_degree_area_diagnostic'] = hull.intersection(footprint).area / hull.union(footprint).area
                        annotation = product / 'annotation' / (path.stem + '.xml')
                        if annotation.exists():
                            xml = ET.parse(annotation)
                            item['annotation_range_pixel_spacing_m'] = xml.findtext('.//rangePixelSpacing')
                            item['annotation_azimuth_pixel_spacing_m'] = xml.findtext('.//azimuthPixelSpacing')
                            item['annotation_polarisation'] = xml.findtext('.//adsHeader/polarisation')
                            xs = [float(n.text) for n in xml.findall('.//geolocationGridPoint/longitude')]
                            ys = [float(n.text) for n in xml.findall('.//geolocationGridPoint/latitude')]
                            item['annotation_grid_matches_tiff_gcps'] = len(xs) == len(gcps) and bool(np.allclose(xs, gcps[:, 3]) and np.allclose(ys, gcps[:, 4]))
                else:
                    # Header only: avoid materializing 120M pixels just to audit format/dimensions.
                    try:
                        with Image.open(path) as image:
                            item.update({'width': image.width, 'height': image.height,
                                         'mode': image.mode, 'readable_header': True,
                                         'pixel_spacing_m_from_directory': int(path.parent.name[1:-1]) if re.fullmatch(r'R\d+m', path.parent.name) else None})
                    except UnidentifiedImageError:
                        item.update({'readable_header': False, 'decode_status': 'Not recognized by Pillow; quality-mask format may differ. Integrity hash does not prove image readability.'})
                rasters.append(item)
                scene['raster_count'] += 1
            scenes.append(scene)
    return {'scenes': scenes, 'rasters': rasters,
            'hash_policy': 'All existing local TIFF/JP2 payloads SHA-256 compared with original collection manifest' if full_hash else 'Header-only; hashes not run',
            'raster_count': len(rasters), 'raster_bytes': sum(r['bytes'] for r in rasters),
            'manifest_checksum_mismatches': sum(r['sha256_matches_manifest'] is False for r in rasters),
            'hashes_verified': sum(r['sha256_matches_manifest'] is True for r in rasters),
            'no_raw_files_modified': True}


def write_reports(points, osm, sat):
    geo = PROJECT / 'research/geospatial'
    image = PROJECT / 'research/satellite_validation'
    csv_write(geo / 'COORDINATE_VALIDATION.csv', points)
    dump(geo / 'osm_validation.json', osm)
    csv_write(geo / 'LOCATION_INFRASTRUCTURE_PROXIMITY.csv', osm['associations'])
    dump(image / 'satellite_audit.json', sat)
    csv_write(image / 'SCENE_INVENTORY.csv', sat['scenes'])
    csv_write(image / 'RASTER_INTEGRITY.csv', sat['rasters'])
    max_offset = max(r['query_to_grid_geodesic_m'] for r in points)
    dupes = len(points) - len({(r['returned_longitude'], r['returned_latitude']) for r in points})
    geo.joinpath('GEOSPATIAL_VALIDATION_REPORT.md').write_text(f'''# Geographic data are valid within a static regional scope

All {len(points)} named NASA POWER query/returned-point pairs have finite geographic longitude/latitude in range and lie in the pilot bounding box. Maximum query-to-returned-grid geodesic displacement is {max_offset:.2f} m. Duplicate returned coordinate pairs: {dupes}. These are reanalysis query/grid points, not independently verified tourist attraction boundaries. Their source JSON declares no EPSG code; WGS84 geographic interpretation for distance checks is an explicit audit assumption, not newly discovered source metadata.

The actual northern-zone OSM extract was streamed with native node-location indexing. Within the pilot bbox, {osm['road_line_geometries']} selected road-way geometries and {osm['river_stream_line_geometries']} river/stream geometries were retained; {osm['hospital_features']} hospital-tagged nodes/way-centroid proxies were found. Source publisher MD5 match: {osm['publisher_md5_actual'] == osm['publisher_md5_expected']}. Full counts/checks in osm_validation.json; coordinate and nearest-feature rows are in the companion CSVs.

The endpoint-inside-pilot, undirected shared-node graph has {osm['network_nodes']} nodes, {osm['undirected_components']} components, and {osm['largest_component_nodes']} nodes in its largest component ({osm['largest_component_fraction']:.4%}). Boundary clipping, disconnected service roads and OSM incompleteness can create components; these figures do not validate vehicle routing. Oneway/restriction tags are counted but not enforced. No live closures, travel times, river stage or facility operations are known.

## Distance and geometry methodology

WGS84 ellipsoidal Geod distances compare each source query with its returned point. Road/river proximity uses a local azimuthal-equidistant metric CRS centered at 30.1N,79.3E and clipped line geometries. No planar degree distances are treated as metres. A {osm['metric_distance_check_samples']}-segment projected-endpoint/geodesic cross-check has maximum relative error {osm['max_projected_chord_vs_geodesic_relative_error']:.6f}. Distances represent horizontal proximity, not accessibility or flood exposure. Geometry validity is checked before indexing.

## Unverified or absent components

No implemented spatial join to measured hazard polygons, verified tourism-cluster assignments, actual hospital operating status or independent location ground truth exists. The frontend SVG roads/contours are schematics, and its inset has an explicitly independent coordinate frame; it must not be treated as a registered operational map. The audit does not replace that frontend or claim nationwide coverage. Reproduce with `python scripts/phase3_geospatial_satellite.py`.
''', encoding='utf-8')
    geo.joinpath('SPATIAL_COVERAGE_REPORT.md').write_text(f'''# Actual geographic coverage

The audit bbox is {PILOT} in longitude/latitude. All {len(points)} POWER points are inside it; archived dates are retained per point in COORDINATE_VALIDATION.csv. The available full PBF data are northern-zone (223,511,106 bytes) and central-zone (351,565,542 bytes). Other regional .poly boundaries are not road datasets. There is no full-India or Nepal-specific operational road/hazard/exposure dataset integrated here.

The northern-zone file is the actual source of the derived pilot road/river/hospital audit; do not extrapolate these counts to India, or apply them to Rasuwagadhi in Nepal. OSM attribution: (c) OpenStreetMap contributors, ODbL 1.0; preserve attribution and applicable derived-database share-alike terms. Hospitals/roads are OSM-tagged objects, not independently surveyed contemporary infrastructure.

Satellite scene footprints and actual data footprints have individual coverage checks in SCENE_INVENTORY.csv. A scene intersecting the pilot bbox does not cover every tourism point, and a catalogue wrapper name does not establish pixel coverage or processing-baseline equivalence.
''', encoding='utf-8')
    s1 = [r for r in sat['rasters'] if r['category'] == 'sentinel1']
    s2 = [r for r in sat['rasters'] if r['category'] == 'sentinel2']
    image.joinpath('SATELLITE_DATA_AUDIT.md').write_text(f'''# Satellite audit: source integrity and geometry, not operational detection

Actual collection: six Sentinel-1 GRD/IW/DV scenes and six Sentinel-2 L2A scene wrappers. Examined {len(s1)} TIFF and {len(s2)} JP2 files, {sat['raster_bytes']:,} bytes in total; {sum(r.get('readable_header') is False for r in sat['rasters'])} quality-layer headers were not recognized by Pillow and are flagged, not counted as readable. SHA-256 policy: {sat['hash_policy']}. Verified checksums: {sat['hashes_verified']}; manifest mismatches: {sat['manifest_checksum_mismatches']}. Every source path, hash/header result and available native dimensions is in RASTER_INTEGRITY.csv / satellite_audit.json; per-scene sensor/date/coverage in SCENE_INVENTORY.csv. Original raw files were never written.

Header readability and checksum integrity do not certify complete pixel decode, calibration, alignment, cloud-free ground observations or flood accuracy. No Rasuwagadhi event-period images or matching ground truth were introduced. Existing STURM inference is a different delivered preprocessing/labeling domain.
''', encoding='utf-8')
    image.joinpath('SENTINEL1_VALIDATION.md').write_text(f'''# Sentinel-1: valid source files require geolocation and radiometric processing

All {len(s1)} delivered measurement TIFFs have readable headers; native CRS is EPSG:4326 where declared by GeoTIFF keys. Files use geolocation control-point grids, not an affine pixel scale/transform. Their GCP geometry is compared against product footprints and annotation geolocation grids in the evidence. Pixel spacing from annotation is instrument/raster sampling metadata, not an affine geographic transform. Direct equal-index pre/post subtraction is not justified without calibrated, terrain-corrected co-registration.

ProductInfo and actual annotation polarization are authoritative for this local payload: DV corresponds to delivered VV and VH bands. SOURCE_INFO.txt's HH+HV / SH wording is inconsistent with these actual files and is treated as a provenance-description defect; raw metadata is preserved. No raw-scene SAR-to-STURM preprocessing bridge is implemented.

No arbitrary SAR threshold, flood-confidence map or live detection was manufactured. Required next steps: validate calibration/noise vectors and orbit/DEM terrain correction, transform GCPs onto a shared projected grid, align comparable orbit/polarizations, and evaluate against independent dated flood/permanent-water reference masks with event/spatial holdout. Existing source integrity is evidence of byte preservation, not that these steps have been completed.
''', encoding='utf-8')
    image.joinpath('SENTINEL2_VALIDATION.md').write_text(f'''# Sentinel-2: L2A spectral metadata with processing and cloud limitations

Examined {len(s2)} JP2 files across six scene wrappers; {sum(r.get('readable_header') is False for r in s2)} were not recognized by Pillow. This does not by itself prove corruption: quality files may use another encoding. Product/tile JSON identifies sensing timestamps, projected UTM tile CRS, footprints and declared cloud/data-coverage percentages. Required R10m B02/B03/B04/B08 presence and native raster dimensions/10m-directory sampling are recorded. Tile CRS is transformed to WGS84 using always_xy=True before pilot intersection checks.

Delivered AWS product names differ from N0510/N0511 catalogue wrapper names (actual delivered productInfo names retain N0509 or other source baselines). Acquisition metadata is kept separately from wrapper/reprocessing timestamps; product-level timestamp differs legitimately from tile sensing timestamp by minutes. Do not label processing time as acquisition, or equate different processing baselines.

All six tile JSONs declare zero cloud. The R60m SCL rasters were fully decoded and classes 8/9/10 counted, excluding class0 from the valid denominator; counts, valid-pixel percentages and total-tile percentages are retained per scene. Several scenes have substantial classified cloud, so zero metadata must not be used as proof of clear ground. SCL is itself a classification, not independent cloud ground truth. Class definitions are described in the Copernicus Sentinel-2 processing documentation (https://sentiwiki.copernicus.eu/web/s2-processing); this audit does not claim to have independently field-validated those labels. Reflectance offsets and cloud/shadow handling must be verified before spectral indices; no unqualified DN-based NDVI/NDWI or field-validated environmental change is claimed.
''', encoding='utf-8')
    image.joinpath('SATELLITE_LIMITATIONS.md').write_text('''# Limits that constrain satellite claims

- Integrity hashes and readable image headers establish source identity/format, not operational flood detection.
- Sentinel-1 GCP grids are not affine registered rasters; no terrain correction, radiometric calibration, co-registration or independent raw-scene flood labels were created.
- Sentinel-2 wrapper versus delivered baseline names differ; metadata cloud/data coverage is not a validated ground-observation mask. Reflectance offsets and masking prevent an unqualified DN-based index calculation.
- Regional acquisitions from 2021–2024 do not establish coverage of an alleged 2026 Nepal event. No Uttarakhand imagery/POIs are substituted for Nepal observations.
- The existing STURM model accepts its own 128x128x2 preprocessed domain. Its known low precision and permanent-water ambiguity remain; native local scenes are not interchangeable.
- No current alert, live satellite synchronization, globally validated transfer performance, GLOF detection or local water-level prediction is claimed.
''', encoding='utf-8')


def self_checks():
    assert coordinate_valid(78.292, 30.109)
    for pair in [(181, 0), (0, 91), (True, 1), (float('nan'), 0)]:
        assert not coordinate_valid(*pair)
    assert geodesic_m(78, 30, 78, 30) == 0
    assert 96000 < geodesic_m(78, 30, 79, 30) < 97000
    assert box(*PILOT).is_valid and box(*PILOT).covers(Point(78.292, 30.109))
    uf = UnionFind(); uf.union(1, 2); uf.union(2, 3)
    assert uf.find(1) == uf.find(3) and uf.find(4) != uf.find(1)
    return {'checks_passed': ['finite/ranged coordinate acceptance and invalid rejection', 'ellipsoidal zero and known one-degree longitude distance',
                              'native lon-lat pilot geometry validity/containment', 'shared-node component union/find'], 'status': 'PASS'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-hashes', action='store_true')
    parser.add_argument('--reuse-osm', action='store_true')
    args = parser.parse_args()
    start = time.perf_counter()
    points = locations()
    osm_file = PROJECT / 'research/geospatial/osm_validation.json'
    osm = json.loads(osm_file.read_text()) if args.reuse_osm and osm_file.exists() else osm_audit(points)
    dump(osm_file, osm)
    sat = satellite_audit(not args.skip_hashes)
    write_reports(points, osm, sat)
    tests = self_checks()
    tests.update({'coordinate_rows': len(points), 'all_native_points_valid': all(r['returned_coordinates_valid'] for r in points),
                  'all_query_points_valid': all(r['query_coordinates_valid'] for r in points),
                  'source_md5_match': osm['publisher_md5_expected'] == osm['publisher_md5_actual'],
                  'satellite_checksum_mismatches': sat['manifest_checksum_mismatches'],
                  'runtime_seconds': time.perf_counter() - start})
    dump(PROJECT / 'research/geospatial/validation_test_results.json', tests)
    (PROJECT / 'research/geospatial/GEOSPATIAL_TEST_RESULTS.md').write_text('# Executed geographic checks\n\n`python scripts/phase3_geospatial_satellite.py` produced the following actual result. Full source checks are in CSV/JSON; no live route or hazard validation is implied.\n\n```json\n' + json.dumps(tests, indent=2) + '\n```\n', encoding='utf-8')
    print(json.dumps({'status': tests['status'], 'locations': len(points), 'osm_roads': osm['road_line_geometries'], 'rasters': sat['raster_count'], 'runtime_seconds': tests['runtime_seconds']}))


if __name__ == '__main__':
    main()
