import os
import json
import math

js_path = r'C:\Workspace\projects\DMtrio\outputs\maps\grid_data.js'
with open(js_path, 'r', encoding='utf-8') as f:
    text = f.read()

json_str = text[text.find('{'):text.rfind('}')+1]
data = json.loads(json_str)

grids = data['grids']
buses = data['buses']
subways = data['subways']

BUCKET_SIZE = 1000
bus_buckets = {}
subway_buckets = {}

for b in buses:
    key = f"{int(b['x'] // BUCKET_SIZE)}_{int(b['y'] // BUCKET_SIZE)}"
    bus_buckets.setdefault(key, []).append(b)

for s in subways:
    key = f"{int(s['x'] // BUCKET_SIZE)}_{int(s['y'] // BUCKET_SIZE)}"
    subway_buckets.setdefault(key, []).append(s)

bus_passengers = sorted([b['passengers'] for b in buses])
subway_passengers = sorted([s['passengers'] for s in subways])
med_bus = bus_passengers[len(bus_passengers)//2]
med_subway = subway_passengers[len(subway_passengers)//2]

w_bus = 0.544
w_subway = 0.456
r_bus = 400
r_subway = 800

max_raw_bus = 0.0001
max_raw_subway = 0.0001

valid_grids = []

for g in grids:
    if g.get('masked'):
        continue
    gx, gy = g['cx'], g['cy']
    
    # bus raw score
    bus_raw = 0.0
    bx_center = int(gx // BUCKET_SIZE)
    by_center = int(gy // BUCKET_SIZE)
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            k = f"{bx_center+dx}_{by_center+dy}"
            for b in bus_buckets.get(k, []):
                dist = math.hypot(gx - b['x'], gy - b['y'])
                if dist <= r_bus:
                    decay = math.exp(-0.5 * (dist / (r_bus / 3.0))**2)
                    weight = b['passengers'] / med_bus
                    bus_raw += weight * decay
                    
    # subway raw score
    subway_raw = 0.0
    sx_center = int(gx // BUCKET_SIZE)
    sy_center = int(gy // BUCKET_SIZE)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            k = f"{sx_center+dx}_{sy_center+dy}"
            for s in subway_buckets.get(k, []):
                dist = math.hypot(gx - s['x'], gy - s['y'])
                if dist <= r_subway:
                    decay = math.exp(-0.5 * (dist / (r_subway / 3.0))**2)
                    weight = s['passengers'] / med_subway
                    subway_raw += weight * decay

    g['bus_raw'] = bus_raw
    g['subway_raw'] = subway_raw
    if bus_raw > max_raw_bus: max_raw_bus = bus_raw
    if subway_raw > max_raw_subway: max_raw_subway = subway_raw
    valid_grids.append(g)

dong_scores = {}
for g in valid_grids:
    norm_bus = g['bus_raw'] / max_raw_bus
    norm_subway = g['subway_raw'] / max_raw_subway
    norm_weighted = w_bus * norm_bus + w_subway * norm_subway
    g['norm_weighted'] = norm_weighted
    g['norm_bus'] = norm_bus
    g['norm_subway'] = norm_subway
    
    gu = g.get('gu', '')
    dong = g.get('dong', '')
    key = f"{gu} {dong}".strip()
    dong_scores.setdefault(key, []).append((norm_weighted, norm_bus, norm_subway, g['bus_raw'], g['subway_raw']))

dong_avg = []
for key, vals in dong_scores.items():
    avg_weighted = sum(v[0] for v in vals) / len(vals)
    avg_bus_norm = sum(v[1] for v in vals) / len(vals)
    avg_sub_norm = sum(v[2] for v in vals) / len(vals)
    dong_avg.append((key, avg_weighted, avg_bus_norm, avg_sub_norm, len(vals)))

dong_avg.sort(key=lambda x: x[1])

with open(r'C:\Workspace\projects\DMtrio\.brain\result.txt', 'w', encoding='utf-8') as out:
    out.write("=== [행정동 기준] 교통이동성(접근성) 낮은 순위 TOP 15 ===\n")
    for rank, (dong_name, score, b_norm, s_norm, count) in enumerate(dong_avg[:15], 1):
        out.write(f"{rank:2d}위: {dong_name:15s} | 종합 접근성 점수: {score:.4f} (버스: {b_norm:.4f}, 지하철: {s_norm:.4f}, 격자수: {count}개)\n")

    valid_grids.sort(key=lambda x: x['norm_weighted'])
    out.write("\n=== [250m 격자 기준] 교통이동성(접근성) 낮은 순위 TOP 15 ===\n")
    for rank, g in enumerate(valid_grids[:15], 1):
        out.write(f"{rank:2d}위: {g.get('gu','')} {g.get('dong','')} (ID: {g['id']}) | 점수: {g['norm_weighted']:.4f} (버스: {g['norm_bus']:.4f}, 지하철: {g['norm_subway']:.4f})\n")

