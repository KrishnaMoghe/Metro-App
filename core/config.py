"""Static configuration: stations, venues and operating constants (Ahmedabad Metro, simplified)."""

TRAIN_CAPACITY = 1000          # passengers per 3-coach train (normal load)
MIN_HEADWAY = 4                # minutes, tightest safe headway with standby rakes
NORMAL_HEADWAY_PEAK = 8
NORMAL_HEADWAY_NIGHT = 12
GATE_THROUGHPUT = 90           # pax/min per gate bank (approx. 4 AFC turnstiles)
OPERATING_HOURS = list(range(6, 25))   # 6:00 .. 24:00 (hour 24 = 00:00-01:00, only on event days)

STATIONS = {
    "MOTERA": {
        "name": "Motera Stadium", "line": "Red Line (N-S)", "base": 900, "terminus": True,
        "hourly_capacity": 9000, "paid_area_capacity": 2500,
        "gates": ["Gate A (Stadium side)", "Gate B (Stadium side)", "Gate C (Highway side)", "Gate D (Service road)"],
        "holding": ["Stadium Plaza - Zone H1 (1,500 pax)", "Service Road Barricade Zone H2 (2,000 pax)", "Parking P3 - Zone H3 (3,000 pax)"],
        "platforms": ["Platform 1 (towards APMC)"],
    },
    "SABARMATI": {
        "name": "Sabarmati", "line": "Red Line (N-S)", "base": 1100, "terminus": False,
        "hourly_capacity": 8000, "paid_area_capacity": 2000,
        "gates": ["Gate A (Highway)", "Gate B (Railway colony)", "Gate C (Bus stop)"],
        "holding": ["Forecourt Zone H1 (1,000 pax)", "Bus Bay Zone H2 (1,500 pax)"],
        "platforms": ["Platform 1 (towards Motera)", "Platform 2 (towards APMC)"],
    },
    "GUJ_UNI": {
        "name": "Gujarat University", "line": "Blue Line (E-W)", "base": 1400, "terminus": False,
        "hourly_capacity": 8500, "paid_area_capacity": 2200,
        "gates": ["Gate A (GMDC Ground side)", "Gate B (University side)", "Gate C (Helmet circle)", "Gate D (Memnagar)"],
        "holding": ["GMDC Approach Road Zone H1 (1,500 pax)", "University Parking Zone H2 (2,000 pax)"],
        "platforms": ["Platform 1 (towards Thaltej)", "Platform 2 (towards Vastral)"],
    },
    "OLD_HC": {
        "name": "Old High Court (Interchange)", "line": "Blue + Red interchange", "base": 2200, "terminus": False,
        "hourly_capacity": 12000, "paid_area_capacity": 3500,
        "gates": ["Gate A (Ashram Road)", "Gate B (Riverfront)", "Gate C (Income Tax)", "Gate D (Interchange link)"],
        "holding": ["Riverfront Walkway Zone H1 (2,000 pax)", "Ashram Road Service Lane H2 (1,500 pax)"],
        "platforms": ["Blue Line platforms", "Red Line platforms"],
    },
    "GANDHIGRAM": {
        "name": "Gandhigram", "line": "Red Line (N-S)", "base": 1000, "terminus": False,
        "hourly_capacity": 7500, "paid_area_capacity": 1800,
        "gates": ["Gate A (Riverfront)", "Gate B (Ellisbridge)", "Gate C (Town Hall)"],
        "holding": ["Riverfront Lower Promenade H1 (2,500 pax)", "Town Hall Ground H2 (1,500 pax)"],
        "platforms": ["Platform 1 (towards Motera)", "Platform 2 (towards APMC)"],
    },
    "KALUPUR": {
        "name": "Kalupur Railway Station", "line": "Blue Line (E-W)", "base": 2600, "terminus": False,
        "hourly_capacity": 12000, "paid_area_capacity": 3000,
        "gates": ["Gate A (Railway station)", "Gate B (Sarangpur)", "Gate C (Bus terminal)"],
        "holding": ["Railway Forecourt H1 (2,000 pax)"],
        "platforms": ["Platform 1 (towards Thaltej)", "Platform 2 (towards Vastral)"],
    },
    "THALTEJ": {
        "name": "Thaltej", "line": "Blue Line (E-W)", "base": 1200, "terminus": True,
        "hourly_capacity": 8000, "paid_area_capacity": 2000,
        "gates": ["Gate A (SG Highway)", "Gate B (Thaltej village)"],
        "holding": ["SG Highway Service Lane H1 (1,000 pax)"],
        "platforms": ["Platform 1 (towards Vastral)"],
    },
    "APMC": {
        "name": "APMC", "line": "Red Line (N-S)", "base": 1300, "terminus": True,
        "hourly_capacity": 8000, "paid_area_capacity": 2000,
        "gates": ["Gate A (Vasna)", "Gate B (APMC market)"],
        "holding": ["Market Parking H1 (1,000 pax)"],
        "platforms": ["Platform 1 (towards Motera)"],
    },
}

# Venues -> share of metro riders that use each nearby station
VENUES = {
    "NMS": {"name": "Narendra Modi Stadium, Motera", "stations": {"MOTERA": 0.75, "SABARMATI": 0.25}},
    "GMDC": {"name": "GMDC Ground (Navratri Garba)", "stations": {"GUJ_UNI": 0.8, "OLD_HC": 0.2}},
    "RIVERFRONT": {"name": "Sabarmati Riverfront Event Centre", "stations": {"GANDHIGRAM": 0.55, "OLD_HC": 0.45}},
}

# Fraction of attendees who use the metro, by event type
METRO_SHARE = {"cricket": 0.32, "concert": 0.38, "navratri": 0.22, "riverfront": 0.28}

EVENT_TYPES = ["none", "cricket", "concert", "navratri", "riverfront"]
