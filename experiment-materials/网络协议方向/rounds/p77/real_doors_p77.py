# 协议第 77 轮（D-2）：列出每张图的“真房间门”——门格（第 27 轮 doors_rooms 口径）连通块，四邻接到的房间区至少两个、且全部 >= 25 格（第 76 轮规则，不看轨迹）。
# 另算离门 1..K 步的房间格数（转身罚区大小），以及第 43 轮账本口径的转身份额由 p43 账本给出，这里不重算。
# 用法：python -I -B real_doors_p77.py 实例表.json 门清单目录 输出实例表.json 汇总.json
import json, sys, collections
from pathlib import Path
from collections import deque
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
import ipfix_account as A
MIN_ROOM = 25
cfg, ld, outcfg, outsum = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
full = json.loads((A.H / cfg).read_text(encoding='utf8')); A.CFG = {k: v for k, v in full.items() if not k.startswith('_')}
ld.mkdir(parents=True, exist_ok=True); summ = {}
for inst in A.CFG:
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free); size = collections.Counter(rlab.values())
    comp = collections.defaultdict(list)
    for v, k in dlab.items(): comp[k].append(v)
    keep = []
    for k, cells in comp.items():
        adj = {rlab[u] for (a, b) in cells for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if u in rlab}
        if len(adj) >= 2 and min(size[x] for x in adj) >= MIN_ROOM: keep.append(cells)
    cells = [c for cs in keep for c in cs]
    (ld / f'{inst}.txt').write_text(''.join(f'{r} {c}\n' for r, c in cells), encoding='utf8')
    dist = {v: 0 for v in cells}; q = deque(cells)
    while q:
        v = q.popleft()
        if dist[v] >= 3: continue
        a, b = v
        for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if F(*u) and u not in dist: dist[u] = dist[v] + 1; q.append(u)
    nfree = sum(map(sum, free))
    summ[inst] = dict(doors_all=nd, doors_real=len(keep), door_cells=len(cells), zone2=sum(1 for d in dist.values() if 1 <= d <= 2), zone3=sum(1 for d in dist.values() if 1 <= d <= 3), free=nfree)
    full[inst]['env'] = dict(full[inst]['env'], ROBOT_PRETURN_FILE=(ld / f'{inst}.txt').resolve().as_posix())
    print(f"{inst:12s} 门 {nd:3d}  真房间门 {len(keep):3d}  门格 {len(cells):3d}  罚区 k2 {summ[inst]['zone2']:4d} k3 {summ[inst]['zone3']:4d} / 空地 {nfree}", flush=True)
json.dump(full, open(outcfg, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
json.dump(dict(rule=dict(min_room=MIN_ROOM), maps=summ), open(outsum, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
