# 서울시 교통 소외지역 GIS 분석 프로젝트 (Seoul Transportation Vulnerability GIS Analysis)

본 연구 프로젝트는 서울특별시 내 **교통 불균형 지역 시각화 및 교통 소외지역 도출**을 위한 공간 데이터 분석 체계입니다.
모든 공간 데이터의 좌표계는 **EPSG:5179 (ITRF2000 / UTK)**로 통일되며, 250m × 250m 공간 정방격자를 기반으로 대중교통 접근성 및 이동성 분석을 수행합니다.

---

## 📁 프로젝트 구조 (Directory Structure)

```
c:\Workspace\MD트리오\
├── data/
│   ├── seoul_boundary/               # 원천 서울시 경계 Shapefile (EPSG:5186)
│   └── processed/                    # 전처리 완료 공간 데이터 (EPSG:5179)
│       ├── seoul_boundary_5179.geojson  # 서울시 통합 경계 GeoJSON
│       └── seoul_grid_250m.geojson      # 250m x 250m 정방형 공간 격자 GeoJSON
│
├── src/
│   ├── config.py                     # 글로벌 설정 (EPSG:5179, 250m, 경로)
│   ├── data_loader.py                # 데이터 로드 및 좌표계 재투영 모듈
│   ├── grid_generator.py             # 250m 격자 생성 및 Spatial Intersection 연산
│   └── visualization.py              # Matplotlib 정적 / Folium 대화형 시각화 모듈
│
├── notebooks/
│   └── 01_grid_generation_and_visualization.ipynb # 인터랙티브 분석 노트북
│
├── outputs/
│   ├── maps/                         # 생성된 시각화 지도 파일 저장소
│   │   ├── seoul_250m_grid_static.png     # 정적 PNG 이미지 지도
│   │   └── seoul_250m_grid_interactive.html # 대화형 HTML 웹 지도
│   └── reports/                      # 분석 보고서
│
├── main.py                           # 파이프라인 일괄 실행 메인 스크립트
├── requirements.txt                  # 파이썬 의존성 패키지 목록
└── README.md                         # 프로젝트 설명서
```

---

## 🛠️ 환경 구축 및 실행 방법 (Usage)

### 1. 가상환경 및 패키지 설치
```powershell
# 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt
```

### 2. 파이프라인 일괄 실행 (250m 격자 생성 & 시각화)
```powershell
python main.py
```

---

## 📊 격자 데이터 사양 (Grid Specification)
- **표준 좌표계**: `EPSG:5179` (Korea 2000 / Central Belt 2010 - UTMK)
- **격자 셀 크기**: 250m × 250m (셀당 면적: 62,500 m²)
- **생성 격자 수**: 약 10,750 여 개 (서울시 전체 공간 커버리지)
- **속성 데이터**: `grid_id`, `col_idx`, `row_idx`, `center_x`, `center_y`, `area_sqm`
