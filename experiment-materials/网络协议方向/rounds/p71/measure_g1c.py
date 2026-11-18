# 协议第 71 轮 G-1 第一步：门空却在门口等（第 70 轮第三步集合 S），被挡的顺着“挡我的车”追到队头，按队头原因记账。
# 定义见 先量_拆原因_事先写定.md。用法：python -I -B measure_g1c.py 完整输出目录 输出.json
import json, sys, collections, bisect
from pathlib import Path
from collections import deque
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27'))
import ipfix_account as A
K = ('O', 'Q', 'N', 'X', 'head_O', 'head_Q', 'head_N', 'S', 'S_blocked')

def one(f):
    inst = Path(f).stem.split('_LCAPWD')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    near = dict(dlab); q = deque(dlab); dist = {v: 0 for v in dlab}
    while q:
        v = q.popleft()
        if dist[v] >= A.APRON: continue
        a, b = v
        for u in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if F(*u) and u not in dist: dist[u] = dist[v] + 1; near[u] = near[v]; q.append(u)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    P = []; occ = [set() for _ in range(T)]; ent = collections.defaultdict(list)  # 门 -> [(进门时刻, 车, 进门前所在房间)]
    for i in range(N):
        acts, pos = A.sim(o, i); P.append((acts, pos))
        for t in range(T):
            v = pos[t]
            if v in dlab:
                occ[t].add(dlab[v])
                if t > 0 and pos[t - 1] not in dlab: ent[dlab[v]].append((t, i, rlab.get(pos[t - 1])))
    for g in ent: ent[g].sort()
    et = {g: [e[0] for e in L] for g, L in ent.items()}
    at = [dict() for _ in range(T)]
    for i in range(N):
        for t, v in enumerate(P[i][1]): at[t][v] = i
    S = {}  # (i,t) -> (门, 挡我的车或 None)
    tot = 0
    for i in range(N):
        acts, pos = P[i]
        nxt = [None] * T; nmv = [None] * T; d = None; m = None
        for t in range(T - 1, -1, -1):
            if pos[t] in dlab and (t == 0 or pos[t - 1] not in dlab): d = dlab[pos[t]]
            nxt[t] = d
            if t + 1 < T and pos[t + 1] != pos[t]: m = pos[t + 1]
            nmv[t] = m
        sched = [(int(x.split(':')[0]), int(x.split(':')[1])) for x in o['actualSchedule'][i].split(',') if x]
        cur = [-1] * T; j = 0
        for t in range(T):
            while j + 1 < len(sched) and sched[j + 1][0] <= t: j += 1
            cur[t] = sched[j][1] if sched and sched[0][0] <= t else -1
        delay = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): delay[t] = True
        for t in range(T):
            tot += 1
            a = acts[t]; v = pos[t]
            if delay[t] or cur[t] < 0 or a in 'RCF' or v in dlab or v not in apron: continue
            g = near.get(v)
            if g in occ[t] or nxt[t] != g: continue
            bl = at[t].get(nmv[t], i) if nmv[t] is not None else i
            S[(i, t)] = (g, bl if bl != i else None)
    c = collections.Counter()
    def cause(hd, t, g):
        k = bisect.bisect_right(et.get(g, []), t)
        if k >= len(et.get(g, [])): return 'N'
        _, car, room = ent[g][k]
        if car == hd: return 'N'
        return 'Q' if room == rlab.get(P[hd][1][t]) else 'O'
    for (i, t), (g, bl) in S.items():
        c['S'] += 1
        hd = i; cur_bl = bl; n = 0
        if bl is None: c['head_' + cause(i, t, g)] += 1
        else: c['S_blocked'] += 1
        while cur_bl is not None and n < 20:
            s = S.get((cur_bl, t))
            if s is None or s[0] != g: hd = None; break
            hd = cur_bl; cur_bl = s[1]; n += 1
        if hd is None or cur_bl is not None: c['X'] += 1
        else: c[cause(hd, t, g)] += 1
    r = {k: c[k] / tot for k in K}
    r.update(inst=inst, completed=o['numTaskFinished'])
    return r

if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, map(str, fs)))
    avg = {k: sum(r[k] for r in res) / len(res) for k in K}
    dec = 'O 过线：软抢占' if avg['O'] >= 0.01 else ('N 过线：预判放行' if avg['N'] >= 0.01 else '都不到 1.0%：G-1 跳过')
    Path(sys.argv[2]).write_text(json.dumps(dict(mean_17=avg, decision=dec, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], {k: round(100 * r[k], 2) for k in K})
    print('17 图平均', {k: round(100 * v, 2) for k, v in avg.items()}, '→', dec)
