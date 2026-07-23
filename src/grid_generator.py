import math
import geopandas as gpd
from shapely.geometry import box
from src.config import TARGET_CRS, GRID_SIZE_METERS

def generate_250m_grid(seoul_boundary_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Generates a regular 250m x 250m spatial grid snapped to the official
    Korean National Spatial Grid (국토통계 250m 격자) system in EPSG:5179.
    
    Grid code format: '다사' + (X_min-900000)//10 + (Y_min-1900000)//10
    """
    # Ensure boundary is in target CRS
    if seoul_boundary_gdf.crs.to_string() != TARGET_CRS:
        seoul_boundary_gdf = seoul_boundary_gdf.to_crs(TARGET_CRS)
    
    # Get unified boundary polygon
    seoul_geom = seoul_boundary_gdf.geometry.union_all()
    minx, miny, maxx, maxy = seoul_geom.bounds
    
    # Snap bounding box to 250m multiples
    start_x = math.floor((minx - 900000) / GRID_SIZE_METERS) * GRID_SIZE_METERS + 900000
    end_x = math.ceil((maxx - 900000) / GRID_SIZE_METERS) * GRID_SIZE_METERS + 900000
    start_y = math.floor((miny - 1900000) / GRID_SIZE_METERS) * GRID_SIZE_METERS + 1900000
    end_y = math.ceil((maxy - 1900000) / GRID_SIZE_METERS) * GRID_SIZE_METERS + 1900000
    
    grid_polys = []
    grid_codes = []
    centers_x = []
    centers_y = []
    
    curr_x = start_x
    while curr_x < end_x:
        curr_y = start_y
        while curr_y < end_y:
            b = box(curr_x, curr_y, curr_x + GRID_SIZE_METERS, curr_y + GRID_SIZE_METERS)
            if seoul_geom.intersects(b):
                x_off = int(round(curr_x - 900000)) // 10
                y_off = int(round(curr_y - 1900000)) // 10
                code = f"다사{x_off:04d}{y_off:04d}"
                
                grid_polys.append(b)
                grid_codes.append(code)
                centers_x.append(curr_x + GRID_SIZE_METERS / 2.0)
                centers_y.append(curr_y + GRID_SIZE_METERS / 2.0)
            curr_y += GRID_SIZE_METERS
        curr_x += GRID_SIZE_METERS
    
    grid_gdf = gpd.GeoDataFrame({
        "grid_id": [f"GRID_{i+1:05d}" for i in range(len(grid_polys))],
        "grid_code": grid_codes,
        "center_x": centers_x,
        "center_y": centers_y,
        "area_m2": [GRID_SIZE_METERS * GRID_SIZE_METERS] * len(grid_polys)
    }, geometry=grid_polys, crs=TARGET_CRS)
    
    print(f"[GridGenerator] Successfully generated {len(grid_gdf)} snapped 250m grid cells with National Grid Codes.")
    return grid_gdf
