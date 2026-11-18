# 协议第 29 轮（建模研究）第四遍：所有门的“路由器”细节。只读第 27 轮完整轨迹，不跑新运行。
# ① 去某扇门的车在那扇门 3 步内等的时候，挡它的是谁（按门的种类汇总）：前面也是去这扇门的车（再分它在转身 / 前进 / 等 / 故障）、
#    门里的车、刚出这扇门的车、别的车、没任务的车、前面空着（规则或执行器扣着）。
# ② 门口格（门两侧紧挨门的那一格；1 格宽的门每侧只有这一格能进门）上的停留：去这扇门的车站在门口格上时在干什么；
#    其中“站着不动时开始故障”的次数和故障拍数（这段时间这一侧的门就被堵死）。
# ③ 车在门格里每次过门花的拍数（前进 / 转身 / 等 / 故障），1 格门和 2 格门分开。
# 用法：python -I model_measure4.py 完整输出目录 输出.json
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
    kind = {}
    for g in range(nd):
        cs = dcells[g]; side = [u for v in cs for u in nb(v) if u in rlab and rlab[u] in big]
        rs = sorted({rlab[u] for u in side})
        if len(rs) < 2: continue
        a = next(u for u in side if rlab[u] == rs[0]); b = next(u for u in side if rlab[u] == rs[1])
        dd = bfs(F, [a], blocked=frozenset(cs), limit=80).get(b)
        det = (dd - 2) if dd is not None else 999; br = g in S['bridges']; wd = len(cs)
        kind[g] = ('1格' if wd == 1 else '2格') + ('·管' if (wd == 1 and (br or det >= 20)) else '·不管')
    mouth = {}   # 门口格 -> 门
    for g in kind:
        for v in dcells[g]:
            for u in nb(v):
                if u in rlab: mouth[u] = g
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
    occ = [dict() for _ in range(T)]
    for i in range(N):
        pos = P[i][1]
        for t in range(T): occ[t][pos[t]] = i

    def bound(i, t):
        g = NXT_G[i][t]; nt = NXT_T[i][t]
        if g < 0 or nt - t > LOOK or CUR[i][t] < 0 or CUR[i][nt - 1] != CUR[i][t]: return -1
        return g
    blk = collections.defaultdict(collections.Counter); mouthst = collections.defaultdict(collections.Counter)
    mouth_fault_starts = collections.Counter(); mouth_fault_ticks = collections.Counter()
    for i in range(N):
        acts, pos = P[i]; dl = DEL[i]
        nx = [None] * T; c = None
        for t in range(T - 1, -1, -1):
            if t + 1 < T and pos[t + 1] != pos[t]: c = pos[t + 1]
            nx[t] = c
        for t in range(T):
            g = bound(i, t)
            if g < 0 or g not in kind: continue
            d = dfield[g].get(pos[t])
            if d is None or d == 0: continue
            st = '故障' if dl[t] else ('转身' if acts[t] in 'RC' else ('前进' if acts[t] == 'F' else '等'))
            if mouth.get(pos[t]) == g:
                mouthst[kind[g]][st] += 1
                if dl[t]:
                    mouth_fault_ticks[kind[g]] += 1
                    if t > 0 and not dl[t - 1] and acts[t - 1] != 'F': mouth_fault_starts[kind[g]] += 1
            if st != '等': continue
            j = occ[t].get(nx[t]) if nx[t] is not None else None
            if j is None: b = '前面空着（规则或执行器扣着）'
            elif pos[t] in dlab or (nx[t] in dlab and dlab[nx[t]] == g): b = '门里的车'
            elif DEL[j][t]: b = '前车在故障'
            elif CUR[j][t] < 0: b = '没任务的车'
            elif LE[j][t][1] == g and t - LE[j][t][0] < OUT: b = '刚出这扇门的车'
            elif bound(j, t) == g:
                aj = P[j][0][t]; b = '同去这扇门的车（它在' + ('转身' if aj in 'RC' else ('前进' if aj == 'F' else '等')) + '）'
            else: b = '别的车'
            blk[kind[g]][b] += 1
    inside = collections.defaultdict(collections.Counter); npass = collections.Counter()
    for i, g, t0, t1, b, a in passes:
        if g not in kind: continue
        acts = P[i][0]; dl = DEL[i]; npass[kind[g]] += 1
        for t in range(t0, min(t1, T)):
            inside[kind[g]]['故障' if dl[t] else ('转身' if acts[t] in 'RC' else ('前进' if acts[t] == 'F' else '等'))] += 1
    return dict(inst=inst, blockers={k: dict(v) for k, v in blk.items()}, mouth_state={k: dict(v) for k, v in mouthst.items()},
                mouth_fault_starts=dict(mouth_fault_starts), mouth_fault_ticks=dict(mouth_fault_ticks),
                inside={k: dict(v) for k, v in inside.items()}, npass=dict(npass), robot_ticks=N * T)


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')):
        r = one(fp.name.split('_LCAP_')[0], fp); rows.append(r); print(r['inst'], r['npass'], flush=True)
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    # 汇总
    agg = lambda key: (lambda acc: [acc[k].update(v) for r in rows for k, v in r[key].items()] and acc)(collections.defaultdict(collections.Counter))
    blk = collections.defaultdict(collections.Counter); ms = collections.defaultdict(collections.Counter); ins = collections.defaultdict(collections.Counter)
    npass = collections.Counter(); mfs = collections.Counter(); mft = collections.Counter()
    for r in rows:
        for k, v in r['blockers'].items(): blk[k].update(v)
        for k, v in r['mouth_state'].items(): ms[k].update(v)
        for k, v in r['inside'].items(): ins[k].update(v)
        npass.update(r['npass']); mfs.update(r['mouth_fault_starts']); mft.update(r['mouth_fault_ticks'])
    lines = []
    for k in sorted(npass):
        tb = sum(blk[k].values()); lines.append(f'{k}：过门 {npass[k]} 次。3 步内等待每次过门 {tb/npass[k]:.1f} 拍，挡它的：' + '，'.join(f'{b} {v/tb*100:.0f}%' for b, v in sorted(blk[k].items(), key=lambda x: -x[1])))
        tm = sum(ms[k].values()); lines.append(f'    站在门口格上每次过门 {tm/npass[k]:.1f} 拍：' + '，'.join(f'{s} {v/npass[k]:.1f}' for s, v in sorted(ms[k].items())) + f'；站着不动时开始故障 {mfs[k]} 次（每 100 次过门 {mfs[k]/npass[k]*100:.1f} 次）')
        ti = sum(ins[k].values()); lines.append(f'    门格里每次过门 {ti/npass[k]:.1f} 拍：' + '，'.join(f'{s} {v/npass[k]:.1f}' for s, v in sorted(ins[k].items())))
    open(outp.replace('.json', '_summary.txt'), 'w', encoding='utf8').write('\n'.join(lines))
