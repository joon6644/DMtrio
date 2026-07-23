import sys
import os

# Add project root directory to sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium

from src.config import PROCESSED_DATA_DIR, MAPS_DIR, TARGET_CRS
from src.data_loader import load_seoul_gu_boundaries, load_seoul_dong_boundaries

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

def process_population_data(csv_path: str) -> pd.DataFrame:
    """
    Loads 250m population CSV.
    - If a grid has 24 hours of '*', daily mean population is set to NaN (미집계/비주거).
    - If a grid has numeric hours, calculates average over valid numeric hours.
    """
    print("[SpatialAnalyzer] Processing population data (24h '*' set to NaN)...")
    pop_df = pd.read_csv(csv_path, encoding='cp949')
    
    pop_df['is_star'] = (pop_df['생활인구합계'] == '*')
    pop_df['pop_num'] = pd.to_numeric(pop_df['생활인구합계'], errors='coerce')
    
    grouped = pop_df.groupby('250M격자').agg(
        star_hours=('is_star', 'sum'),
        total_hours=('is_star', 'count'),
        mean_pop=('pop_num', 'mean'),
        max_pop=('pop_num', 'max')
    ).reset_index()
    
    grouped.loc[grouped['star_hours'] == 24, 'mean_pop'] = np.nan
    grouped.loc[grouped['star_hours'] == 24, 'max_pop'] = np.nan
    
    return grouped

def run_spatial_analysis_pipeline(grid_gdf: gpd.GeoDataFrame, data_dir: str):
    """
    Performs Spatial Join of Bus & Subway data as well as Gu & Dong administrative boundaries
    onto 250m Seoul grid and exports 3 interactive HTML maps & 3 static PNG maps.
    """
    # 0. Load Administrative Boundaries (Gu & Dong)
    print("[SpatialAnalyzer] Mapping 25 Autonomous Districts (Gu) and 467 Dongs onto 250m grids...")
    dong_gdf = load_seoul_dong_boundaries()
    gu_gdf = load_seoul_gu_boundaries()
    
    # Spatial Join centroids to assign Gu & Dong
    centroids = grid_gdf.copy()
    centroids['geometry'] = centroids.geometry.centroid
    grid_admin = gpd.sjoin(centroids[['grid_id', 'geometry']], dong_gdf[['gu_name', 'dong_name', 'geometry']], how='left', predicate='within')
    
    grid = grid_gdf.merge(grid_admin[['grid_id', 'gu_name', 'dong_name']], on='grid_id', how='left')
    grid['gu_name'] = grid['gu_name'].fillna('서울시')
    grid['dong_name'] = grid['dong_name'].fillna('')
    grid['full_address'] = "서울특별시 " + grid['gu_name'] + " " + grid['dong_name']
    
    # 1. Load Bus & Subway Data
    subway_csv = os.path.join(data_dir, '서울시 역사마스터 정보.csv')
    subway_df = pd.read_csv(subway_csv, encoding='cp949')
    subway_gdf = gpd.GeoDataFrame(
        subway_df,
        geometry=gpd.points_from_xy(subway_df['경도'], subway_df['위도']),
        crs='EPSG:4326'
    ).to_crs(TARGET_CRS)
    
    bus_xlsx = os.path.join(data_dir, '서울시버스정류소위치정보(20260701).xlsx')
    bus_df = pd.read_excel(bus_xlsx)
    bus_gdf = gpd.GeoDataFrame(
        bus_df,
        geometry=gpd.points_from_xy(bus_df['X좌표'], bus_df['Y좌표']),
        crs='EPSG:4326'
    ).to_crs(TARGET_CRS)
    
    # 2. Population Data Integration
    pop_csv = os.path.join(data_dir, '250_LOCAL_RESD_20260719.csv')
    pop_stats = process_population_data(pop_csv)
    
    # Merge Population onto Grid
    grid = grid.merge(pop_stats, left_on='grid_code', right_on='250M격자', how='left')
    
    # 3. Spatial Join for Point-in-Polygon Counts
    print("[SpatialAnalyzer] Performing Spatial Join for Bus stops & Subway stations...")
    bus_joined = gpd.sjoin(bus_gdf, grid, how='inner', predicate='within')
    bus_counts = bus_joined.groupby('grid_id').size().rename('bus_count')
    
    subway_joined = gpd.sjoin(subway_gdf, grid, how='inner', predicate='within')
    subway_counts = subway_joined.groupby('grid_id').size().rename('subway_count')
    
    grid = grid.merge(bus_counts, on='grid_id', how='left').merge(subway_counts, on='grid_id', how='left')
    grid['bus_count'] = grid['bus_count'].fillna(0).astype(int)
    grid['subway_count'] = grid['subway_count'].fillna(0).astype(int)
    
    # Categorize combined transit availability
    def categorize_transit(row):
        has_bus = row['bus_count'] > 0
        has_subway = row['subway_count'] > 0
        if has_bus and has_subway:
            return 'Both (버스+지하철)'
        elif has_bus:
            return 'Bus Only (버스만)'
        elif has_subway:
            return 'Subway Only (지하철만)'
        else:
            return 'Neither (미배치)'
            
    grid['transit_cat'] = grid.apply(categorize_transit, axis=1)
    
    # 4. 500m Buffer Accessibility
    print("[SpatialAnalyzer] Calculating 500m buffer accessibility for transport nodes...")
    centroids_gdf = grid.copy()
    centroids_gdf['geometry'] = centroids_gdf.geometry.centroid.buffer(500)
    
    bus_buffer_joined = gpd.sjoin(bus_gdf, centroids_gdf, how='inner', predicate='within')
    bus_buffer_counts = bus_buffer_joined.groupby('grid_id').size().rename('bus_500m_count')
    
    subway_buffer_joined = gpd.sjoin(subway_gdf, centroids_gdf, how='inner', predicate='within')
    subway_buffer_counts = subway_buffer_joined.groupby('grid_id').size().rename('subway_500m_count')
    
    grid = grid.merge(bus_buffer_counts, on='grid_id', how='left').merge(subway_buffer_counts, on='grid_id', how='left')
    grid['bus_500m_count'] = grid['bus_500m_count'].fillna(0).astype(int)
    grid['subway_500m_count'] = grid['subway_500m_count'].fillna(0).astype(int)
    
    # Save Final Analysis GeoJSON
    out_analysis_geojson = os.path.join(PROCESSED_DATA_DIR, "seoul_vulnerability_grid.geojson")
    grid.to_file(out_analysis_geojson, driver="GeoJSON")
    print(f"[SpatialAnalyzer] Saved complete vulnerability GeoJSON to: {out_analysis_geojson}")
    
    # 5. Generate 3 Visualizations (Bus Only, Subway Only, Combined Overlay)
    generate_three_visualizations(grid, bus_gdf, subway_gdf, gu_gdf)

def generate_three_visualizations(grid: gpd.GeoDataFrame, bus_gdf: gpd.GeoDataFrame, subway_gdf: gpd.GeoDataFrame, gu_gdf: gpd.GeoDataFrame):
    """
    Generates 3 separate pairs (Static PNG & Interactive HTML) of maps:
    1) Bus Only Map (버스 위치/격자)
    2) Subway Only Map (지하철 위치/격자)
    3) Combined Overlay Map (버스+지하철 실제 위치 오버레이 - 구 경계 레이어 포함)
    """
    # 1. Bus Map
    print("[SpatialAnalyzer] Generating Visualization 1: 버스 정류소 위치 시각화...")
    plot_static_transport_map(grid, gu_gdf, mode='bus', title="Seoul Bus Stop Distribution & Grid Coverage (250m Grid)")
    plot_interactive_transport_map(grid, bus_gdf, None, gu_gdf, mode='bus', filename="seoul_bus_accessibility_interactive.html")
    
    # 2. Subway Map
    print("[SpatialAnalyzer] Generating Visualization 2: 지하철역 위치 시각화...")
    plot_static_transport_map(grid, gu_gdf, mode='subway', title="Seoul Subway Station Distribution & Grid Coverage (250m Grid)")
    plot_interactive_transport_map(grid, None, subway_gdf, gu_gdf, mode='subway', filename="seoul_subway_accessibility_interactive.html")
    
    # 3. Combined Map
    print("[SpatialAnalyzer] Generating Visualization 3: 버스 + 지하철 통합 실제 위치 오버레이 시각화...")
    plot_static_transport_map(grid, gu_gdf, mode='combined', title="Seoul Combined Transit Infrastructure Overlay (Bus + Subway)")
    plot_interactive_transport_map(grid, bus_gdf, subway_gdf, gu_gdf, mode='combined', filename="seoul_combined_vulnerability_interactive.html")

def plot_static_transport_map(grid: gpd.GeoDataFrame, gu_gdf: gpd.GeoDataFrame, mode: str, title: str):
    fig, ax = plt.subplots(figsize=(16, 14), facecolor="#111827")
    ax.set_facecolor("#111827")
    
    if mode == 'bus':
        out_png = os.path.join(MAPS_DIR, "seoul_bus_accessibility_static.png")
        mask_valid = grid['bus_count'] > 0
        grid[~mask_valid].plot(ax=ax, color='#1f2937', edgecolor='#374151', linewidth=0.2, alpha=0.5)
        grid[mask_valid].plot(ax=ax, column='bus_count', cmap='Blues', linewidth=0.2, edgecolor='#111827', legend=True,
                             legend_kwds={'label': 'Bus Stop Count per 250m Grid', 'shrink': 0.7})
    elif mode == 'subway':
        out_png = os.path.join(MAPS_DIR, "seoul_subway_accessibility_static.png")
        mask_valid = grid['subway_count'] > 0
        grid[~mask_valid].plot(ax=ax, color='#1f2937', edgecolor='#374151', linewidth=0.2, alpha=0.5)
        grid[mask_valid].plot(ax=ax, column='subway_count', cmap='Purples', linewidth=0.2, edgecolor='#111827', legend=True,
                             legend_kwds={'label': 'Subway Station Count per 250m Grid', 'shrink': 0.7})
    else:
        out_png = os.path.join(MAPS_DIR, "seoul_combined_vulnerability_static.png")
        color_map = {
            'Both (버스+지하철)': '#f59e0b',     # Gold / Yellow
            'Bus Only (버스만)': '#3b82f6',     # Blue
            'Subway Only (지하철만)': '#9333ea',  # Purple
            'Neither (미배치)': '#1f2937'        # Dark Gray
        }
        grid['color'] = grid['transit_cat'].map(color_map)
        grid.plot(ax=ax, color=grid['color'], linewidth=0.2, edgecolor='#111827', alpha=0.85)
        
        legend_patches = [
            mpatches.Patch(color='#f59e0b', label='Both Bus & Subway Grid (버스+지하철 모두 존재)'),
            mpatches.Patch(color='#3b82f6', label='Bus Only Grid (버스만 존재)'),
            mpatches.Patch(color='#9333ea', label='Subway Only Grid (지하철만 존재)'),
            mpatches.Patch(color='#1f2937', label='No Transit Grid (미배치 격자)')
        ]
        ax.legend(handles=legend_patches, loc='lower right', facecolor='#1f2937', edgecolor='none', 
                  labelcolor='white', fontsize=11)
    
    # Overlay Gu Boundaries
    if gu_gdf is not None:
        gu_gdf.plot(ax=ax, facecolor='none', edgecolor='#f9fafb', linewidth=1.2, linestyle='--')
        for _, row in gu_gdf.iterrows():
            c = row.geometry.centroid
            ax.annotate(row['gu_name'], xy=(c.x, c.y), color='#f3f4f6', fontsize=10, fontweight='bold', ha='center')
            
    ax.set_title(title, fontsize=16, fontweight='bold', color='white', pad=20)
    ax.set_xlabel("UTMK X (m)", color='#9ca3af', fontsize=12)
    ax.set_ylabel("UTMK Y (m)", color='#9ca3af', fontsize=12)
    ax.tick_params(colors='#9ca3af', labelsize=10)
    ax.grid(True, linestyle='--', alpha=0.2, color='#4b5563')
    
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SpatialAnalyzer] Static PNG ({mode}) saved to: {out_png}")

def plot_interactive_transport_map(grid: gpd.GeoDataFrame, bus_gdf, subway_gdf, gu_gdf, mode: str, filename: str):
    grid_wgs84 = grid.to_crs(epsg=4326)
    bounds = grid_wgs84.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles=None)
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Esri 위성 지도 (Satellite)'
    ).add_to(m)
    
    # 1. Autonomous District (Gu) Boundary Layer
    if gu_gdf is not None:
        gu_wgs84 = gu_gdf.to_crs(epsg=4326)
        fg_gu = folium.FeatureGroup(name='🏛️ 서울시 25개 자치구 경계', show=True)
        folium.GeoJson(
            gu_wgs84,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': '#ef4444',
                'weight': 2,
                'dashArray': '4, 4'
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['gu_name'],
                aliases=['자치구:']
            )
        ).add_to(fg_gu)
        fg_gu.add_to(m)
    
    if mode == 'bus':
        # Bus Grid Layer
        fg_grid = folium.FeatureGroup(name='🚌 버스 정류소 보유 격자', show=True)
        folium.GeoJson(
            grid_wgs84[grid_wgs84['bus_count'] > 0],
            style_function=lambda feat: {
                'fillColor': '#3b82f6',
                'color': '#1d4ed8',
                'weight': 0.5,
                'fillOpacity': 0.6
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['full_address', 'grid_code', 'bus_count', 'mean_pop'],
                aliases=['소속 행정구역:', '격자코드:', '버스정류장수:', '평균생활인구:']
            )
        ).add_to(fg_grid)
        fg_grid.add_to(m)
        
    elif mode == 'subway':
        # Subway Grid Layer
        fg_grid = folium.FeatureGroup(name='🚇 지하철역 보유 격자', show=True)
        folium.GeoJson(
            grid_wgs84[grid_wgs84['subway_count'] > 0],
            style_function=lambda feat: {
                'fillColor': '#8b5cf6',
                'color': '#6d28d9',
                'weight': 0.8,
                'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['full_address', 'grid_code', 'subway_count', 'mean_pop'],
                aliases=['소속 행정구역:', '격자코드:', '지하철역수:', '평균생활인구:']
            )
        ).add_to(fg_grid)
        fg_grid.add_to(m)
        
        if subway_gdf is not None:
            subway_wgs84 = subway_gdf.to_crs(epsg=4326)
            fg_sub_markers = folium.FeatureGroup(name='🚇 지하철 역사 위치 마커', show=True)
            for _, row in subway_wgs84.iterrows():
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5,
                    color='#6d28d9',
                    fill=True,
                    fill_color='#a78bfa',
                    fill_opacity=0.9,
                    popup=f"지하철역: {row.get('역사명', '')} ({row.get('호선', '')})"
                ).add_to(fg_sub_markers)
            fg_sub_markers.add_to(m)
        
    else:
        # Combined Actual Overlay Layer (버스 + 지하철 색상 구분 + 행정구역 표시)
        fg_both = folium.FeatureGroup(name='🟡 버스 + 지하철 둘 다 있는 격자', show=True)
        folium.GeoJson(
            grid_wgs84[grid_wgs84['transit_cat'] == 'Both (버스+지하철)'],
            style_function=lambda feat: {
                'fillColor': '#f59e0b',
                'color': '#d97706',
                'weight': 0.8,
                'fillOpacity': 0.75
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['full_address', 'grid_code', 'bus_count', 'subway_count', 'mean_pop'],
                aliases=['소속 행정구역:', '격자코드:', '버스정류장수:', '지하철역수:', '평균생활인구:']
            )
        ).add_to(fg_both)
        fg_both.add_to(m)

        fg_bus_only = folium.FeatureGroup(name='🔵 버스만 있는 격자', show=True)
        folium.GeoJson(
            grid_wgs84[grid_wgs84['transit_cat'] == 'Bus Only (버스만)'],
            style_function=lambda feat: {
                'fillColor': '#3b82f6',
                'color': '#1d4ed8',
                'weight': 0.5,
                'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['full_address', 'grid_code', 'bus_count', 'mean_pop'],
                aliases=['소속 행정구역:', '격자코드:', '버스정류장수:', '평균생활인구:']
            )
        ).add_to(fg_bus_only)
        fg_bus_only.add_to(m)

        fg_sub_only = folium.FeatureGroup(name='🟣 지하철만 있는 격자', show=True)
        folium.GeoJson(
            grid_wgs84[grid_wgs84['transit_cat'] == 'Subway Only (지하철만)'],
            style_function=lambda feat: {
                'fillColor': '#9333ea',
                'color': '#7e22ce',
                'weight': 0.8,
                'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['full_address', 'grid_code', 'subway_count', 'mean_pop'],
                aliases=['소속 행정구역:', '격자코드:', '지하철역수:', '평균생활인구:']
            )
        ).add_to(fg_sub_only)
        fg_sub_only.add_to(m)

        # Add Subway Markers to Combined Map
        if subway_gdf is not None:
            subway_wgs84 = subway_gdf.to_crs(epsg=4326)
            fg_sub_markers = folium.FeatureGroup(name='🚇 지하철 역사 위치 마커', show=True)
            for _, row in subway_wgs84.iterrows():
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5,
                    color='#581c87',
                    fill=True,
                    fill_color='#c084fc',
                    fill_opacity=0.9,
                    popup=f"지하철역: {row.get('역사명', '')} ({row.get('호선', '')})"
                ).add_to(fg_sub_markers)
            fg_sub_markers.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    
    out_html = os.path.join(MAPS_DIR, filename)
    m.save(out_html)
    print(f"[SpatialAnalyzer] Interactive HTML map ({mode}) saved to: {out_html}")
