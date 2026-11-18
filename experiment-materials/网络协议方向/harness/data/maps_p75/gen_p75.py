"""协议第75轮（由 gen_p69.py 复制，只改名字和种子）：新留出地图。同第71轮 gen_r70.py 的稀疏房间生成器；本机无 scipy，去掉 rho>=0.95 一条（见 protocol_p18.md）。"""
import sys, json, os, tempfile
REPO = os.path.expanduser('~/robotnet-lab/repo/workspace')
for p in ('maps_new', 'maps_r25', 'maps_r29', 'netmodel_r41'): sys.path.insert(0, os.path.join(REPO, p))
import gen_maps
from gen_r29 import sparse_room_map
import regiongraph as RG
TPL = sys.argv[1]
_orig = json.load
def write_instance(name, G, counts, seed, ntasks):
    gen_maps.write_map(name, G); F = gen_maps.free_cells(G); import random; rnd = random.Random(seed)
    starts = rnd.sample(F, max(counts))
    open(f'{name}.agents', 'w').write('# version for LoRR 2026\n%d\n' % len(starts) + '\n'.join(map(str, starts)) + '\n')
    tasks = []
    for _ in range(ntasks):
        a = rnd.choice(F); b = rnd.choice(F)
        while b == a: b = rnd.choice(F)
        tasks.append(f'{a},{b}')
    open(f'{name}.tasks', 'w').write('# version for LoRR 2026\n%d\n' % ntasks + '\n'.join(tasks) + '\n')
    tpl = json.load(open(TPL)); out = {}
    for n in counts:
        t = dict(tpl); t.update(mapFile=f'{name}.map', agentFile=f'{name}.agents', taskFile=f'{name}.tasks', teamSize=n)
        json.dump(t, open(f'{name}_{n}.json', 'w'), indent=1); out[f'{name}_{n}'] = n
    return len(F), out
def check(G):
    with tempfile.NamedTemporaryFile('w', suffix='.map', delete=False) as f:
        f.write('type octile\nheight %d\nwidth %d\nmap\n' % (len(G), len(G[0])) + '\n'.join(''.join(r) for r in G) + '\n'); p = f.name
    try:
        A = RG.analyse(p); W = {d['id']: d['width'] for d in A['doors']}
        for b in A['bridges']:
            if W[b['door']] < 2: continue
            cells = [x['cells'] for x in b['parts']]; T = sum(cells)
            if min(cells) < 0.05 * T: continue
            return dict(door=b['door'], parts=cells, rooms=len(A['rooms']), doors=len(A['doors'])), 'kept'
        return None, 'no 2-cell bridge with both sides >= 5 %'
    finally: os.unlink(p)
names = ['roomNA', 'roomNB', 'roomNC', 'roomND', 'roomNE', 'roomNF']; sizes = [16, 15, 14, 13, 12, 11]
log = []; specs = {}; seed = 95001; i = 0
while len(specs) < 6 and seed < 95500:
    S = sizes[len(specs)]; G = sparse_room_map(64, S, seed); info, why = check(G)
    log.append(dict(seed=seed, S=S, result=why, **(info or {})))
    if info:
        name = names[len(specs)]; free = sum(r.count('.') for r in G)
        specs[name] = write_instance(name, G, [round(0.055 * free), round(0.07 * free)], 96000 + len(specs), 4000)
        log[-1]['name'] = name; print(name, seed, S, info, flush=True)
    seed += 1
json.dump(specs, open('instances.json', 'w'), indent=1); json.dump(log, open('generation_log.json', 'w'), indent=1)
print('tried', len(log), 'seeds; kept', len(specs))
