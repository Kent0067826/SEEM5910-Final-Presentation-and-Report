# 协议第 35 轮：从一台长期不动的车出发，沿“朝向前方那格的车”往下追，看等待链（每台车：位置、朝向、从哪拍起不动、故障区间、手上任务）。
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim
f, start, t = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
inst = Path(f).stem.split('_LCAP')[0].split('_PICK')[0]
h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
P = [sim(o, i) for i in range(N)]
at = {P[i][0][t]: i for i in range(N)}
acts = {i: A.expand(o['actualPaths'][i]) for i in range(N)}
def since(i):
    k = t
    while k > 0 and P[i][0][k - 1] == P[i][0][t] and P[i][1][k - 1] == P[i][1][t]: k -= 1
    return k
ev = {}
for e in o['events']: ev.setdefault(e[2] if len(e) > 2 else None, []).append(e)
x = start; seen = []
while x is not None and x not in seen:
    seen.append(x); (r, c), d = P[x][0][t], P[x][1][t]
    u = (r + A.MV[d][0], c + A.MV[d][1])
    dl = [iv for iv in o['delayIntervals'][x] if iv[0] <= t + 500 and iv[-1] >= since(x) - 50] if o['delayIntervals'][x] else []
    sched = o['actualSchedule'][x]
    print(f'agent {x} at {(r, c)} {"ESWN"[d]} still since {since(x)} kind={"door" if (r,c) in dlab else ("apron" if (r,c) in apron else "room")} '
          f'acts[{since(x)}:{since(x)+8}]={"".join(acts[x][since(x):since(x)+8])} front={u} free={F(*u)} delays={str(dl)[:120]} sched={str(sched)[:160]}')
    x = at.get(u)
