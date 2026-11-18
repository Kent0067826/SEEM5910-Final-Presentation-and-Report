# 协议第 35 轮：每扇门过门数和门口 3 步内的等待拍（前 1000 拍 / 之后），比较分道和 LCAP 同一局。
# 用法：python -I -B diag_alldoors.py 分道输出.json LCAP输出.json
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim

def stats(f):
    inst = Path(f).stem.split('_LCAP')[0].split('_PICK')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    near = {}
    for g in range(nd):
        cs = {v for v in dlab if dlab[v] == g}; s = set(cs); fr = set(cs)
        for _ in range(3):
            fr = {u for (a, b) in fr for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if F(*u)} - s; s |= fr
        for v in s: near.setdefault(v, []).append(g)
    ps = collections.defaultdict(lambda: [0, 0]); wt = collections.defaultdict(lambda: [0, 0]); idle = [0, 0]
    for i in range(N):
        pos, _ = sim(o, i); t = 0
        while t < T:
            v = pos[t]
            if v in dlab:
                g = dlab[v]; t0 = t
                while t < T and pos[t] in dlab and dlab[pos[t]] == g: t += 1
                b = pos[t0 - 1] if t0 else None; a = pos[t] if t < T else None
                if b and a and b not in dlab and a not in dlab and b != a: ps[g][t0 >= 1000] += 1
                continue
            t += 1
        for t in range(1, T):
            if pos[t] == pos[t - 1]:
                for g in near.get(pos[t], []): wt[g][t >= 1000] += 1
    return ps, wt, nd

a = stats(sys.argv[1]); b = stats(sys.argv[2])
print('door  pick:pass(<1000,>=1000) wait  |  lcap:pass wait')
rows = sorted(range(a[2]), key=lambda g: -(b[0][g][1] + a[0][g][1]))
for g in rows[:14]:
    print(g, a[0][g], a[1][g], '|', b[0][g], b[1][g])
print('sum pass', [sum(a[0][g][k] for g in a[0]) for k in (0, 1)], [sum(b[0][g][k] for g in b[0]) for k in (0, 1)])
print('sum wait', [sum(a[1][g][k] for g in a[1]) for k in (0, 1)], [sum(b[1][g][k] for g in b[1]) for k in (0, 1)])
