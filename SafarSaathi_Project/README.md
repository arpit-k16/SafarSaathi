# SafarSaathi

**AI-Powered Tourism Intelligence & Resilience Platform** for Uttarakhand and India.

SafarSaathi is a destination-level decision-support system. It puts visitor demand next to
capacity, climate, flood and cyclone evidence, so destination managers can test a scenario
before the season arrives, compare interventions, and keep a person in charge of the final call.

Core loop, from the project report: **predict → simulate → optimise → explain → support human action.**

## Run it

**Windows, one click:** double-click `START_SAFARSAATHI.bat` in the repository root. It creates a
Python environment, installs packages, stops any older SafarSaathi server, starts the server
and opens <http://localhost:8000>.

**Any platform:**

```bash
cd SafarSaathi_Project
python -m pip install -r requirements.txt
python run_safarsaathi.py            # or: PYTHONPATH=src uvicorn safarsaathi_ml.asgi:app --port 8000
```

The built web console is served by the backend at `/`. To rebuild it: `cd web && npm ci && npm run build`.
Map tiles use CARTO basemaps, which need a free key (<https://carto.com/basemaps/apikey>): copy
`web/public/map-config.example.json` to `web/public/map-config.json`, add the key, and rebuild (or put the
same file in `web/dist/`). The key file is git-ignored. Without a key the maps still work, with a watermark.

**Docker / Render:** `render.yaml` and `Dockerfile` build the console and serve it with the API from
one container. See [docs/RENDER_DEPLOYMENT.md](docs/RENDER_DEPLOYMENT.md).

## What it does

| Area | Page | What you get |
|---|---|---|
| Demand | Tourism demand | Annual and monthly arrival forecasts, held-out error, and a "why this forecast" explanation |
| Places | Destinations and climate | 25 years of NASA POWER climate for 29 Uttarakhand locations |
| Places | Hotspots and anomalies | DBSCAN / K-means hotspots of 28 destinations; anomaly detection on visitor and rainfall years, checked against the 2013 disaster and COVID |
| Risk | Cyclone archive | North Indian Ocean cyclone-count forecaster |
| Risk | Flood segmentation | Sentinel-1 water and flood-extent segmentation (STURM-Flood) |
| Risk | Risk-aware routing | OpenStreetMap road network; fastest route vs a route weighing hazard, vulnerability, congestion and uncertainty; simulated closures |
| Visitors | Review insights | TF-IDF + linear sentiment classifier |
| Planning | Digital twin and stress | State of 28 destinations, a transparent Destination Stress Index, what-if scenarios, every value labelled observed / derived / simulated |
| Planning | Capacity scenarios | Demand vs capacity arithmetic |
| Planning | Allocation optimiser | GA / PSO visitor allocation, and an intervention planner that scores plans through the digital twin against do-nothing, greedy and the exhaustive optimum |
| Evidence | Model center, Data hub, Reports, System | Model cards, release gate, data inventory, evidence reports, API console |

## Models: release v1.0

Every saved model passed the release gate in `src/safarsaathi_ml/release_gate.py`
(results frozen in `models/release_v1.json`). The gate requires: (1) the artifact matches its
checksum and reloads; (2) on held-out test data it does at least as well as a naive baseline;
(3) its limitations are documented. **Final v1.0 means frozen, reproducible and baseline-checked
within its documented scope, not operationally validated.**

| Model | Held-out test | Naive baseline |
|---|---|---|
| Review classifier | accuracy 0.85 | 0.52 (majority class) |
| Annual tourism demand (drift) | MAE 5.79 lakh arrivals | 9.61 lakh (repeat last year) |
| Monthly foreign arrivals | is the persistence baseline itself, chosen on validation over drift, seasonal-naive and ridge | — |
| Cyclone counts (seasonal mean) | MAE 0.63 | 0.85 (constant mean) |
| PM2.5 exposure (ridge) | MAE 2.55 | 2.65 (repeat last year) |
| Flood segmentation (gradient boosting) | IoU 0.31 on unseen countries (0.67 on validation) | 0 (no water) |

Two capabilities are served by the report's MVP choices (§9.10) rather than learned models,
because no outcome labels exist to train one:

- **Destination stress**: the transparent Destination Stress Index (Index v1.0). Its ranking is robust to re-weighting (Spearman ρ ≈ 0.98).
- **Disaster risk**: rule- and scenario-based exposure (Rule-based v1.0): risk-aware routing, anomaly detection and the cyclone forecaster.

## Data

| Source | Used for |
|---|---|
| Uttarakhand Tourism (UTDB) statistics, 2000–2024 | Visitors to 28 destinations; every row passes the Indian + foreign = total check |
| World Bank, Ministry of Tourism | National annual and monthly arrivals |
| NASA POWER daily reanalysis, 2000–2024 | Climate for 29 locations |
| IBTrACS | North Indian Ocean cyclone tracks |
| STURM-Flood (Sentinel-1) | Flood segmentation (CC BY 4.0) |
| OpenStreetMap (ODbL), Geofabrik extract | Road network for routing |
| World Bank / GBD | National PM2.5 exposure |

Raw downloads are not in git (see `SafarSaathi_Datasets/DATA_MANIFEST.csv`). The repository carries
the small processed files the app needs (`data/processed/`) and a checksum-verified
`deploy_snapshot/`, so a fresh clone runs without the raw collection.
Rebuild steps: `python -m safarsaathi_ml.utdb .` (visitor table), `scripts/osm_road_graph/` (road graph),
`python -m safarsaathi_ml.cli build-snapshot`, `python -m safarsaathi_ml.release_gate .`.

## Tests

```bash
cd SafarSaathi_Project
python -m pip install -r requirements-dev.txt
PYTHONPATH=src python -m pytest tests -q      # 204 tests
cd web && npm test
```

## Limitations

The stress index, routing risk terms and intervention effects are proxies built from public data:
there is no observed crowding, landslide-susceptibility, live road-status or verified intervention-cost
data in this project. Visitor counts are annual, not daily. Climate comes from a 0.5° grid.
Each page lists its own limitations. SafarSaathi supports decisions; it does not predict sudden
disasters or replace emergency authorities. See [docs/REMAINING_LIMITATIONS.md](docs/REMAINING_LIMITATIONS.md).

## Repository layout

```
SafarSaathi_Project/
  src/safarsaathi_ml/   backend: models, digital twin (resilience.py), routing, release gate, API
  web/                  React + Vite console (served from web/dist)
  models/               saved model artifacts, registry, release_v1.json
  data/processed/       processed data the app reads at runtime
  deploy_snapshot/      checksum-verified adapter outputs for hosted runs
  scripts/              data build scripts (OpenStreetMap road graph, etc.)
  tests/                pytest suite
  docs/                 model cards, provenance, licences, deployment, history
SafarSaathi_Datasets/   manifest and checksums for the raw collection
```

Earlier release notes: [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md).
Model details: [ML_MODELS.md](ML_MODELS.md) and [docs/MODEL_CARDS.md](docs/MODEL_CARDS.md).

SafarSaathi is an AIML team project at Bennett University.
