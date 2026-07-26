import json

js_path = r'C:\Workspace\projects\DMtrio\outputs\maps\grid_data.js'
with open(js_path, 'r', encoding='utf-8') as f:
    text = f.read()

json_str = text[text.find('{'):text.rfind('}')+1]
data = json.loads(json_str)

grids = data['grids']
buses = data['buses']
subways = data['subways']

import math

bus_passengers = sorted([b['passengers'] for b in buses])
subway_passengers = sorted([s['passengers'] for s in subways])
med_bus = bus_passengers[len(bus_passengers)//2] or 1
med_subway = subway_passengers[len(subway_passengers)//2] or 1

bus_fac = [math.log1p(b['passengers'] / med_bus) for b in buses]
sub_fac = [math.log1p(s['passengers'] / med_subway) for s in subways]

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
    
    bus_score = 0.0
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            k = f"{gbx+dx}_{gby+dy}"
            for b, fac in bus_buckets.get(k, []):
                dist = math.hypot(gx - b['x'], gy - b['y'])
                if dist <= r_bus:
                    bus_score += calculate_decay_weight(dist, r_bus) * fac
                    
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
    
    # Population adjusted norm: norm_weighted / ln(1 + pop)
    pop = g.get('pop', 0)
    ln_pop = math.log1p(pop) if pop > 0 else 1.0
    pop_adj_norm = norm_weighted / ln_pop if (pop > 0) else 0.0
    
    g['pop_adj_norm'] = pop_adj_norm
    
    dong_key = f"{g['gu']} {g['dong']}"
    if dong_key not in dong_stats:
        dong_stats[dong_key] = {'fullName': dong_key, 'sumScore': 0.0, 'validGrids': 0, 'totalPop': 0}
    dong_stats[dong_key]['sumScore'] += pop_adj_norm
    dong_stats[dong_key]['validGrids'] += 1
    dong_stats[dong_key]['totalPop'] += pop

dong_list = []
for k, st in dong_stats.items():
    mean_score = st['sumScore'] / st['validGrids'] if st['validGrids'] > 0 else 0
    dong_list.append({'fullName': k, 'meanScore': mean_score, 'validGrids': st['validGrids'], 'totalPop': st['totalPop']})

dong_list.sort(key=lambda x: x['meanScore'])

with open(r'C:\Workspace\projects\DMtrio\.brain\pop_rank.txt', 'w', encoding='utf-8') as out:
    out.write("=== [👥 인구 고려 정규화 가중 지표 기준] 행정동 최하위 TOP 15 ===\n")
    for rk, d in enumerate(dong_list[:15], 1):
        out.write(f"최하위 {rk:2d}위 (웹앱 {427 - rk + 1}위): {d['fullName']:15s} | 인구고려 평균점수: {d['meanScore']:.4f} | 총생활인구: {d['totalPop']:.1f}명\n")

