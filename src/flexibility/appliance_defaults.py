"""
appliance_defaults.py
=====================
Default electrical parameters for every modelled appliance.

All values are based on publicly available German household energy studies
(e.g. BDEW Lastprofile, DESTATIS Energieverbrauch, Stiftung Warentest tests).

The dictionary can be overridden at runtime by passing a modified copy to
HouseholdProfile or ShiftableAppliance.

Load curve format
-----------------
``load_curve`` is a list of normalised power fractions summing to approximately
the device's full cycle.  Each element represents one 15-minute slot.
The values are relative (0–1) and scaled by ``power_kw`` during profile synthesis.

Season factor keys
------------------
``"winter"``      → December–February
``"transition"``  → March–May, September–November
``"summer"``      → June–August
"""

from __future__ import annotations

APPLIANCE_DEFAULTS: dict[str, dict] = {
    # ------------------------------------------------------------------
    # Washing machine  (front-loader, EU Eco 60 °C programme ~1.5 h)
    # ------------------------------------------------------------------
    "Washing_machine": {
        "power_kw": 2.0,
        "runtime_hours": 1.5,
        # 6 × 15-min slots: heat-up → wash plateau → rinse × 2 → spin × 2
        "load_curve": [0.30, 1.00, 0.80, 0.50, 0.40, 0.25],
        "is_shiftable": True,
        "max_shift_hours": 8,
        "season_factor": {"winter": 1.10, "transition": 1.00, "summer": 0.90},
    },
    # ------------------------------------------------------------------
    # Tumble dryer  (condenser, B-rated, ~60 min for 5 kg)
    # ------------------------------------------------------------------
    "Dryer": {
        "power_kw": 2.5,
        "runtime_hours": 1.0,
        "load_curve": [0.80, 1.00, 0.95, 0.60],
        "is_shiftable": True,
        "max_shift_hours": 8,
        "season_factor": {"winter": 1.15, "transition": 1.00, "summer": 0.70},
    },
    # ------------------------------------------------------------------
    # Dishwasher  (A+++ 12-place, eco 50 °C, ~1.5 h)
    # ------------------------------------------------------------------
    "Dishwasher": {
        "power_kw": 1.8,
        "runtime_hours": 1.5,
        "load_curve": [0.25, 1.00, 0.85, 0.40, 0.40, 0.20],
        "is_shiftable": True,
        "max_shift_hours": 6,
        "season_factor": {"winter": 1.05, "transition": 1.00, "summer": 0.95},
    },
    # ------------------------------------------------------------------
    # Electric oven  (conventional baking, ~45 min)
    # ------------------------------------------------------------------
    "Oven": {
        "power_kw": 2.2,
        "runtime_hours": 0.75,
        "load_curve": [1.00, 0.70, 0.55],
        "is_shiftable": False,
        "max_shift_hours": 1,
        "season_factor": {"winter": 1.10, "transition": 1.00, "summer": 0.85},
    },
    # ------------------------------------------------------------------
    # Microwave  (900 W, short 5-min bursts → model as single slot)
    # ------------------------------------------------------------------
    "Mikrowave": {
        "power_kw": 0.9,
        "runtime_hours": 0.25,
        "load_curve": [1.00],
        "is_shiftable": False,
        "max_shift_hours": 0,
        "season_factor": {"winter": 1.00, "transition": 1.00, "summer": 1.00},
    },
    # ------------------------------------------------------------------
    # Desktop/Laptop computer  (gaming desktop ~150 W, laptop ~45 W → avg 100 W)
    # Used as semi-continuous baseload during working hours
    # ------------------------------------------------------------------
    "Computer": {
        "power_kw": 0.10,
        "runtime_hours": 8.0,
        # 32 × 15-min slots: roughly flat with small variation
        "load_curve": [
            0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.00,
            1.00, 1.00, 1.00, 0.95, 0.90, 0.85, 0.80, 0.75,
            0.70, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70,
            0.70, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70, 0.70,
        ],
        "is_shiftable": False,
        "max_shift_hours": 0,
        "season_factor": {"winter": 1.05, "transition": 1.00, "summer": 0.95},
    },
    # ------------------------------------------------------------------
    # Television  (50" LED, ~80 W, ~3 h evening)
    # ------------------------------------------------------------------
    "TV": {
        "power_kw": 0.08,
        "runtime_hours": 3.0,
        "load_curve": [
            0.50, 0.80, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00,
            0.90, 0.70, 0.40, 0.20,
        ],
        "is_shiftable": False,
        "max_shift_hours": 0,
        "season_factor": {"winter": 1.15, "transition": 1.00, "summer": 0.80},
    },
    # ------------------------------------------------------------------
    # Durchlauferhitzer (instantaneous water heater, 18–24 kW, short ~5 min)
    # Modelled as two 15-min slots (morning + evening shower)
    # ------------------------------------------------------------------
    "Durchlauferhitzer": {
        "power_kw": 21.0,
        "runtime_hours": 0.25,
        "load_curve": [1.00],
        "is_shiftable": False,
        "max_shift_hours": 1,
        "season_factor": {"winter": 1.30, "transition": 1.00, "summer": 0.70},
    },
    # ------------------------------------------------------------------
    # Electric Vehicle  (11 kW AC home charger, overnight, ~6 h)
    # ------------------------------------------------------------------
    "EV": {
        "power_kw": 11.0,
        "runtime_hours": 6.0,
        "load_curve": [
            1.00, 1.00, 1.00, 1.00, 0.90, 0.80, 0.60, 0.40,
            0.30, 0.20, 0.10, 0.05, 0.05, 0.05, 0.05, 0.05,
            0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05,
        ],
        "is_shiftable": True,
        "max_shift_hours": 10,
        "season_factor": {"winter": 1.20, "transition": 1.00, "summer": 0.90},
    },
    # ------------------------------------------------------------------
    # Heat pump  (air-source, COP ~3, 8 kW thermal → 2.7 kW electrical)
    # For DWD-temperature-based scaling see seasonal_modifier.py
    # ------------------------------------------------------------------
    "Heatpump": {
        "power_kw": 2.7,
        "runtime_hours": 12.0,
        "load_curve": [
            1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 0.90,
            0.80, 0.70, 0.60, 0.50, 0.40, 0.40, 0.50, 0.60,
            0.70, 0.80, 0.90, 1.00, 1.00, 1.00, 1.00, 1.00,
            1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00,
            1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00,
            1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00,
        ],
        "is_shiftable": True,
        "max_shift_hours": 4,
        "season_factor": {"winter": 2.50, "transition": 1.00, "summer": 0.20},
    },
}

# ---------------------------------------------------------------------------
# Convenience alias: appliance CSV column prefix → defaults key
# ---------------------------------------------------------------------------
COLUMN_TO_APPLIANCE: dict[str, str] = {
    "Washing_machine": "Washing_machine",
    "Dryer": "Dryer",
    "Dishwasher": "Dishwasher",
    "Oven": "Oven",
    "Mikrowave": "Mikrowave",
    "Computer": "Computer",
    "TV": "TV",
    "Durchlauferhitzer": "Durchlauferhitzer",
    "EV": "EV",
    "Heatpump": "Heatpump",
}

# Flexibility column mapping: appliance name → survey column suffix
FLEX_COLUMN_MAP: dict[str, str] = {
    "Washing_machine": "waschmaschine",
    "Dryer": "trockner",
    "Oven": "backofen",
    "Dishwasher": "spuelmaschine",
    "TV": "fernseher",
    "EV": "e_auto",
}
