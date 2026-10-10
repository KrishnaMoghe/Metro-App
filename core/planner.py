"""Minute-by-minute crowd plan generator.

Simulates the post-event surge at the venue's main metro station minute by minute
(arrivals -> street queue -> gates -> paid area/platform -> trains) and derives the
actions (gates, holding areas, extra trains, announcements) that keep the station safe.
A "no plan" baseline is simulated too, so the benefit of the plan is visible.
"""
import math
import re

import numpy as np

from .announcements import render
from .config import (GATE_THROUGHPUT, MIN_HEADWAY, NORMAL_HEADWAY_NIGHT, NORMAL_HEADWAY_PEAK,
                     STATIONS, TRAIN_CAPACITY, VENUES)
from .crowd import egress_curve, ingress_curve, station_riders, to_hhmm, to_min

HEADWAY_OPTIONS = [10, 8, 6, 5, 4]


def _zone_cap(zone):
    m = re.search(r"\(([\d,]+) pax\)", zone)
    return int(m.group(1).replace(",", "")) if m else 1000


def _per_train_capacity(st):
    # terminus: empty trains, one direction; through station: trains arrive part-full, two directions
    return TRAIN_CAPACITY if st["terminus"] else 2 * int(TRAIN_CAPACITY * 0.6)


def _normal_headway(minute):
    h = (minute // 60) % 24
    return NORMAL_HEADWAY_PEAK if (8 <= h < 11 or 17 <= h < 20) else NORMAL_HEADWAY_NIGHT


def simulate(arrivals, t0, st, headways, gates_open, metered):
    """arrivals[i] = people reaching the station at minute t0+i. Returns per-minute states."""
    cap_train = _per_train_capacity(st)
    paid_cap = st["paid_area_capacity"]
    outside = inside = 0.0
    next_train = 0
    out = []
    for i, a in enumerate(arrivals):
        outside += a
        gate_cap = gates_open[i] * GATE_THROUGHPUT
        room = max(0.0, paid_cap - inside) if metered else 1e9
        admit = min(outside, gate_cap, room)
        outside -= admit
        inside += admit
        boarded = 0.0
        train = False
        if i >= next_train:
            boarded = min(inside, cap_train)
            inside -= boarded
            next_train = i + headways[i]
            train = True
        out.append(dict(minute=t0 + i, time=to_hhmm(t0 + i), arrivals=round(a, 1), street_queue=round(outside),
                        inside=round(inside), boarded=round(boarded), train=train, gates=int(gates_open[i]),
                        headway=int(headways[i]), load_pct=round(100 * inside / paid_cap, 1)))
    return out


def generate_plan(event_name, event_type, venue, attendance, start_time, end_time, station=None):
    attendance = int(attendance)
    stations = VENUES[venue]["stations"]
    code = station or max(stations, key=stations.get)
    st = STATIONS[code]
    riders = station_riders(event_type, attendance, venue, code)
    s, e = to_min(start_time), to_min(end_time)
    if e < s:
        e += 1440

    # ---------- post-event egress window (main risk) ----------
    t0, t1 = e - 45, e + 150
    mins = np.arange(t0, t1)
    arrivals = riders * egress_curve(mins - e, event_type)
    total_gates = len(st["gates"])
    cap_train = _per_train_capacity(st)

    # choose surge headway: smallest headway whose throughput covers ~85% of the peak 15-min arrival rate
    peak_rate = np.convolve(arrivals, np.ones(15) / 15, mode="same").max()
    surge_hw = MIN_HEADWAY
    for h in HEADWAY_OPTIONS:
        if cap_train / h >= 0.85 * peak_rate:
            surge_hw = h
            break

    # planned gates: enough gate banks for the next-10-minute arrival rate (min 2)
    fwd = np.array([arrivals[i:i + 10].mean() for i in range(len(arrivals))])
    gates_plan = np.clip(np.ceil(fwd * 1.2 / GATE_THROUGHPUT), 2, total_gates).astype(int)

    # planned headway: surge from end-15 until the crowd clears (iterate once to find clearance)
    headway_plan = np.array([_normal_headway(m) for m in mins])
    headway_plan[mins >= e - 15] = surge_hw
    sim = simulate(arrivals, t0, st, headway_plan, gates_plan, metered=True)
    peak_i = int(np.argmax([x["street_queue"] + x["inside"] for x in sim]))
    clear_i = next((i for i in range(peak_i, len(sim)) if sim[i]["street_queue"] + sim[i]["inside"] < 150), len(sim) - 1)
    headway_plan[clear_i + 1:] = _normal_headway(t0 + clear_i)
    gates_plan[clear_i + 1:] = 2
    sim = simulate(arrivals, t0, st, headway_plan, gates_plan, metered=True)

    # baseline: no plan -> normal headway, 2 gates, no metering
    base = simulate(arrivals, t0, st, np.array([_normal_headway(m) for m in mins]),
                    np.full(len(mins), min(2, total_gates)), metered=False)

    # holding zones (activated by street-queue size)
    zones = st["holding"]
    thresholds, acc = [], 300
    for z in zones:
        thresholds.append(acc)
        acc += _zone_cap(z)
    for x in sim:
        x["holding_zones"] = sum(1 for th in thresholds if x["street_queue"] > th)

    # ---------- build action timeline ----------
    tl = []

    def add(minute, phase, category, action, detail="", severity="info", ann=None):
        tl.append(dict(minute=int(minute), time=to_hhmm(minute), phase=phase, category=category, action=action,
                       detail=detail, severity=severity, announcement=ann))

    staff = max(10, int(math.ceil(riders / 500)))
    main_exit = st["gates"][0]
    add(s - 240, "Preparation", "staff", f"Deploy {staff} station staff + {max(4, staff // 4)} security/RPF personnel",
        f"Expected {int(riders):,} metro riders at {st['name']} (of {attendance:,} attendees). Barricades to holding zones: "
        + ", ".join(zones), "warning")
    add(s - 180, "Pre-event", "gate", f"Open all {total_gates} gates in EXIT mode for arriving fans",
        "Arrival wave peaks ~60 min before start", ann=render("pre_arrival", station=st["name"], event=event_name, gate=main_exit))
    add(s - 150, "Pre-event", "train", f"Run peak headway ({NORMAL_HEADWAY_PEAK} min) on inbound trains",
        f"~{int(riders * ingress_curve(np.arange(-30, 181))[60:120].sum()):,} arrivals expected in the peak hour")
    add(s - 90, "Pre-event", "ticketing", "Open extra ticket counters + promote return QR tickets (WhatsApp / app)",
        "Pre-sold return tickets cut gate processing time after the event")
    add(s + 15, "During event", "gate", "Switch gates to normal mode; set up queue lanes for egress", "Arrival wave over")
    add(e - 60, "During event", "train", f"Position standby rakes; prepare {surge_hw}-min surge headway",
        f"Peak egress forecast {int(peak_rate * 15):,} people per 15 min", "warning")
    add(e - 30, "Egress", "staff", "Staff at stadium exits to stagger crowd release block-wise; escalators set to platform-bound",
        "~10% of spectators leave early")

    prev = dict(gates=None, headway=None, zones=0, plat=False)
    for x in sim:
        m = x["minute"]
        if prev["headway"] is not None and x["headway"] != prev["headway"]:
            if x["headway"] < prev["headway"]:
                add(m, "Egress", "train", f"ADD TRAINS: headway {prev['headway']} -> {x['headway']} min",
                    f"{cap_train:,} pax per departure", "critical",
                    render("train_added", station=st["name"], minutes=x["headway"]))
            else:
                add(m, "Recovery", "train", f"Restore normal headway ({x['headway']} min), return standby rakes")
        if prev["gates"] is not None and x["gates"] > prev["gates"]:
            g = st["gates"][x["gates"] - 1]
            add(m, "Egress", "gate", f"OPEN {g} for entry ({x['gates']}/{total_gates} gates)",
                f"Incoming {x['arrivals']:.0f} pax/min", "warning", render("gate_open", gate=g))
        elif prev["gates"] is not None and x["gates"] < prev["gates"]:
            add(m, "Recovery", "gate", f"Close gate(s), {x['gates']} gates remain open")
        if x["holding_zones"] > prev["zones"]:
            z = zones[x["holding_zones"] - 1]
            add(m, "Egress", "holding", f"ACTIVATE HOLDING: {z}",
                f"Street queue {x['street_queue']:,}; release in batches of ~{cap_train} per train", "critical",
                render("holding", holding=z.split(" (")[0], minutes=x["headway"]))
        elif x["holding_zones"] < prev["zones"]:
            add(m, "Recovery", "holding", f"Release holding zone {zones[prev['zones'] - 1].split(' (')[0]}")
        plat = x["load_pct"] >= 85 or (prev["plat"] and x["load_pct"] >= 50)
        if plat and not prev["plat"]:
            add(m, "Egress", "platform", "Platform/paid area >85%: hold gates (metering) until next train",
                f"Paid area {x['inside']:,}/{st['paid_area_capacity']:,}", "critical",
                render("platform_full", minutes=x["headway"]))
        prev.update(gates=x["gates"], headway=x["headway"], zones=x["holding_zones"], plat=plat)
    worst_wait = max(x["street_queue"] + x["inside"] for x in sim) / (cap_train / surge_hw)
    if worst_wait > 25:
        add(e, "Egress", "staff", "Request AMTS/BRTS shuttle buses to the next 2 stations",
            f"Worst-case wait ~{worst_wait:.0f} min exceeds 25 min; divert ~15% of the crowd", "warning")
    add(t0 + clear_i, "Recovery", "staff", "Crowd cleared - stand down holding zones, debrief", "", "info",
        render("release", station=st["name"]))
    tl.sort(key=lambda r: r["minute"])

    planned_trains = sum(1 for x in sim if x["train"])
    base_trains = sum(1 for x in base if x["train"])
    clear_base = next((i for i in range(int(np.argmax([b["street_queue"] + b["inside"] for b in base])), len(base))
                       if base[i]["street_queue"] + base[i]["inside"] < 150), None)
    summary = dict(
        station=code, station_name=st["name"], venue=VENUES[venue]["name"], metro_riders=int(riders),
        peak_arrival_rate=round(float(peak_rate)), surge_headway=surge_hw, extra_trains=planned_trains - base_trains,
        peak_street_queue=max(x["street_queue"] for x in sim), peak_inside=max(x["inside"] for x in sim),
        peak_time=sim[peak_i]["time"], clear_time=sim[clear_i]["time"],
        clear_minutes_after_end=int(t0 + clear_i - e), staff=staff,
        max_wait_min=round(max(x["street_queue"] + x["inside"] for x in sim) / (cap_train / surge_hw)),
        paid_area_capacity=st["paid_area_capacity"],
        baseline_peak_inside=max(b["inside"] for b in base),
        baseline_overcrowded_minutes=sum(1 for b in base if b["inside"] > st["paid_area_capacity"]),
        baseline_clear_minutes_after_end=int(t0 + clear_base - e) if clear_base is not None else "150+",
    )
    for b, x in zip(base, sim):
        x["baseline_inside"] = b["inside"]
        x["baseline_queue"] = b["street_queue"]

    others = []
    for c, share in stations.items():
        if c == code:
            continue
        r = station_riders(event_type, attendance, venue, c)
        pr = (r * egress_curve(mins - e, event_type)).max() * 15
        others.append(dict(station=c, name=STATIONS[c]["name"], riders=int(r), peak_15min=int(pr),
                           advice=f"Run {6 if pr > 1500 else 8}-min headway {to_hhmm(e - 10)}-{to_hhmm(e + 60)}; "
                                  f"open {min(len(STATIONS[c]['gates']), 2 + int(pr // 1500))} gates; "
                                  f"use {STATIONS[c]['holding'][0].split(' (')[0]} if queue builds"))

    announcements = [a for a in (r["announcement"] for r in tl) if a]
    uniq = {}
    for a in announcements:
        uniq.setdefault(a["key"], a)
    return dict(summary=summary, timeline=tl, minutes=sim, other_stations=others,
                announcements=list(uniq.values()),
                event=dict(name=event_name, type=event_type, venue=venue, attendance=attendance,
                           start=start_time, end=end_time))
