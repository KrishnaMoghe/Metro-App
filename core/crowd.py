"""Crowd-flow curves shared by the data generator, the ML features and the planner."""
import numpy as np

from .config import METRO_SHARE, VENUES


def to_min(hhmm: str) -> int:
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def to_hhmm(minute: int) -> str:
    minute = int(minute) % (24 * 60)
    return f"{minute // 60:02d}:{minute % 60:02d}"


def station_riders(event_type: str, attendance: int, venue: str, station: str) -> float:
    share = VENUES[venue]["stations"].get(station, 0.0)
    return attendance * METRO_SHARE[event_type] * share


def egress_curve(minutes_after_end: np.ndarray, event_type: str) -> np.ndarray:
    """Relative arrival intensity at the station after the event ends.
    ~10% leave early (last 30 min), main wave peaks ~20 min after end, long tail to ~2 h."""
    t = minutes_after_end.astype(float)
    early = np.where((t >= -30) & (t < 0), 0.10 / 30, 0.0)
    k, theta = (3.0, 10.0) if event_type != "navratri" else (2.5, 16.0)
    tp = np.clip(t, 0, None)
    gamma = np.where(t >= 0, tp ** (k - 1) * np.exp(-tp / theta), 0.0)
    gamma = gamma / (gamma.sum() + 1e-9) * 0.90
    return early + gamma


def ingress_curve(minutes_before_start: np.ndarray) -> np.ndarray:
    """Relative arrival intensity (people alighting) before the event starts: bell around T-60 min."""
    t = minutes_before_start.astype(float)
    w = np.exp(-0.5 * ((t - 60) / 40) ** 2)
    w[(t < -30) | (t > 180)] = 0
    return w / w.sum()


def hourly_event_load(event_type, attendance, venue, station, start, end):
    """Extra passengers per clock hour at a station caused by the event (entries + exits)."""
    riders = station_riders(event_type, attendance, venue, station)
    if riders <= 0:
        return {}
    s, e = to_min(start), to_min(end)
    if e < s:
        e += 24 * 60
    minutes = np.arange(s - 240, e + 180)
    inflow = riders * ingress_curve(s - minutes)
    outflow = riders * egress_curve(minutes - e, event_type)
    total = inflow + outflow
    load = {}
    for m, v in zip(minutes, total):
        h = int(m // 60)
        load[h] = load.get(h, 0.0) + v
    return load
