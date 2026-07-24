import os
import sys
import json
import numpy as np
import pandas as pd
import geopandas as gpd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.config import PROCESSED_DATA_DIR, MAPS_DIR
from src.transit_scoring import gaussian_decay_weight

def compute_weighted_transit_accessibility(
    js_data_path=os.path.join(MAPS_DIR, "grid_data.js"),
    r_bus=400.0,
    r_subway=800.0,
    w_bus=0.544,
    w_subway=0.456
):
    """
    Computes mode-weighted transit accessibility using:
    - Bus Weight: 0.544 (54.4%)
    - Subway Weight: 0.456 (45.6%)
    - Denominators: Median passenger count across all facilities
    - Facility Score = ln(1 + passengers / median_passengers)
    - Weighted Mobility = 0.544 * BusMobility + 0.456 * SubwayMobility
    - Population-Adjusted Mobility = WeightedMobility / ln(1 + living_population)
    """
    print("[WeightedScoring] Reading grid_data.js payload...")
    with open(js_data_path, "r", encoding="utf-8") as f:
        content = f.read()
        json_str = content.replace("window.ACCESSIBILITY_DATA = ", "").rstrip(";\n")
        data = json.loads(json_str)

    grids = data["grids"]
    buses = data["buses"]
    subways = data["subways"]

    print(f"[WeightedScoring] Loaded {len(grids)} grids, {len(buses)} buses, {len(subways)} subways.")

    # Calculate Medians
    bus_passengers = np.array([b["passengers"] for b in buses])
    subway_passengers = np.array([s["passengers"] for s in subways])

    median_bus = float(np.median(bus_passengers))
    median_subway = float(np.median(subway_passengers))

    print(f"[WeightedScoring] Median Bus Passengers: {median_bus:,.1f}")
    print(f"[WeightedScoring] Median Subway Passengers: {median_subway:,.1f}")

    # Compute Facility Scores: ln(1 + passengers / median)
    bus_fac_scores = np.log1p(bus_passengers / median_bus)
    sub_fac_scores = np.log1p(subway_passengers / median_subway)

    bus_x = np.array([b["x"] for b in buses])
    bus_y = np.array([b["y"] for b in buses])
    sub_x = np.array([s["x"] for s in subways])
    sub_y = np.array([s["y"] for s in subways])

    results = []

    print("[WeightedScoring] Computing spatial distance decay and weighted superposition...")
    for g in grids:
        gx, gy = g["cx"], g["cy"]

        # Bus Mobility
        d_bus = np.hypot(bus_x - gx, bus_y - gy)
        mask_bus = d_bus <= r_bus
        if np.any(mask_bus):
            w_d = gaussian_decay_weight(d_bus[mask_bus], r_bus)
            bus_mobility = np.sum(w_d * bus_fac_scores[mask_bus])
        else:
            bus_mobility = 0.0

        # Subway Mobility
        d_sub = np.hypot(sub_x - gx, sub_y - gy)
        mask_sub = d_sub <= r_subway
        if np.any(mask_sub):
            w_d = gaussian_decay_weight(d_sub[mask_sub], r_subway)
            sub_mobility = np.sum(w_d * sub_fac_scores[mask_sub])
        else:
            sub_mobility = 0.0

        # Weighted Superposition: 0.544 * Bus + 0.456 * Subway
        weighted_mobility = w_bus * bus_mobility + w_subway * sub_mobility

        # Population Adjustment: WeightedMobility / ln(1 + LivingPopulation)
        pop = g["pop"]
        masked = g["masked"]
        ln_pop = np.log1p(pop) if pop > 0 else 1.0
        pop_adjusted_mobility = (weighted_mobility / ln_pop) if (pop > 0 and not masked) else 0.0

        results.append({
            "grid_id": g["id"],
            "grid_code": g["code"],
            "gu_name": g["gu"],
            "dong_name": g["dong"],
            "living_pop": pop,
            "masked": masked,
            "bus_mobility": round(float(bus_mobility), 4),
            "subway_mobility": round(float(sub_mobility), 4),
            "weighted_mobility": round(float(weighted_mobility), 4),
            "pop_adjusted_weighted_mobility": round(float(pop_adjusted_mobility), 4)
        })

    df = pd.DataFrame(results)
    out_csv = os.path.join(PROCESSED_DATA_DIR, "seoul_weighted_transit_accessibility.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[WeightedScoring] Exported CSV output to: {out_csv}")
    return df

if __name__ == '__main__':
    compute_weighted_transit_accessibility()
