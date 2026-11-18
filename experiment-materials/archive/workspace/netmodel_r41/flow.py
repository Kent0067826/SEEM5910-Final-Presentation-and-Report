"""第 41 轮 / 网络建模第 3 步：任务 → 流量。

每个任务 = 先去取货点、再去送货点。一台机器人做一单要走两段：
  第 1 段：从领任务时所在位置 -> 取货点（取决于派单，派单通常挑离取货点近的机器人）；
  第 2 段：取货点 -> 送货点（完全由任务本身决定）。
一个割每完成一单平均被穿越几次 = f_c，它就是这个割的"流量份额"。

这里算三种 f_c：
  (1) 任务文件：第 2 段穿越的比例（用真实任务算）；
  (2) 均匀假设：取货、送货点在所有房间格里均匀分布时，第 2 段穿越的概率 2p(1-p)（只用地图，不偷看任务）；
  (3) 回放实测：每完成一单，实际穿越几次（分第 1 段、第 2 段、空闲时）。"""
import json, collections, sys, os, gzip, bisect
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG
import replay


def read_cells(path, W):
    L = [l.strip() for l in open(path) if l.strip() and not l.startswith('#')]
    n = int(L[0]); out = []
    for l in L[1:n + 1]:
        v = [int(x) for x in l.split(',')]
        out.append([(x // W, x % W) for x in v])
    return out


def cut_list(g):
    """所有单门割和门对：(种类, 门列表, 每个房间在哪一侧, 小侧编号)。"""
    cuts = []
    for kind, ds in [('单门割', [b['door']]) for b in g['bridges']] + [('门对', p['doors']) for p in g['door_pairs']]:
        parts = RG.side_sizes(g['rooms'], g['doors'], set(ds))
        side = {}
        for i, p in enumerate(parts):
            for rm in p['rooms']: side[rm] = i
        small = min(range(len(parts)), key=lambda i: parts[i]['cells'])
        cuts.append(dict(kind=kind, doors=ds, side=side, small=small, small_cells=parts[small]['cells'],
                         big_cells=sum(p['cells'] for i, p in enumerate(parts) if i != small)))
    return cuts


def room_lookup(mapf):
    g = RG.read_map(mapf); R, D, odd, room_of = RG.build(g)
    lab = dict(room_of)
    for d in D:      # 门格归到它连着的第一个房间（任务点几乎不会落在门格上）
        for c in d['cells']: lab.setdefault(tuple(c), d['rooms'][0])
    return lab


def task_flow(inst_json, g, lab):
    d = json.load(open(inst_json)); base = os.path.dirname(inst_json)
    tasks = read_cells(os.path.join(base, d['taskFile']), g['W'])
    cuts = cut_list(g); free = sum(r['size'] for r in g['rooms'])
    out = []
    for c in cuts:
        side = c['side']; n2 = 0
        for t in tasks:
            a, b = lab.get(t[0]), lab.get(t[-1])
            if a is None or b is None: continue
            n2 += side[a] != side[b]
        p = c['small_cells'] / (c['small_cells'] + c['big_cells'])
        out.append(dict(kind=c['kind'], doors=c['doors'], small_frac=p, leg2_task=n2 / len(tasks), leg2_uniform=2 * p * (1 - p)))
    # 房间 -> 房间矩阵（第 2 段）
    M = collections.Counter()
    for t in tasks:
        a, b = lab.get(t[0]), lab.get(t[-1])
        if a is not None and b is not None: M[(a, b)] += 1
    return out, M, len(tasks)


def replay_flow(row, out_gz, g, lab):
    """回放实测：每个割、每完成一单，被穿越几次，按段分。"""
    o = json.load(gzip.open(out_gz))
    sched = []
    for s in o['actualSchedule']:
        v = []
        for part in s.split(','):
            if part: t, k = part.split(':'); v.append((int(t), int(k)))
        sched.append(v)
    first_done = {}       # (agent, task) -> 第 1 个任务点完成时刻
    for t, a, tid, seq in o['events']:
        if seq == 1: first_done.setdefault((a, tid), t)
    cuts = cut_list(g)
    done = o['numTaskFinished']
    res = []
    for c in cuts:
        side = c['side']; cnt = collections.Counter()
        for ag, did, ra, rb, t_ap, t_in, t_out, t_as in row['crossings']:
            if did not in c['doors'] or side.get(ra) == side.get(rb): continue
            times = [x[0] for x in sched[ag]]; j = bisect.bisect_right(times, t_in) - 1
            task = sched[ag][j][1] if j >= 0 else -1
            if task < 0: cnt['空闲'] += 1
            elif first_done.get((ag, task), 10 ** 9) <= t_in: cnt['第2段'] += 1
            else: cnt['第1段'] += 1
        res.append(dict(kind=c['kind'], doors=c['doors'], per_task={k: v / max(1, done) for k, v in cnt.items()},
                        total=sum(cnt.values()) / max(1, done)))
    return res, done
