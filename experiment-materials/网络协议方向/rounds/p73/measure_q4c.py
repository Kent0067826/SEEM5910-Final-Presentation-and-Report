# 协议第 73 轮 Q-4 补充二（事后加，不改判）：“别处”不在故障的长站立按离最近门格的步数分桶。前一版：站立段里去掉自己在故障的拍，再分“四邻有故障车”与否。原 Q-4：看门狗会抓的长站立段（有任务、不在故障、同一格站满 300 拍）按位置拆（定义见 先量_Q4_长站立在哪_事先写定.md）
# 用法：python -I -B measure_q4.py 完整输出目录 输出.json
import json, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27')); sys.path.insert(0, str(R / 'rounds' / 'p35')); sys.path.insert(0, str(R / 'rounds' / 'p39'))
import ipfix_account as A
from diag_collapse import sim
from measure_idle_block import task_series
K = 300

def one(f):
    inst = Path(f).stem.split('_LCAPWD')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    tot = {'door': 0, 'apron': 0, 'else': 0}; eps = {'door': 0, 'apron': 0, 'else': 0}; nofault = {'door': 0, 'apron': 0, 'else': 0}; nbfault = {'door': 0, 'apron': 0, 'else': 0}
    from collections import deque
    dd = {v: 0 for v in dlab}; q = deque(dlab)
    while q:
        v = q.popleft(); a, b = v
        for u in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if F(*u) and u not in dd: dd[u] = dd[v] + 1; q.append(u)
    bk = lambda d: 'd4_6' if d <= 6 else 'd7_12' if d <= 12 else 'd13p'
    dist_b = {'d4_6': 0, 'd7_12': 0, 'd13p': 0}
    PP = [sim(o, i)[0] for i in range(N)]; DL = []
    for i in range(N):
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        DL.append(dl)
    import collections
    dcell = [set() for _ in range(T)]
    for j in range(N):
        for t in range(T):
            if DL[j][t]: dcell[t].add(PP[j][t])
    for i in range(N):
        P = PP[i]; S = task_series(o['actualSchedule'][i], T); dl = DL[i]
        s = 0; fired = False
        def close(end):
            v = P[s]; k = 'door' if v in dlab else 'apron' if v in apron else 'else'
            tot[k] += end - s; eps[k] += 1
            a, b = v; nb = ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1))
            for t in range(s, end):
                if not dl[t]:
                    nofault[k] += 1
                    if k == 'else': dist_b[bk(dd.get(v, 99))] += 1
                    if any(u in dcell[t] for u in nb): nbfault[k] += 1
        for t in range(1, T):
            if P[t] != P[t-1]:
                if fired: close(t)
                s = t; fired = False
            if not fired and t - s >= K and S[t] >= 0 and not dl[t]: fired = True
        if fired: close(T)
    return dict(inst=inst, completed=o['numTaskFinished'], **{k + '_share': v / (N * T) for k, v in tot.items()}, **{k + '_eps': v for k, v in eps.items()}, **{k + '_nofault': v / (N * T) for k, v in nofault.items()}, **{k + '_nbfault': v / (N * T) for k, v in nbfault.items()}, **{k: v / (N * T) for k, v in dist_b.items()})

if __name__ == '__main__':
    fs = sorted(str(f) for f in Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, fs))
    keys = ('else_nofault', 'd4_6', 'd7_12', 'd13p')
    avg = {k: sum(r[k] for r in res) / len(res) for k in keys}
    Path(sys.argv[2]).write_text(json.dumps(dict(K=K, mean_17=avg, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], {k: round(100 * r[k], 2) for k in keys})
    print('MEAN', {k: round(100 * v, 3) for k, v in avg.items()}, '')
