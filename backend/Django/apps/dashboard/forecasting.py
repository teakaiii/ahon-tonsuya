"""Leakage-aware water-level regression forecasting on validated sensor data."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

MAX_SENSOR_CM = 4.0
WARNING_CM = 2.0
DANGER_CM = 3.0
RESAMPLE_SECONDS = 30
FORECAST_MINUTES = 5
MIN_SUPERVISED_ROWS = 80
FEATURE_COLUMNS = [
    "level_now",
    "lag_1",
    "lag_2",
    "lag_4",
    "lag_10",
    "lag_20",
    "mean_5",
    "mean_10",
]


def _status_for_level(level):
    if level >= DANGER_CM:
        return "Danger"
    if level >= WARNING_CM:
        return "Warning"
    return "Normal"


def _metrics(actual, predicted):
    return {
        "mae_cm": round(float(mean_absolute_error(actual, predicted)), 4),
        "rmse_cm": round(float(np.sqrt(mean_squared_error(actual, predicted))), 4),
        "r_squared": round(float(r2_score(actual, predicted)), 4),
    }


def _unavailable(reason, raw_count, valid_count=0, resampled_count=0, supervised_count=0):
    return {
        "available": False,
        "reason": reason,
        "raw_readings": raw_count,
        "valid_readings": valid_count,
        "excluded_readings": raw_count - valid_count,
        "resampled_readings": resampled_count,
        "supervised_rows": supervised_count,
        "horizon_minutes": FORECAST_MINUTES,
        "unit": "cm",
    }


def forecast_water_level(readings):
    """Train/evaluate on valid 0-4 cm readings; prefer persistence if it scores better.

    `readings` is an iterable of (timestamp, water_level_cm) pairs, ordered or not.
    The final output never treats this exploratory model as an emergency decision.
    """
    rows = list(readings)
    raw_count = len(rows)
    if not rows:
        return _unavailable("No historical readings are available.", raw_count)

    frame = pd.DataFrame(rows, columns=["timestamp", "water_level_cm"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    frame["water_level_cm"] = pd.to_numeric(frame["water_level_cm"], errors="coerce")
    valid_mask = (
        frame["timestamp"].notna()
        & frame["water_level_cm"].between(0, MAX_SENSOR_CM, inclusive="both")
    )
    valid = frame.loc[valid_mask].drop_duplicates("timestamp", keep="last")
    valid = valid.sort_values("timestamp")
    valid_count = len(valid)
    if valid_count == 0:
        return _unavailable(
            "No readings fall within the calibrated 0-4 cm sensor range.", raw_count
        )

    series = (
        valid.set_index("timestamp")["water_level_cm"]
        .resample(f"{RESAMPLE_SECONDS}s")
        .median()
        .dropna()
        .sort_index()
    )
    resampled_count = len(series)
    gap_limit = pd.Timedelta(seconds=RESAMPLE_SECONDS * 1.5)
    segment_ids = series.index.to_series().diff().gt(gap_limit).cumsum()
    feature_frames = []

    for _, segment in series.groupby(segment_ids):
        part = pd.DataFrame(index=segment.index)
        part["level_now"] = segment
        for lag in (1, 2, 4, 10, 20):
            part[f"lag_{lag}"] = segment.shift(lag)
        part["mean_5"] = segment.rolling(5, min_periods=5).mean()
        part["mean_10"] = segment.rolling(10, min_periods=10).mean()
        part["target_cm"] = segment.shift(-FORECAST_MINUTES * 60 // RESAMPLE_SECONDS)
        part["target_time"] = pd.Series(segment.index, index=segment.index).shift(
            -FORECAST_MINUTES * 60 // RESAMPLE_SECONDS
        )
        feature_frames.append(part.dropna())

    if not feature_frames:
        return _unavailable(
            "Not enough continuous readings to build lag features.",
            raw_count,
            valid_count,
            resampled_count,
        )

    supervised = pd.concat(feature_frames).sort_index()
    supervised_count = len(supervised)
    if supervised_count < MIN_SUPERVISED_ROWS:
        return _unavailable(
            f"Need at least {MIN_SUPERVISED_ROWS} continuous forecast rows; "
            f"only {supervised_count} are available.",
            raw_count,
            valid_count,
            resampled_count,
            supervised_count,
        )

    split_position = int(supervised_count * 0.8)
    split_time = supervised["target_time"].iloc[split_position]
    train = supervised[supervised["target_time"] < split_time]
    test = supervised[supervised["target_time"] >= split_time]
    if len(train) < 20 or len(test) < 10:
        return _unavailable(
            "Not enough rows remain for a reliable chronological train/test split.",
            raw_count,
            valid_count,
            resampled_count,
            supervised_count,
        )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[FEATURE_COLUMNS], train["target_cm"])
    model_test_predictions = model.predict(test[FEATURE_COLUMNS])
    baseline_test_predictions = test["level_now"].to_numpy()
    model_metrics = _metrics(test["target_cm"], model_test_predictions)
    baseline_metrics = _metrics(test["target_cm"], baseline_test_predictions)
    model_wins = model_metrics["mae_cm"] < baseline_metrics["mae_cm"]

    latest_segment_id = segment_ids.iloc[-1]
    latest_segment = series[segment_ids == latest_segment_id]
    if len(latest_segment) < 21:
        return _unavailable(
            "The latest continuous segment is too short for the forecast lag window.",
            raw_count,
            valid_count,
            resampled_count,
            supervised_count,
        )

    latest_features = {"level_now": float(latest_segment.iloc[-1])}
    for lag in (1, 2, 4, 10, 20):
        latest_features[f"lag_{lag}"] = float(latest_segment.iloc[-lag - 1])
    latest_features["mean_5"] = float(latest_segment.iloc[-5:].mean())
    latest_features["mean_10"] = float(latest_segment.iloc[-10:].mean())

    final_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    final_model.fit(supervised[FEATURE_COLUMNS], supervised["target_cm"])
    model_forecast = float(
        final_model.predict(pd.DataFrame([latest_features], columns=FEATURE_COLUMNS))[0]
    )
    baseline_forecast = float(latest_segment.iloc[-1])
    selected_forecast = model_forecast if model_wins else baseline_forecast
    target_time = latest_segment.index[-1] + pd.Timedelta(minutes=FORECAST_MINUTES)

    return {
        "available": True,
        "reason": None if model_wins else "Persistence baseline has lower holdout MAE; it is used as the displayed estimate.",
        "model_name": "Random Forest Regressor",
        "model_forecast_cm": round(float(np.clip(model_forecast, 0, MAX_SENSOR_CM)), 3),
        "baseline_forecast_cm": round(baseline_forecast, 3),
        "selected_forecast_cm": round(selected_forecast, 3),
        "selected_status": _status_for_level(selected_forecast),
        "selected_method": "random_forest" if model_wins else "persistence_baseline",
        "model_better_than_baseline": model_wins,
        "model_metrics": model_metrics,
        "baseline_metrics": baseline_metrics,
        "train_rows": len(train),
        "test_rows": len(test),
        "raw_readings": raw_count,
        "valid_readings": valid_count,
        "excluded_readings": raw_count - valid_count,
        "resampled_readings": resampled_count,
        "supervised_rows": supervised_count,
        "horizon_minutes": FORECAST_MINUTES,
        "latest_reading_cm": round(float(latest_segment.iloc[-1]), 3),
        "latest_timestamp": latest_segment.index[-1].isoformat(),
        "forecast_timestamp": target_time.isoformat(),
        "unit": "cm",
        "safety_note": "Exploratory forecast only; never use as the sole basis for warnings or evacuation.",
    }
