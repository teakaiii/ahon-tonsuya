"""Leakage-aware water-level regression forecasting on validated sensor data."""

import calendar
from collections import defaultdict
from datetime import date, timedelta

import numpy as np
import pandas as pd
from django.utils import timezone
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


def forecast_month_profile(readings, year, month):
    """Forecast a future month using rolling-origin metrics at exact day horizons."""
    rows = list(readings)
    raw_count = len(rows)
    day_count = calendar.monthrange(year, month)[1]
    daily_values = defaultdict(list)
    valid_count = 0
    today = timezone.localdate()
    forecast_start = date(year, month, 1)

    def unavailable(reason, history_days=0, horizon_metrics=None):
        month_metrics = (horizon_metrics or {}).get(str(day_count), {})
        validation_samples = month_metrics.get("sample_count", 0)
        return {
            "available": False,
            "reason": reason,
            "year": year,
            "month": month,
            "month_label": calendar.month_name[month],
            "raw_readings": raw_count,
            "valid_readings": valid_count,
            "history_days": history_days,
            "validation_days": validation_samples,
            "backtest_folds": validation_samples,
            "forecast_horizon_days": day_count,
            "minimum_validation_origins": 5,
            "horizon_metrics": horizon_metrics or {},
            "points": [],
            "unit": "cm",
            "safety_note": "Exploratory forecast only; verify field conditions before operational decisions.",
        }

    if forecast_start <= today:
        return unavailable("Select a future month to generate a forecast.")

    for timestamp, raw_level in rows:
        try:
            level = float(raw_level)
        except (TypeError, ValueError):
            continue
        if timestamp is None or not 0 <= level <= MAX_SENSOR_CM:
            continue

        local_timestamp = timezone.localtime(timestamp) if timezone.is_aware(timestamp) else timestamp
        if local_timestamp.date() >= forecast_start:
            continue

        daily_values[local_timestamp.date()].append(level)
        valid_count += 1

    daily_history = sorted(
        (day, sum(values) / len(values))
        for day, values in daily_values.items()
    )
    history_days = len(daily_history)
    minimum_training_days = 7
    minimum_validation_origins = 5
    horizons = sorted({1, 3, 7, 14, 30, day_count})
    if history_days < minimum_training_days:
        return unavailable(
            f"Need at least {minimum_training_days} valid daily readings to begin backtesting; "
            f"only {history_days} days are available.",
            history_days,
        )

    first_day = daily_history[0][0]
    day_indexes = np.array([(day - first_day).days for day, _ in daily_history], dtype=float)
    levels = np.array([level for _, level in daily_history], dtype=float)
    day_positions = {day: index for index, (day, _) in enumerate(daily_history)}
    samples_by_horizon = {
        horizon: {"actual": [], "trend": [], "persistence": [], "target_days": []}
        for horizon in horizons
    }

    for origin_index in range(minimum_training_days - 1, history_days, 7):
        origin_day = daily_history[origin_index][0]
        training_indexes = day_indexes[:origin_index + 1]
        training_levels = levels[:origin_index + 1]
        slope, intercept = np.polyfit(training_indexes, training_levels, 1)
        persistence_prediction = float(np.mean(training_levels[-7:]))

        for horizon in horizons:
            target_day = origin_day + timedelta(days=horizon)
            target_index = day_positions.get(target_day)
            if target_index is None:
                continue

            samples = samples_by_horizon[horizon]
            samples["actual"].append(float(levels[target_index]))
            target_day_index = (target_day - first_day).days
            samples["trend"].append(float(np.clip(
                slope * target_day_index + intercept, 0, MAX_SENSOR_CM
            )))
            samples["persistence"].append(persistence_prediction)
            samples["target_days"].append(target_day)

    horizon_metrics = {}
    for horizon, samples in samples_by_horizon.items():
        sample_count = len(samples["actual"])
        if sample_count:
            trend_mae = float(mean_absolute_error(samples["actual"], samples["trend"]))
            trend_rmse = float(np.sqrt(mean_squared_error(samples["actual"], samples["trend"])))
            persistence_mae = float(mean_absolute_error(
                samples["actual"], samples["persistence"]
            ))
            persistence_rmse = float(np.sqrt(mean_squared_error(
                samples["actual"], samples["persistence"]
            )))
            selected_method = (
                "linear_trend" if trend_mae <= persistence_mae
                else "recent_7_day_average"
            )
            validation_start = samples["target_days"][0].isoformat()
            validation_end = samples["target_days"][-1].isoformat()
        else:
            trend_mae = trend_rmse = persistence_mae = persistence_rmse = None
            selected_method = None
            validation_start = validation_end = None

        horizon_metrics[str(horizon)] = {
            "horizon_days": horizon,
            "sample_count": sample_count,
            "trend_mae_cm": None if trend_mae is None else round(trend_mae, 3),
            "trend_rmse_cm": None if trend_rmse is None else round(trend_rmse, 3),
            "persistence_mae_cm": None if persistence_mae is None else round(persistence_mae, 3),
            "persistence_rmse_cm": None if persistence_rmse is None else round(persistence_rmse, 3),
            "selected_method": selected_method,
            "validation_start": validation_start,
            "validation_end": validation_end,
        }

    month_horizon = horizon_metrics[str(day_count)]
    month_samples = samples_by_horizon[day_count]
    if month_horizon["sample_count"] < minimum_validation_origins:
        return unavailable(
            f"Need at least {minimum_validation_origins} historical {day_count}-day "
            f"forecast examples; only {month_horizon['sample_count']} are available.",
            history_days,
            horizon_metrics,
        )

    trend_mae = float(mean_absolute_error(month_samples["actual"], month_samples["trend"]))
    persistence_mae = float(mean_absolute_error(
        month_samples["actual"], month_samples["persistence"]
    ))
    trend_selected = trend_mae <= persistence_mae
    selected_method = "linear_trend" if trend_selected else "recent_7_day_average"
    selected_mae = trend_mae if trend_selected else persistence_mae
    selected_rmse = float(np.sqrt(mean_squared_error(
        month_samples["actual"],
        month_samples["trend"] if trend_selected else month_samples["persistence"],
    )))

    final_slope, final_intercept = np.polyfit(day_indexes, levels, 1)
    recent_average = float(np.mean(levels[-7:]))
    last_history_day = daily_history[-1][0]
    points = []
    for day_number in range(1, day_count + 1):
        forecast_day = date(year, month, day_number)
        day_index = (forecast_day - first_day).days
        forecast_level = (
            final_slope * day_index + final_intercept
            if trend_selected else recent_average
        )
        points.append({
            "day": day_number,
            "forecast_cm": round(float(np.clip(forecast_level, 0, MAX_SENSOR_CM)), 3),
        })

    return {
        "available": True,
        "reason": None,
        "year": year,
        "month": month,
        "month_label": calendar.month_name[month],
        "method": selected_method,
        "raw_readings": raw_count,
        "valid_readings": valid_count,
        "history_days": history_days,
        "training_days": history_days,
        "validation_days": month_horizon["sample_count"],
        "backtest_folds": month_horizon["sample_count"],
        "forecast_horizon_days": day_count,
        "minimum_validation_origins": minimum_validation_origins,
        "horizon_metrics": horizon_metrics,
        "validation_start": month_horizon["validation_start"],
        "validation_end": month_horizon["validation_end"],
        "validation_mae_cm": round(selected_mae, 3),
        "validation_rmse_cm": round(selected_rmse, 3),
        "trend_mae_cm": round(trend_mae, 3),
        "persistence_mae_cm": round(persistence_mae, 3),
        "training_start": daily_history[0][0].isoformat(),
        "training_end": last_history_day.isoformat(),
        "unit": "cm",
        "points": points,
        "safety_note": "Exploratory projection; backtest accuracy is not a guarantee of future conditions or an evacuation decision.",
    }
