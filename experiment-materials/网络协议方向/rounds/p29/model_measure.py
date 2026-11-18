# 协议第 29 轮（建模研究）：把地图当成网络来量。只读第 27 轮完整轨迹（基线 LCAP，17 图 × 种子 9700 × 规划 101），不跑新运行。
# 量五样：① 房间图（房间=节点、门=链路）有没有环、哪些门是桥；② 最忙门两侧“路由器区”的范围；③ 门附近等待的车被谁挡着
# （去这扇门的车 / 刚出门的车 / 门里的车 / 不相干的车 / 没任务的车 / 故障车 / 空着）；④ 过门车按距离、方位的时间拆分；
# ⑤ 过门时车上有没有货（门的“有效载荷率”）和“车 = 窗口”的利特尔定律核对。
# 用法：python -I model_measure.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
import ipfix_account as A
H = 30                     # 30 拍内要进这扇门 = “去这扇门的车”；30 拍内刚出来 = “刚出门的车”
BANDS = [(1, 3, '门口1-3步'), (4, 8, '近处4-8步'), (9, 15, '中间9-15步'), (16, 10**6, '远处16步以上')]
INF = 10**9


def band(d):
    if d == 0: return '门格'
    for lo, hi, n in BANDS:
        if lo <= d <= hi: return n
    return BANDS[-1][2]


def sim2(o, i):
    MC = o['agentMaxCounter']; r, c, d = o['start'][i]; d = A.DIRS[d]; cnt = 0; pos = []; acts = A.expand(o['actualPaths'][i])
    for a in acts:
        if a != 'W':
            cnt += 1
            if cnt == MC:
                cnt = 0
                if a == 'F': r += A.MV[d][0]; c += A.MV[d][1]
                elif a == 'R': d = (d + 1) % 4
                elif a == 'C': d = (d - 1) % 4
        pos.append((r, c))
    return acts, pos


def nb(v):
    a, b = v
    return ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1))


def structure(dlab, nd, rlab):
    size = collections.Counter(rlab.values()); big = {k for k, s in size.items() if s >= 30}
    cells = collections.defaultdict(list)
    for v, g in dlab.items(): cells[g].append(v)
    edges = []; dead = 0
    for g in range(nd):
        rs = sorted({rlab[u] for v in cells[g] for u in nb(v) if u in rlab and rlab[u] in big})
        if len(rs) >= 2: edges.append((g, rs[0], rs[1]))
        else: dead += 1
    adj = collections.defaultdict(list)
    for g, a, b in edges: adj[a].append((b, g)); adj[b].append((a, g))
    comp = {}; nc = 0
    for v in sorted(big):
        if v in comp: continue
        st = [v]; comp[v] = nc
        while st:
            x = st.pop()
            for y, _ in adj[x]:
                if y not in comp: comp[y] = nc; st.append(y)
        nc += 1
    disc, low, bridges, clock = {}, {}, set(), [0]

    def dfs(u, pe):
        disc[u] = low[u] = clock[0]; clock[0] += 1
        for v, g in adj[u]:
            if g == pe: continue
            if v in disc: low[u] = min(low[u], disc[v])
            else:
                dfs(v, g); low[u] = min(low[u], low[v])
                if low[v] > disc[u]: bridges.add(g)
    for v in sorted(big):
        if v not in disc: dfs(v, -1)
    pair = collections.Counter((a, b) for _, a, b in edges)
    return dict(rooms=len(big), doors=len(edges), dead_end=dead, cyclomatic=len(edges) - len(big) + nc, bridges=sorted(bridges),
                widths=dict(collections.Counter(len(cells[g]) for g, _, _ in edges)), parallel_pairs=sum(1 for k, n in pair.items() if n > 1),
                door_rooms={g: (a, b) for g, a, b in edges}), cells, big


def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    S, dcells, big = structure(dlab, nd, rlab)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    pick = {(a, k): t for t, a, k, e in o['events'] if e == 1}
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
    # 距离场（从最忙门的门格出发）
    dist = {v: 0 for v in gset}; q = collections.deque(gset)
    while q:
        v = q.popleft()
        for u in nb(v):
            if F(*u) and u not in dist: dist[u] = dist[v] + 1; q.append(u)
    area = collections.Counter(band(dist.get((r, c), INF)) for r in range(h) for c in range(w) if free[r][c])
    # 每台车每拍：离下一次进门 / 上一次出门多久
    NE, LE = [], []
    gp = [p for p in passes if p[1] == gs]
    ent = collections.defaultdict(set); ext = collections.defaultdict(set)
    for i, g, t0, t1, b, a in gp: ent[i].add(t0); ext[i].add(t1)
    for i in range(N):
        ne = [INF] * T; c = INF
        for t in range(T - 1, -1, -1):
            ne[t] = c
            if t in ent[i]: c = t
        le = [-INF] * T; c = -INF
        for t in range(T):
            if t in ext[i]: c = t
            le[t] = c
        NE.append(ne); LE.append(le)

    def rel(i, t):
        if P[i][1][t] in gset: return '门里的车'
        if NE[i][t] - t <= H: return '去这扇门的车'
        if t - LE[i][t] < H: return '刚出门的车'
        return '不相干的车'
    occ = [dict() for _ in range(T)]
    for i in range(N):
        pos = P[i][1]
        for t in range(T): occ[t][pos[t]] = i
    waits = collections.Counter(); ticks = collections.Counter(); idle_band = collections.Counter()
    cellwait = collections.defaultdict(lambda: collections.Counter())   # 只存离门 15 步以内的格子，画图用
    for i in range(N):
        acts, pos = P[i]; cur = CUR[i]; dl = DEL[i]
        nxt = [None] * T; c = None
        for t in range(T - 1, -1, -1):
            if t + 1 < T and pos[t + 1] != pos[t]: c = pos[t + 1]
            nxt[t] = c
        for t in range(T):
            dv = dist.get(pos[t], INF); bd = band(dv)
            if dl[t]: st = '故障'
            elif cur[t] < 0: st = '没任务'; idle_band[bd] += 1
            elif acts[t] in 'RC': st = '转身'
            elif acts[t] == 'F': st = '前进'
            else: st = '等'
            r = rel(i, t); ticks[(bd, r, st)] += 1
            if dv <= 15 and st in ('等', '没任务'): cellwait[pos[t]][r if st == '等' else '没任务'] += 1
            if st != '等' or bd == '门格': continue
            j = occ[t].get(nxt[t]) if nxt[t] is not None else None
            if j is None: bt = '空着（规则或执行器让它等）'
            elif DEL[j][t]: bt = '挡路车在故障'
            elif CUR[j][t] < 0: bt = '挡路车没任务'
            else: bt = rel(j, t)
            waits[(bd, r, bt)] += 1
    # 过门车按距离、方位拆分（只看最忙门）
    side = collections.Counter(); side_apron = collections.defaultdict(list); side_turn = collections.defaultdict(list)
    per_band = collections.defaultdict(collections.Counter); goodput = collections.Counter(); occ_time = []
    for i, g, t0, t1, b, a in gp:
        acts, pos = P[i]; cur = CUR[i]; dl = DEL[i]; occ_time.append(t1 - t0)
        k = cur[t0]
        goodput['没任务' if k < 0 else ('有货' if (i, k) in pick and pick[(i, k)] <= t0 else '空车去取货')] += 1
        t = t0 - 1; k0 = cur[t0 - 1] if t0 > 0 else -1
        while t >= 0 and t0 - t <= 150 and cur[t] == k0 and NE[i][t] == t0:
            bd = band(dist.get(pos[t], INF))
            st = '故障' if dl[t] else ('转身' if acts[t] in 'RC' else ('前进' if acts[t] == 'F' else '等'))
            per_band[bd][st] += 1; t -= 1
        dc = next(u for u in nb(b) if u in gset); axis = (dc[0] - b[0], dc[1] - b[1])
        t = t0 - 1
        while t >= 0 and pos[t] == b: t -= 1
        if t < 0: s = '不明'
        else:
            pv = pos[t]; arr = (b[0] - pv[0], b[1] - pv[1])
            s = '直着来' if arr == axis else ('掉头来' if arr == (-axis[0], -axis[1]) else '从侧面来')
        side[s] += 1
        t = t0 - 1
        while t >= 0 and dist.get(pos[t], INF) <= 3: t -= 1
        side_apron[s].append(t0 - 1 - t); side_turn[s].append(sum(1 for u in range(t + 1, t0) if acts[u] in 'RC'))
    np_ = max(1, len(gp))
    seq = sorted(gp, key=lambda p: p[2]); dirs = [rlab[p[4]] for p in seq]
    runs = (1 + sum(1 for x, y in zip(dirs, dirs[1:]) if x != y)) if dirs else 0
    busy = len({t for i in range(N) for t in range(T) if P[i][1][t] in gset}) / T
    Wn = sum(1 for i in range(N) for t in range(T) if CUR[i][t] >= 0) / T; lam = o['numTaskFinished'] / T
    return dict(inst=inst, robots=N, completed=o['numTaskFinished'], T=T, size=[h, w], structure=S, busiest_door=gs,
                busiest_is_bridge=gs in S['bridges'], busiest_rooms=S['door_rooms'].get(gs), door_cells=sorted(gset), door_width=len(gset),
                passes_busiest=len(gp), passes_all=len(passes), passes_share=len(gp) / max(1, len(passes)),
                passes_by_door={str(g): n for g, n in per_door.items()},
                door_busy=busy, occ_mean=sum(occ_time) / np_, batches=runs, batch_mean=len(gp) / max(1, runs),
                area=dict(area), idle_band=dict(idle_band),
                ticks={'|'.join(k): v for k, v in ticks.items()}, waits={'|'.join(k): v for k, v in waits.items()},
                cellwait={f'{v[0]},{v[1]}': dict(c) for v, c in cellwait.items()},
                per_cross_band={bd: {s: c / np_ for s, c in cs.items()} for bd, cs in per_band.items()},
                side={s: c / np_ for s, c in side.items()}, side_apron={s: sum(v) / len(v) for s, v in side_apron.items()},
                side_turn={s: sum(v) / len(v) for s, v in side_turn.items()}, goodput={s: c / np_ for s, c in goodput.items()},
                little=dict(W=Wn, lam=lam, cycle=Wn / lam if lam else 0, robots=N))


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')):
        r = one(fp.name.split('_LCAP_')[0], fp); rows.append(r); S = r['structure']
        print(f"{r['inst']:12s} 房间{S['rooms']:3d} 门{S['doors']:3d} 环数{S['cyclomatic']:3d} 桥{len(S['bridges']):2d} 最忙门是桥:{str(r['busiest_is_bridge']):5s} "
              f"最忙门占过门{r['passes_share']*100:5.1f}% 忙{r['door_busy']*100:5.1f}% 批{r['batch_mean']:.1f} 有货{r['goodput'].get('有货', 0)*100:5.1f}% "
              f"方位 直{r['side'].get('直着来', 0)*100:4.0f}% 侧{r['side'].get('从侧面来', 0)*100:4.0f}% W={r['little']['W']:.0f} 周期{r['little']['cycle']:.0f}", flush=True)
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
