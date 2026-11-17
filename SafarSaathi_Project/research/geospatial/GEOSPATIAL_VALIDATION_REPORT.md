# Geographic data are valid within a static regional scope

All 29 named NASA POWER query/returned-point pairs have finite geographic longitude/latitude in range and lie in the pilot bounding box. Maximum query-to-returned-grid geodesic displacement is 71.31 m. Duplicate returned coordinate pairs: 0. These are reanalysis query/grid points, not independently verified tourist attraction boundaries. Their source JSON declares no EPSG code; WGS84 geographic interpretation for distance checks is an explicit audit assumption, not newly discovered source metadata.

The actual northern-zone OSM extract was streamed with native node-location indexing. Within the pilot bbox, 42541 selected road-way geometries and 1476 river/stream geometries were retained; 209 hospital-tagged nodes/way-centroid proxies were found. Source publisher MD5 match: True. Full counts/checks in osm_validation.json; coordinate and nearest-feature rows are in the companion CSVs.

The endpoint-inside-pilot, undirected shared-node graph has 659069 nodes, 147 components, and 546319 nodes in its largest component (82.8925%). Boundary clipping, disconnected service roads and OSM incompleteness can create components; these figures do not validate vehicle routing. Oneway/restriction tags are counted but not enforced. No live closures, travel times, river stage or facility operations are known.

## Distance and geometry methodology

WGS84 ellipsoidal Geod distances compare each source query with its returned point. Road/river proximity uses a local azimuthal-equidistant metric CRS centered at 30.1N,79.3E and clipped line geometries. No planar degree distances are treated as metres. A 101-segment projected-endpoint/geodesic cross-check has maximum relative error 0.000265. Distances represent horizontal proximity, not accessibility or flood exposure. Geometry validity is checked before indexing.

## Unverified or absent components

No implemented spatial join to measured hazard polygons, verified tourism-cluster assignments, actual hospital operating status or independent location ground truth exists. The frontend SVG roads/contours are schematics, and its inset has an explicitly independent coordinate frame; it must not be treated as a registered operational map. The audit does not replace that frontend or claim nationwide coverage. Reproduce with `python scripts/phase3_geospatial_satellite.py`.
