import os
import sys
import json
import numpy as np
import pandas as pd

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
    Computes mode-weighted transit accessibility with BOTH Raw and Min-Max Normalized (0~1) scores:
    1. Raw Scores:
       - BusMobility = Sum( W(d_i, R_bus) * ln(1 + bus_passengers_i / median_bus) )
       - SubwayMobility = Sum( W(d_j, R_subway) * ln(1 + subway_passengers_j / median_subway) )
       - RawWeightedMobility = w_bus * BusMobility + w_subway * SubwayMobility
    2. Normalized Scores (Eliminates the 89% Bus dominance scale distortion):
       - NormBusMobility = BusMobility / Max(BusMobility)
       - NormSubwayMobility = SubwayMobility / Max(SubwayMobility)
       - NormWeightedMobility = w_bus * NormBusMobility + w_subway * NormSubwayMobility
    3. Population Adjustment:
       - PopAdjustedNormWeightedMobility = NormWeightedMobility / ln(1 + LivingPopulation)
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

    raw_bus_scores = []
    raw_sub_scores = []

    print("[WeightedScoring] Computing raw spatial accessibility scores...")
    for g in grids:
        gx, gy = g["cx"], g["cy"]

        # Bus Mobility
        d_bus = np.hypot(bus_x - gx, bus_y - gy)
        mask_bus = d_bus <= r_bus
        bm = np.sum(gaussian_decay_weight(d_bus[mask_bus], r_bus) * bus_fac_scores[mask_bus]) if np.any(mask_bus) else 0.0
        raw_bus_scores.append(bm)

        # Subway Mobility
        d_sub = np.hypot(sub_x - gx, sub_y - gy)
        mask_sub = d_sub <= r_subway
        sm = np.sum(gaussian_decay_weight(d_sub[mask_sub], r_subway) * sub_fac_scores[mask_sub]) if np.any(mask_sub) else 0.0
        raw_sub_scores.append(sm)

    raw_bus_scores = np.array(raw_bus_scores)
    raw_sub_scores = np.array(raw_sub_scores)

    # Valid (Non-masked) Grids for Max Calculation
    valid_mask = np.array([not g["masked"] for g in grids])
    max_bus = float(np.max(raw_bus_scores[valid_mask])) if np.any(valid_mask) else 1.0
    max_sub = float(np.max(raw_sub_scores[valid_mask])) if np.any(valid_mask) else 1.0

    print(f"[WeightedScoring] Max Valid Bus Score: {max_bus:.4f}")
    print(f"[WeightedScoring] Max Valid Subway Score: {max_sub:.4f}")

    # Normalization (0~1)
    norm_bus_scores = np.where(valid_mask, raw_bus_scores / max_bus, 0.0)
    norm_sub_scores = np.where(valid_mask, raw_sub_scores / max_sub, 0.0)

    # Weighted Combinations
    raw_weighted = w_bus * raw_bus_scores + w_subway * raw_sub_scores
    norm_weighted = w_bus * norm_bus_scores + w_subway * norm_sub_scores

    results = []
    for idx, g in enumerate(grids):
        pop = g["pop"]
        masked = g["masked"]
        ln_pop = np.log1p(pop) if pop > 0 else 1.0

        pop_adj_raw = (raw_weighted[idx] / ln_pop) if (pop > 0 and not masked) else 0.0
        pop_adj_norm = (norm_weighted[idx] / ln_pop) if (pop > 0 and not masked) else 0.0

        results.append({
            "grid_id": g["id"],
            "grid_code": g["code"],
            "gu_name": g["gu"],
            "dong_name": g["dong"],
            "living_pop": pop,
            "masked": masked,
            "raw_bus_mobility": round(float(raw_bus_scores[idx]), 4),
            "raw_subway_mobility": round(float(raw_sub_scores[idx]), 4),
            "raw_weighted_mobility": round(float(raw_weighted[idx]), 4),
            "norm_bus_mobility": round(float(norm_bus_scores[idx]), 4),
            "norm_subway_mobility": round(float(norm_sub_scores[idx]), 4),
            "norm_weighted_mobility": round(float(norm_weighted[idx]), 4),
            "pop_adjusted_norm_weighted_mobility": round(float(pop_adj_norm), 4)
        })

    df = pd.DataFrame(results)
    out_csv = os.path.join(PROCESSED_DATA_DIR, "seoul_weighted_transit_accessibility.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[WeightedScoring] Exported CSV output to: {out_csv}")
    return df

if __name__ == '__main__':
    compute_weighted_transit_accessibility()
