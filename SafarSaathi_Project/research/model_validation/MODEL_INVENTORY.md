# Six persisted pipelines are experimental within narrowly defined targets

This inventory was rebuilt from the current registry, trusted artifacts, source code and local source files on 2026-10-30. Versions below are recorded values; the NLP registry ID includes a timestamp but has no separately recorded model_version. No active artifact, registry entry or source file was changed.

| Actual model ID | Recorded version | Exact artifact | Current SHA-256 |
|---|---|---|---|
| nlp-20261024T182952Z | Not separately recorded | `models/nlp/nlp-20261024T182952Z/pipeline.joblib` | `e52b83b7e1ab82a4c36559285f287bd7f98203a74931cee2689c7be70c536150` |
| tourism_demand_forecaster | 20261025T111230951433Z | `models/tourism_demand/20261025T111230951433Z/pipeline.joblib` | `3b2f5aaab559fda07638f088e689bbd55d206f29995d9d6e52f40f6fb8cd7e7c` |
| tourism_monthly_fta_forecaster | 20261025T120954676478Z | `models/tourism_monthly_fta/20261025T120954676478Z/pipeline.joblib` | `81d3fa1b452e0f0640a037ed5616c4ad572d9b8fed4716a87f8b7e17a2b390f3` |
| flood_segmentation_model | 20261025T125258870059Z | `models/flood_segmentation/20261025T125258870059Z/pipeline.joblib` | `d791b2416f0459fbade39bdc20179573530058d2074f8bb9efe41c7b998decb4` |
| north_indian_cyclone_count_forecaster | 20261025T132148112617Z | `models/cyclone_count/20261025T132148112617Z/pipeline.joblib` | `7d4a8b81ebc5e901300a12fc0cbbae29a3f88689c8e87f951c04e6c42981d3bb` |
| india_pm25_exposure_forecaster | 20261025T132148214483Z | `models/pm25/20261025T132148214483Z/pipeline.joblib` | `012204a357ae9ade97269aaf952f0ca2cac26ff3178c2702495246ab48883366` |

## Actual algorithms, features and targets

| Pipeline | Algorithm actually selected | Input / preprocessing / target |
|---|---|---|
| Review source labels | sklearn TF-IDF + LogisticRegression(max_iter=1000, random_state=20261024) | Text: train-fitted 1–2 word n-grams, min_df=2, maximum 30,000 vocabulary. Output is source-defined POSITIVE/NEGATIVE; no neutral or validated local/multilingual label. |
| Annual international arrivals | AnnualForecaster(method=drift) | Previous annual value plus fitted mean first difference, recursive nonnegative counts. Schema lists lag_1, lag_2, lag_3, past_3_mean, lag_1_minus_lag_2 used by Ridge candidate; the selected drift does not consume all five as fitted regression features. Target: India national World Bank ST.INT.ARVL arrivals/year. |
| Monthly foreign tourist arrivals | MonthlyForecaster(method=persistence) | Last observed monthly FTA carried forward. Candidate Ridge feature order: lag1, lag2, lag12, past3mean, calendar_sin, calendar_cos with train-prefix StandardScaler. Selected persistence only uses the latest observation. Target: Ministry FTA excluding nonresident Indian arrivals/month. |
| Reference-positive water/flood pixels | HistGradientBoostingClassifier, max_iter=80, max_leaf_nodes=15, l2_regularization=1, class_weight=balanced; selected threshold 0.3 | Delivered STURM finite 128x128x2 float32 input, range [-10,10]. Seven per-pixel features: two bands, two 3x3 local means, two 3x3 local standard deviations, band1-band2. Source mask >0 is positive, which may include permanent water. No arbitrary raw-SAR preprocessing is accepted. |
| NI archived cyclone IDs | CountForecaster(method=seasonal_mean) | Calendar month indexes one of twelve means fit on past eligible NI-basin MAIN/TS SID counts. Fourier sin/cos harmonics belong to the Poisson candidate, not the selected seasonal-mean estimator. Target is monthly archive IDs including depressions, not landfall or impact. |
| India modeled PM2.5 exposure | AnnualForecaster(method=ridge): StandardScaler + Ridge(alpha=10) | Past-only feature order: lag1, lag2, lag3, past3mean, lag1-lag2. Each evaluation origin fits preprocessing/regressor on prior values. Target is national population-weighted modeled annual exposure in micrograms/m3, not sensor/destination stress. |

## Sources and partitions

| Pipeline | Training data and original evaluation separation |
|---|---|
| NLP | `../SafarSaathi_Datasets/raw/reviews/Aditya1010__17k-hotel-reviews-dataset__balanced_dataset.csv`; 17,840 raw rows, 12,532 usable unique text-label pairs. Undated source-domain corpus. Stratified 80/20 split, seed 20261024: 10,025 train / 2,507 test. No separate validation/calibration partition. |
| Annual | `../SafarSaathi_Datasets/raw/worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json`; 25 observed years 1995–2019. Initial train 1995–2009, validation 2010–2014, test 2015–2019. Validation chooses drift, heldout evaluation drift freezes fitting through 2014; final inference refits through 2019. |
| Monthly | `data/processed/tourism_monthly_fta/20261025/monthly_fta.csv` and provenance.json; 72 months. Initial 2019–2021 train, 2022 validation, 2023–2024 test. Expanding past-only prefix at each origin; validation mean MAE at horizons 1/3/6 selects persistence. |
| Flood | `data/external/sturm_flood/12748983/Dataset.zip`, DOI 10.5281/zenodo.12748983. Only eligible source/reference dates within 24 hours. Train 66 tiles/8 countries, validation 12 tiles/2 countries, test 42 tiles/4 countries. Up to six tiles/event, 512 training pixels/tile, seed 20261025. Countries/events are disjoint. |
| Cyclone | `data/processed/india_scope_20261025/cyclone_monthly.csv`, cyclone_events.csv, model_data_provenance.json; 540 months 1980–2024. Train 1980–2009, validation 2010–2014, fixed test 2015–2024. Validation Poisson deviance selects seasonal mean. The original 120-month test is fixed-origin aggregate, not 120 operational one-step refits. New rolling-origin horizon diagnostics are labeled separately. |
| PM2.5 | `data/processed/india_scope_20261025/pm25_annual.csv`; 34 years 1990–2023. Train 1990–2009, validation 2010–2016, test 2017–2023. Expanding one-year prefix, validation MAE chooses Ridge; inference refits all observed values. |

## Interfaces and reproducibility

Existing API boundaries remain: POST /reviews/classify, /tourism/forecast, /tourism/monthly-forecast, /flood/segment, /disaster/cyclone-count, /environment/pm25-forecast. Exact input constraints are in integration_docs/API_CONTRACT.md. Loading integrity is distinct from prediction validity and historical evaluation. No geographic local hazard/stress model is hidden behind these six identifiers.

Run from project root with PYTHONPATH=src, OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1: `python scripts/phase3_model_validation.py`. The script writes only research/model_validation; it recreates known partitions, reads bounded selected ZIP members and independently computes sklearn metrics. It does not fetch data, train/register replacement models or fit a calibrator on test outcomes. MODEL_INVENTORY.json preserves exact schema, provenance, hashes and split metadata; evaluation_results.json records actual execution environment.
