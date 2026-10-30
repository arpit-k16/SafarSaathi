# SafarSaathi model cards

Capability statuses use a shared vocabulary: `EXPERIMENTAL` for saved models without operational validation, `HISTORICAL_ONLY` for past observations, `INDICATOR_ONLY` for sourced measurements/estimates without outcome prediction, `DATA_INSUFFICIENT` when valid labels or coverage are missing, and `UNAVAILABLE` when an artifact/dependency cannot be loaded. `VALIDATED` is reserved for a task with evidence fit for its stated use; none of these six is claimed as an operational warning. See the release `verification_report.json` for complete split metrics and command evidence.

## Hotel review sentiment — `nlp-20261024T182952Z`

- **Status / use:** Experimental binary classification of source review labels; not destination-specific unless the underlying source establishes that scope.
- **Target and features:** `NEGATIVE` or `POSITIVE`; persisted TF-IDF and logistic-classification pipeline applies the same text preprocessing at training and inference. Neutral labels are not supported.
- **Evaluation:** Held-out 2,507 reviews; accuracy 0.8500, macro F1 0.8495. Negative precision/recall/F1: 0.8512/0.8654/0.8582 (n=1,315); positive: 0.8487/0.8331/0.8408 (n=1,192). The source-split audit and pipeline artifact are retained with the model evidence.
- **Limits:** Labels inherit source annotation and domain bias; do not interpret as objective service quality or coverage of all languages/destinations.

## Annual tourism arrivals — `tourism_demand_forecaster`

- **Status / use:** Experimental historical India annual international tourist arrivals, World Bank `ST.INT.ARVL`, 1995–2019 (25 annual observations). Unit: arrivals/year. Separate target from monthly FTA.
- **Evaluation:** Chronological historical-origin evaluation; five one-step test targets. MAE 578,589 arrivals; RMSE 710,023; MASE 2.113; WAPE 0.0367. Horizon MAE: 1y 578,589 (n=5), 2y 1,080,395 (n=4), 3y 1,572,175 (n=3). Metrics are not current-demand validation.
- **Limits:** Source ends in 2019; no pandemic/post-pandemic test, revised data vintages, or calibrated intervals. National only, not Uttarakhand/destination demand.

## Monthly foreign tourist arrivals — `tourism_monthly_fta_forecaster`

- **Status / use:** Experimental monthly FTA count forecasting, 2019-01–2024-12 (72 observations), excluding NRI arrivals. Monthly target stays distinct from annual ITA.
- **Evaluation:** Chronological validation selects persistence. Fixed test 2023–2024, expanding past-only origins. At 1/3/6 months: MAE 100,187 (n=24), 185,914 (n=22), and 266,022 (n=19); corresponding MASE 0.214, 0.397, and 0.568. Validation period includes recovery from pandemic disruption.
- **Limits:** No 2025/2026 actuals; small post-pandemic test and no calibrated intervals. Annual totals and monthly definitions are not interchangeable.

## Flood-scene segmentation — `flood_segmentation_model`

- **Status / use:** Experimental segmentation of the delivered STURM Sentinel-1 preprocessed 128×128×2 input; target is publisher reference mask where mask > 0.
- **Evaluation:** Event/country-separated held-out reference pixels; validation-selected threshold 0.3. Test IoU 0.3103, Dice/F1 0.4736, precision 0.3302, recall 0.8372. Confusion counts and per-scene details are in registry evaluation metadata.
- **Limits:** Low precision and many false positives; reference water can include permanent water, not only temporary flood. Input is not arbitrary satellite imagery. Not a flood warning or operational detector.

## North Indian Ocean archived cyclone counts — `north_indian_cyclone_count_forecaster`

- **Status / use:** Experimental expected monthly counts of distinct qualifying MAIN IBTrACS NI-basin tropical-storm IDs (includes depressions), 1980–2024; 540 monthly rows.
- **Evaluation:** Chronological train 1980–2009, validation 2010–2014, fixed test 2015–2024. Validation-selected seasonal mean test MAE 0.6348 IDs/month, RMSE 0.9109, MASE 0.9646, WAPE 0.6682. Test constant-mean MAE 0.8521 and Poisson calendar MAE 0.6847.
- **Limits:** Archive counts, not India landfalls, impacts, severity, or event probability. Archive zeros are not verified disaster-free observations. Revised track vintages prevent true historical publication-time backtesting. Forecast begins 2025.

## India modeled annual PM2.5 exposure — `india_pm25_exposure_forecaster`

- **Status / use:** Experimental forecast of national population-weighted modeled annual exposure, World Bank `EN.ATM.PM25.MC.M3` / GBD2023, 1990–2023 (34 observations); unit µg/m³.
- **Evaluation:** Train 1990–2009, validation 2010–2016, test 2017–2023, expanding one-year past-only fits. Validation-selected ridge test MAE 2.5454 µg/m³, RMSE 2.6588, MASE 3.0521, WAPE 0.04714. Persistence baseline MAE 2.6477; small difference over only seven test years.
- **Limits:** Modeled national exposure, not local monitor readings or destination ecological pressure. Source vintage is revised/published in 2026, so historical backtest is retrospective. Forecast starts 2024; no current exposure or health advice.

## Unsupported requested predictors

India-wide multi-disaster warnings and destination-level ecological stress remain `DATA_INSUFFICIENT`. They are not registered predictive models. API controls report unavailable; historical indicators are separately labeled `INDICATOR_ONLY`.
