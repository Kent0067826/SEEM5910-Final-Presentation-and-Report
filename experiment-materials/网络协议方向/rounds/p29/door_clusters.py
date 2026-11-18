# 协议第 29 轮补充：门挨得多近——两扇门的门格之间（走空地）不超过 6 步，就算它们的“路由器”重叠，合成一簇。
# 只读地图和第一遍的过门计数（model_measure.json），不跑新运行。用法：python -I -B door_clusters.py 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27')); sys.path.insert(0, str(Path(__file__).resolve().parent))
import ipfix_account as A
from model_measure import structure
from model_measure2 import bfs
R = 6
M1 = {r['inst']: r for r in json.load(open(Path(__file__).resolve().parent / 'model_measure.json', encoding='utf8'))}
rows = []
for inst in sorted(A.CFG):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    S, dcells, big = structure(dlab, nd, rlab); doors = [int(g) for g in S['door_rooms']]
    near = collections.defaultdict(set)
    for g in doors:
        dd = bfs(F, list(dcells[g]), limit=R)
        for v, d in dd.items():
            if v in dlab and dlab[v] != g and dlab[v] in doors: near[g].add(dlab[v])
    lab = {}; k = 0
    for g in doors:
        if g in lab: continue
        st = [g]; lab[g] = k
        while st:
            x = st.pop()
            for y in near[x]:
                if y not in lab: lab[y] = k; st.append(y)
        k += 1
    size = collections.Counter(lab.values()); pbd = {int(a): b for a, b in M1[inst]['passes_by_door'].items()}
    tot = sum(pbd.get(g, 0) for g in doors)
    clustered = sum(pbd.get(g, 0) for g in doors if size[lab[g]] > 1)
    rows.append(dict(inst=inst, doors=len(doors), clusters=k, multi=sum(1 for c, s in size.items() if s > 1),
                     doors_in_multi=sum(1 for g in doors if size[lab[g]] > 1), cross_in_multi=clustered / max(1, tot), biggest=max(size.values())))
for r in rows: print(f"{r['inst']:12s} 门 {r['doors']:2d} → 簇 {r['clusters']:2d}（多门簇 {r['multi']:2d}，在多门簇里的门 {r['doors_in_multi']:2d}，最大簇 {r['biggest']} 扇）  在多门簇里过的门占 {r['cross_in_multi']*100:5.1f}%")
n = len(rows)
print(f"17 图平均：在多门簇里的门 {sum(r['doors_in_multi']/r['doors'] for r in rows)/n*100:.1f}%，在多门簇里过的门 {sum(r['cross_in_multi'] for r in rows)/n*100:.1f}%")
json.dump(rows, open(sys.argv[1], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
