import sys
import os

# Add project root directory to sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.patheffects import withStroke
import folium
import branca.colormap as cm

from src.config import PROCESSED_DATA_DIR, MAPS_DIR, TARGET_CRS, DATA_DIR
from src.data_loader import load_seoul_gu_boundaries, load_seoul_dong_boundaries, load_seoul_boundary
from src.grid_generator import generate_250m_grid

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

def attach_admin_info(grid_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Spatially joins Dong & Gu boundaries onto 250m grid cells so every cell
    is tagged with 'gu_name' and 'dong_name'.
    """
    dong_gdf = load_seoul_dong_boundaries()
    centroids = grid_gdf.copy()
    centroids['geometry'] = centroids.geometry.centroid
    
    grid_admin = gpd.sjoin_nearest(
        centroids[['grid_id', 'geometry']],
        dong_gdf[['gu_name', 'dong_name', 'geometry']],
        how='left'
    ).drop_duplicates(subset='grid_id')
    
    merged = grid_gdf.merge(grid_admin[['grid_id', 'gu_name', 'dong_name']], on='grid_id', how='left')
    merged['gu_name'] = merged['gu_name'].fillna('서울시')
    merged['dong_name'] = merged['dong_name'].fillna('')
    merged['full_address'] = "서울특별시 " + merged['gu_name'] + " " + merged['dong_name']
    return merged

def analyze_and_visualize_masked_grids(grid_gdf: gpd.GeoDataFrame, csv_path: str):
    """
    Analyzes population masking ('*' for <= 3 people) and population counts across Seoul 250m grid cells.
    Visualizes masked & missing info grids in Dark Gray, and valid population grids in Green gradient (진한~옅은 초록색).
    """
    print("[MaskedGridAnalyzer] Loading population CSV dataset...")
    pop_df = pd.read_csv(csv_path, encoding='cp949')
    
    # Identify star values ('*')
    pop_df['is_star'] = (pop_df['생활인구합계'] == '*')
    pop_df['pop_num'] = pd.to_numeric(pop_df['생활인구합계'], errors='coerce')
    
    # Aggregate per grid code over 24 hours
    grid_stats = pop_df.groupby('250M격자').agg(
        star_hours=('is_star', 'sum'),
        mean_pop=('pop_num', 'mean'),
        max_pop=('pop_num', 'max')
    ).reset_index()
    
    # 24h Star -> Mean Pop is NaN (Masked/Uncounted)
    grid_stats.loc[grid_stats['star_hours'] == 24, 'mean_pop'] = np.nan
    
    # Attach Administrative Info (Gu & Dong)
    grid_admin_gdf = attach_admin_info(grid_gdf)
    
    # Merge with spatial grid
    merged = grid_admin_gdf.merge(grid_stats, left_on='grid_code', right_on='250M격자', how='left')
    
    # Categorize grid status
    def categorize_mask(row):
        if pd.isna(row['mean_pop']):
            if row['star_hours'] == 24:
                return '상시 마스킹 (24시간 3인이하 *)'
            else:
                return '미집계/미정보 (산지/수역/공백)'
        else:
            return '정상 집계 (생활인구 분포)'
            
    merged['status_cat'] = merged.apply(categorize_mask, axis=1)
    merged['is_masked_or_missing'] = merged['mean_pop'].isna()
    
    # Display statistics
    print("\n--- 서울시 250m 격자 생활인구 마스킹 및 분포 통계 ---")
    total_cells = len(merged)
    masked_cells = (merged['star_hours'] == 24).sum()
    missing_cells = merged['250M격자'].isna().sum()
    valid_cells = merged['mean_pop'].notna().sum()
    
    print(f"- 24시간 상시 마스킹 (Always Masked): {masked_cells:,} 개 셀")
    print(f"- 미집계/미정보 (Uncounted/Missing):  {missing_cells:,} 개 셀")
    print(f"- 생활인구 집계 (Populated Cells):     {valid_cells:,} 개 셀")
    print(f"- 총 250m 격자 셀:                    {total_cells:,} 개 셀\n")
    
    # Save processed GeoJSON
    out_geojson = os.path.join(PROCESSED_DATA_DIR, "seoul_masked_grid_250m.geojson")
    merged.to_file(out_geojson, driver="GeoJSON")
    print(f"[MaskedGridAnalyzer] Saved GeoJSON to: {out_geojson}")
    
    # 1. Static Visualization (Matplotlib PNG)
    plot_static_masked_map(merged)
    
    # 2. Interactive Visualization (Folium HTML)
    plot_interactive_masked_map(merged)

def plot_static_masked_map(gdf: gpd.GeoDataFrame):
    """
    Renders Static PNG Map:
    - Masked/Missing Grids: Dark Gray (#1f2937 / #111827)
    - Valid Population Grids: Green Gradient (YlGn cmap: 옅은 초록 -> 진한 초록)
    """
    fig, ax = plt.subplots(figsize=(16, 14), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")
    
    gu_gdf = load_seoul_gu_boundaries()
    
    # Separate masked/missing vs valid pop
    masked_gdf = gdf[gdf['is_masked_or_missing']]
    valid_gdf = gdf[~gdf['is_masked_or_missing']].copy()
    
    # 1. Plot Masked & Missing Grids (Dark Gray)
    masked_gdf.plot(
        ax=ax,
        color='#1e293b',
        edgecolor='#334155',
        linewidth=0.2,
        alpha=0.6
    )
    
    # 2. Plot Valid Population Grids (Green Gradient)
    norm = mcolors.LogNorm(vmin=max(1, valid_gdf['mean_pop'].min()), vmax=valid_gdf['mean_pop'].max())
    valid_plot = valid_gdf.plot(
        ax=ax,
        column='mean_pop',
        cmap='YlGn',
        norm=norm,
        linewidth=0.2,
        edgecolor='#0f172a',
        legend=True,
        legend_kwds={
            'label': '평균 생활인구수 (명 / 250m 격자 - Log Scale)',
            'shrink': 0.65,
            'orientation': 'horizontal',
            'pad': 0.04
        }
    )
    
    # Overlay Gu Boundaries
    if gu_gdf is not None:
        gu_gdf.plot(ax=ax, facecolor='none', edgecolor='#ffffff', linewidth=1.2, linestyle='--')
        for _, row in gu_gdf.iterrows():
            c = row.geometry.centroid
            txt = ax.annotate(
                row['gu_name'], xy=(c.x, c.y), color='white',
                fontsize=10, fontweight='bold', ha='center', va='center'
            )
            txt.set_path_effects([withStroke(linewidth=2.5, foreground='#0f172a')])
            
    ax.set_title("서울시 250m 격자 생활인구수 분포 및 마스킹/미정보 현황 지도", 
                 fontsize=16, fontweight='bold', color='white', pad=22)
    ax.set_xlabel("UTMK X (m)", color='#9ca3af', fontsize=11)
    ax.set_ylabel("UTMK Y (m)", color='#9ca3af', fontsize=11)
    ax.tick_params(colors='#9ca3af', labelsize=9)
    ax.grid(True, linestyle='--', alpha=0.2, color='#4b5563')
    
    # Legend patch for Masked/Missing
    legend_patch = mpatches.Patch(color='#1e293b', edgecolor='#334155', label='마스킹(*) 및 미정보 구간 (어두운 회색)')
    ax.legend(handles=[legend_patch], loc='lower right', facecolor='#1e293b', edgecolor='none', 
              labelcolor='white', fontsize=10)
    
    out_png = os.path.join(MAPS_DIR, "seoul_masked_grid_static.png")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[MaskedGridAnalyzer] Static PNG map saved to: {out_png}")

def plot_interactive_masked_map(gdf: gpd.GeoDataFrame):
    """
    Renders Interactive Folium HTML Map:
    - Masked/Missing Grids: Dark Slate (#1e293b)
    - Valid Population Grids: Green Gradient (Light Green -> Dark Green)
    """
    gdf_wgs84 = gdf.to_crs(epsg=4326)
    gu_gdf = load_seoul_gu_boundaries()
    
    bounds = gdf_wgs84.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles=None
    )
    
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
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
        
    # Create Green Colormap for Valid Population
    valid_pop_series = gdf_wgs84['mean_pop'].dropna()
    min_pop = float(valid_pop_series.min()) if len(valid_pop_series) > 0 else 0.0
    max_pop = float(valid_pop_series.quantile(0.98)) if len(valid_pop_series) > 0 else 5000.0
    
    # Branca Green Linear Colormap
    green_cmap = cm.LinearColormap(
        colors=['#dcfce7', '#86efac', '#22c55e', '#15803d', '#064e3b'],
        vmin=min_pop,
        vmax=max_pop,
        caption='평균 생활인구수 (명 / 250m 격자)'
    )
    green_cmap.add_to(m)
    
    # 2. Masked & Missing Info Grids (Dark Gray)
    masked_gdf = gdf_wgs84[gdf_wgs84['is_masked_or_missing']]
    fg_masked = folium.FeatureGroup(name='⬛ 마스킹 & 미정보 구간 (어두운 영역)', show=True)
    folium.GeoJson(
        masked_gdf,
        style_function=lambda feat: {
            'fillColor': '#1e293b',
            'color': '#334155',
            'weight': 0.4,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['full_address', 'grid_code', 'status_cat'],
            aliases=['소속 행정구역:', '격자코드:', '구분:']
        )
    ).add_to(fg_masked)
    fg_masked.add_to(m)
    
    # 3. Valid Population Grids (Green Gradient)
    valid_gdf = gdf_wgs84[~gdf_wgs84['is_masked_or_missing']].copy()
    valid_gdf['pop_formatted'] = valid_gdf['mean_pop'].apply(lambda v: f"{v:,.1f} 명" if pd.notna(v) else "미집계")
    
    fg_valid = folium.FeatureGroup(name='🟢 생활인구수 분포 (초록색 옅은~진한)', show=True)
    folium.GeoJson(
        valid_gdf,
        style_function=lambda feat: {
            'fillColor': green_cmap(feat['properties']['mean_pop']),
            'color': green_cmap(feat['properties']['mean_pop']),
            'weight': 0.3,
            'fillOpacity': 0.75
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['full_address', 'grid_code', 'pop_formatted'],
            aliases=['소속 행정구역:', '격자코드:', '평균 생활인구수:']
        )
    ).add_to(fg_valid)
    fg_valid.add_to(m)
    
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Title Banner HTML overlay
    title_html = f'''
    <div style="position: fixed; top: 15px; left: 50px; width: 440px; height: 80px; 
                z-index:9999; background-color: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px);
                border: 1px solid #334155; border-radius: 8px; padding: 10px 15px; color: white;">
        <h4 style="margin: 0 0 4px 0; color: #4ade80; font-family: sans-serif; font-size: 15px; font-weight: bold;">
            👥 서울시 250m 격자 생활인구수 지도
        </h4>
        <p style="margin: 0; color: #cbd5e1; font-family: sans-serif; font-size: 11px; line-height: 1.4;">
            <b>어두운 회색</b>: 마스킹(*) & 미정보 구간 | <b>초록색 계열</b>: 생활인구수 (옅은~진한)<br>
            각 격자 셀 마우스 호버 시 [행정구역] 및 [평균 인구수] 즉시 확인
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    out_html = os.path.join(MAPS_DIR, "seoul_masked_grid_interactive.html")
    m.save(out_html)
    print(f"[MaskedGridAnalyzer] Interactive HTML map saved to: {out_html}")

if __name__ == "__main__":
    boundary = load_seoul_boundary()
    grid_gdf = generate_250m_grid(boundary)
    pop_csv = os.path.join(DATA_DIR, "250_LOCAL_RESD_20260719.csv")
    analyze_and_visualize_masked_grids(grid_gdf, pop_csv)
