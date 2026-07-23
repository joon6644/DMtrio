import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
from src.data_loader import load_seoul_boundary
from src.grid_generator import generate_250m_grid
from src.visualization import plot_static_grid, plot_interactive_grid
from src.spatial_analyzer import run_spatial_analysis_pipeline
from src.config import DATA_DIR

def main():
    print("===============================================================")
    print("  서울시 교통 소외지역 GIS 분석 & 250m 격자 공간 파이프라인  ")
    print("===============================================================")
    
    # 1. Load boundary & generate 250m snapped grid
    boundary_gdf = load_seoul_boundary()
    grid_gdf = generate_250m_grid(boundary_gdf)
    
    # 2. Render Autonomous District (Gu) color-coded 250m grid maps
    plot_static_grid(boundary_gdf, grid_gdf)
    plot_interactive_grid(boundary_gdf, grid_gdf)
    
    # 3. Run Spatial Join & 3-way Transport Visualizations
    run_spatial_analysis_pipeline(grid_gdf, DATA_DIR)
    
    print("\n[Complete] 파이프라인 수행 및 3종 시각화 지도 출력이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    main()
