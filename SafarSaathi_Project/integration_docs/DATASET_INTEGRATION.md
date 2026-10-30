# Dataset integration inventory

Snapshot taken during the 2026-10-29 integration. `dataset_inventory.json` contains every actual catalog file, original filename, format, current size, relative path, declared source, coverage and license when present. Unknown metadata is null. This is a file-stat/source-manifest inventory, not a complete checksum or external connection test. Interim/test/release/trash files are excluded. Raw inputs were not modified.

Root labels resolve locally as follows: raw_collection = sibling SafarSaathi_Datasets/raw; project_raw = data/raw_v2; project_external = data/external; project_derived = data/processed; indicators = outputs/indicators. API clients receive only these labels and relative paths, never absolute machine paths. `/datasets?offset=0&limit=100` paginates the same current file catalog; files may change outside the task, so offset pagination is not a transactional snapshot.

| Root/category | Actual files | Actual bytes |
|---|---:|---:|
| indicators/india_environment_tourism | 2 | 40726 |
| project_derived/india_scope_20261025 | 4 | 18926 |
| project_derived/tourism_monthly_fta | 2 | 29997 |
| project_external/india_scope_20261025 | 18 | 27968855 |
| project_external/sturm_flood | 7 | 3995394732 |
| project_raw/osm | 7 | 351634251 |
| project_raw/tourism_utdb | 5 | 2353620 |
| project_raw/weather_power | 29 | 44213129 |
| raw_collection/disaster_undrr | 2 | 1109340 |
| raw_collection/osm_india | 3 | 223514040 |
| raw_collection/reviews | 7 | 31801575 |
| raw_collection/sentinel1 | 161 | 7982150612 |
| raw_collection/sentinel2 | 496 | 3025129116 |
| raw_collection/tourism_india | 14 | 84028930 |
| raw_collection/weather_nasa_power | 244 | 58212467 |
| raw_collection/worldbank_un_tourism | 34 | 16451929 |

## Integrated consumers and validation

| Source / local path | Format and fields | Coverage / provenance / license | Consumers and validation |
|---|---|---|---|
| raw_collection/worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json | World Bank two-part JSON; indicator.id, countryiso3code, date, value | IND observed 1995–2019; ST.INT.ARVL, UN Tourism/WDI. Source manifest and collection license record. | /tourism/history annual series; existing annual training pipeline. Unique consecutive integer years, IND/indicator enforcement, finite nonnegative integer counts; trailing null values excluded, internal gaps rejected. Per-read SHA recorded. |
| project_derived/tourism_monthly_fta/20261025/monthly_fta.csv and provenance.json | destination,date,arrivals; provenance source PDF hashes/table/page numbers and derived_csv_sha256 | IND monthly FTA excluding NRI, 2019-01 through 2024-12, 72 observations. Ministry of Tourism; see exact source publication terms and source provenance. | /tourism/history monthly series; existing monthly model training. Derived hash checked; monthly unique/contiguous sorted dates, finite count targets. Original PDF files remain immutable. |
| project_raw/weather_power/POWER_*.json | geometry.Point.coordinates, _safarsaathi_query.{lat,lon,destination}, header.{start,end}, parameters | 29 named query locations; archived daily POWER 2000–2024. Actual grid point and query location preserved separately. NASA POWER/MERRA-2 attribution in collection license record. | /destinations, /destinations/{id}, /map/layers. Validate source keys, finite/ranged point geometry and metadata; retain source units/date strings. No source-declared EPSG; no reprojection. No tourism location boundary or live feed inferred. |
| raw_collection/sentinel1 and sentinel2 | Product directories, TIFF/JP2 bands plus productInfo/catalogue/quality metadata | Six scenes per mission. Acquisition timestamps parsed from original product IDs; coverage, publisher and licenses joined from DATA_MANIFEST.csv. Copernicus Sentinel terms; AWS packaging/processing-baseline differences documented in SOURCE_INFO.txt. | /satellite/metadata and /datasets. Scene bytes/file counts are actual stats. No new image processing, flood detection, CRS conversion or acquisition-vintage validation. Raw scenes are not the STURM input. |
| project_external/sturm_flood/12748983 | Dataset.zip, verification/catalog metadata and Sentinel1/2_metadata.csv | Separate STURM benchmark, Zenodo record 12748983. Attribution/terms in docs/STURM_ATTRIBUTION.md. | /datasets inventories actual files. Existing segmentation model consumes 128x128x2 preprocessed arrays, not arbitrary raw scenes. Existing event/country split evaluation is retained; no retraining. |
| project_derived/india_scope_20261025/cyclone_monthly.csv, cyclone_events.csv, model_data_provenance.json | date,value; event IDs/date; source checksums | NI basin 1980–2024, NOAA IBTrACS v04r01 archive. Source manifests retained; NOAA attribution. | Existing cyclone forecast, evaluation and /datasets. Original pipeline checks contiguous finite counts, derived-source checksum and event-group split leakage. No landfall or disaster warning inference. |
| project_derived/india_scope_20261025/pm25_annual.csv | date,value, source provenance | India national modeled annual exposure, 1990–2023; WDI EN.ATM.PM25.MC.M3/GBD2023; WDI attribution/license in existing docs. | Existing /environment/pm25-forecast, evaluation and /datasets. Finite annual modeled targets; checksummed provenance. No destination environmental stress labels. |
| indicators/india_environment_tourism/indicators.json and integrity.json | records with geography/year, domestic_visits, foreign_visits, source_quality, surface_area_km2, derived indicators and null missing values; formulae/source metadata | National annual 2011–2024 and 36 State/UT 2023–2024, source-specific environmental dates. Ministry/WDI source manifests and estimate/revision flags retained. | Existing /stress/indicators and /stress/indicator-metadata; /datasets. Check integrity pin and supported geography/year. Indicators are not a trained stress index. |
| raw_collection/reviews CSV/JSON and dataset cards | Existing selected training schema review,label; classifier pipeline owns TF-IDF preprocessing | Global source-domain text, not verified local community feedback. Some corpora have CC BY-NC 4.0 restrictions; exact license per file in inventory/collection docs. | Existing saved review classification; /datasets exposes metadata only, never review bodies. Preserve source labels and provenance; do not claim all languages or sentiment classes. |
| Other tourism PDF/DOC, weather JSON, OSM PBF/poly, UNDRR taxonomy and external source snapshots | Original source-native formats; no new extraction | Per-file source, coverage and license when known are in dataset_inventory.json and source records. UNDRR HIPs are definitions, not observed disaster outcomes. OSM attribution/ODbL applies. | Catalog only unless explicitly listed above. No operational road graph, hazard-exposure overlay, crowd model or live integration inferred from file presence. |

The full raw collection checksum verification was not rerun over its multi-gigabyte satellite archive. Catalog `declared_sha256` and `declared_size_matches` are distinct from a measured hash check. Model artifacts and the integrated monthly/indicator sources have separate actual integrity checks. Source URLs from manifests are not treated as working remote connectors. Nothing was downloaded or refreshed.
