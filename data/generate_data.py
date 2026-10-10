"""Generate synthetic (but realistic-shaped) Ahmedabad Metro ridership + event calendar.

Outputs (in data/):
  stations.csv          station master
  events.csv            past + scheduled events (cricket, concerts, Navratri, riverfront)
  ridership_hourly.csv  hourly footfall per station, Oct-2024 .. Oct-2026
"""
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import STATIONS, VENUES, OPERATING_HOURS  # noqa: E402
from core.crowd import hourly_event_load  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(42)

START, END = date(2024, 10, 1), date(2026, 10, 9)   # history up to "yesterday"
HOLIDAYS = {date(2024, 10, 12), date(2024, 10, 31), date(2024, 11, 1), date(2025, 1, 14), date(2025, 1, 26),
            date(2025, 3, 14), date(2025, 8, 15), date(2025, 10, 2), date(2025, 10, 20), date(2025, 10, 21),
            date(2026, 1, 14), date(2026, 1, 26), date(2026, 3, 4), date(2026, 8, 15), date(2026, 10, 2),
            date(2026, 11, 8), date(2026, 11, 9)}


def build_events():
    ev = []

    def add(name, etype, venue, d, start, end, att, status=None):
        ev.append(dict(name=name, event_type=etype, venue=venue, date=d.isoformat(), start_time=start,
                       end_time=end, expected_attendance=int(att),
                       status=status or ("completed" if d <= END else "scheduled")))

    # Navratri at GMDC ground (9 nights each year); crowd grows towards the last nights + weekends
    for first in [date(2024, 10, 3), date(2025, 9, 22), date(2026, 10, 11)]:
        for i in range(9):
            d = first + timedelta(days=i)
            att = 22000 + i * 2500 + (8000 if d.weekday() >= 5 else 0) + rng.integers(-2000, 2000)
            add(f"Navratri Garba - Night {i + 1}", "navratri", "GMDC", d, "21:00", "23:59", att)

    # IPL home games at Narendra Modi Stadium (Gujarat Titans)
    for year in [2025, 2026]:
        d0 = date(year, 3, 28)
        for k in range(7):
            d = d0 + timedelta(days=int(k * 8 + rng.integers(0, 3)))
            if k % 3 == 2:
                add(f"IPL {year} - Home Match {k + 1}", "cricket", "NMS", d, "15:30", "19:15", 85000 + rng.integers(-8000, 8000))
            else:
                add(f"IPL {year} - Home Match {k + 1}", "cricket", "NMS", d, "19:30", "23:15", 95000 + rng.integers(-8000, 10000))
        add(f"IPL {year} Final", "cricket", "NMS", date(year, 6, 1), "19:30", "23:30", 115000)

    # International cricket
    add("India vs England ODI", "cricket", "NMS", date(2025, 2, 12), "13:30", "21:30", 90000)
    add("India vs Australia T20", "cricket", "NMS", date(2025, 11, 23), "19:00", "22:30", 100000)
    add("India vs South Africa ODI", "cricket", "NMS", date(2026, 11, 22), "13:30", "21:30", 95000)
    add("India vs New Zealand T20", "cricket", "NMS", date(2026, 12, 13), "19:00", "22:30", 105000)

    # Concerts at the stadium
    add("Coldplay - Music of the Spheres (Day 1)", "concert", "NMS", date(2025, 1, 25), "18:30", "22:30", 100000)
    add("Coldplay - Music of the Spheres (Day 2)", "concert", "NMS", date(2025, 1, 26), "18:30", "22:30", 105000)
    add("Arijit Singh Live", "concert", "NMS", date(2025, 12, 20), "19:00", "22:45", 70000)
    add("New Year Music Festival", "concert", "NMS", date(2026, 12, 31), "20:00", "23:59", 80000)

    # Riverfront events
    for year in [2025, 2026]:
        for i, d in enumerate([date(year, 1, 10) + timedelta(days=j) for j in range(5)]):
            add(f"International Kite Festival {year} - Day {i + 1}", "riverfront", "RIVERFRONT", d, "10:00", "19:00", 45000 + i * 5000)
        add(f"Independence Day Celebration {year}", "riverfront", "RIVERFRONT", date(year, 8, 15), "18:00", "21:30", 40000)
    add("Riverfront Diwali Lights Fest", "riverfront", "RIVERFRONT", date(2025, 10, 20), "18:30", "22:30", 50000)
    add("Riverfront Diwali Lights Fest", "riverfront", "RIVERFRONT", date(2026, 11, 8), "18:30", "22:30", 55000)
    add("Riverfront New Year Eve", "riverfront", "RIVERFRONT", date(2025, 12, 31), "20:00", "23:59", 60000)

    df = pd.DataFrame(ev).sort_values("date").reset_index(drop=True)
    df.insert(0, "event_id", [f"EV{i + 1:03d}" for i in range(len(df))])
    return df


def hourly_profile(hour, weekend):
    """Normal day shape: commute peaks on weekdays, broad evening hump on weekends."""
    if hour == 24:
        return 0.0
    if weekend:
        return 0.25 + 0.75 * np.exp(-0.5 * ((hour - 18) / 3.0) ** 2)
    return (0.2 + 0.9 * np.exp(-0.5 * ((hour - 9) / 1.3) ** 2)
            + 1.0 * np.exp(-0.5 * ((hour - 18.5) / 1.5) ** 2)
            + 0.15 * np.exp(-0.5 * ((hour - 13) / 2) ** 2))


def build_ridership(events):
    days = pd.date_range(START, END, freq="D")
    rows = []
    ev_by_date = {}
    for e in events.itertuples():
        ev_by_date.setdefault(e.date, []).append(e)
    n_days = len(days)
    for di, d in enumerate(days):
        dd = d.date()
        weekend = dd.weekday() >= 5
        holiday = dd in HOLIDAYS
        growth = 0.85 + 0.35 * di / n_days                       # ridership grows over time
        season = 1.0 - 0.12 * (dd.month in (5, 6)) - 0.08 * (dd.month in (7, 8))  # summer heat / monsoon dip
        day_factor = (0.75 if weekend else 1.0) * (0.7 if holiday else 1.0)
        todays = ev_by_date.get(dd.isoformat(), [])
        for code, st in STATIONS.items():
            extra = {}
            for e in todays:
                for h, v in hourly_event_load(e.event_type, e.expected_attendance, e.venue, code,
                                              e.start_time, e.end_time).items():
                    extra[h] = extra.get(h, 0) + v * rng.normal(1.0, 0.08)
            for h in OPERATING_HOURS:
                base = st["base"] * hourly_profile(h, weekend or holiday) * growth * season * day_factor
                val = base * rng.normal(1.0, 0.07) + extra.get(h, 0.0)
                if h == 24 and extra.get(h, 0) < 50:
                    val = 0.0  # metro closed after midnight unless extended for an event
                rows.append((dd.isoformat(), code, h, max(0, int(round(val)))))
    return pd.DataFrame(rows, columns=["date", "station", "hour", "footfall"])


if __name__ == "__main__":
    stations = pd.DataFrame([{"station": k, "name": v["name"], "line": v["line"], "hourly_capacity": v["hourly_capacity"],
                              "paid_area_capacity": v["paid_area_capacity"], "num_gates": len(v["gates"])}
                             for k, v in STATIONS.items()])
    stations.to_csv(os.path.join(OUT, "stations.csv"), index=False)
    events = build_events()
    events.to_csv(os.path.join(OUT, "events.csv"), index=False)
    ride = build_ridership(events)
    ride.to_csv(os.path.join(OUT, "ridership_hourly.csv"), index=False)
    print(f"stations={len(stations)} events={len(events)} ridership rows={len(ride)}")
    print(f"venues: {list(VENUES)}")
