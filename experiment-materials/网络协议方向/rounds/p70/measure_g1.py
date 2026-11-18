# 协议第 70 轮 G-1：门口区等待按最近的门拆成“最忙门 / 别的门”，再看那一拍门格空不空（定义见 先量_非最忙门门口等_事先写定.md）
# 用法：python -I -B measure_g1.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
from collections import deque
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27'))
import ipfix_account as A

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
    P = []; cross = collections.Counter(); occ = [set() for _ in range(T)]
    for i in range(N):
        acts, pos = A.sim(o, i); P.append((acts, pos))
        for t in range(T):
            v = pos[t]
            if v in dlab:
                occ[t].add(dlab[v])
                if t > 0 and pos[t - 1] not in dlab: cross[dlab[v]] += 1
    g0 = cross.most_common(1)[0][0]
    tot = 0; c = collections.Counter()
    for i in range(N):
        acts, pos = P[i]
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
            side = 'busiest' if g == g0 else 'other'
            c[side] += 1
            if g not in occ[t]: c[side + '_empty'] += 1
    r = {k: c[k] / tot for k in ('busiest', 'busiest_empty', 'other', 'other_empty')}
    r.update(inst=inst, completed=o['numTaskFinished'], doors=nd, doors_used=len(cross), busiest_cross_frac=cross[g0] / sum(cross.values()))
    return r

if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, map(str, fs)))
    keys = ('busiest', 'busiest_empty', 'other', 'other_empty', 'busiest_cross_frac')
    avg = {k: sum(r[k] for r in res) / len(res) for k in keys}
    s1 = avg['other'] >= 0.02; s2 = avg['other_empty'] >= 0.02
    Path(sys.argv[2]).write_text(json.dumps(dict(mean_17=avg, step1_pass=s1, step2_pass=s2, skip=not (s1 and s2), per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], r['doors_used'], {k: round(100 * r[k], 2) for k in keys})
    print('17 图平均', {k: round(100 * v, 2) for k, v in avg.items()}, '→', '跳过' if not (s1 and s2) else '不跳过')
