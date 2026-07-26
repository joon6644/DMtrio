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

# 1. Facility score: Math.log1p(passCount / medianPass)
bus_passengers = sorted([b['passengers'] for b in buses])
subway_passengers = sorted([s['passengers'] for s in subways])
med_bus = bus_passengers[len(bus_passengers)//2] or 1
med_subway = subway_passengers[len(subway_passengers)//2] or 1

bus_fac = [math.log1p(b['passengers'] / med_bus) for b in buses]
sub_fac = [math.log1p(s['passengers'] / med_subway) for s in subways]

# Buckets
BUCKET_SIZE = 1000
bus_buckets = {}
subway_buckets = {}

for i, b in enumerate(buses):
    key = f"{int(b['x'] // BUCKET_SIZE)}_{int(b['y'] // BUCKET_SIZE)}"
    bus_buckets.setdefault(key, []).append((b, bus_fac[i]))

for i, s in enumerate(subways):
    key = f"{int(s['x'] // BUCKET_SIZE)}_{int(s['y'] // BUCKET_SIZE)}"
    subway_buckets.setdefault(key, []).append((s, sub_fac[i]))

w_bus = 0.544
w_subway = 0.456
r_bus = 400.0
r_subway = 800.0

def calculate_decay_weight(d, R):
    if d < 0 or d > R: return 0.0
    expD = math.exp(-0.5 * ((d / R)**2))
    expHalf = math.exp(-0.5)
    return (expD - expHalf) / (1.0 - expHalf)

max_bus = 0.001
max_sub = 0.001

for g in grids:
    if g.get('masked'):
        continue
    gx, gy = g['cx'], g['cy']
    gbx, gby = int(gx // BUCKET_SIZE), int(gy // BUCKET_SIZE)
    
    # bus
    bus_score = 0.0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            k = f"{gbx+dx}_{gby+dy}"
            for b, fac in bus_buckets.get(k, []):
                dist = math.hypot(gx - b['x'], gy - b['y'])
                if dist <= r_bus:
                    bus_score += calculate_decay_weight(dist, r_bus) * fac
                    
    # subway
    sub_score = 0.0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            k = f"{gbx+dx}_{gby+dy}"
            for s, fac in subway_buckets.get(k, []):
                dist = math.hypot(gx - s['x'], gy - s['y'])
                if dist <= r_subway:
                    sub_score += calculate_decay_weight(dist, r_subway) * fac
                    
    g['rawBusScore'] = bus_score
    g['rawSubScore'] = sub_score
    if bus_score > max_bus: max_bus = bus_score
    if sub_score > max_sub: max_sub = sub_score

dong_stats = {}
for g in grids:
    if g.get('masked'):
        continue
    norm_bus = g['rawBusScore'] / max_bus
    norm_sub = g['rawSubScore'] / max_sub
    norm_weighted = w_bus * norm_bus + w_subway * norm_sub
    
    g['norm_weighted'] = norm_weighted
    
    dong_key = f"{g['gu']} {g['dong']}"
    if dong_key not in dong_stats:
        dong_stats[dong_key] = {'fullName': dong_key, 'sumScore': 0.0, 'validGrids': 0}
    dong_stats[dong_key]['sumScore'] += norm_weighted
    dong_stats[dong_key]['validGrids'] += 1

dong_list = []
for k, st in dong_stats.items():
    mean_score = st['sumScore'] / st['validGrids'] if st['validGrids'] > 0 else 0
    dong_list.append({'fullName': k, 'meanScore': mean_score, 'validGrids': st['validGrids']})

# Sort ascending (lowest accessibility first)
dong_list.sort(key=lambda x: x['meanScore'])

with open(r'C:\Workspace\projects\DMtrio\.brain\real_exact_rank.txt', 'w', encoding='utf-8') as out:
    out.write("=== [웹 앱 실시간 JS 로직 100% 동일] 행정동 대중교통 접근성 최하위 TOP 15 ===\n")
    for rk, d in enumerate(dong_list[:15], 1):
        # 427개 중 순위 (오름차순)
        # 웹 앱 순위는 내림차순(1위가 최고점)이므로, 오름차순 i위는 427 - i + 1위!
        web_app_rank = 427 - (rk - 1)
        out.write(f"최하위 {rk:2d}위 (웹앱 표기 {web_app_rank}위/427개): {d['fullName']:15s} | 평균 수치: {d['meanScore']:.3f} ({d['meanScore']:.4f}) | 격자수: {d['validGrids']}개\n")

    # 종로구 옥인동 찾기
    for idx, d in enumerate(dong_list, 1):
        if '옥인동' in d['fullName']:
            out.write(f"\n[검증] {d['fullName']} -> 최하위 {idx}위 (웹앱 {427 - idx + 1}위/427개) | 평균 수치: {d['meanScore']:.3f}\n")

