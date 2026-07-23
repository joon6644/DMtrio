import sys
import os

# Add project root directory to sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patheffects import withStroke
from pathlib import Path
import folium
from src import config
from src.data_loader import load_seoul_gu_boundaries, load_seoul_dong_boundaries

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configure Matplotlib fonts & aesthetics
plt.rcParams["font.sans-serif"] = ["Malgun Gothic", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# Vibrant 25 Autonomous District Color Palette
SEOUL_GU_COLORS = {
    '강남구': '#2563eb', '강동구': '#dc2626', '강북구': '#059669', '강서구': '#d97706',
    '관악구': '#7c3aed', '광진구': '#db2777', '구로구': '#0891b2', '금천구': '#65a30d',
    '노원구': '#ea580c', '도봉구': '#0d9488', '동대문구': '#9333ea', '동작구': '#4f46e5',
    '마포구': '#ca8a04', '서대문구': '#0284c7', '서초구': '#1d4ed8', '성동구': '#b45309',
    '성북구': '#047857', '송파구': '#b91c1c', '양천구': '#6b21a8', '영등포구': '#be185d',
    '용산구': '#0369a1', '은평구': '#4d7c0f', '종로구': '#be123c', '중구': '#7e22ce',
    '중랑구': '#e11d48'
}


def attach_admin_boundaries(grid_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Spatially joins Dong & Gu boundaries onto every 250m grid cell so that 100% of cells
    are tagged with 'gu_name' and 'dong_name'.
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


def plot_static_grid(
    boundary_gdf: gpd.GeoDataFrame,
    grid_gdf: gpd.GeoDataFrame,
    output_path: Path = config.STATIC_MAP_PNG
) -> Path:
    """
    Renders a high-resolution static PNG map of Seoul 250m grid colored by 25 Autonomous Districts (Gu).
    """
    logger.info("Generating static PNG grid map differentiated by Autonomous Districts (Gu)...")
    
    # 1. Attach Gu & Dong names to Grid
    grid_gdf = attach_admin_boundaries(grid_gdf)
    gu_gdf = load_seoul_gu_boundaries()
    
    # 2. Map District Colors
    grid_gdf['gu_color'] = grid_gdf['gu_name'].map(SEOUL_GU_COLORS).fillna('#334155')
    
    fig, ax = plt.subplots(figsize=(16, 13), dpi=300)
    fig.patch.set_facecolor('#0f172a')  # Dark slate background
    ax.set_facecolor('#0f172a')
    
    # 3. Plot 250m Grid cells colored by Gu
    grid_gdf.plot(
        ax=ax,
        color=grid_gdf['gu_color'],
        edgecolor='#0f172a',
        linewidth=0.25,
        alpha=0.85
    )
    
    # 4. Overlay Autonomous District (Gu) Outlines
    gu_gdf.plot(
        ax=ax,
        facecolor='none',
        edgecolor='#ffffff',
        linewidth=1.2,
        linestyle='--'
    )
    
    # 5. Label District Names at Centroids
    for _, row in gu_gdf.iterrows():
        c = row.geometry.centroid
        txt = ax.annotate(
            row['gu_name'],
            xy=(c.x, c.y),
            color='white',
            fontsize=10,
            fontweight='bold',
            ha='center',
            va='center'
        )
        txt.set_path_effects([withStroke(linewidth=2.5, foreground='#0f172a')])
        
    # Map Annotations & Titles
    ax.set_title(
        "서울시 자치구별 250m 미세 격자망 공간 시각화 (25개 자치구 구분)",
        fontsize=18,
        color='#f8fafc',
        pad=22,
        fontweight='bold'
    )
    
    cell_count = len(grid_gdf)
    total_area_sqkm = round(grid_gdf.geometry.area.sum() / 1e6, 2)
    subtitle_text = f"총 격자 수: {cell_count:,}개  |  25개 자치구 & 467개 법정동 공간 결합 완료  |  분석 면적: {total_area_sqkm:,} km²"
    ax.text(
        0.5, 1.015, subtitle_text,
        transform=ax.transAxes,
        ha='center', va='bottom',
        fontsize=11, color='#cbd5e1'
    )
    
    ax.set_xlabel("UTMK X 좌표 (m) - EPSG:5179", color='#cbd5e1', fontsize=10, labelpad=8)
    ax.set_ylabel("UTMK Y 좌표 (m) - EPSG:5179", color='#cbd5e1', fontsize=10, labelpad=8)
    
    ax.tick_params(colors='#94a3b8', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#334155')
        
    ax.grid(True, color='#1e293b', linestyle='--', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    
    logger.info(f"Static PNG map (differentiated by Gu) saved to: {output_path}")
    return output_path


def plot_interactive_grid(
    boundary_gdf: gpd.GeoDataFrame,
    grid_gdf: gpd.GeoDataFrame,
    output_path: Path = config.INTERACTIVE_MAP_HTML
) -> Path:
    """
    Renders an interactive Folium HTML map with 250m Grid colored by Autonomous Districts (Gu).
    """
    logger.info("Generating interactive HTML grid map differentiated by Gu with Folium...")
    
    # Attach Gu & Dong names
    grid_gdf = attach_admin_boundaries(grid_gdf)
    gu_gdf = load_seoul_gu_boundaries()
    
    # Reproject to EPSG:4326 for Folium rendering
    grid_4326 = grid_gdf.to_crs("EPSG:4326")
    gu_4326 = gu_gdf.to_crs("EPSG:4326")
    
    bounds = grid_4326.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles=None,
        control_scale=True
    )
    
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Esri 위성 지도 (Satellite)'
    ).add_to(m)
    
    # 1. Seoul 25 Gu Boundary Layer
    bnd_group = folium.FeatureGroup(name='🏛️ 서울시 25개 자치구 경계', show=True)
    folium.GeoJson(
        gu_4326,
        style_function=lambda x: {
            'fillColor': 'transparent',
            'color': '#ef4444',
            'weight': 2.5,
            'dashArray': '4, 4'
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['gu_name'],
            aliases=['자치구:']
        )
    ).add_to(bnd_group)
    bnd_group.add_to(m)
    
    # 2. 250m Grid Layer (Color-coded by Gu)
    grid_group = folium.FeatureGroup(name='🗺️ 250m 격자망 (자치구별 색상 구분)', show=True)
    
    def grid_style(feat):
        gu = feat['properties'].get('gu_name', '서울시')
        color = SEOUL_GU_COLORS.get(gu, '#0284c7')
        return {
            'fillColor': color,
            'color': color,
            'weight': 0.4,
            'fillOpacity': 0.45
        }
        
    def grid_highlight(feat):
        return {
            'fillColor': '#f59e0b',
            'color': '#ffffff',
            'weight': 2,
            'fillOpacity': 0.8
        }
        
    folium.GeoJson(
        grid_4326,
        style_function=grid_style,
        highlight_function=grid_highlight,
        tooltip=folium.GeoJsonTooltip(
            fields=['full_address', 'grid_code', 'grid_id'],
            aliases=['소속 행정구역:', '국가격자코드:', '격자 ID:'],
            localize=True,
            sticky=True
        ),
        popup=folium.GeoJsonPopup(
            fields=['full_address', 'gu_name', 'dong_name', 'grid_code', 'center_x', 'center_y'],
            aliases=['행정구역 전체:', '자치구:', '법정동:', '국가격자코드:', 'UTMK X(m):', 'UTMK Y(m):'],
            labels=True
        )
    ).add_to(grid_group)
    grid_group.add_to(m)
    
    # Add Layer Control
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Title Banner HTML overlay
    title_html = f'''
    <div style="position: fixed; top: 15px; left: 50px; width: 440px; height: 80px; 
                z-index:9999; background-color: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px);
                border: 1px solid #334155; border-radius: 8px; padding: 10px 15px; color: white;">
        <h4 style="margin: 0 0 4px 0; color: #38bdf8; font-family: sans-serif; font-size: 15px; font-weight: bold;">
            🗺️ 서울시 자치구별 250m 공간 격자 지도
        </h4>
        <p style="margin: 0; color: #cbd5e1; font-family: sans-serif; font-size: 11px; line-height: 1.4;">
            총 격자 수: <b>{len(grid_gdf):,}개</b> | 자치구: <b>25개 구 구분</b><br>
            각 격자 클릭 시 [자치구] 및 [법정동] 소속 정보 확인 가능
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    logger.info(f"Interactive HTML map (differentiated by Gu) saved to: {output_path}")
    return output_path
