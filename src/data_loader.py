import os
import geopandas as gpd
from src.config import SEOUL_RAW_SHP, SEOUL_BOUNDARY_GEOJSON, PROCESSED_DATA_DIR, TARGET_CRS

SEOUL_GU_DICT = {
    '11110': '종로구', '11140': '중구', '11170': '용산구', '11200': '성동구', '11215': '광진구',
    '11230': '동대문구', '11260': '중랑구', '11290': '성북구', '11305': '강북구', '11320': '도봉구',
    '11350': '노원구', '11380': '은평구', '11410': '서대문구', '11440': '마포구', '11470': '양천구',
    '11500': '강서구', '11530': '구로구', '11545': '금천구', '11560': '영등포구', '11590': '동작구',
    '11620': '관악구', '11650': '서초구', '11680': '강남구', '11710': '송파구', '11740': '강동구'
}

def load_seoul_boundary() -> gpd.GeoDataFrame:
    """
    Loads raw Seoul legal dong shapefile, reprojects to EPSG:5179,
    assigns Gu and Dong names, and exports unified boundary as well as 25 Gu boundaries.
    """
    if not os.path.exists(SEOUL_RAW_SHP):
        raise FileNotFoundError(f"Raw shapefile not found at: {SEOUL_RAW_SHP}")
    
    print(f"[DataLoader] Loading raw dong shapefile from: {SEOUL_RAW_SHP}")
    dong_gdf = gpd.read_file(SEOUL_RAW_SHP, encoding='cp949')
    
    if dong_gdf.crs.to_string() != TARGET_CRS:
        print(f"[DataLoader] Reprojecting CRS from {dong_gdf.crs} to {TARGET_CRS}...")
        dong_gdf = dong_gdf.to_crs(TARGET_CRS)
        
    dong_gdf['gu_code'] = dong_gdf['EMD_CD'].str[:5]
    dong_gdf['gu_name'] = dong_gdf['gu_code'].map(SEOUL_GU_DICT)
    dong_gdf['dong_name'] = dong_gdf['EMD_NM']
    
    # Save Dong Boundaries GeoJSON
    dong_path = os.path.join(PROCESSED_DATA_DIR, "seoul_dongs_5179.geojson")
    dong_gdf.to_file(dong_path, driver="GeoJSON")
    
    # Dissolve to 25 Gu Boundaries GeoJSON
    gu_gdf = dong_gdf.dissolve(by='gu_name').reset_index()
    gu_path = os.path.join(PROCESSED_DATA_DIR, "seoul_gu_boundaries_5179.geojson")
    gu_gdf.to_file(gu_path, driver="GeoJSON")
    print(f"[DataLoader] Saved 25 Gu Boundaries to: {gu_path}")
    
    # Dissolve to Unified Seoul Boundary GeoJSON
    seoul_gdf = dong_gdf.dissolve().reset_index()
    seoul_gdf['city_name'] = "서울특별시"
    seoul_gdf.to_file(SEOUL_BOUNDARY_GEOJSON, driver="GeoJSON")
    print(f"[DataLoader] Saved unified Seoul Boundary to: {SEOUL_BOUNDARY_GEOJSON}")
    
    return seoul_gdf

def load_seoul_gu_boundaries() -> gpd.GeoDataFrame:
    """Returns GeoDataFrame of 25 Autonomous Districts (Gu) in EPSG:5179."""
    gu_path = os.path.join(PROCESSED_DATA_DIR, "seoul_gu_boundaries_5179.geojson")
    if not os.path.exists(gu_path):
        load_seoul_boundary()
    return gpd.read_file(gu_path)

def load_seoul_dong_boundaries() -> gpd.GeoDataFrame:
    """Returns GeoDataFrame of 467 Legal Dongs in EPSG:5179."""
    dong_path = os.path.join(PROCESSED_DATA_DIR, "seoul_dongs_5179.geojson")
    if not os.path.exists(dong_path):
        load_seoul_boundary()
    return gpd.read_file(dong_path)
