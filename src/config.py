from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "seoul_boundary"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"
MAPS_DIR = OUTPUT_DIR / "maps"
REPORTS_DIR = OUTPUT_DIR / "reports"

# Ensure output directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# GIS Configuration
TARGET_CRS = "EPSG:5179"  # Korea Modified Central Belt / UTMK (ITRF2000)
GRID_SIZE_METERS = 250   # 250m x 250m regular spatial grid

# File Names
SEOUL_RAW_SHP = RAW_DATA_DIR / "admstr_zone_lgldong_bndry_24.shp"
SEOUL_BOUNDARY_GEOJSON = PROCESSED_DATA_DIR / "seoul_boundary_5179.geojson"
SEOUL_GRID_GEOJSON = PROCESSED_DATA_DIR / "seoul_grid_250m.geojson"

STATIC_MAP_PNG = MAPS_DIR / "seoul_250m_grid_static.png"
INTERACTIVE_MAP_HTML = MAPS_DIR / "seoul_250m_grid_interactive.html"
