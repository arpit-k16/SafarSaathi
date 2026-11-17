# Data validation and partition audit

Executed with `scripts/phase3_model_validation.py`; detailed source hashes, periods, labels and partitions are retained below. No raw data were changed. Missing trailing annual targets are excluded, never filled with invented values. These checks do not establish every possible semantic label error or external ground truth.

## nlp-20261024T182952Z

```json
{
  "data": {
    "source": "SafarSaathi_Datasets/raw/reviews/Aditya1010__17k-hotel-reviews-dataset__balanced_dataset.csv",
    "sha256": "3c11a24a5263ed25fe837da36092c393615abbccfe1509329c1fa1d525981511",
    "source_hash_matches_registered": true,
    "source_rows": 17840,
    "missing_text_or_label": 0,
    "exact_duplicate_pairs_removed": 5308,
    "post_strip_duplicate_pairs": 0,
    "conflicting_label_text_groups": 0,
    "exact_train_test_text_overlap": 0,
    "normalized_train_test_text_overlap": 0,
    "class_counts": {
      "source": {
        "NEGATIVE": 6573,
        "POSITIVE": 5959
      },
      "train": {
        "NEGATIVE": 5258,
        "POSITIVE": 4767
      },
      "test": {
        "NEGATIVE": 1315,
        "POSITIVE": 1192
      }
    },
    "train_rows": 10025,
    "test_rows": 2507,
    "tfidf_train_only_vocabulary_reproduced": true,
    "tfidf_train_only_idf_reproduced": true,
    "heldout_zero_vocabulary_vector_rows": 0,
    "controlled_unsupported_probe_zero_vectors": 2,
    "controlled_unsupported_probe_count": 3,
    "entity_temporal_split": "Hotel/reviewer identity and temporal group labels not available; no entity or future-domain generalization established."
  }
}
```

## tourism_demand_forecaster

```json
{
  "source_profile": {
    "path": "worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json",
    "format": "World Bank JSON",
    "sha256": "6cd0c77c9560fcbf4c1514d89c53dcc0e9d077904d6156f38a87730ee95ac579",
    "rows": 31,
    "observed_rows": 25,
    "duplicate_keys": 0,
    "columns": {
      "destination": "ISO3 string",
      "year": "int",
      "arrivals": "float/count"
    },
    "missing_rates": {
      "destination": 0.0,
      "year": 0.0,
      "arrivals": 0.1935483870967742
    },
    "missing_target_years": [
      2025,
      2024,
      2023,
      2022,
      2021,
      2020
    ],
    "observed_years": [
      1995,
      2019
    ],
    "geography": "India national total; not Uttarakhand or individual destinations",
    "units": "international tourist arrivals per calendar year; annual dates have no time zone",
    "imputation": "none; trailing null targets excluded, internal gaps rejected",
    "source_updated": "2026-07-13"
  },
  "data": {
    "rows": 25,
    "columns": [
      "destination",
      "year",
      "arrivals"
    ],
    "dtypes": {
      "destination": "object",
      "year": "int64",
      "arrivals": "float64"
    },
    "missing": {
      "destination": 0,
      "year": 0,
      "arrivals": 0
    },
    "duplicate_rows": 0,
    "duplicate_keys": 0,
    "invalid_or_nonfinite_targets": 0,
    "negative_targets": 0,
    "first_key": "1995",
    "last_key": "2019"
  }
}
```

## tourism_monthly_fta_forecaster

```json
{
  "data": {
    "rows": 72,
    "columns": [
      "destination",
      "date",
      "arrivals"
    ],
    "dtypes": {
      "destination": "object",
      "date": "object",
      "arrivals": "int64"
    },
    "missing": {
      "destination": 0,
      "date": 0,
      "arrivals": 0
    },
    "duplicate_rows": 0,
    "duplicate_keys": 0,
    "invalid_or_nonfinite_targets": 0,
    "negative_targets": 0,
    "first_key": "2019-01",
    "last_key": "2024-12"
  }
}
```

## north_indian_cyclone_count_forecaster

```json
{
  "data": {
    "rows": 540,
    "columns": [
      "date",
      "value"
    ],
    "dtypes": {
      "date": "object",
      "value": "int64"
    },
    "missing": {
      "date": 0,
      "value": 0
    },
    "duplicate_rows": 0,
    "duplicate_keys": 0,
    "invalid_or_nonfinite_targets": 0,
    "negative_targets": 0,
    "first_key": "1980-01",
    "last_key": "2024-12",
    "event_ids_disjoint_across_splits": true,
    "zero_target_months": 304,
    "event_rows": 388,
    "unique_events": 388
  }
}
```

## india_pm25_exposure_forecaster

```json
{
  "data": {
    "rows": 34,
    "columns": [
      "date",
      "value"
    ],
    "dtypes": {
      "date": "object",
      "value": "float64"
    },
    "missing": {
      "date": 0,
      "value": 0
    },
    "duplicate_rows": 0,
    "duplicate_keys": 0,
    "invalid_or_nonfinite_targets": 0,
    "negative_targets": 0,
    "first_key": "1990",
    "last_key": "2023"
  }
}
```

## flood_segmentation_model

```json
{
  "metadata_inventory": {
    "total_s1_tiles": 21602,
    "eligible_within_24_hours": 3575,
    "excluded_time_mismatch": 18027
  },
  "split_country_groups": {
    "train": [
      "France",
      "Greece",
      "Slovakia",
      "Ukraine",
      "Iran, Islamic Republic of",
      "Netherlands",
      "Croatia",
      "Iraq"
    ],
    "validation": [
      "Timor-Leste",
      "Pakistan"
    ],
    "test": [
      "Italy",
      "Ireland",
      "Spain",
      "Mexico"
    ]
  },
  "saved_splits_reproduced": true,
  "threshold": 0.3
}
```

NLP TF-IDF vocabulary/IDF were independently fitted on the recovered training split and matched the saved transform. Exact and normalized text overlap are checked; unavailable hotel/reviewer/time identifiers prevent group leakage certification. Flood country/event holdouts are checked from delivered metadata. No pixel-independent confidence interval is claimed. The annual final inference artifact is refit on the full observed history; historical metrics are replayed with the original frozen split rather than evaluating that refit on its training years. Baselines and horizon diagnostics are exploratory comparisons on already known test periods.
