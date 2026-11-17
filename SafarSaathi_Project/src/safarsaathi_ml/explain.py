"""Explanations for the saved forecasting models (project report §10.5).

The forecasters are ridge regressions on standardised features or simple rules, so
explanations are exact, not approximations: for a linear model the contribution of a
feature is coefficient × standardised value, and the contributions plus the intercept
add up to the prediction.
"""
from __future__ import annotations

import numpy as np

ANNUAL_NAMES = {"lag_1": "Last year's arrivals", "lag_2": "Arrivals two years ago", "lag_3": "Arrivals three years ago",
                "past_3_mean": "Mean of the last three years", "lag_1_minus_lag_2": "Most recent year-on-year change"}
MONTHLY_NAMES = {"lag1": "Last month's arrivals", "lag2": "Arrivals two months ago", "lag12": "Same month last year",
                 "past3mean": "Mean of the last three months", "calendar_sin": "Time of year (sine term)",
                 "calendar_cos": "Time of year (cosine term)"}
RULES = {"persistence": "The forecast repeats the last observed value.",
         "naive": "The forecast repeats the last observed value.",
         "drift": "The forecast extends the average historical change from the last value.",
         "historical_mean": "The forecast is the mean of the training series.",
         "seasonal_naive": "The forecast repeats the value from the same month a year earlier."}


def explain(model, feature_vector, names: dict, prediction: float, test_metrics: dict | None, freshness: str) -> dict:
    out = {"method": model.method, "freshness": freshness}
    if model.method == "ridge" and model.estimator is not None:
        scaler, ridge = model.estimator.steps[0][1], model.estimator.steps[-1][1]
        z = (np.asarray(feature_vector, dtype=float) - scaler.mean_) / scaler.scale_
        parts = ridge.coef_ * z
        items = [{"feature": k, "label": v, "value": float(x), "contribution": float(c)}
                 for (k, v), x, c in zip(names.items(), feature_vector, parts)]
        items.sort(key=lambda r: -abs(r["contribution"]))
        out.update({"kind": "linear_contributions", "baseline": float(ridge.intercept_),
                    "baseline_label": "Average arrivals in the training data (model intercept)",
                    "contributions": items,
                    "check": {"baseline_plus_contributions": float(ridge.intercept_ + parts.sum()), "prediction": float(prediction)}})
    else:
        out.update({"kind": "rule", "rule": RULES.get(model.method, model.method)})
    if test_metrics:
        mae = test_metrics.get("MAE")
        out["uncertainty"] = {"held_out_MAE": mae, "WAPE": test_metrics.get("WAPE"), "n": test_metrics.get("n"),
                              "note": "Typical error on held-out periods. The models have no calibrated prediction intervals."}
    return out
