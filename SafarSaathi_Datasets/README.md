# SafarSaathi — RAW Dataset Collection

**Collection date:** 2026-10-03  ·  **Manifest generated:** 2026-10-03T11:29:26Z  ·  **Files:** 961  ·  **Total size:** 10.6 GB (11,422,398,009 bytes)

---

## 1. What SafarSaathi is

SafarSaathi is an AI-Powered Tourism Intelligence & Disaster Resilience Platform. It is intended to combine **tourism demand**, **weather and climate**, **geographic infrastructure**, **disaster records**, **satellite imagery** and **tourist/community feedback** in order to support:

- tourist demand forecasting
- destination stress prediction
- crowd hotspot detection
- environmental monitoring
- disaster-risk estimation
- tourist exposure estimation
- route-risk analysis
- what-if simulation
- GA/PSO optimisation of tourism-resilience planning

The provisional pilot region for this first collection is **Uttarakhand, India** (Indian Himalayan tourism).

## 2. This folder contains RAW DATA ONLY

> ### NO PREPROCESSING HAS BEEN PERFORMED
>
> Every file here is the **original file exactly as downloaded**. Nothing in this folder has been cleaned, merged, normalised, deduplicated, imputed, renamed or converted. There is **no** train/test split, **no** ML-ready matrix, **no** feature engineering, **no** labels and **no** synthetic data. All of that is the AIML team's job, at the next stage, on a copy.

## 3–5. Datasets, their sources, and what they are for

### `tourism_india` — tourism india

- **Source:** Ministry of Tourism, Government of India
- **Contains:** Domestic/foreign tourist visits, state-wise tourism, accommodation, tourism GDP and expenditure, long historical series
- **Will be used for:** Tourist demand forecasting, destination stress prediction, state-level baseline for what-if simulation
- **Size:** 80.1 MB across 14 files
- **Details:** [`raw/tourism_india/SOURCE_INFO.txt`](raw/tourism_india/SOURCE_INFO.txt)

### `weather_nasa_power` — weather nasa power

- **Source:** NASA POWER (MERRA-2) daily reanalysis
- **Contains:** Daily temperature, rainfall, humidity, wind, pressure, dew point, solar radiation over the Uttarakhand pilot grid, 2000-2026
- **Will be used for:** Hazard modelling, monsoon intensity, exposure and feasibility inputs
- **Size:** 55.5 MB across 244 files
- **Details:** [`raw/weather_nasa_power/SOURCE_INFO.txt`](raw/weather_nasa_power/SOURCE_INFO.txt)

### `osm_india` — osm india

- **Source:** OpenStreetMap via Geofabrik
- **Contains:** Roads, buildings, landuse, tourism attractions, accommodation POIs for the Northern Zone of India (includes Uttarakhand)
- **Will be used for:** Route-risk analysis, road/bridge exposure, accessibility and crowd-hotspot geolocation
- **Size:** 213.2 MB across 3 files
- **Details:** [`raw/osm_india/SOURCE_INFO.txt`](raw/osm_india/SOURCE_INFO.txt)

### `disaster_undrr` — disaster undrr

- **Source:** UNDRR Datum
- **Contains:** Hazard Information Profiles (153 global hazard definitions)
- **Will be used for:** Disaster-risk estimation, hazard taxonomy for labelling events
- **Size:** 1.1 MB across 2 files
- **Details:** [`raw/disaster_undrr/SOURCE_INFO.txt`](raw/disaster_undrr/SOURCE_INFO.txt)

### `sentinel1` — sentinel1

- **Source:** Copernicus Sentinel-1 GRD (AWS Open Data mirror)
- **Contains:** 6 raw SAR scenes over the Uttarakhand pilot bounding box, baseline / monsoon / post-monsoon, 2021 and 2023
- **Will be used for:** Flood detection, water-extent detection, disaster change detection, infrastructure exposure
- **Size:** 7.4 GB across 161 files
- **Details:** [`raw/sentinel1/SOURCE_INFO.txt`](raw/sentinel1/SOURCE_INFO.txt)

### `sentinel2` — sentinel2

- **Source:** Copernicus Sentinel-2 Level-2A (AWS Open Data mirror)
- **Contains:** 6 raw optical scenes over the Uttarakhand pilot bounding box across seasons, 2023 and 2024
- **Will be used for:** Land cover, vegetation and environment monitoring, water extent, destination expansion analysis
- **Size:** 2.8 GB across 496 files
- **Details:** [`raw/sentinel2/SOURCE_INFO.txt`](raw/sentinel2/SOURCE_INFO.txt)

### `reviews` — reviews

- **Source:** Hugging Face datasets with declared open licences
- **Contains:** Tourism/hotel review text (English and multilingual)
- **Will be used for:** Sentiment, crowding complaints, cleanliness, safety, transport, accommodation, accessibility, environmental concerns
- **Size:** 30.3 MB across 7 files
- **Details:** [`raw/reviews/SOURCE_INFO.txt`](raw/reviews/SOURCE_INFO.txt)

### `worldbank_un_tourism` — worldbank un tourism

- **Source:** World Bank WDI (UN Tourism source data)
- **Contains:** 8 international tourism indicators for all economies and India, 1995-2025
- **Will be used for:** International benchmarking, tourism demand context, cross-country normalisation of tourism economics
- **Size:** 15.7 MB across 34 files
- **Details:** [`raw/worldbank_un_tourism/SOURCE_INFO.txt`](raw/worldbank_un_tourism/SOURCE_INFO.txt)

## 6–7. Geographic and time coverage

| Dataset | Geographic coverage | Time coverage |
|---|---|---|
| `tourism_india` | India, all states/UTs (incl. a dedicated Uttarakhand Regional Tourism Satellite Account) | reference years 2019–2023 in the raw series; compendium volumes carry multi-decade history |
| `weather_nasa_power` | 42-point POWER grid over lat 28.60–31.65 N, lon 77.20–81.50 E (Uttarakhand) | 2000-01-01 → 2026-09-30, daily |
| `osm_india` | Geofabrik Northern Zone of India (includes Uttarakhand) | single snapshot, 2026-10-02/03 |
| `disaster_undrr` | Global hazard taxonomy | versioned v1.0.0, not a time series |
| `sentinel1` | bbox POLYGON((77.24 28.61, 81.45 28.61, 81.45 31.63, 77.24 31.63, 77.24 28.61)) | acquisitions 2021-05 → 2023-07 |
| `sentinel2` | same bbox | acquisitions 2023-05 → 2024-10 |
| `reviews` | global | undated review corpora |
| `worldbank_un_tourism` | all World Bank economies | 1995–2025 |

## 8. Licensing and attribution

**Read [`LICENSES_AND_ATTRIBUTION.md`](LICENSES_AND_ATTRIBUTION.md) before using any of this.** Three things to watch:

- **OpenStreetMap** is ODbL 1.0 — attribution *and share-alike* on any derived database.
- **Two of the three review datasets are CC-BY-NC-4.0 — non-commercial use only.**
- Everything else (NASA POWER, Copernicus Sentinel, World Bank, UNDRR, Ministry of Tourism) is free/open with attribution.

## 9. Approximate total size

**10.6 GB** across **961 files**.

| Folder | Files | Size |
|---|---:|---:|
| `raw/tourism_india` | 14 | 80.1 MB |
| `raw/weather_nasa_power` | 244 | 55.5 MB |
| `raw/osm_india` | 3 | 213.2 MB |
| `raw/disaster_undrr` | 2 | 1.1 MB |
| `raw/sentinel1` | 161 | 7.4 GB |
| `raw/sentinel2` | 496 | 2.8 GB |
| `raw/reviews` | 7 | 30.3 MB |
| `raw/worldbank_un_tourism` | 34 | 15.7 MB |
| **TOTAL** | **961** | **10.6 GB** |

## 10. Downloads that succeeded

| # | Dataset | Result |
|---|---|---|
| 1 | India Tourism (Ministry of Tourism) | ✅ Complete — 13 original files (raw statistics 2019–2023, compendiums, Uttarakhand RTSA) |
| 2 | NASA POWER weather | ✅ Complete — 243 files, 9 parameters × 27 years, 2000–2026 |
| 3 | OpenStreetMap | ⚠️ **Partial by scope** — Northern Zone extract (official sub-region, verified against publisher MD5). Full India extract unavailable, see §11 |
| 4 | UNDRR disaster data | ⚠️ **Partial** — Hazard Information Profiles downloaded (153 records). DesInventar India/Uttarakhand event-loss data not publicly available, see §11 |
| 5 | Sentinel-1 | ✅ 6 raw scenes (via AWS Open Data mirror, see §12) |
| 6 | Sentinel-2 | ✅ 6 raw scenes (via AWS Open Data mirror, see §12) |
| 7 | Tourism reviews | ✅ 3 openly-licensed datasets + their dataset cards |
| 8 | World Bank / UN Tourism | ✅ 8 indicators × (bulk ZIP + all-countries JSON + India JSON) + metadata = 33 files |

## 11. Downloads that failed or could not be completed

**Full-India OpenStreetMap extract (1.6–1.7 GB).** Throughout the collection window the Geofabrik India extract was mid daily rebuild: every dated file (`india-261002.osm.pbf` and earlier) returned **HTTP 404**, and the `india-latest.osm.pbf` alias redirected to the Geofabrik homepage. An automated poller retried **120 times over ~2 hours** without success. The official **Northern Zone** sub-region extract — which does contain Uttarakhand — was downloaded instead and verified against the publisher's own MD5. **No unofficial mirror was substituted.** Full detail in [`raw/osm_india/SOURCE_INFO.txt`](raw/osm_india/SOURCE_INFO.txt).

**UNDRR DesInventar disaster-loss event data for India / Uttarakhand.** The official DesInventar platform does not publish this database. Checked: `www.desinventar.com` and `api.desinventar.org` (no response), `data.undrr.org/api` (login wall), and the official *India Uttarakhand* download link `desinventar.cimafoundation.org/DesInventar/download_base.jsp?countrycode=005` — reachable, but that instance only serves Albania, Armenia, Kosovo, Moldova, Montenegro, Serbia and Tanzania. The Wayback Machine holds no India/Uttarakhand DesInventar data file. **No unofficial mirror was substituted.** Alternatives that do hold India disaster-loss data — EM-DAT (CRED) and the UNDRR Sendai Framework Monitor — both require free registration and were therefore out of scope here.

**UN Tourism's own statistics tables.** The UN Tourism Tourism Statistics Database sits behind a registration / request-access wall. The World Bank tourism indicators (which carry the same UN Tourism figures) were collected instead.

**Indian / Himalayan tourism review text.** No openly-licensed corpus was found. The Uttarakhand datasets that exist on Hugging Face are speech and translation corpora, not tourism reviews. TripAdvisor, Booking.com and Google reviews were **not scraped** — their terms of service prohibit it. Global hotel-review corpora were collected as the NLP baseline instead.

**India monthly tourism bulletins / older India Tourism Statistics volumes.** The Ministry's monthly-statistics site is a JavaScript application whose backend API is not publicly reachable, and older volumes (2003–2018) are listed on the portal without working attachment links. The raw-data section (2019–2023) and the current compendium volumes were obtained.

## 12. Sources that require account / API credentials

| Source | Credential needed | What was done instead |
|---|---|---|
| **Copernicus Data Space Ecosystem** (product download) | **Yes** — free CDSE account + OAuth token. The *catalogue* is open; the *product* endpoint is not. Anonymous request → `HTTP 401 DAT-ZIP-604 "Token not found"` | Official catalogue queried and saved in full for every month (the exact scene list). Products then fetched from the **AWS Open Data** mirror with the project owner's explicit approval. **Deviation documented below.** |
| UNDRR Datum API | No | Downloaded directly. |
| NASA POWER API | No (free, open) | Downloaded directly, rate-limited. |
| World Bank API | No | Downloaded directly. |
| Ministry of Tourism portal | No | Downloaded directly. |
| Geofabrik | No | Downloaded directly. |
| Hugging Face Hub | No | Downloaded directly. |
| EM-DAT / Sendai Monitor | Yes (registration) | Not attempted. |

### Documented Sentinel deviation

Because the Copernicus product endpoint is credential-gated, the Sentinel products come from AWS Open Data:

- **Sentinel-2** — bucket `sentinel-s2-l2a`. Original Level-2A `.jp2` band data. The bucket flattens the `.SAFE` wrapper and the `GRANULE` sub-tree; files were written under the product's official `.SAFE` name from the Copernicus catalogue. The AWS copy corresponds to the **pre-N0509** processing baseline while the catalogue names the reprocessed N0510/N0511 product for the same acquisition.
- **Sentinel-1** — bucket `sentinel-s1-l1c` (Sentinel Hub / Element 84). Measurements are **cloud-optimised GeoTIFF**, *not* the original SAFE/JAXA structure. Object payloads were not altered; only the directory layout was reconstructed.

Both remain free and fully open under the Copernicus Sentinel Data Legal Notice. If a CDSE account is provided later, these twelve scenes can be re-fetched as original SAFE products.

## 13. What must NOT be done with this data *yet*

This folder is an **archive**, not a workspace. Before any of the following, copy the data somewhere else and work on the copy.

**Do not**

- merge the per-year NASA POWER files, or the per-parameter files
- fill, interpolate or drop the `-999.0` missing values NASA returns
- convert any `.doc`, `.pdf`, `.zip`, `.jp2` or `.tiff` file
- parse `india-latest.osm.pbf` and extract roads, hotels or GeoJSON from it
- run your own cloud mask, atmospheric correction or resampling on the Sentinel products — use the delivered Level-2A as-is
- compute NDVI or any other index here
- threshold Sentinel-1 into a water or flood mask here
- tokenise, stem, translate, de-duplicate or score sentiment on the reviews
- concatenate the World Bank per-indicator JSON into one table
- rename columns, change dtypes, normalise units or encode categoricals
- create labels, splits, feature matrices or synthetic rows
- overwrite or re-save any file in place — that would invalidate [`CHECKSUMS.txt`](CHECKSUMS.txt)

**Do, as the next stage**

- verify integrity first: `python verify_checksums.py` from this folder (full run, or `--sample 50` for a quick smoke test)
- record provenance from `DATA_MANIFEST.csv` alongside any derived artefact
- carry the attributions in `LICENSES_AND_ATTRIBUTION.md` into every downstream deliverable

---

## Files in this folder

| File | Purpose |
|---|---|
| `README.md` | this document |
| `DATA_MANIFEST.csv` | one row per file: source, URL, dates, size, geography, licence, SHA-256 |
| `LICENSES_AND_ATTRIBUTION.md` | per-source licence terms and required credits |
| `DOWNLOAD_LOG.txt` | every HTTP attempt, retry and failure, with timestamps |
| `CHECKSUMS.txt` | SHA-256 + size + mtime for every file |
| `verify_checksums.py` | re-verify the whole collection with one command |
| `raw/<category>/SOURCE_INFO.txt` | detailed provenance for each category |

*Generated 2026-10-03T11:29:26Z by the SafarSaathi raw data acquisition run.*
