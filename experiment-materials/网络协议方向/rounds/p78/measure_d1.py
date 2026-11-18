# D-1 先量（口径见 先量_事先写定.md）。用法：python -I -B measure_d1.py 完整轨迹目录 门清单目录 输出.json
import json, sys, collections
from pathlib import Path
from collections import deque
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
import ipfix_account as A
fd, ld, outp = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
APR = 2; SHARE = 0.15; ABS = 0.001
def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron3, F = A.doors_rooms(h, w, free)
    real = {tuple(map(int, l.split())) for l in (ld / f'{inst}.txt').read_text().split('\n') if l.strip()}
    gid = {v: dlab[v] for v in real if v in dlab}
    near = {v: (0, g) for v, g in gid.items()}; q = deque(gid)
    while q:
        v = q.popleft(); d, g = near[v]
        if d >= APR: continue
        a, b = v
        for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if F(*u) and u not in near and u not in dlab: near[u] = (d + 1, g); q.append(u)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    R = []
    for i in range(N):
        acts, pos = A.sim(o, i)
        sched = [(int(x.split(':')[0]), int(x.split(':')[1])) for x in o['actualSchedule'][i].split(',') if x]
        task = [False] * T; j = 0
        for t in range(T):
            while j + 1 < len(sched) and sched[j + 1][0] <= t: j += 1
            task[t] = bool(sched) and sched[0][0] <= t and sched[j][1] >= 0
        delay = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): delay[t] = True
        nxt = [None] * T; nd_ = [-1] * T; np_, ndoor = None, -1
        for t in range(T - 1, -1, -1):
            if t + 1 < T and pos[t + 1] != pos[t]: np_ = pos[t + 1]
            if t + 1 < T and pos[t + 1] in dlab and pos[t + 1] != pos[t]: ndoor = dlab[pos[t + 1]] if pos[t + 1] in gid else -2
            if pos[t] in dlab: ndoor_here = ndoor
            nxt[t] = np_; nd_[t] = ndoor
            if pos[t] in dlab and (t == 0 or pos[t - 1] not in dlab): ndoor = dlab[pos[t]] if pos[t] in gid else -2
        R.append((acts, pos, task, delay, nxt, nd_))
    occ = [dict() for _ in range(T)]
    for i, (acts, pos, *_r) in enumerate(R):
        for t in range(T): occ[t][pos[t]] = i
    wait = collections.Counter(); hol = collections.Counter(); passes = collections.defaultdict(collections.Counter)
    for i, (acts, pos, task, delay, nxt, nd_) in enumerate(R):
        prev_room = None; t = 0
        while t < T:
            v = pos[t]
            if v in rlab: prev_room = rlab[v]
            if v in gid:
                g = gid[v]; t0 = t
                while t < T and pos[t] in gid and gid[pos[t]] == g: t += 1
                if t < T and pos[t] in rlab and prev_room is not None and rlab[pos[t]] != prev_room: passes[g][prev_room] += 1
                continue
            t += 1
        for t in range(T):
            v = pos[t]
            if v not in near or near[v][0] == 0 or not task[t] or delay[t] or acts[t] != 'W': continue
            g = near[v][1]; wait[g] += 1
            if nd_[t] != g or nxt[t] is None: continue
            j = occ[t].get(nxt[t])
            if j is None or j == i: continue
            aj, pj, tj, dj, xj, ndj = R[j]
            if aj[t] == 'W' and ndj[t] != g: hol[g] += 1
    tot = N * T; rows = []
    for g in sorted(set(gid.values())):
        p = passes[g]; n = sum(p.values()); two = (n - max(p.values())) / n if n else 0.0
        sh = hol[g] / wait[g] if wait[g] else 0.0
        pick = sh >= SHARE and hol[g] >= ABS * tot
        rows.append(dict(door=g, passes=n, two_way=round(two, 3), wait=wait[g], hol=hol[g], hol_share=round(sh, 3), pick=pick))
    up = sum(r['hol'] for r in rows if r['pick']) / tot
    allh = sum(r['hol'] for r in rows) / tot; allw = sum(r['wait'] for r in rows) / tot
    return dict(inst=inst, doors=len(rows), picked=sum(r['pick'] for r in rows), apron_wait=allw, hol_all=allh, upper=up, rows=rows)
res = []
for f in sorted(fd.glob('*_LCAPWD_9700_103.json')):
    inst = f.name.split('_LCAPWD_')[0]; r = one(inst, f); res.append(r)
    print(f"{inst:12s} 真门 {r['doors']:3d} 选中 {r['picked']:2d}  门口等 {100*r['apron_wait']:.2f}%  队首阻塞 {100*r['hol_all']:.2f}%  选中门上限 {100*r['upper']:.2f}%", flush=True)
summ = dict(mean_apron_wait=sum(r['apron_wait'] for r in res) / len(res), mean_hol=sum(r['hol_all'] for r in res) / len(res),
            mean_upper=sum(r['upper'] for r in res) / len(res), maps_with_pick=sum(r['picked'] > 0 for r in res))
print(json.dumps(summ, ensure_ascii=False))
json.dump(dict(rule=dict(apron=APR, share=SHARE, abs=ABS), summary=summ, maps=res), open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
