# India-scope forecasting and historical indicators

The current release is `release/india_scope_20261025_03/`. It adds two genuine
trained experiments and a separate historical indicator view while preserving
all four earlier registered models. The broad `disaster_risk_predictor` and
`destination_stress_predictor` use the shared `DATA_INSUFFICIENT` status because
the required outcome labels and coverage are absent. Their original 503
contracts and disabled controls remain intact.

## North Indian Ocean archive counts

Model ID: `north_indian_cyclone_count_forecaster`. NOAA NCEI IBTrACS v04r01 NI
CSV snapshot: 27,886,424 bytes, SHA-256
`b30984b56c428391eff17a44d1a9662e444fc4ba419417e9613c18db07424155`.
Of 62,864 source positions, the experiment retains distinct storm SIDs with at
least one BASIN=NI, NATURE=TS, TRACK_TYPE=main position. It includes tropical
depressions and applies no wind threshold. Provisional/spur, non-tropical,
out-of-basin positions and incomplete recent years are excluded.

Each eligible SID is counted once in the month of its first qualifying position,
determined before the date restriction. There are 388 eligible storm IDs in
540 months, January 1980–December 2024. Zero-count months number 304. Their
meaning is exactly zero qualifying archive IDs, not verified absence of every
real-world cyclone or disaster. No binary negative disaster labels are invented.
This basin includes waters and countries outside India; no political-country
boundary, Indian landfall, severity or disaster-impact label is inferred.

Training: 1980–2009 (360 months). Validation: 2010–2014 (60 months). Frozen-fit
test: 2015–2024 (120 months). Validation compares constant mean, seasonal mean
and regularized Poisson calendar regression. Calendar sine/cosine harmonics are
known before any forecast date; no contemporaneous weather/impact is used.
Lowest validation Poisson deviance selects seasonal mean. It refits through
2014 for the fixed ten-year holdout and through 2024 for the final artifact.
The holdout measures a fixed seasonal climatology, not a rolling emergency
warning system. Event SIDs are disjoint across splits. Geography holdout is
NOT_APPLICABLE for one basin; there is no country/district-generalization claim.

Held-out MAE: 0.6347619048 recorded storm IDs/month; RMSE: 0.9109313467;
MASE: 0.9646163444; WAPE: 0.6681704261; Poisson deviance: 1.0357690964.
Full baseline comparisons and yearly folds are in the saved evaluation.
Fractional forecasts are expected counts, not probabilities or observed storms.
The output starts January 2025 and has no current-2026 condition claim.

## National modeled PM2.5 exposure

Model ID: `india_pm25_exposure_forecaster`. Target: World Bank WDI
EN.ATM.PM25.MC.M3, India national population-weighted annual ambient PM2.5
exposure, micrograms/m³. The underlying GBD2023/IHME indicator is modeled;
it is not a raw sensor measurement, tourism-caused pollution, destination
occupancy, or ecological capacity utilization.

The public World Bank series has 34 complete annual values, 1990–2023; no
target imputation. Training: 1990–2009 (20). Validation: 2010–2016 (7).
Test: 2017–2023 (7). Persistence, drift and ridge are compared at identical
expanding one-year origins, fitting only past exposure prefixes. Lowest
validation MAE selects ridge; test outcomes never select the method. Later
test origins may use earlier observed test outcomes, as an expanding backtest.

Held-out MAE: 2.5454047768 µg/m³; RMSE: 2.6587779351; MASE: 3.0520549524;
WAPE: 0.0471400054. Ridge's test MAE is only 0.1023263783 µg/m³ below
persistence; seven targets do not establish robust superiority. The final
artifact refits through 2023 and extrapolates 2024 only. No current air-quality
or health decision guidance is supplied. There are no calibrated intervals.

The current GBD vintage was published in 2026. Revised historical estimates
were not necessarily available at past origins. Both experiments are explicitly
retrospective revised-vintage studies, not publication-vintage real-time
backtests. No observed future weather, post-event impact or tourism volume
is used as a predictive feature. National and basin models cannot support a
destination-held-out evaluation.

## Historical tourism/environment indicators

`outputs/indicators/india_environment_tourism/indicators.json` is a compact,
checksummed source-derived snapshot, outside the trained model registry.
It contains 14 national country-years (2011–2024) and 72 State/UT-years
(36 geographies, 2023–2024), extracted from official local Compendium 2025
tables 4.1.1 and 4.1.2 (PDF pages 211, 213, 214). Relevant pages were rendered
and inspected. The printed Jammu & Pradesh row is canonicalized by row identity
to Jammu and Kashmir, with no numeric changes. Source pages/tables/rows remain
traceable. State units stay rounded millions; national totals retain printed
integer counts. State sums reconcile within the declared rounding tolerance.

Delhi and Maharashtra 2024 values are publisher estimates using national growth;
they remain explicitly flagged. Published 2023 revision flags are retained.
Compiling state hotel returns and national estimates does not establish complete
independent visitor enumeration. Visits can repeat the same person.

The only intensity formula is national domestic visits divided by same-year
World Bank/FAO surface area in km². It gives visits/km²/year, not simultaneous
crowding or capacity utilization. Missing area yields null; nonpositive area
is rejected. Growth is 100 × (current visits / previous observed visits − 1),
with missing/zero previous values yielding null. No weighted stress score exists.

National yearly modeled PM2.5 and FAO water-stress context align on IND/year.
There are 13 exposure years through 2023, 12 water-stress years through 2022,
and 14 area years in 2011–2024. Missing values remain null, without interpolation
or carry-forward. These national indicators are never allocated to State/UTs.
No correlation is presented as tourism causation. No observed aligned occupancy,
destination capacity or ecological-pressure labels are available, so the broad
stress model remains untrained. Two state years cannot establish temporal
forecast generalization.

## CLI, HTTP and application

With the normal requirements installed, run from the project directory:

```powershell
$env:PYTHONPATH = 'src'
$env:OMP_NUM_THREADS = '2'
python -m safarsaathi_ml.cli validate-artifacts
python -m safarsaathi_ml.cli evaluate --model cyclone_count
python -m safarsaathi_ml.cli evaluate --model pm25
python -m safarsaathi_ml.cli predict --model cyclone_count --destination NI --horizon 3
python -m safarsaathi_ml.cli predict --model pm25 --destination IND --horizon 1
python -m safarsaathi_ml.cli serve --port 8000
```

In `frontend`, run `npm ci`, then `npm run dev`. Production build and preview:
`npm run build`; `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort`.
The API defaults to localhost:8000; set VITE_SAFARSAATHI_API_URL at Vite startup
to change it. Select AI Models. New panels display exact scope, dates, units,
version, evaluation and limitations. Broad unsupported controls stay disabled.

- POST `/disaster/cyclone-count`: exactly `{"geography":"NI","horizon":1}`;
  integer horizon 1–12, periods anchored after 2024-12.
- POST `/environment/pm25-forecast`: exactly `{"geography":"IND","horizon":1}`;
  only one annual period after 2023 is supported.
- GET `/stress/indicator-metadata`: supported geographies, years, definitions.
- POST `/stress/indicators`: exactly `{"geography":"IND","year":2024}`;
  national 2011–2024 or an exact supported State/UT name for 2023–2024.
- POST `/disaster/predict` and `/stress/predict`: broad models remain explicit 503.

Forecast responses include historical origin, target definition, dates, version,
units, predictions and limitations. Indicator responses say prediction=false,
trained_model=false, with source-quality flags and missingness rules. Strict
JSON schemas reject unsupported locations, dates/years, bool horizons, extra
fields and nonfinite numbers. Existing safe JSON errors, content-type/size limits,
artifact checksums and exclusive Windows socket binding remain. HTTP accepts
no filesystem paths and inference never trains or downloads data.

## Reproduce and troubleshoot

Acquisition scripts store new immutable snapshots under
`data/external/india_scope_20261025/`; original raw sources are untouched.
`scripts/fetch_india_sources.py` bounds download sizes and records URLs, dates,
HTTP modification date, checksum and terms. It refuses overwrite. Do not rerun
it over an existing snapshot; future source vintages need a new directory.
`scripts/india_source_audit.py` requires optional pypdf from the bundled runtime.
`prepare_model_data(project)` in india_data.py builds checksummed count/exposure
datasets; `scripts/build_india_indicators.py` extracts the indicator snapshot.
Extraction caches and source files are deliberately excluded from the ZIP.

On a fresh research checkout with validated derived files and without those
IDs already registered, `train --model cyclone_count` / `train --model pm25`
creates versioned artifacts, metrics, feature schemas, source manifests,
dependencies and checksums. Existing IDs refuse overwrite. Do not delete
registry entries to bypass that guard. Final inference artifacts bundle their
own past history and work without raw/derived training data. Actual dependency
versions are pinned in each model's metadata; use compatible serialized-artifact
versions rather than assuming all future sklearn versions are compatible.

If a model is unavailable, run validate-artifacts and inspect its trusted
metadata/checksum; restore the verified release rather than retrain during API
startup. If a location/year is rejected, use indicator metadata or supported
NI/IND forecast geography. Do not substitute an arbitrary district. A null
environment value means unavailable, not zero. API/backend errors should remain
visible in the form. If port 8000 is occupied, choose a free port and set the
frontend API URL consistently. Playwright/Chrome are optional testing tools;
set PLAYWRIGHT_MODULE_PATH when using the bundled package. No browser download
is required. External fonts/Tailwind still affect offline appearance.

The versioned release verifier runs full scoped project tests, real HTTP,
frontend tests/build, all six artifact replays, raw checksums, training refusals
and final browser journeys. `python -m safarsaathi_ml.india_release verify`
then `package` targets only the already prepared current release and refuses
output overwrite. A future audit requires a new release name and snapshot.
Packaging CRC/hash-checks the ZIP and runs every model and the indicator snapshot
from a fresh extracted copy without raw/external data.

## Sources and attribution

- NOAA: Gahtan, Jennifer; Knapp, Kenneth R.; Schreck, Carl J. III; Diamond,
  Howard J.; Kossin, James P.; Kruk, Michael C. (2024). IBTrACS Version 4.01,
  North Indian subset. NOAA NCEI. DOI https://doi.org/10.25921/82ty-9e16.
  Also Knapp et al. (2010), https://doi.org/10.1175/2009BAMS2755.1.
  Official NOAA metadata permits use and redistribution without restriction.
- World Bank Open Data/WDI; underlying PM2.5: GBD2023 Collaborator Network,
  IHME modeled exposure. Indicator page CC BY 4.0:
  https://data.worldbank.org/indicator/EN.ATM.PM25.MC.M3.
- FAO AQUASTAT water stress and FAO surface area, republished by World Bank,
  CC BY 4.0: https://data.worldbank.org/indicator/ER.H2O.FWST.ZS and
  https://data.worldbank.org/indicator/AG.SRF.TOTL.K2.
- Source: Ministry of Tourism, Government of India — Research & Analytics
  Division; State/UT Tourism Departments, India Tourism Data Compendium 2025.
  No new open license is assigned to the local PDF; PDF not redistributed.

The original review/flood/annual-series licensing and restrictions remain in
the existing attribution documents. No large dataset was uploaded externally,
and no account, paid service or access-control bypass was used. Public-source
downloads were about 28 MB plus small JSON/HTML files, without pretrained weights.
