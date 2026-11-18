# 协议第 73 轮 Q-4 补充四（改正计数错误）：站立段里只计“有任务且不在故障”的拍（前几版把领到任务前那段空闲站着也算进去了，偏大）。补充三：“别处”不在故障的长站立分：四邻有别的车（排队）/ 四邻能走的格都空着（自己停着）。另记这拍最忙门是否“饿着”（门格和门口区都没有干活的车）。前一版：站立段里去掉自己在故障的拍，再分“四邻有故障车”与否。原 Q-4：看门狗会抓的长站立段（有任务、不在故障、同一格站满 300 拍）按位置拆（定义见 先量_Q4_长站立在哪_事先写定.md）
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
    occ = [set() for _ in range(T)]
    for j in range(N):
        for t in range(T): occ[t].add(PP[j][t])
    import collections as C
    cross = C.Counter()
    for j in range(N):
        for t in range(1, T):
            if PP[j][t] in dlab and PP[j][t-1] not in dlab: cross[dlab[PP[j][t]]] += 1
    g = cross.most_common(1)[0][0]; gcells = {v for v, k in dlab.items() if k == g}
    gap = {v for v in apron if any(dd.get(v, 99) == dd2 for dd2 in ())}
    dist_b.update(queue=0, openstand=0, open_starve=0, queue_starve=0)
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
                if not dl[t] and S[t] >= 0:
                    nofault[k] += 1
                    if k == 'else':
                        dist_b[bk(dd.get(v, 99))] += 1
                        nbs = [u for u in nb if F(*u)]
                        qd = any(u in occ[t] for u in nbs)
                        stv = not any(PP[j][t] in gcells for j in range(N))
                        dist_b['queue' if qd else 'openstand'] += 1
                        if stv: dist_b['queue_starve' if qd else 'open_starve'] += 1
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
    keys = ('door_nofault', 'apron_nofault', 'else_nofault', 'queue', 'openstand', 'open_starve', 'd4_6', 'd7_12', 'd13p')
    avg = {k: sum(r[k] for r in res) / len(res) for k in keys}
    Path(sys.argv[2]).write_text(json.dumps(dict(K=K, mean_17=avg, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], {k: round(100 * r[k], 2) for k in keys})
    print('MEAN', {k: round(100 * v, 3) for k, v in avg.items()}, '')
