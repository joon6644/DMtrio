import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
from src.data_loader import load_seoul_boundary
from src.grid_generator import generate_250m_grid
from src.spatial_analyzer import run_spatial_analysis_pipeline
from src.config import DATA_DIR

def main():
    print("=== 서울시 250m 격자 교통 불균형 및 소외지역 종합 GIS 분석 파이프라인 ===")
    
    # 1. Load boundary & generate 250m snapped grid
    boundary_gdf = load_seoul_boundary()
    grid_gdf = generate_250m_grid(boundary_gdf)
    
    # 2. Run Spatial Analysis Pipeline (Bus, Subway, Combined)
    run_spatial_analysis_pipeline(grid_gdf, DATA_DIR)
    
    print("\n=== 전체 분석 및 3종 시각화 지도 생성 완료! ===")

if __name__ == "__main__":
    main()
