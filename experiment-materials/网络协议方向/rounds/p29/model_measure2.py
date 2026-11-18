# 协议第 29 轮（建模研究）第二遍：修正第一遍“等的是谁”的分类，再加三样。只读第 27 轮完整轨迹，不跑新运行。
# 第一遍的问题：用“30 拍内要进门”判断去门的车，排队超过 30 拍的车被算成“不相干的车”。这一遍改成按“同一任务里下一扇要进的门”判断：
#   门里的车 / 刚出门的车（出门 30 拍内）/ 去这扇门的车（同一任务里下一扇门就是它，150 拍内）/ 去别的门的车 / 房间里干活的车。
# 新加：① 最忙门每拍的状态（空 / 正放 A→B / 正放 B→A），“门空着、门口 3 步内却有去这扇门的车在等”的拍数（链路空着但路由器喂不上）；
#       去这扇门的车在门口 3 步内等的时候，门在干什么（放对面 / 放同向 / 空着）。
#       ② 所有门的门口开销：每次过门前，在那扇门 3 步内、8 步内花的拍数（等/转身/故障/前进），按门的种类（1 格/2 格，桥/非桥，
#       LCAP 门规则管不管：1 格且（是桥或绕路 ≥ 20 格）算“管”）汇总。③ 每个任务平均过几扇门。
# 用法：python -I model_measure2.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ipfix_account as A
from model_measure import sim2, nb, structure, INF
LOOK = 150; OUT = 30


def bfs(F, srcs, blocked=frozenset(), limit=None):
    dist = {v: 0 for v in srcs}; q = collections.deque(srcs)
    while q:
        v = q.popleft()
        if limit is not None and dist[v] >= limit: continue
        for u in nb(v):
            if F(*u) and u not in dist and u not in blocked: dist[u] = dist[v] + 1; q.append(u)
    return dist


def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    S, dcells, big = structure(dlab, nd, rlab)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
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
    per_door = collections.Counter(p[1] for p in passes)
    gs = per_door.most_common(1)[0][0]; gset = set(dcells[gs])
    # 门的种类：宽度、是不是桥、绕路多远（堵住这扇门后两侧门口格之间的最短路 − 2）
    kind = {}
    for g in range(nd):
        cs = dcells[g]; side = [u for v in cs for u in nb(v) if u in rlab and rlab[u] in big]
        rs = sorted({rlab[u] for u in side})
        if len(rs) < 2: continue
        a = next(u for u in side if rlab[u] == rs[0]); b = next(u for u in side if rlab[u] == rs[1])
        dd = bfs(F, [a], blocked=frozenset(cs), limit=80).get(b)
        det = (dd - 2) if dd is not None else 999
        br = g in S['bridges']; wd = len(cs)
        kind[g] = dict(width=wd, bridge=br, detour=det, managed=(wd == 1 and (br or det >= 20)))
    # 每台车：下一次进门（任意门）的时间和门号；上一次出最忙门的时间
    NXT_T, NXT_G, LE = [], [], []
    ent = collections.defaultdict(dict); ext_s = collections.defaultdict(set)
    for i, g, t0, t1, b, a in passes:
        ent[i][t0] = g
        if g == gs: ext_s[i].add(t1)
    for i in range(N):
        nt = [INF] * T; ng = [-1] * T; c, cg = INF, -1
        for t in range(T - 1, -1, -1):
            nt[t] = c; ng[t] = cg
            if t in ent[i]: c, cg = t, ent[i][t]
        le = [-INF] * T; c = -INF
        for t in range(T):
            if t in ext_s[i]: c = t
            le[t] = c
        NXT_T.append(nt); NXT_G.append(ng); LE.append(le)

    def rel(i, t):
        pos = P[i][1]
        if pos[t] in gset: return '门里的车'
        if t - LE[i][t] < OUT: return '刚出门的车'
        nt = NXT_T[i][t]
        if nt < INF and nt - t <= LOOK and CUR[i][t] >= 0 and CUR[i][nt - 1] == CUR[i][t]:
            return '去这扇门的车' if NXT_G[i][t] == gs else '去别的门的车'
        return '房间里干活的车'
    dist = bfs(F, list(gset), limit=40)

    def band(d):
        return '门格' if d == 0 else ('门口1-3步' if d <= 3 else ('近处4-8步' if d <= 8 else ('中间9-15步' if d <= 15 else '远处16步以上')))
    occ = [dict() for _ in range(T)]
    for i in range(N):
        pos = P[i][1]
        for t in range(T): occ[t][pos[t]] = i
    # 最忙门每拍的状态
    gp = [p for p in passes if p[1] == gs]
    state = [None] * T
    for i, g, t0, t1, b, a in gp:
        for t in range(t0, min(t1, T)): state[t] = rlab[b]
    waits = collections.Counter(); demand_idle = 0; demand_any = 0; mouth_wait_state = collections.Counter()
    for t in range(T):
        dem = False
        for v, i in occ[t].items():
            if dist.get(v, INF) <= 3 and v not in gset and rel(i, t) == '去这扇门的车': dem = True; break
        if dem:
            demand_any += 1
            if state[t] is None: demand_idle += 1
    for i in range(N):
        acts, pos = P[i]; cur = CUR[i]; dl = DEL[i]
        nxt = [None] * T; c = None
        for t in range(T - 1, -1, -1):
            if t + 1 < T and pos[t + 1] != pos[t]: c = pos[t + 1]
            nxt[t] = c
        for t in range(T):
            dv = dist.get(pos[t], INF)
            if dv > 15 or dv == 0 or dl[t] or cur[t] < 0 or acts[t] != 'W': continue
            r = rel(i, t); bd = band(dv)
            j = occ[t].get(nxt[t]) if nxt[t] is not None else None
            if j is None: bt = '空着（规则或执行器让它等）'
            elif DEL[j][t]: bt = '挡路车在故障'
            elif CUR[j][t] < 0: bt = '挡路车没任务'
            else: bt = rel(j, t)
            waits[(bd, r, bt)] += 1
            if r == '去这扇门的车' and dv <= 3:
                my = rlab.get(pos[t])
                mouth_wait_state['门空着' if state[t] is None else ('门在放同向' if state[t] == my else '门在放对面')] += 1
    # 所有门的门口开销（每次过门前，同一任务内、最多 150 拍）
    dfield = {g: bfs(F, list(dcells[g]), limit=8) for g in kind}
    over = collections.defaultdict(collections.Counter); ncross = collections.Counter()
    for i, g, t0, t1, b, a in passes:
        if g not in kind: continue
        acts, pos = P[i]; cur = CUR[i]; dl = DEL[i]; k = kind[g]
        key = ('1格' if k['width'] == 1 else '2格') + ('·管' if k['managed'] else '·不管')
        ncross[key] += 1; t = t0 - 1; k0 = cur[t0 - 1] if t0 > 0 else -1
        while t >= 0 and t0 - t <= LOOK and cur[t] == k0 and NXT_T[i][t] == t0:
            dv = dfield[g].get(pos[t], INF)
            if dv <= 8:
                st = '故障' if dl[t] else ('转身' if acts[t] in 'RC' else ('前进' if acts[t] == 'F' else '等'))
                over[(key, '3步内' if dv <= 3 else '4-8步')][st] += 1
            t -= 1
    tot = N * T
    return dict(inst=inst, robots=N, T=T, completed=o['numTaskFinished'], passes_all=len(passes), cross_per_task=len(passes) / max(1, o['numTaskFinished']),
                busiest_door=gs, busiest_kind=kind.get(gs), door_kinds=dict(collections.Counter(('1格' if k['width'] == 1 else '2格') + ('·管' if k['managed'] else '·不管') for k in kind.values())),
                demand_ticks=demand_any / T, demand_idle_ticks=demand_idle / T, door_idle=sum(1 for s in state if s is None) / T,
                mouth_wait_state=dict(mouth_wait_state), waits={'|'.join(k): v for k, v in waits.items()},
                over={'|'.join(k): dict(v) for k, v in over.items()}, ncross=dict(ncross), robot_ticks=tot)


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')):
        r = one(fp.name.split('_LCAP_')[0], fp); rows.append(r)
        print(r['inst'], round(r['cross_per_task'], 2), r['door_kinds'], round(r['door_idle'], 3), round(r['demand_ticks'], 3), round(r['demand_idle_ticks'], 3), flush=True)
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
