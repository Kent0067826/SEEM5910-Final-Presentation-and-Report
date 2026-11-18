# 协议第 29 轮（建模研究）第三遍。只读第 27 轮完整轨迹，不跑新运行。
# 更正：events 里 e=1 是“任务派给车”，e=2 是“任务完成”，不是“取到货”。第 27 轮记账和本轮第一遍把 e=1 当成取货，
# 所以“载货前进 / 空车前进”和“过门时有货”的比例都不对。这里按轨迹算：车在派单之后第一次站到第一个任务点的那一拍 = 取到货。
# 量三样：
# ① 门空着、却有车要过这扇门（同一任务里下一扇门就是它，150 拍内，离门 1–3 步）时，离门最近的那台车在干什么——
#    在路上（还没到）/ 转身对准 / 故障 / 等（前面空着 = 规则或执行器扣着）/ 等（被谁挡着）。所有门按种类汇总，最忙门单列。
# ② 跳数膨胀：每个完成的任务实际过了几扇门，和房间图上最少要过几扇门（派单时所在房间 → 取货房间 → 送货房间）相比。
# ③ 更正后的“有货过门”比例，和更正后的载货 / 空车前进占车·拍的比例。
# 用法：python -I model_measure3.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ipfix_account as A
from model_measure import sim2, nb, structure, INF
from model_measure2 import bfs
LOOK = 150; OUT = 30


def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    S, dcells, big = structure(dlab, nd, rlab)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    errand = {t[0]: [(t[2][j], t[2][j + 1]) for j in range(0, len(t[2]), 2)] for t in o['tasks']}
    assign = {}; finish = {}
    for t, a, k, e in o['events']:
        if e == 1: assign[(a, k)] = t
        elif e == 2: finish[(a, k)] = t
    P, CUR, DEL = [], [], []
    for i in range(N):
        acts, pos = sim2(o, i); acts = (acts + ['W'] * T)[:T]; pos = (pos + [pos[-1]] * T)[:T]; P.append((acts, pos))
        sched = [(int(x.split(':')[0]), int(x.split(':')[1])) for x in o['actualSchedule'][i].split(',') if x]
        cur = [-1] * T; j = 0
        for t in range(T):
            while j + 1 < len(sched) and sched[j + 1][0] <= t: j += 1
            cur[t] = sched[j][1] if sched and sched[0][0] <= t else -1
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        CUR.append(cur); DEL.append(dl)
    # 取货时刻：派单后第一次站到第一个任务点
    pickup = {}
    for (a, k), t0 in assign.items():
        e1 = errand[k][0]; pos = P[a][1]; t = max(0, t0)
        while t < T and pos[t] != e1: t += 1
        if t < T: pickup[(a, k)] = t
    passes = []
    for i in range(N):
        pos = P[i][1]; t = 0
        while t < T:
            v = pos[t]
            if v in dlab:
                g = dlab[v]; t0 = t
                while t < T and pos[t] in dlab and dlab[pos[t]] == g: t += 1
                b = pos[t0 - 1] if t0 > 0 else None; a = pos[t] if t < T else None
                if b in rlab and a in rlab and rlab[b] != rlab[a]: passes.append((i, g, t0, t, b, a))
                continue
            t += 1
    per_door = collections.Counter(p[1] for p in passes); gs = per_door.most_common(1)[0][0]
    kind = {}
    for g in range(nd):
        cs = dcells[g]; side = [u for v in cs for u in nb(v) if u in rlab and rlab[u] in big]
        rs = sorted({rlab[u] for u in side})
        if len(rs) < 2: continue
        a = next(u for u in side if rlab[u] == rs[0]); b = next(u for u in side if rlab[u] == rs[1])
        dd = bfs(F, [a], blocked=frozenset(cs), limit=80).get(b)
        det = (dd - 2) if dd is not None else 999; br = g in S['bridges']; wd = len(cs)
        kind[g] = ('1格' if wd == 1 else '2格') + ('·管' if (wd == 1 and (br or det >= 20)) else '·不管')
    # ③ 有货过门、载货/空车前进
    good = collections.Counter(); good_b = collections.Counter(); mv = collections.Counter()
    for i, g, t0, t1, b, a in passes:
        k = CUR[i][t0]
        s = '没任务' if k < 0 else ('有货' if (i, k) in pickup and pickup[(i, k)] <= t0 else '空车去取货')
        good[s] += 1
        if g == gs: good_b[s] += 1
    for i in range(N):
        acts = P[i][0]
        for t in range(T):
            if DEL[i][t] or CUR[i][t] < 0 or acts[t] != 'F': continue
            k = CUR[i][t]; mv['载货前进' if (i, k) in pickup and pickup[(i, k)] <= t else '空车前进'] += 1
    # ① 门空着却有车要过时，最近那台车在干什么
    NXT_T, NXT_G, LE = [], [], []
    ent = collections.defaultdict(dict); ext = collections.defaultdict(dict)
    for i, g, t0, t1, b, a in passes: ent[i][t0] = g; ext[i][t1] = g
    for i in range(N):
        nt = [INF] * T; ng = [-1] * T; c, cg = INF, -1
        for t in range(T - 1, -1, -1):
            nt[t] = c; ng[t] = cg
            if t in ent[i]: c, cg = t, ent[i][t]
        le = [(-INF, -1)] * T; c = (-INF, -1)
        for t in range(T):
            if t in ext[i]: c = (t, ext[i][t])
            le[t] = c
        NXT_T.append(nt); NXT_G.append(ng); LE.append(le)
    dfield = {g: bfs(F, list(dcells[g]), limit=3) for g in kind}
    indoor = collections.defaultdict(set)
    for i in range(N):
        pos = P[i][1]
        for t in range(T):
            if pos[t] in dlab: indoor[(dlab[pos[t]], t)].add(i)
    occ = [dict() for _ in range(T)]
    for i in range(N):
        pos = P[i][1]
        for t in range(T): occ[t][pos[t]] = i
    nearest = {}   # (g, t) -> (距离, 车)
    for i in range(N):
        pos = P[i][1]; cur = CUR[i]
        for t in range(T):
            g = NXT_G[i][t]
            if g < 0 or g not in kind: continue
            nt = NXT_T[i][t]
            if nt - t > LOOK or cur[t] < 0 or cur[nt - 1] != cur[t]: continue
            d = dfield[g].get(pos[t])
            if d is None or d == 0: continue
            key = (g, t)
            if key not in nearest or d < nearest[key][0]: nearest[key] = (d, i)
    NEXT = []
    for i in range(N):
        pos = P[i][1]; nx = [None] * T; c = None
        for t in range(T - 1, -1, -1):
            if t + 1 < T and pos[t + 1] != pos[t]: c = pos[t + 1]
            nx[t] = c
        NEXT.append(nx)

    def who(j, t, g):
        if DEL[j][t]: return '被故障车挡'
        if CUR[j][t] < 0: return '被没任务的车挡'
        lt, lg = LE[j][t]
        if lg == g and t - lt < OUT: return '被刚出这扇门的车挡'
        return '被别的车挡'
    idle = collections.defaultdict(collections.Counter); idle_b = collections.Counter(); dist_c = collections.defaultdict(collections.Counter)
    for (g, t), (d, i) in nearest.items():
        if indoor.get((g, t)): continue
        acts = P[i][0]
        if DEL[i][t]: s = '故障'
        elif acts[t] in 'RC': s = '转身对准'
        elif acts[t] == 'F': s = '在路上（还没到）'
        else:
            j = occ[t].get(NEXT[i][t]) if NEXT[i][t] is not None else None
            s = '等：前面空着（规则或执行器扣着）' if j is None else '等：' + who(j, t, g)
        idle[kind[g]][s] += 1; dist_c[kind[g]][d] += 1
        if g == gs: idle_b[s] += 1
    # ② 跳数膨胀
    rooms = sorted(big); radj = collections.defaultdict(set)
    for g, (a, b) in S['door_rooms'].items(): radj[a].add(b); radj[b].add(a)

    def rd(a, b):
        if a == b: return 0
        dist = {a: 0}; q = collections.deque([a])
        while q:
            x = q.popleft()
            for y in radj[x]:
                if y not in dist:
                    dist[y] = dist[x] + 1
                    if y == b: return dist[y]
                    q.append(y)
        return None
    rdc = {}
    crossings = collections.Counter()
    for i, g, t0, t1, b, a in passes:
        k = CUR[i][t0]
        if k >= 0: crossings[(i, k)] += 1
    infl = collections.Counter(); n_ok = 0; act_sum = 0; min_sum = 0
    for (a, k), tf in finish.items():
        ta = assign.get((a, k))
        if ta is None or ta < 0 or ta >= T: continue
        s0 = P[a][1][min(T - 1, ta)]; e1, e2 = errand[k][0], errand[k][1]
        r0, r1, r2 = rlab.get(s0), rlab.get(e1), rlab.get(e2)
        if None in (r0, r1, r2): continue
        key = (r0, r1, r2)
        if key not in rdc:
            x, y = rd(r0, r1), rd(r1, r2); rdc[key] = None if x is None or y is None else x + y
        m = rdc[key]
        if m is None: continue
        c = crossings.get((a, k), 0); n_ok += 1; act_sum += c; min_sum += m; infl[min(c - m, 6)] += 1
    tot = N * T
    return dict(inst=inst, robots=N, T=T, busiest=gs, busiest_kind=kind.get(gs), goodput_all=dict(good), goodput_busiest=dict(good_b),
                move_split={k: v / tot for k, v in mv.items()}, idle_hol=({k: dict(v) for k, v in idle.items()}), idle_hol_busiest=dict(idle_b),
                idle_dist={k: dict(v) for k, v in dist_c.items()}, ncross_kind=dict(collections.Counter(kind[p[1]] for p in passes if p[1] in kind)),
                hops=dict(tasks=n_ok, actual=act_sum / max(1, n_ok), minimum=min_sum / max(1, n_ok), inflation_hist=dict(infl)))


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')):
        r = one(fp.name.split('_LCAP_')[0], fp); rows.append(r)
        g = r['goodput_all']; gt = max(1, sum(g.values()))
        print(r['inst'], 'loaded%', round(g.get('有货', 0) / gt * 100, 1), 'hops', round(r['hops']['actual'], 2), 'min', round(r['hops']['minimum'], 2), flush=True)
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
