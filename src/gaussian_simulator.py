import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from src.config import OUTPUT_DIR, MAPS_DIR, PROCESSED_DATA_DIR, TARGET_CRS
from src.transit_scoring import gaussian_decay_weight, calculate_facility_score

def build_interactive_simulator_html(out_path: str = None):
    """
    Generates a high-end interactive visual web app simulator allowing the user to experiment
    with Gaussian distance decay parameters (R_bus, R_subway), base scores, passenger scaling
    formulas (log, sqrt, linear), and distance-weighted score aggregation in real-time.
    """
    if out_path is None:
        out_path = os.path.join(MAPS_DIR, "gaussian_scoring_simulator.html")
        
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>대중교통 접근성 가우시안 감쇠 & 시설 점수 시뮬레이터</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --panel-bg: #1e293b;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-amber: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            padding: 24px;
        }

        header {
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
        }

        header h1 {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(90deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }

        header p {
            color: var(--text-muted);
            font-size: 0.95rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 360px 1fr;
            gap: 24px;
        }

        @media (max-width: 1024px) {
            .dashboard-grid { grid-template-columns: 1fr; }
        }

        .controls-panel {
            background: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #e2e8f0;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .control-group label {
            font-size: 0.88rem;
            font-weight: 500;
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
            font-size: 0.9rem;
            outline: none;
        }

        .main-panel {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .card {
            background: var(--panel-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .chart-container {
            position: relative;
            height: 320px;
            width: 100%;
        }

        .formula-box {
            background: #090d16;
            border-left: 4px solid var(--accent-blue);
            border-radius: 8px;
            padding: 14px 18px;
            font-family: monospace;
            font-size: 0.9rem;
            color: #cbd5e1;
            line-height: 1.6;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 0.88rem;
        }

        th, td {
            padding: 10px 14px;
            text-align: center;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background-color: #0f172a;
            color: var(--text-muted);
            font-weight: 600;
        }

        tr:hover {
            background-color: rgba(59, 130, 246, 0.08);
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .badge-bus { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge-subway { background: rgba(139, 92, 246, 0.2); color: #c084fc; }
    </style>
</head>
<body>

    <header>
        <h1>🧪 대중교통 접근성 가우시안 감쇠 & 점수 산정 실시간 시뮬레이터</h1>
        <p>거리별 가우시안 가중치 감쇠 $W(d, R)$와 승하차인원 기반 시설 점수 수식을 유연하게 조정하며 결과를 확인하세요.</p>
    </header>

    <div class="dashboard-grid">
        <!-- Controls Panel -->
        <div class="controls-panel">
            <div class="section-title">⚙️ 가우시안 감쇠 거리 설정</div>
            
            <div class="control-group">
                <label>🚌 버스 최대 접근거리 (R_bus): <span id="val-r-bus" class="val">400m</span></label>
                <input type="range" id="r-bus" min="100" max="1000" step="50" value="400">
            </div>

            <div class="control-group">
                <label>🚇 지하철 최대 접근거리 (R_subway): <span id="val-r-subway" class="val">800m</span></label>
                <input type="range" id="r-subway" min="200" max="2000" step="50" value="800">
            </div>

            <div class="section-title">🎯 시설 점수 (승하차인원 반영)</div>

            <div class="control-group">
                <label>🚌 버스 기본 점수 (Base): <span id="val-base-bus" class="val">10점</span></label>
                <input type="range" id="base-bus" min="0" max="50" step="1" value="10">
            </div>

            <div class="control-group">
                <label>🚇 지하철 기본 점수 (Base): <span id="val-base-subway" class="val">50점</span></label>
                <input type="range" id="base-subway" min="0" max="200" step="5" value="50">
            </div>

            <div class="control-group">
                <label>📈 승하차인원 스케일링 함수:</label>
                <select id="scaling-mode">
                    <option value="log" selected>Logarithmic [ c × ln(1 + 이용객) ]</option>
                    <option value="sqrt">Square Root [ c × √(이용객) ]</option>
                    <option value="linear">Linear [ c × 이용객 ]</option>
                </select>
            </div>

            <div class="control-group">
                <label>⚖️ 승하차 추가점수 계수 (c): <span id="val-p-weight" class="val">3.0</span></label>
                <input type="range" id="p-weight" min="0.1" max="10" step="0.1" value="3.0">
            </div>

            <div class="control-group">
                <label>🛡️ 승하차 추가점수 최대 상한선: <span id="val-max-add" class="val">50점</span></label>
                <input type="range" id="max-add" min="10" max="200" step="5" value="50">
            </div>

            <div class="section-title">📍 테스트용 거리 (d) 설정</div>
            <div class="control-group">
                <label>시설과의 거리 d: <span id="val-d-test" class="val">200m</span></label>
                <input type="range" id="d-test" min="0" max="1200" step="25" value="200">
            </div>
            <div class="control-group">
                <label>테스트 정류소 승하차인원: <span id="val-pass-test" class="val">5,000 명</span></label>
                <input type="range" id="pass-test" min="0" max="50000" step="1000" value="5000">
            </div>
        </div>

        <!-- Main Dashboard View -->
        <div class="main-panel">
            <!-- Formula Display -->
            <div class="card">
                <div class="section-title">📐 사용 중인 가우시안 감쇠 및 종합 점수 공식</div>
                <div class="formula-box">
                    <strong>가우시안 가중치:</strong> W(d, R) = [ exp(-0.5 × (d / R)²) - exp(-0.5) ] / [ 1 - exp(-0.5) ]  (0 ≤ d ≤ R), 0 (d > R)<br>
                    <strong>시설 개별 점수:</strong> S_facility = S_base + min( max_add, c × f(승하차인원) )<br>
                    <strong>격자 종합 점수:</strong> Score_grid = ∑ [ W(d_bus, R_bus) × S_bus ] + ∑ [ W(d_sub, R_subway) × S_subway ]
                </div>
            </div>

            <!-- Decay Curve Chart -->
            <div class="card">
                <div class="section-title">📉 거리별 가중치 감쇠 곡선 (Gaussian Decay Curve)</div>
                <div class="chart-container">
                    <canvas id="decayChart"></canvas>
                </div>
            </div>

            <!-- Score Simulation Table -->
            <div class="card">
                <div class="section-title">📊 샘플 비율별 가중치 & 시뮬레이션 결과 표</div>
                <table>
                    <thead>
                        <tr>
                            <th>거리 비율</th>
                            <th>버스 거리</th>
                            <th>지하철 거리</th>
                            <th>가우시안 가중치 W(d, R)</th>
                            <th>버스 최종 반영점수</th>
                            <th>지하철 최종 반영점수</th>
                        </tr>
                    </thead>
                    <tbody id="result-table">
                        <!-- Dynamic Rows -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let decayChart;

        function gaussianWeight(d, R) {
            if (d < 0 || d > R) return 0.0;
            const expD = Math.exp(-0.5 * Math.pow(d / R, 2));
            const expHalf = Math.exp(-0.5);
            return (expD - expHalf) / (1.0 - expHalf);
        }

        function calcFacilityScore(baseScore, passCount, mode, weight, maxAdd) {
            let add = 0;
            if (mode === 'log') {
                add = Math.log1p(passCount) * weight;
            } else if (mode === 'sqrt') {
                add = Math.sqrt(passCount) * weight * 0.1;
            } else if (mode === 'linear') {
                add = passCount * weight * 0.001;
            }
            add = Math.min(add, maxAdd);
            return baseScore + add;
        }

        function updateSimulation() {
            const rBus = parseFloat(document.getElementById('r-bus').value);
            const rSubway = parseFloat(document.getElementById('r-subway').value);
            const baseBus = parseFloat(document.getElementById('base-bus').value);
            const baseSubway = parseFloat(document.getElementById('base-subway').value);
            const mode = document.getElementById('scaling-mode').value;
            const pWeight = parseFloat(document.getElementById('p-weight').value);
            const maxAdd = parseFloat(document.getElementById('max-add').value);
            const dTest = parseFloat(document.getElementById('d-test').value);
            const passTest = parseFloat(document.getElementById('pass-test').value);

            // Update Label Text
            document.getElementById('val-r-bus').innerText = rBus + 'm';
            document.getElementById('val-r-subway').innerText = rSubway + 'm';
            document.getElementById('val-base-bus').innerText = baseBus + '점';
            document.getElementById('val-base-subway').innerText = baseSubway + '점';
            document.getElementById('val-p-weight').innerText = pWeight.toFixed(1);
            document.getElementById('val-max-add').innerText = maxAdd + '점';
            document.getElementById('val-d-test').innerText = dTest + 'm';
            document.getElementById('val-pass-test').innerText = passTest.toLocaleString() + ' 명';

            // Calculate facility scores
            const busFacScore = calcFacilityScore(baseBus, passTest, mode, pWeight, maxAdd);
            const subFacScore = calcFacilityScore(baseSubway, passTest * 3, mode, pWeight, maxAdd); // Subway typically higher passenger volume

            // Chart Data Generation
            const distances = [];
            const busWeights = [];
            const subWeights = [];
            const maxDist = Math.max(rBus, rSubway) * 1.1;
            const step = maxDist / 100;

            for (let d = 0; d <= maxDist; d += step) {
                distances.push(Math.round(d));
                busWeights.push(gaussianWeight(d, rBus));
                subWeights.push(gaussianWeight(d, rSubway));
            }

            // Update Chart
            decayChart.data.labels = distances;
            decayChart.data.datasets[0].data = busWeights;
            decayChart.data.datasets[1].data = subWeights;
            decayChart.update();

            // Update Table
            const ratios = [0.0, 0.25, 0.50, 0.75, 1.00];
            const tbody = document.getElementById('result-table');
            tbody.innerHTML = '';

            ratios.forEach(r => {
                const dB = r * rBus;
                const dS = r * rSubway;
                const w = gaussianWeight(dB, rBus); // identical to weight at dS, rSubway
                const finalBus = (w * busFacScore).toFixed(1);
                const finalSub = (w * subFacScore).toFixed(1);

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${Math.round(r * 100)}%</strong></td>
                    <td><span class="badge badge-bus">${Math.round(dB)}m</span></td>
                    <td><span class="badge badge-subway">${Math.round(dS)}m</span></td>
                    <td><strong>${w.toFixed(2)}</strong></td>
                    <td style="color:#60a5fa; font-weight:700;">${finalBus} 점</td>
                    <td style="color:#c084fc; font-weight:700;">${finalSub} 점</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Init Chart
        window.onload = function() {
            const ctx = document.getElementById('decayChart').getContext('2d');
            decayChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: '버스 가중치 W(d, R_bus)',
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.3,
                            data: []
                        },
                        {
                            label: '지하철 가중치 W(d, R_subway)',
                            borderColor: '#a855f7',
                            backgroundColor: 'rgba(168, 85, 247, 0.1)',
                            fill: true,
                            tension: 0.3,
                            data: []
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: { display: true, text: '거리 d (m)', color: '#94a3b8' },
                            ticks: { color: '#94a3b8' },
                            grid: { color: '#334155' }
                        },
                        y: {
                            title: { display: true, text: '가우시안 가중치 W(d, R)', color: '#94a3b8' },
                            min: 0, max: 1.05,
                            ticks: { color: '#94a3b8' },
                            grid: { color: '#334155' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#f8fafc' } }
                    }
                }
            });

            // Add Event Listeners
            const inputs = ['r-bus', 'r-subway', 'base-bus', 'base-subway', 'scaling-mode', 'p-weight', 'max-add', 'd-test', 'pass-test'];
            inputs.forEach(id => {
                document.getElementById(id).addEventListener('input', updateSimulation);
                document.getElementById(id).addEventListener('change', updateSimulation);
            });

            updateSimulation();
        };
    </script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[GaussianSimulator] Created interactive simulation dashboard at: {out_path}")
    return out_path

if __name__ == '__main__':
    build_interactive_simulator_html()
