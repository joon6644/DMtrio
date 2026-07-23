import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
from src.data_loader import load_seoul_boundary
from src.grid_generator import generate_250m_grid
from src.masked_grid_analyzer import analyze_and_visualize_masked_grids
from src.config import DATA_DIR

def main():
    print("=== 서울시 250m 격자 생활인구 마스킹(*) 시각화 파이프라인 ===")
    boundary = load_seoul_boundary()
    grid_gdf = generate_250m_grid(boundary)
    
    pop_csv = os.path.join(DATA_DIR, "250_LOCAL_RESD_20260719.csv")
    analyze_and_visualize_masked_grids(grid_gdf, pop_csv)
    print("=== 파이프라인 수행 완료 ===")

if __name__ == "__main__":
    main()
