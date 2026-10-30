# Remaining limitations and unblock requirements

## Predictors intentionally unavailable

- **India-wide multi-disaster warning (`DATA_INSUFFICIENT`):** Available hazard material does not establish a complete, date-versioned India area/time panel with positive outcomes, observation completeness, verified negative windows, and predictors available before each forecast cutoff. A basin-wide cyclone archive-count series is not an India landfall or impact warning. To unblock: obtain licensed event outcomes and exposure/observation coverage by geography and time, document completeness and source vintage, then create spatially and temporally held-out evaluation with pre-event features and calibrated decision metrics.
- **Destination ecological stress (`DATA_INSUFFICIENT`):** No aligned destination/time target for occupancy, capacity utilization, water quality, ecological damage or tourism-attributable pressure was found. National annual PM2.5 cannot supply local target labels. To unblock: provide validated geocoded destination boundaries, timestamped environmental observations, visitor/capacity denominators, and defensible independent labels with reuse rights.

The UI offers separately scoped experimental forecasts and sourced historical indicators. It does not imply an official emergency-warning service. Experimental output must not be the sole basis for emergency decisions.

## Model and source limits

- Annual ITA ends 2019; monthly FTA ends 2024-12. Neither estimates current 2026 demand.
- The flood model has low held-out precision (0.3302); its reference masks may combine permanent water and flood extent. It only accepts the benchmark's preprocessed tile format.
- Cyclone test is historical basin archive count, with 120 held-out months and no reconstructed publication vintages, spatial generalization, landfall, severity or calibrated interval.
- PM2.5 uses 34 annual national modeled values and only seven held-out years; its 2026-revised source vintage means the backtest is retrospective and its forecast starts in 2024.
- Review classification supports two source labels only and inherits source-domain and annotation bias.
- External Tailwind/fonts may not render with full fidelity offline. Model requests remain usable through the documented local API.

## Operational prerequisites

Install Python dependencies and frontend dependencies. `npm ci` may need network access if the lockfile packages are not cached. The approved STURM archive is intentionally not in the release; only flood inference on a compatible preprocessed input works without it. No API key is required for documented local workflows. Refreshing external data requires a new dated source snapshot, license review, evaluation, and a new release; never overwrite prior snapshots/releases.
