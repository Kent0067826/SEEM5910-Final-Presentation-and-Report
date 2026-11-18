# 协议第 72 轮 N-1：门饿着时全局名额是不是满的（定义见 先量_N1_分层名额_事先写定.md）；门饿着的定义原样取自第 67 轮 measure_starve.py
# 用法：python -B measure_starve.py 完整输出目录 实例表.json 输出.json
import json, sys, collections, bisect
from pathlib import Path
from collections import deque
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27')); sys.path.insert(0, str(R / 'rounds' / 'p35')); sys.path.insert(0, str(R / 'rounds' / 'p39'))
import ipfix_account as A
from diag_collapse import sim
from measure_idle_block import task_series
STEP = 15

def one(args):
    f, capfrac = args
    inst = Path(f).stem.split('_LCAPWD')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    P = [sim(o, i)[0] for i in range(N)]; S = [task_series(o['actualSchedule'][i], T) for i in range(N)]
    dl = [[False] * T for _ in range(N)]
    for i in range(N):
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[i][t] = True
    cross = collections.Counter()
    for i in range(N):
        for t in range(1, T):
            v = P[i][t]
            if v in dlab and P[i][t-1] not in dlab: cross[dlab[v]] += 1
    g = cross.most_common(1)[0][0]
    cells = {v for v, k in dlab.items() if k == g}
    dist = {v: 0 for v in cells}; q = deque(cells)
    while q:
        v = q.popleft()
        if dist[v] >= A.APRON: continue
        a, b = v
        for u in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if F(*u) and u not in dist and u not in dlab: dist[u] = dist[v] + 1; q.append(u)
    ap = {v for v, d in dist.items() if d > 0}
    # 第一步的 c（同 measure_idle.py）
    first = {}
    for i in range(N):
        for x in o['actualSchedule'][i].split(','):
            if x:
                t0, k = map(int, x.split(':'))
                if k >= 0: first[k] = min(first.get(k, 10**9), t0)
    rel_sorted = sorted(t[1] for t in o['tasks']); firsts = sorted(first.get(t[0], 10**9) for t in o['tasks'])
    ts = list(range(0, T, STEP))
    active = [sum(S[i][t] >= 0 for i in range(N)) for t in ts]
    cap = int(capfrac * N) if capfrac else N
    if max(active) > cap + 2: cap = N
    starve = held = both = 0; c_tot = c_on_starve = 0; G = full = 0
    for x, t in enumerate(ts):
        st = not any(P[i][t] in cells for i in range(N)) and not any(P[i][t] in ap and S[i][t] >= 0 and not dl[i][t] for i in range(N))
        pool = bisect.bisect_right(rel_sorted, t) - bisect.bisect_right(firsts, t)
        n = sum(1 for i in range(N) if S[i][t] < 0 and not dl[i][t])
        c = min(n, max(0, pool), max(0, cap - active[x])) if pool > 0 else 0
        gfull = active[x] >= cap; G += st and gfull and pool > 0 and n > 0; full += gfull
        starve += st; held += c > 0; both += st and c > 0; c_tot += c; c_on_starve += c if st else 0
    n = len(ts)
    return dict(inst=inst, completed=o['numTaskFinished'], starve=starve / n, held=held / n, held_and_starve=both / n,
                c_share=c_tot / (N * n), c_on_starve_share=c_on_starve / (N * n), starve_with_held=both / max(1, starve), G=G / n, global_full=full / n, cap=cap, N=N)

if __name__ == '__main__':
    env = json.load(open(sys.argv[2], encoding='utf-8'))
    fs = sorted(Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    jobs = [(str(f), float(env[f.name.split('_LCAPWD_')[0]]['env'].get('ROBOT_ACTIVE_CAP', 0) or 0)) for f in fs]
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, jobs))
    keys = ('starve', 'held_and_starve', 'global_full', 'G')
    avg = {k: sum(r[k] for r in res) / len(res) for k in keys}
    Path(sys.argv[3]).write_text(json.dumps(dict(mean_17=avg, skip=avg['G'] < 0.02, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], {k: round(100 * r[k], 2) for k in keys})
    print('17 图平均', {k: round(100 * v, 2) for k, v in avg.items()}, '→', '跳过' if avg['G'] < 0.02 else '不跳过')
