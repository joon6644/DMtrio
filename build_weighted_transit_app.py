import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.config import MAPS_DIR
from src.export_interactive_data import prepare_and_export_interactive_data

def generate_weighted_transit_html():
    """
    Generates a dedicated web application for the Mode-Weighted Transit Mobility Model
    with Scale Normalization (0~1) to eliminate scale imbalance (Bus ~16.56 vs Subway ~3.78):
    
    Normalized Mobility = w_bus * (BusScore / MaxBus) + w_subway * (SubwayScore / MaxSubway)
    """
    js_data_path = os.path.join(MAPS_DIR, "grid_data.js")
    if not os.path.exists(js_data_path):
        prepare_and_export_interactive_data()
        
    out_html = os.path.join(MAPS_DIR, "weighted_transit_accessibility_map.html")
    
    html_code = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>서울시 0.544 버스 + 0.456 지하철 정규화 가중 대중교통 접근성 지도</title>
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- Load Spatial Data Payload -->
    <script src="grid_data.js"></script>
    
    <style>
        :root {
            --bg-dark: #0b0f19;
            --panel-bg: rgba(15, 23, 42, 0.95);
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-amber: #f59e0b;
            --accent-pink: #ec4899;
            --accent-emerald: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Pretendard', -apple-system, sans-serif; }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            background: #0f172a;
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
            height: 60px;
        }

        header h1 {
            font-size: 1.18rem;
            font-weight: 700;
            background: linear-gradient(90deg, #38bdf8, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        header .header-stats {
            display: flex;
            gap: 16px;
            font-size: 0.83rem;
        }

        header .stat-item {
            display: flex;
            align-items: center;
            gap: 5px;
            color: var(--text-muted);
        }

        header .stat-item span.val {
            color: #38bdf8;
            font-weight: 700;
        }

        .main-container {
            display: flex;
            flex: 1;
            position: relative;
            height: calc(100vh - 60px);
        }

        /* Sidebar Controls */
        .sidebar {
            width: 420px;
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border-right: 1px solid var(--border-color);
            padding: 18px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
            z-index: 1000;
            box-shadow: 5px 0 25px rgba(0,0,0,0.5);
        }

        .section-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #f1f5f9;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .control-group label {
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
        }

        .control-group label span.val {
            color: #38bdf8;
            font-weight: 700;
        }

        input[type="range"] {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #334155;
            outline: none;
            accent-color: var(--accent-blue);
            cursor: pointer;
        }

        select {
            background: #0f172a;
            color: var(--text-main);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 0.85rem;
            outline: none;
        }

        .checkbox-container {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(236, 72, 153, 0.1);
            border: 1px solid rgba(236, 72, 153, 0.3);
            padding: 9px 12px;
            border-radius: 8px;
            cursor: pointer;
            user-select: none;
        }

        .checkbox-container input {
            width: 16px;
            height: 16px;
            accent-color: var(--accent-pink);
            cursor: pointer;
        }

        .checkbox-container span {
            font-size: 0.83rem;
            font-weight: 700;
            color: #f472b6;
        }

        /* Map Container */
        #map {
            flex: 1;
            height: 100%;
            background: #0b0f19;
            z-index: 1;
        }

        /* Floating Info Box on Map */
        .info-panel {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(15, 23, 42, 0.96);
            backdrop-filter: blur(14px);
            border: 1.5px solid var(--border-color);
            border-radius: 12px;
            padding: 14px 16px;
            width: 385px;
            max-height: calc(100vh - 120px);
            overflow-y: auto;
            z-index: 999;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            font-size: 0.86rem;
            transition: border-color 0.2s ease;
        }

        .info-panel.pinned {
            border-color: #f59e0b;
        }

        .info-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
            margin-bottom: 8px;
        }

        .info-panel-header h3 {
            font-size: 0.95rem;
            color: #38bdf8;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .close-btn {
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #94a3b8;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
        }

        .close-btn:hover {
            background: #ef4444;
            color: #ffffff;
        }

        .toggle-info-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid var(--border-color);
            color: #38bdf8;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 700;
            cursor: pointer;
            z-index: 998;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            display: none;
        }

        .toggle-info-btn:hover {
            background: #1e293b;
            color: #60a5fa;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }

        .info-row label { color: var(--text-muted); }
        .info-row span { font-weight: 600; }

        .mask-badge {
            display: inline-block;
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .rank-badge {
            display: inline-block;
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.4);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .vuln-badge {
            display: inline-block;
            background: rgba(236, 72, 153, 0.2);
            color: #f472b6;
            border: 1px solid rgba(236, 72, 153, 0.4);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .pin-badge {
            display: inline-block;
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.4);
            padding: 2px 7px;
            border-radius: 5px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-left: 6px;
        }

        /* Formula Breakdown Box */
        .breakdown-box {
            background: rgba(15, 23, 42, 0.85);
            border: 1px dashed rgba(56, 189, 248, 0.4);
            border-radius: 8px;
            padding: 10px 12px;
            margin-top: 8px;
            font-size: 0.79rem;
        }

        .breakdown-box h4 {
            color: #38bdf8;
            font-size: 0.83rem;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .breakdown-item {
            background: rgba(30, 41, 59, 0.6);
            border-left: 3.5px solid var(--accent-blue);
            padding: 6px 9px;
            border-radius: 4px;
            margin-bottom: 6px;
        }

        .breakdown-item.subway {
            border-left-color: var(--accent-purple);
        }

        .breakdown-item.weight {
            border-left-color: var(--accent-amber);
        }

        .breakdown-item .title {
            font-weight: 700;
            color: #f8fafc;
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
        }

        .breakdown-item .formula {
            color: #94a3b8;
            font-family: monospace;
            font-size: 0.74rem;
            line-height: 1.35;
        }

        .breakdown-item .highlight {
            color: #f59e0b;
            font-weight: 700;
        }

        /* Map Legend */
        .map-legend {
            position: absolute;
            bottom: 30px;
            right: 20px;
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
            z-index: 999;
            font-size: 0.8rem;
        }

        .legend-gradient {
            height: 12px;
            width: 240px;
            border-radius: 6px;
            margin: 6px 0;
        }

        .legend-labels {
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
        }

        .legend-extra-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .legend-masked-color {
            width: 14px;
            height: 14px;
            background: #0d1f19;
            border: 1px solid #132c24;
            border-radius: 3px;
        }

        .legend-vuln-color {
            width: 14px;
            height: 14px;
            background: rgba(236, 72, 153, 0.5);
            border: 2px solid #ec4899;
            border-radius: 3px;
        }

        .chart-box {
            height: 130px;
            width: 100%;
            margin-top: 6px;
        }
    </style>
</head>
<body>

    <header>
        <h1>🚌🚇 서울시 0.544 버스 + 0.456 지하철 정규화 가중 접근성 지도</h1>
        <div class="header-stats">
            <div class="stat-item">표시 단위: <span class="val" style="color:#60a5fa;" id="stat-view-mode-label">250m 격자</span></div>
            <div class="stat-item">계산 시간: <span class="val" id="stat-calc-time">0 ms</span></div>
            <div class="stat-item">최대 수치: <span class="val" id="stat-max-score">0</span></div>
            <div class="stat-item">하위 1% 기준점: <span class="val" style="color:#f472b6;" id="stat-bottom1-cutoff">0</span></div>
        </div>
    </header>

    <div class="main-container">
        <!-- Sidebar Controls -->
        <div class="sidebar">
            <div class="section-title">
                <span>🗺️ 공간 분석 단위 선택 (Grid / Dong / Gu)</span>
            </div>
            <div class="control-group">
                <select id="spatial-view-mode" style="background:#1e293b; border-color:#38bdf8; font-weight:700; color:#38bdf8;">
                    <option value="grid" selected>📍 250m 격자 단위 (10,125개 [기본])</option>
                    <option value="dong">🏙️ 행정동 단위 합산/평균 (427개 동)</option>
                    <option value="gu">🏛️ 자치구 단위 합산/평균 (25개 구)</option>
                </select>
            </div>

            <div class="section-title">
                <span>⚖️ 교통 수단 가중치 설정 (Mode Weights)</span>
            </div>
            <div class="control-group">
                <label>🚌 버스 가중치 (w_bus): <span id="val-w-bus" class="val">0.544 (54.4%)</span></label>
                <input type="range" id="w-bus" min="0.0" max="1.0" step="0.001" value="0.544">
            </div>

            <div class="control-group">
                <label>🚇 지하철 가중치 (w_subway): <span id="val-w-subway" class="val">0.456 (45.6%)</span></label>
                <input type="range" id="w-subway" min="0.0" max="1.0" step="0.001" value="0.456" disabled style="opacity:0.6;">
            </div>

            <div class="section-title">
                <span>🎯 시각화 분석 지표 선택</span>
            </div>
            <div class="control-group">
                <select id="score-target" style="background:#0f172a; border-color:#38bdf8; font-weight:700; color:#38bdf8;">
                    <option value="norm_weighted" selected>✨ [추천] 정규화 반영 가중 교통이동성 [ 0.544×(Bus/Max) + 0.456×(Sub/Max) ]</option>
                    <option value="pop_adjusted_norm">👥 인구 고려 정규화 가중 교통이동성 [ 정규화가중 / ln(생활인구) ]</option>
                    <option value="raw_weighted">⚠️ [원시] 단순 원본 가중합 (미정규화 - 버스 89.1% 지배)</option>
                    <option value="norm_bus">🚌 버스 이동성 (단독 정규화 0~1)</option>
                    <option value="norm_subway">🚇 지하철 이동성 (단독 정규화 0~1)</option>
                </select>
            </div>

            <div class="control-group" id="group-agg-metric" style="display:none;">
                <label>📊 행정구역 집계 수치 기준:</label>
                <select id="agg-metric">
                    <option value="mean" selected>평균 수치 (Mean [추천])</option>
                    <option value="sum">총 누적 합산 수치 (Total Sum)</option>
                    <option value="max">최대 수치 (Max)</option>
                </select>
            </div>

            <div class="section-title">
                <span>📐 거리 감쇠 함수 선택</span>
            </div>
            <div class="control-group">
                <select id="decay-mode">
                    <option value="gaussian" selected>Gaussian Decay (가우시안 감쇠 - 곡선)</option>
                    <option value="exponential">Exponential Decay (지수 감쇠 - 급격한 감소)</option>
                    <option value="linear">Linear Decay (선형 감쇠 - 직선 감소)</option>
                    <option value="none">No Decay (감쇠 없음 - 계단형 버퍼)</option>
                </select>
            </div>

            <div class="section-title">
                <span>⚙️ 접근거리 임계값 (R)</span>
            </div>
            
            <div class="control-group">
                <label>🚌 버스 최대 접근거리 (R_bus): <span id="val-r-bus" class="val">400m</span></label>
                <input type="range" id="r-bus" min="100" max="1000" step="50" value="400">
            </div>

            <div class="control-group">
                <label>🚇 지하철 최대 접근거리 (R_subway): <span id="val-r-subway" class="val">800m</span></label>
                <input type="range" id="r-subway" min="200" max="2000" step="50" value="800">
            </div>

            <div class="section-title" id="sec-bottom1-title">
                <span>🎯 하위 1% 접근성 소외지역 강조</span>
            </div>

            <label class="checkbox-container" id="container-bottom1">
                <input type="checkbox" id="toggle-bottom1" checked>
                <span>⚠️ 지표 하위 1% 소외 격자 강조 표시 (0점/마스킹 제외)</span>
            </label>

            <div class="section-title">
                <span>🎨 지도 레이어 & 색상</span>
            </div>

            <div class="control-group">
                <label>색상 맵 (Color Ramp):</label>
                <select id="color-ramp">
                    <option value="BlueRed" selected>Blue ~ Red (파랑-초록-노랑-빨강 [기본])</option>
                    <option value="YlOrRd">Yellow-Orange-Red (열지도)</option>
                    <option value="Viridis">Viridis (청록-노랑)</option>
                    <option value="Plasma">Plasma (보라-주황)</option>
                </select>
            </div>

            <div class="section-title">
                <span>📉 실시간 감쇠 곡선 그래프</span>
            </div>
            <div class="chart-box">
                <canvas id="miniChart"></canvas>
            </div>
        </div>

        <!-- Map Container -->
        <div id="map"></div>

        <!-- Open Info Button (shown when closed) -->
        <button class="toggle-info-btn" id="open-info-btn" onclick="toggleInfoPanel(true)">📍 선택 정보창 펼치기</button>

        <!-- Floating Info Box on Map -->
        <div class="info-panel" id="info-panel">
            <div class="info-panel-header">
                <h3>📍 선택 대상 상세 정보 <span id="pin-indicator" style="display:none;" class="pin-badge">📌 고정됨</span></h3>
                <button class="close-btn" onclick="toggleInfoPanel(false)" title="닫기">✕</button>
            </div>
            <div id="info-content">
                <p style="color: var(--text-muted);">지도의 격자나 행정구역을 클릭하면 스케일 정규화가 적용된 가중 수식 분해가 출력됩니다.</p>
            </div>
        </div>

        <!-- Legend -->
        <div class="map-legend">
            <div style="font-weight: 700; margin-bottom: 4px;" id="legend-title-label">접근성 점수 범주</div>
            <div class="legend-gradient" id="legend-gradient"></div>
            <div class="legend-labels">
                <span>0점 (최저)</span>
                <span id="legend-max">Max점 (최고)</span>
            </div>
            <div class="legend-extra-item" id="legend-vuln-row">
                <div class="legend-vuln-color"></div>
                <span style="color:#f472b6;">⚠️ 점수 하위 1% 접근성 취약 격자</span>
            </div>
            <div class="legend-extra-item" id="legend-masked-row">
                <div class="legend-masked-color"></div>
                <span style="color:#10b981;">⛰️ 산지/하천/공원/미집계 영역</span>
            </div>
        </div>
    </div>

    <script>
        if (!window.ACCESSIBILITY_DATA) {
            alert('데이터 파일(grid_data.js)을 찾을 수 없습니다.');
        }

        const rawData = window.ACCESSIBILITY_DATA;
        const grids = rawData.grids;
        const buses = rawData.buses;
        const subways = rawData.subways;

        const busPassengers = buses.map(b => b.passengers).sort((a, b) => a - b);
        const subwayPassengers = subways.map(s => s.passengers).sort((a, b) => a - b);
        const medianBusPassengers = busPassengers[Math.floor(busPassengers.length / 2)] || 1;
        const medianSubwayPassengers = subwayPassengers[Math.floor(subwayPassengers.length / 2)] || 1;

        let pinnedGridIndex = -1;
        let pinnedRegionKey = null;

        function toggleInfoPanel(show) {
            const panel = document.getElementById('info-panel');
            const openBtn = document.getElementById('open-info-btn');
            if (show) {
                panel.style.display = 'block';
                openBtn.style.display = 'none';
            } else {
                panel.style.display = 'none';
                openBtn.style.display = 'block';
            }
        }

        // 1. Spatial Buckets
        const BUCKET_SIZE = 1000;
        const busBuckets = {};
        const subwayBuckets = {};
        const gridSpatialIndex = {};

        buses.forEach(b => {
            const bx = Math.floor(b.x / BUCKET_SIZE);
            const by = Math.floor(b.y / BUCKET_SIZE);
            const key = bx + '_' + by;
            if (!busBuckets[key]) busBuckets[key] = [];
            busBuckets[key].push(b);
        });

        subways.forEach(s => {
            const sx = Math.floor(s.x / BUCKET_SIZE);
            const sy = Math.floor(s.y / BUCKET_SIZE);
            const key = sx + '_' + sy;
            if (!subwayBuckets[key]) subwayBuckets[key] = [];
            subwayBuckets[key].push(s);
        });

        grids.forEach((g, idx) => {
            const latBucket = Math.floor(g.lat * 100);
            const lonBucket = Math.floor(g.lon * 100);
            const key = latBucket + '_' + lonBucket;
            if (!gridSpatialIndex[key]) gridSpatialIndex[key] = [];
            gridSpatialIndex[key].push(idx);
        });

        function findGridIndexAtLatLng(lat, lon) {
            const latBucket = Math.floor(lat * 100);
            const lonBucket = Math.floor(lon * 100);

            for (let dLat = -1; dLat <= 1; dLat++) {
                for (let dLon = -1; dLon <= 1; dLon++) {
                    const key = (latBucket + dLat) + '_' + (lonBucket + dLon);
                    const candidates = gridSpatialIndex[key];
                    if (candidates) {
                        for (let i = 0; i < candidates.length; i++) {
                            const idx = candidates[i];
                            const b = grids[idx].bounds;
                            if (lat >= b[0][0] && lat <= b[1][0] && lon >= b[0][1] && lon <= b[1][1]) {
                                return idx;
                            }
                        }
                    }
                }
            }
            return -1;
        }

        // 2. Leaflet Map Setup
        const map = L.map('map', {
            center: [37.5665, 126.9780],
            zoom: 11,
            zoomSnap: 0.25,
            zoomDelta: 0.25,
            wheelPxPerZoomLevel: 220,
            wheelDebounceTime: 60,
            zoomControl: true
        });

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; CartoDB',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);

        const canvasRenderer = L.canvas({ padding: 0.5 });
        const gridLayers = [];
        let guLayerGroup = L.layerGroup().addTo(map);
        let dongLayerGroup = L.layerGroup().addTo(map);

        grids.forEach((g, idx) => {
            const initialColor = g.masked ? '#0d1f19' : '#1e293b';
            const initialBorder = g.masked ? '#132c24' : '#1e293b';

            const rect = L.rectangle(g.bounds, {
                renderer: canvasRenderer,
                stroke: true,
                color: initialBorder,
                weight: g.masked ? 0.3 : 0.2,
                fill: true,
                fillColor: initialColor,
                fillOpacity: g.masked ? 0.6 : 0.7,
                interactive: false
            });

            rect.addTo(map);
            gridLayers.push(rect);
        });

        map.on('click', function(e) {
            const viewMode = document.getElementById('spatial-view-mode').value;
            if (viewMode === 'grid') {
                const clickedIdx = findGridIndexAtLatLng(e.latlng.lat, e.latlng.lng);
                if (clickedIdx >= 0) {
                    pinGridByIndex(clickedIdx);
                } else {
                    unpinGrid();
                }
            }
        });

        let hoverIdx = -1;
        map.on('mousemove', function(e) {
            const viewMode = document.getElementById('spatial-view-mode').value;
            if (viewMode === 'grid') {
                const curHover = findGridIndexAtLatLng(e.latlng.lat, e.latlng.lng);
                if (curHover !== hoverIdx) {
                    if (hoverIdx >= 0 && hoverIdx !== pinnedGridIndex) {
                        resetGridStyle(hoverIdx);
                    }
                    hoverIdx = curHover;
                    if (hoverIdx >= 0 && hoverIdx !== pinnedGridIndex) {
                        gridLayers[hoverIdx].setStyle({ weight: 2.2, color: '#38bdf8' });
                        if (pinnedGridIndex < 0) {
                            showGridInfo(grids[hoverIdx], false);
                        }
                    }
                }
            }
        });

        function resetGridStyle(idx) {
            if (idx < 0 || idx >= grids.length) return;
            const g = grids[idx];
            const isVuln = g.isBottom1 && document.getElementById('toggle-bottom1').checked;
            const borderCol = (idx === pinnedGridIndex) ? '#f59e0b' : (isVuln ? '#ec4899' : (g.masked ? '#132c24' : '#1e293b'));
            const borderWeight = (idx === pinnedGridIndex) ? 3.0 : (isVuln ? 1.6 : (g.masked ? 0.3 : 0.2));
            gridLayers[idx].setStyle({ weight: borderWeight, color: borderCol });
        }

        function pinGridByIndex(idx) {
            const oldPinned = pinnedGridIndex;
            pinnedGridIndex = idx;
            if (oldPinned >= 0) resetGridStyle(oldPinned);
            
            if (pinnedGridIndex >= 0) {
                const g = grids[pinnedGridIndex];
                gridLayers[pinnedGridIndex].setStyle({ weight: 3.0, color: '#f59e0b' });
                gridLayers[pinnedGridIndex].bringToFront();

                document.getElementById('info-panel').classList.add('pinned');
                document.getElementById('pin-indicator').style.display = 'inline-block';
                toggleInfoPanel(true);
                showGridInfo(g, true);
            }
        }

        function unpinGrid() {
            if (pinnedGridIndex >= 0) {
                const old = pinnedGridIndex;
                pinnedGridIndex = -1;
                resetGridStyle(old);
                document.getElementById('info-panel').classList.remove('pinned');
                document.getElementById('pin-indicator').style.display = 'none';
                document.getElementById('info-content').innerHTML = `<p style="color: var(--text-muted);">지도의 격자를 클릭하면 해당 격자의 상세 수치가 고정됩니다.</p>`;
            }
        }

        // 3. Distance Decay Functions
        function calculateDecayWeight(d, R, decayMode) {
            if (d < 0 || d > R) return 0.0;
            if (decayMode === 'none') {
                return 1.0;
            } else if (decayMode === 'linear') {
                return 1.0 - (d / R);
            } else if (decayMode === 'exponential') {
                const lambda = 3.0;
                const expVal = Math.exp(-lambda * (d / R));
                const expMin = Math.exp(-lambda);
                return (expVal - expMin) / (1.0 - expMin);
            } else {
                const expD = Math.exp(-0.5 * Math.pow(d / R, 2));
                const expHalf = Math.exp(-0.5);
                return (expD - expHalf) / (1.0 - expHalf);
            }
        }

        function calcFacilityScore(passCount, medianPass) {
            return Math.log1p(passCount / (medianPass || 1));
        }

        function getColor(val, maxVal, rampName, isMasked) {
            if (isMasked) return '#0d1f19';
            if (maxVal <= 0 || val <= 0) return '#1e293b';
            const ratio = Math.min(val / maxVal, 1.0);

            if (rampName === 'BlueRed') {
                const hue = (1.0 - ratio) * 240;
                return `hsla(${hue}, 85%, 52%, ${0.5 + ratio * 0.4})`;
            } else if (rampName === 'YlOrRd') {
                if (ratio < 0.25) return `rgba(254, 240, 178, ${0.45 + ratio * 0.35})`;
                if (ratio < 0.50) return `rgba(253, 187, 132, ${0.55 + ratio * 0.35})`;
                if (ratio < 0.75) return `rgba(252, 141, 89, ${0.65 + ratio * 0.35})`;
                return `rgba(215, 48, 31, ${0.75 + ratio * 0.25})`;
            } else if (rampName === 'Viridis') {
                const r = Math.round(68 + ratio * (253 - 68));
                const g = Math.round(1 + ratio * (231 - 1));
                const b = Math.round(84 + (1 - ratio) * 150);
                return `rgba(${r}, ${g}, ${b}, ${0.55 + ratio * 0.4})`;
            } else if (rampName === 'Plasma') {
                const r = Math.round(13 + ratio * (240 - 13));
                const g = Math.round(8 + ratio * (249 - 8));
                const b = Math.round(135 + (1 - ratio) * 100);
                return `rgba(${r}, ${g}, ${b}, ${0.55 + ratio * 0.4})`;
            }
        }

        let miniChart;
        let guStats = {};
        let dongStats = {};
        let currentMaxBusScore = 1.0;
        let currentMaxSubwayScore = 1.0;

        function updateWeightLabels() {
            const wBus = parseFloat(document.getElementById('w-bus').value);
            const wSubway = 1.0 - wBus;
            document.getElementById('w-subway').value = wSubway.toFixed(3);
            
            document.getElementById('val-w-bus').innerText = `${wBus.toFixed(3)} (${(wBus*100).toFixed(1)}%)`;
            document.getElementById('val-w-subway').innerText = `${wSubway.toFixed(3)} (${(wSubway*100).toFixed(1)}%)`;
        }

        function recalculateAccessibility() {
            const t0 = performance.now();

            updateWeightLabels();
            const wBus = parseFloat(document.getElementById('w-bus').value);
            const wSubway = 1.0 - wBus;

            const viewMode = document.getElementById('spatial-view-mode').value;
            const aggMetric = document.getElementById('agg-metric').value;
            const decayMode = document.getElementById('decay-mode').value;
            const rBus = parseFloat(document.getElementById('r-bus').value);
            const rSubway = parseFloat(document.getElementById('r-subway').value);
            const scoreTarget = document.getElementById('score-target').value;
            const colorRamp = document.getElementById('color-ramp').value;
            const showBottom1 = document.getElementById('toggle-bottom1').checked;

            document.getElementById('val-r-bus').innerText = rBus + 'm';
            document.getElementById('val-r-subway').innerText = rSubway + 'm';

            if (viewMode === 'grid') {
                document.getElementById('stat-view-mode-label').innerText = '250m 격자 (10,125개)';
                document.getElementById('group-agg-metric').style.display = 'none';
                document.getElementById('sec-bottom1-title').style.display = 'flex';
                document.getElementById('container-bottom1').style.display = 'flex';
                document.getElementById('legend-vuln-row').style.display = showBottom1 ? 'flex' : 'none';
                document.getElementById('legend-masked-row').style.display = 'flex';
            } else if (viewMode === 'dong') {
                document.getElementById('stat-view-mode-label').innerText = '행정동 단위 (427개 동)';
                document.getElementById('group-agg-metric').style.display = 'flex';
                document.getElementById('sec-bottom1-title').style.display = 'none';
                document.getElementById('container-bottom1').style.display = 'none';
                document.getElementById('legend-vuln-row').style.display = 'none';
                document.getElementById('legend-masked-row').style.display = 'none';
            } else {
                document.getElementById('stat-view-mode-label').innerText = '자치구 단위 (25개 구)';
                document.getElementById('group-agg-metric').style.display = 'flex';
                document.getElementById('sec-bottom1-title').style.display = 'none';
                document.getElementById('container-bottom1').style.display = 'none';
                document.getElementById('legend-vuln-row').style.display = 'none';
                document.getElementById('legend-masked-row').style.display = 'none';
            }

            const busFacScores = buses.map(b => calcFacilityScore(b.passengers, medianBusPassengers));
            const subFacScores = subways.map(s => calcFacilityScore(s.passengers, medianSubwayPassengers));

            const busBucketRange = Math.ceil(rBus / BUCKET_SIZE);
            const subBucketRange = Math.ceil(rSubway / BUCKET_SIZE);

            // Pass 1: Compute raw busScore and subScore to determine city-wide MAX for normalization
            let maxBus = 0.001;
            let maxSub = 0.001;

            grids.forEach((g) => {
                const gx = g.cx, gy = g.cy;
                const gbx = Math.floor(gx / BUCKET_SIZE), gby = Math.floor(gy / BUCKET_SIZE);

                let busScore = 0.0, subScore = 0.0;

                for (let dx = -busBucketRange; dx <= busBucketRange; dx++) {
                    for (let dy = -busBucketRange; dy <= busBucketRange; dy++) {
                        const bList = busBuckets[(gbx + dx) + '_' + (gby + dy)];
                        if (bList) {
                            for (let i = 0; i < bList.length; i++) {
                                const b = bList[i];
                                const dist = Math.hypot(gx - b.x, gy - b.y);
                                if (dist <= rBus) busScore += calculateDecayWeight(dist, rBus, decayMode) * busFacScores[b.id];
                            }
                        }
                    }
                }

                for (let dx = -subBucketRange; dx <= subBucketRange; dx++) {
                    for (let dy = -subBucketRange; dy <= subBucketRange; dy++) {
                        const sList = subwayBuckets[(gbx + dx) + '_' + (gby + dy)];
                        if (sList) {
                            for (let i = 0; i < sList.length; i++) {
                                const s = sList[i];
                                const dist = Math.hypot(gx - s.x, gy - s.y);
                                if (dist <= rSubway) subScore += calculateDecayWeight(dist, rSubway, decayMode) * subFacScores[s.id];
                            }
                        }
                    }
                }

                g.rawBusScore = busScore;
                g.rawSubScore = subScore;

                if (!g.masked) {
                    if (busScore > maxBus) maxBus = busScore;
                    if (subScore > maxSub) maxSub = subScore;
                }
            });

            currentMaxBusScore = maxBus;
            currentMaxSubwayScore = maxSub;

            let maxGridScore = 0.0;
            const validNonZeroScores = [];

            guStats = {};
            dongStats = {};

            // Pass pass 2: Compute normalized scores and target metrics
            grids.forEach((g) => {
                g.normBusScore = g.masked ? 0.0 : (g.rawBusScore / maxBus);
                g.normSubScore = g.masked ? 0.0 : (g.rawSubScore / maxSub);

                g.rawWeightedMobility = wBus * g.rawBusScore + wSubway * g.rawSubScore;
                g.normWeightedMobility = wBus * g.normBusScore + wSubway * g.normSubScore;

                const lnPop = (g.pop > 0) ? Math.log1p(g.pop) : 1.0;
                g.popAdjustedNormMobility = (g.pop > 0 && !g.masked) ? (g.normWeightedMobility / lnPop) : 0.0;

                let targetVal = g.normWeightedMobility;
                if (scoreTarget === 'pop_adjusted_norm') targetVal = g.popAdjustedNormMobility;
                if (scoreTarget === 'raw_weighted') targetVal = g.rawWeightedMobility;
                if (scoreTarget === 'norm_bus') targetVal = g.normBusScore;
                if (scoreTarget === 'norm_subway') targetVal = g.normSubScore;

                g.currentScore = targetVal;

                if (!g.masked) {
                    if (targetVal > maxGridScore) maxGridScore = targetVal;
                    if (targetVal > 0) {
                        validNonZeroScores.push(targetVal);
                    }
                }

                const guKey = g.gu;
                const dongKey = g.gu + ' ' + g.dong;

                if (guKey) {
                    if (!guStats[guKey]) guStats[guKey] = { name: guKey, sumScore: 0, validGrids: 0, totalPop: 0, maxScore: 0, scores: [] };
                    if (!g.masked) {
                        guStats[guKey].sumScore += targetVal;
                        guStats[guKey].validGrids += 1;
                        guStats[guKey].totalPop += g.pop;
                        guStats[guKey].scores.push(targetVal);
                        if (targetVal > guStats[guKey].maxScore) guStats[guKey].maxScore = targetVal;
                    }
                }

                if (dongKey) {
                    if (!dongStats[dongKey]) dongStats[dongKey] = { name: g.dong, gu: g.gu, fullName: dongKey, sumScore: 0, validGrids: 0, totalPop: 0, maxScore: 0, scores: [] };
                    if (!g.masked) {
                        dongStats[dongKey].sumScore += targetVal;
                        dongStats[dongKey].validGrids += 1;
                        dongStats[dongKey].totalPop += g.pop;
                        dongStats[dongKey].scores.push(targetVal);
                        if (targetVal > dongStats[dongKey].maxScore) dongStats[dongKey].maxScore = targetVal;
                    }
                }
            });

            const guList = Object.values(guStats);
            guList.forEach(st => {
                st.meanScore = st.validGrids > 0 ? (st.sumScore / st.validGrids) : 0;
                st.metricVal = (aggMetric === 'sum') ? st.sumScore : ((aggMetric === 'max') ? st.maxScore : st.meanScore);
            });
            guList.sort((a, b) => b.metricVal - a.metricVal);
            guList.forEach((st, rk) => { st.rank = rk + 1; });

            const dongList = Object.values(dongStats);
            dongList.forEach(st => {
                st.meanScore = st.validGrids > 0 ? (st.sumScore / st.validGrids) : 0;
                st.metricVal = (aggMetric === 'sum') ? st.sumScore : ((aggMetric === 'max') ? st.maxScore : st.meanScore);
            });
            dongList.sort((a, b) => b.metricVal - a.metricVal);
            dongList.forEach((st, rk) => { st.rank = rk + 1; });

            validNonZeroScores.sort((a, b) => a - b);
            let cutoff1 = 0.0;
            if (validNonZeroScores.length > 0) {
                const idx1 = Math.floor(validNonZeroScores.length * 0.01);
                cutoff1 = validNonZeroScores[idx1] || validNonZeroScores[0];
            }
            document.getElementById('stat-bottom1-cutoff').innerText = cutoff1.toFixed(3);

            guLayerGroup.clearLayers();
            dongLayerGroup.clearLayers();

            let activeMaxVal = maxGridScore;

            if (viewMode === 'grid') {
                gridLayers.forEach((rect, idx) => {
                    const g = grids[idx];
                    g.isBottom1 = (!g.masked && g.currentScore > 0 && g.currentScore <= cutoff1);
                    const fillColor = getColor(g.currentScore, maxGridScore, colorRamp, g.masked);

                    const isPinned = (pinnedGridIndex === idx);
                    let strokeColor = g.masked ? '#132c24' : '#1e293b';
                    let strokeW = g.masked ? 0.3 : 0.2;

                    if (isPinned) {
                        strokeColor = '#f59e0b';
                        strokeW = 3.0;
                    } else if (showBottom1 && g.isBottom1) {
                        strokeColor = '#ec4899';
                        strokeW = 1.6;
                    }

                    rect.setStyle({
                        fillColor: fillColor,
                        fillOpacity: g.masked ? 0.55 : (g.currentScore > 0 ? 0.8 : 0.15),
                        color: strokeColor,
                        weight: strokeW
                    });
                });
            } else if (viewMode === 'dong') {
                gridLayers.forEach(rect => rect.setStyle({ fillOpacity: 0, weight: 0 }));
                activeMaxVal = dongList.length > 0 ? dongList[0].metricVal : 1;

                if (rawData.dong_geojson) {
                    L.geoJSON(rawData.dong_geojson, {
                        style: function(feature) {
                            const dName = feature.properties.gu_dong;
                            const st = dongStats[dName];
                            const val = st ? st.metricVal : 0;
                            return {
                                fillColor: getColor(val, activeMaxVal, colorRamp, false),
                                fillOpacity: 0.75,
                                color: '#1e293b',
                                weight: 0.8
                            };
                        },
                        onEachFeature: function(feature, layer) {
                            layer.on('mouseover', function() {
                                this.setStyle({ weight: 2.5, color: '#38bdf8' });
                                if (!pinnedRegionKey) {
                                    showRegionInfo('dong', feature.properties.gu_dong);
                                }
                            });
                            layer.on('mouseout', function() {
                                if (pinnedRegionKey !== feature.properties.gu_dong) {
                                    this.setStyle({ weight: 0.8, color: '#1e293b' });
                                }
                            });
                            layer.on('click', function(e) {
                                L.DomEvent.stopPropagation(e);
                                pinnedRegionKey = feature.properties.gu_dong;
                                document.getElementById('info-panel').classList.add('pinned');
                                document.getElementById('pin-indicator').style.display = 'inline-block';
                                toggleInfoPanel(true);
                                showRegionInfo('dong', feature.properties.gu_dong, true);
                            });
                        }
                    }).addTo(dongLayerGroup);
                }
            } else if (viewMode === 'gu') {
                gridLayers.forEach(rect => rect.setStyle({ fillOpacity: 0, weight: 0 }));
                activeMaxVal = guList.length > 0 ? guList[0].metricVal : 1;

                if (rawData.gu_geojson) {
                    L.geoJSON(rawData.gu_geojson, {
                        style: function(feature) {
                            const gName = feature.properties.gu_name;
                            const st = guStats[gName];
                            const val = st ? st.metricVal : 0;
                            return {
                                fillColor: getColor(val, activeMaxVal, colorRamp, false),
                                fillOpacity: 0.75,
                                color: '#f8fafc',
                                weight: 1.5
                            };
                        },
                        onEachFeature: function(feature, layer) {
                            layer.on('mouseover', function() {
                                this.setStyle({ weight: 3.5, color: '#38bdf8' });
                                if (!pinnedRegionKey) {
                                    showRegionInfo('gu', feature.properties.gu_name);
                                }
                            });
                            layer.on('mouseout', function() {
                                if (pinnedRegionKey !== feature.properties.gu_name) {
                                    this.setStyle({ weight: 1.5, color: '#f8fafc' });
                                }
                            });
                            layer.on('click', function(e) {
                                L.DomEvent.stopPropagation(e);
                                pinnedRegionKey = feature.properties.gu_name;
                                document.getElementById('info-panel').classList.add('pinned');
                                document.getElementById('pin-indicator').style.display = 'inline-block';
                                toggleInfoPanel(true);
                                showRegionInfo('gu', feature.properties.gu_name, true);
                            });
                        }
                    }).addTo(guLayerGroup);
                }
            }

            const t1 = performance.now();

            document.getElementById('stat-calc-time').innerText = Math.round(t1 - t0) + ' ms';
            document.getElementById('stat-max-score').innerText = activeMaxVal.toFixed(3);
            document.getElementById('legend-max').innerText = activeMaxVal.toFixed(3);

            const legGrad = document.getElementById('legend-gradient');
            if (colorRamp === 'BlueRed') {
                legGrad.style.background = 'linear-gradient(to right, #3b82f6, #06b6d4, #10b981, #eab308, #ef4444)';
            } else if (colorRamp === 'YlOrRd') {
                legGrad.style.background = 'linear-gradient(to right, #1e293b, #fef0d9, #fdbb84, #fc8d59, #d7301f)';
            } else if (colorRamp === 'Viridis') {
                legGrad.style.background = 'linear-gradient(to right, #1e293b, #440154, #21908d, #fde725)';
            } else if (colorRamp === 'Plasma') {
                legGrad.style.background = 'linear-gradient(to right, #1e293b, #0d0887, #cc4678, #f0f921)';
            }

            if (viewMode === 'grid' && pinnedGridIndex >= 0) {
                showGridInfo(grids[pinnedGridIndex], true);
            } else if (pinnedRegionKey) {
                showRegionInfo(viewMode, pinnedRegionKey, true);
            }

            updateMiniChart(rBus, rSubway, decayMode);
        }

        // Detailed Formula Breakdown Panel (Showing Raw -> Max Normalization -> Weighted Superposition)
        function showGridInfo(g, isPinned) {
            const container = document.getElementById('info-content');
            const maskHtml = g.masked ? `<div class="mask-badge">⛰️ 산지/하천/공원/미집계 마스킹 영역</div>` : ``;
            const vulnHtml = (!g.masked && g.isBottom1) ? `<div class="vuln-badge">⚠️ 지표 하위 1% 접근성 취약 격자</div>` : ``;
            
            const wBus = parseFloat(document.getElementById('w-bus').value);
            const wSubway = 1.0 - wBus;

            const lnPop = (g.pop > 0) ? Math.log1p(g.pop) : 1.0;

            const busContrib = wBus * g.normBusScore;
            const subContrib = wSubway * g.normSubScore;
            const totalWeighted = busContrib + subContrib;

            const busRatioPercent = totalWeighted > 0 ? ((busContrib / totalWeighted) * 100).toFixed(1) : "0.0";
            const subRatioPercent = totalWeighted > 0 ? ((subContrib / totalWeighted) * 100).toFixed(1) : "0.0";

            container.innerHTML = `
                ${maskHtml}
                ${vulnHtml}
                <div class="info-row"><label>격자 코드:</label> <span>${g.code}</span></div>
                <div class="info-row"><label>행정구역:</label> <span>${g.address || (g.gu + ' ' + g.dong)}</span></div>
                <div class="info-row"><label>평균 생활인구:</label> <span>${g.masked ? '미집계 (0명)' : g.pop.toLocaleString() + ' 명 (ln = ' + lnPop.toFixed(2) + ')'}</span></div>
                <hr style="border-color: var(--border-color); margin: 6px 0;">
                <div class="info-row"><label>✨ [정규화] 가중 교통이동성:</label> <span style="color:#38bdf8; font-size:1.1rem; font-weight:800;">${(g.normWeightedMobility || 0).toFixed(3)}</span></div>
                <div class="info-row"><label>👥 인구 고려 정규화 가중점수:</label> <span style="color:#f59e0b; font-weight:700;">${(g.popAdjustedNormMobility || 0).toFixed(3)}</span></div>
                <div class="info-row"><label>📊 실질 기여 비중 (Bus vs Sub):</label> <span style="color:#a855f7; font-weight:700;">버스 ${busRatioPercent}% : 지하철 ${subRatioPercent}%</span></div>

                <!-- FORMULA BREAKDOWN BOX -->
                <div class="breakdown-box">
                    <h4>🔍 정규화 스케일 보정 수식 분해 (Normalized Breakdown)</h4>

                    <div class="breakdown-item">
                        <div class="title">
                            <span>1️⃣ 버스 정규화 (Max=${currentMaxBusScore.toFixed(2)})</span>
                            <span class="highlight">${busContrib.toFixed(3)}</span>
                        </div>
                        <div class="formula">
                            • 원본 버스점수 S_bus = ${g.rawBusScore.toFixed(3)}<br>
                            • 정규화 점수 NormS = ${g.rawBusScore.toFixed(3)} / ${currentMaxBusScore.toFixed(2)} = <b>${g.normBusScore.toFixed(3)}</b><br>
                            • 버스 기여액 = ${wBus.toFixed(3)} × ${g.normBusScore.toFixed(3)} = <span class="highlight">${busContrib.toFixed(3)}</span>
                        </div>
                    </div>

                    <div class="breakdown-item subway">
                        <div class="title">
                            <span>2️⃣ 지하철 정규화 (Max=${currentMaxSubwayScore.toFixed(2)})</span>
                            <span class="highlight">${subContrib.toFixed(3)}</span>
                        </div>
                        <div class="formula">
                            • 원본 지하철점수 S_sub = ${g.rawSubScore.toFixed(3)}<br>
                            • 정규화 점수 NormS = ${g.rawSubScore.toFixed(3)} / ${currentMaxSubwayScore.toFixed(2)} = <b>${g.normSubScore.toFixed(3)}</b><br>
                            • 지하철 기여액 = ${wSubway.toFixed(3)} × ${g.normSubScore.toFixed(3)} = <span class="highlight">${subContrib.toFixed(3)}</span>
                        </div>
                    </div>

                    <div class="breakdown-item weight">
                        <div class="title">
                            <span>3️⃣ 최종 가중 결합 및 인구 스케일링</span>
                            <span class="highlight" style="color:#f59e0b;">${(g.popAdjustedNormMobility || 0).toFixed(3)}</span>
                        </div>
                        <div class="formula">
                            • 총 정규화 이동성 = 버스(${busContrib.toFixed(3)}) + 지하철(${subContrib.toFixed(3)}) = <b>${g.normWeightedMobility.toFixed(3)}</b><br>
                            • 인구 분모 = ln(1 + ${g.pop.toLocaleString()}명) = <b>${lnPop.toFixed(3)}</b><br>
                            • 인구 고려 최종 수치 = <span style="color:#f59e0b; font-weight:700;">${g.normWeightedMobility.toFixed(3)} / ${lnPop.toFixed(3)} = ${(g.popAdjustedNormMobility || 0).toFixed(3)}</span>
                        </div>
                    </div>
                </div>
            `;
        }

        function showRegionInfo(type, key, isPinned) {
            const container = document.getElementById('info-content');
            let st = (type === 'gu') ? guStats[key] : dongStats[key];

            if (!st) {
                container.innerHTML = `<p style="color: var(--text-muted);">정보를 불러올 수 없습니다.</p>`;
                return;
            }

            const title = (type === 'gu') ? `🏛️ 자치구: ${st.name}` : `🏙️ 행정동: ${st.fullName}`;
            const totalCount = (type === 'gu') ? 25 : 427;
            const aggMetric = document.getElementById('agg-metric').value;
            const aggLabel = (aggMetric === 'sum') ? '총 합산 수치' : ((aggMetric === 'max') ? '최대 수치' : '평균 수치');

            container.innerHTML = `
                <div class="rank-badge">🏆 서울시 ${type === 'gu' ? '자치구' : '행정동'} 순위: ${st.rank}위 / ${totalCount}개</div>
                <div class="info-row" style="font-size:1.0rem; font-weight:700; color:#38bdf8; margin: 4px 0;"><label>행정구역명:</label> <span>${st.fullName || st.name}</span></div>
                <div class="info-row"><label>유효 분석 격자 수:</label> <span>${st.validGrids.toLocaleString()} 개</span></div>
                <div class="info-row"><label>총 생활인구 합계:</label> <span>${st.totalPop.toLocaleString()} 명</span></div>
                <hr style="border-color: var(--border-color); margin: 6px 0;">
                <div class="info-row"><label>📊 선택 지표 (${aggLabel}):</label> <span style="color:#f59e0b; font-size:1.08rem; font-weight:800;">${st.metricVal.toFixed(3)}</span></div>
                
                <div class="breakdown-box">
                    <h4>🔍 행정구역 집계 세부 분해</h4>
                    <div class="breakdown-item">
                        <div class="title">
                            <span>구역 내 지표 분포</span>
                            <span class="highlight">평균 ${st.meanScore.toFixed(3)}</span>
                        </div>
                        <div class="formula">
                            • 평균 수치 = 총합(${st.sumScore.toFixed(2)}) / 격자수(${st.validGrids}개) = <b style="color:#60a5fa;">${st.meanScore.toFixed(3)}</b><br>
                            • 구역 내 최고 격자 수치: <b style="color:#10b981;">${st.maxScore.toFixed(3)}</b><br>
                            • 구역 총 생활인구: ${st.totalPop.toLocaleString()} 명
                        </div>
                    </div>
                </div>
            `;
        }

        function updateMiniChart(rBus, rSubway, decayMode) {
            const maxD = Math.max(rBus, rSubway);
            const dists = [];
            const wB = [];
            const wS = [];

            for (let d = 0; d <= maxD; d += maxD / 20) {
                dists.push(Math.round(d) + 'm');
                wB.push(calculateDecayWeight(d, rBus, decayMode).toFixed(2));
                wS.push(calculateDecayWeight(d, rSubway, decayMode).toFixed(2));
            }

            miniChart.data.labels = dists;
            miniChart.data.datasets[0].data = wB;
            miniChart.data.datasets[1].data = wS;
            miniChart.update();
        }

        window.onload = function() {
            const ctx = document.getElementById('miniChart').getContext('2d');
            miniChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: '버스 W(d, R_bus)', borderColor: '#3b82f6', data: [], borderWidth: 2, pointRadius: 0 },
                        { label: '지하철 W(d, R_subway)', borderColor: '#a855f7', data: [], borderWidth: 2, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { ticks: { color: '#94a3b8', font: { size: 9 } } },
                        y: { min: 0, max: 1, ticks: { color: '#94a3b8', font: { size: 9 } } }
                    },
                    plugins: { legend: { labels: { color: '#f8fafc', font: { size: 10 } } } }
                }
            });

            const inputs = ['spatial-view-mode', 'agg-metric', 'w-bus', 'r-bus', 'r-subway', 'score-target', 'color-ramp', 'decay-mode', 'toggle-bottom1'];
            inputs.forEach(id => {
                const elem = document.getElementById(id);
                if (elem) {
                    elem.addEventListener('input', recalculateAccessibility);
                    elem.addEventListener('change', recalculateAccessibility);
                }
            });

            recalculateAccessibility();
        };
    </script>
</body>
</html>
"""
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_code)
        
    print(f"[AppBuilder] Successfully generated normalized weighted transit accessibility HTML at: {out_html}")
    return out_html

if __name__ == '__main__':
    generate_weighted_transit_html()
