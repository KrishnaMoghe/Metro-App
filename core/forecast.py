"""ML rush-hour forecaster: Gradient Boosting on calendar + event features -> hourly footfall per station."""
import json
import os
from datetime import date

import joblib
import numpy as np
import pandas as pd

from .config import EVENT_TYPES, OPERATING_HOURS, STATIONS, VENUES
from .crowd import station_riders, to_min

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MODEL_PATH = os.path.join(ROOT, "model", "rush_model.joblib")
METRICS_PATH = os.path.join(ROOT, "model", "metrics.json")

STATION_CODES = list(STATIONS)
FEATURES = ["station_idx", "hour", "dow", "month", "is_weekend", "is_holiday", "event_type_idx",
            "event_riders", "min_to_start", "min_from_end", "in_event"]
HOLIDAYS = None


def _holidays():
    global HOLIDAYS
    if HOLIDAYS is None:
        from data.generate_data import HOLIDAYS as H  # noqa
        HOLIDAYS = {d.isoformat() for d in H}
    return HOLIDAYS


def feature_rows(day: str, station: str, events: list):
    """events: list of dicts with event_type, venue, start_time, end_time, expected_attendance."""
    d = date.fromisoformat(day)
    rows = []
    for h in OPERATING_HOURS:
        mid = h * 60 + 30
        best = dict(event_type_idx=0, event_riders=0.0, min_to_start=-999, min_from_end=-999, in_event=0)
        for e in events:
            riders = station_riders(e["event_type"], int(e["expected_attendance"]), e["venue"], station)
            if riders <= best["event_riders"]:
                continue
            s, en = to_min(e["start_time"]), to_min(e["end_time"])
            if en < s:
                en += 1440
            best = dict(event_type_idx=EVENT_TYPES.index(e["event_type"]), event_riders=riders,
                        min_to_start=float(np.clip(s - mid, -600, 600)), min_from_end=float(np.clip(mid - en, -600, 600)),
                        in_event=int(s <= mid <= en))
        rows.append(dict(station_idx=STATION_CODES.index(station), hour=h, dow=d.weekday(), month=d.month,
                         is_weekend=int(d.weekday() >= 5), is_holiday=int(day in _holidays()), **best))
    return pd.DataFrame(rows)


def build_training_frame():
    ride = pd.read_csv(os.path.join(DATA, "ridership_hourly.csv"))
    events = pd.read_csv(os.path.join(DATA, "events.csv"))
    ev_by_date = {d: g.to_dict("records") for d, g in events.groupby("date")}
    frames = []
    for (day, st), _ in ride.groupby(["date", "station"]):
        f = feature_rows(day, st, ev_by_date.get(day, []))
        f["date"], f["station"] = day, st
        frames.append(f)
    X = pd.concat(frames, ignore_index=True)
    return X.merge(ride, on=["date", "station", "hour"])


def train():
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.inspection import permutation_importance

    df = build_training_frame()
    cutoff = "2026-07-01"   # time-based split: train on the past, test on the most recent 3 months
    tr, te = df[df.date < cutoff], df[df.date >= cutoff]
    model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06, max_leaf_nodes=48,
                                          categorical_features=[0], random_state=0)
    model.fit(tr[FEATURES], tr.footfall)
    pred = model.predict(te[FEATURES])
    ev_mask = te.event_riders > 0
    # importance measured on normal hours + all event hours, so event features are represented
    imp_df = pd.concat([df.sample(4000, random_state=0), df[df.event_riders > 0]])
    imp = permutation_importance(model, imp_df[FEATURES], imp_df.footfall, n_repeats=3, random_state=0)
    metrics = {
        "model": "HistGradientBoostingRegressor (scikit-learn)",
        "train_rows": int(len(tr)), "test_rows": int(len(te)), "test_period": f"{cutoff} .. {df.date.max()}",
        "mae": round(float(mean_absolute_error(te.footfall, pred)), 1),
        "r2": round(float(r2_score(te.footfall, pred)), 4),
        "event_hours_mae": round(float(mean_absolute_error(te.footfall[ev_mask], pred[ev_mask.values])), 1) if ev_mask.any() else None,
        "feature_importance": dict(sorted({f: round(float(v), 4) for f, v in zip(FEATURES, imp.importances_mean)}.items(),
                                          key=lambda kv: -kv[1])),
    }
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    return metrics


_model = None


def get_model():
    global _model
    if _model is None and os.path.exists(MODEL_PATH):
        _model = joblib.load(MODEL_PATH)
    return _model


def rush_level(value, capacity):
    r = value / capacity
    return "critical" if r >= 0.8 else "high" if r >= 0.5 else "moderate" if r >= 0.3 else "low"


def predict_day(day: str, station: str, events: list):
    """Return hourly forecast with and without the event(s) for one station."""
    model = get_model()
    cap = STATIONS[station]["hourly_capacity"]
    X = feature_rows(day, station, events)
    Xb = feature_rows(day, station, [])
    if model is not None:
        yhat, ybase = model.predict(X[FEATURES]), model.predict(Xb[FEATURES])
        source = "ml"
    else:  # heuristic fallback so the UI still works without a trained model
        from data.generate_data import hourly_profile
        from .crowd import hourly_event_load
        wk = date.fromisoformat(day).weekday() >= 5
        ybase = np.array([STATIONS[station]["base"] * hourly_profile(h, wk) for h in OPERATING_HOURS])
        extra = {}
        for e in events:
            for h, v in hourly_event_load(e["event_type"], int(e["expected_attendance"]), e["venue"], station,
                                          e["start_time"], e["end_time"]).items():
                extra[h] = extra.get(h, 0) + v
        yhat = ybase + np.array([extra.get(h, 0) for h in OPERATING_HOURS])
        source = "heuristic"
    hours = []
    for h, y, b in zip(OPERATING_HOURS, yhat, ybase):
        b = max(0, float(b))
        y = max(b, float(y))  # an event never reduces footfall below a normal day
        hours.append(dict(hour=h, label=f"{h % 24:02d}:00", predicted=round(y), baseline=round(b),
                          level=rush_level(y, cap), load_pct=round(100 * y / cap, 1)))
    rush = [x["label"] for x in hours if x["level"] in ("high", "critical")]
    return dict(station=station, station_name=STATIONS[station]["name"], date=day, capacity=cap,
                source=source, hours=hours, rush_hours=rush,
                peak=max(hours, key=lambda x: x["predicted"]))


def stations_for_venue(venue):
    return list(VENUES[venue]["stations"])
