import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import folium
from scipy.spatial import cKDTree

from src.config import PROCESSED_DATA_DIR, MAPS_DIR, TARGET_CRS, DATA_DIR
from src.transit_scoring import gaussian_decay_weight, calculate_facility_score, plot_gaussian_decay_curve
from src.gaussian_simulator import build_interactive_simulator_html

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

def calculate_grid_transit_accessibility(
    r_bus: float = 400.0,
    r_subway: float = 800.0,
    base_bus: float = 10.0,
    base_subway: float = 50.0,
    passenger_scaling: str = "log",
    passenger_weight: float = 3.0,
    max_add_score: float = 50.0
):
    """
    Computes spatial Gaussian distance-decayed transit accessibility scores for all 250m Seoul grids.
    """
    print("[Pipeline] Loading Seoul Grid, Bus & Subway node GeoJSON datasets...")
    grid_path = os.path.join(PROCESSED_DATA_DIR, "seoul_masked_grid_250m.geojson")
    if not os.path.exists(grid_path):
        grid_path = os.path.join(PROCESSED_DATA_DIR, "seoul_grid_250m.geojson")
        
    grid_gdf = gpd.read_file(grid_path)
    bus_gdf = gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "seoul_bus_nodes_5179.geojson"))
    subway_gdf = gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "seoul_subway_nodes_5179.geojson"))
    gu_gdf = gpd.read_file(os.path.join(PROCESSED_DATA_DIR, "seoul_gu_boundaries_5179.geojson"))
    
    # 1. Facility Score Calculation (Mock passenger data if not present)
    bus_passengers = bus_gdf.get('승하차인원', np.random.uniform(500, 5000, len(bus_gdf)))
    subway_passengers = subway_gdf.get('승하차인원', np.random.uniform(5000, 50000, len(subway_gdf)))
    
    bus_gdf['facility_score'] = calculate_facility_score(
        base_score=base_bus, passengers=bus_passengers,
        scaling_mode=passenger_scaling, passenger_weight=passenger_weight,
        max_additional_score=max_add_score
    )
    
    subway_gdf['facility_score'] = calculate_facility_score(
        base_score=base_subway, passengers=subway_passengers,
        scaling_mode=passenger_scaling, passenger_weight=passenger_weight,
        max_additional_score=max_add_score
    )
    
    # 2. Fast KD-Tree Nearest Neighbor / Radius Query for Grid Centroids
    print("[Pipeline] Computing Gaussian-weighted spatial accessibility scores...")
    centroids = np.array([[geom.centroid.x, geom.centroid.y] for geom in grid_gdf.geometry])
    
    bus_coords = np.array([[geom.x, geom.y] for geom in bus_gdf.geometry])
    subway_coords = np.array([[geom.x, geom.y] for geom in subway_gdf.geometry])
    
    bus_tree = cKDTree(bus_coords)
    subway_tree = cKDTree(subway_coords)
    
    # Query Bus within R_bus
    bus_indices_list = bus_tree.query_ball_point(centroids, r=r_bus)
    grid_bus_scores = []
    for idx_grid, bus_indices in enumerate(bus_indices_list):
        if not bus_indices:
            grid_bus_scores.append(0.0)
            continue
        c = centroids[idx_grid]
        dists = np.linalg.norm(bus_coords[bus_indices] - c, axis=1)
        weights = gaussian_decay_weight(dists, R=r_bus)
        f_scores = bus_gdf['facility_score'].iloc[bus_indices].values
        grid_bus_scores.append(np.sum(weights * f_scores))
        
    # Query Subway within R_subway
    subway_indices_list = subway_tree.query_ball_point(centroids, r=r_subway)
    grid_subway_scores = []
    for idx_grid, subway_indices in enumerate(subway_indices_list):
        if not subway_indices:
            grid_subway_scores.append(0.0)
            continue
        c = centroids[idx_grid]
        dists = np.linalg.norm(subway_coords[subway_indices] - c, axis=1)
        weights = gaussian_decay_weight(dists, R=r_subway)
        f_scores = subway_gdf['facility_score'].iloc[subway_indices].values
        grid_subway_scores.append(np.sum(weights * f_scores))
        
    grid_gdf['bus_accessibility_score'] = grid_bus_scores
    grid_gdf['subway_accessibility_score'] = grid_subway_scores
    grid_gdf['total_transit_score'] = grid_gdf['bus_accessibility_score'] + grid_gdf['subway_accessibility_score']
    
    # Save outputs & visualizations
    curve_png = os.path.join(MAPS_DIR, "gaussian_decay_curve.png")
    plot_gaussian_decay_curve(curve_png)
    print(f"[Pipeline] Distance decay curve plot saved to: {curve_png}")
    
    simulator_html = build_interactive_simulator_html()
    
    # Generate Map Output
    plot_static_accessibility_map(grid_gdf, gu_gdf)
    
    out_geojson = os.path.join(PROCESSED_DATA_DIR, "seoul_gaussian_transit_scores.geojson")
    grid_gdf.to_file(out_geojson, driver="GeoJSON")
    print(f"[Pipeline] Complete Gaussian Transit Accessibility GeoJSON saved to: {out_geojson}")

def plot_static_accessibility_map(grid_gdf: gpd.GeoDataFrame, gu_gdf: gpd.GeoDataFrame):
    out_png = os.path.join(MAPS_DIR, "seoul_gaussian_transit_accessibility_map.png")
    fig, ax = plt.subplots(figsize=(16, 14), facecolor='#111827')
    ax.set_facecolor('#111827')
    
    grid_gdf.plot(
        ax=ax,
        column='total_transit_score',
        cmap='YlOrRd',
        legend=True,
        linewidth=0.1,
        edgecolor='#111827',
        legend_kwds={'label': 'Gaussian Weighted Total Transit Score', 'shrink': 0.7}
    )
    
    if gu_gdf is not None:
        gu_gdf.plot(ax=ax, facecolor='none', edgecolor='#f9fafb', linewidth=1.2, linestyle='--')
        for _, row in gu_gdf.iterrows():
            c = row.geometry.centroid
            ax.annotate(row['gu_name'], xy=(c.x, c.y), color='#ffffff', fontsize=10, fontweight='bold', ha='center')
            
    ax.set_title("Seoul 250m Grid Gaussian Transit Accessibility Score Map", fontsize=16, color='white', fontweight='bold', pad=20)
    ax.set_xlabel("UTMK X (m)", color='#9ca3af')
    ax.set_ylabel("UTMK Y (m)", color='#9ca3af')
    ax.tick_params(colors='#9ca3af')
    ax.grid(True, linestyle=':', alpha=0.3, color='#4b5563')
    
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[Pipeline] Static Transit Accessibility Heatmap saved to: {out_png}")

if __name__ == '__main__':
    calculate_grid_transit_accessibility()
