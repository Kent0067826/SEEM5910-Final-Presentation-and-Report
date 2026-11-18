"""割的"时延"：领任务 -> 走到割的门所用时间。
模型（只用地图）：要穿过割进入 s 侧的任务，取货点在另一侧均匀分布；
  T_free(s) = 第 1 段（约 25 拍，派单挑近的机器人）+ 从取货点到门的自由流最短时间的平均。
与回放实测的平均时延比，得到一个全局的"变慢倍数"（故障 + 互相让路）。"""
import heapq, sys, json, statistics
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG, flow

DR = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def time_to_cells(g, targets):
    """从所有格到 targets 中任一格的最短时间（前进 3 拍，转向 3 拍；反向 Dijkstra，到达时朝向不限）。"""
    H, W = len(g), len(g[0])
    best = {}; pq = []
    for (r, c) in targets:
        for o in range(4): pq.append((0, r, c, o))
    heapq.heapify(pq)
    # 反向图：状态 (r,c,o) 表示"站在 (r,c) 朝向 o"，前驱：从 (r-dr, c-dc) 朝 o 前进而来；或同格转向
    while pq:
        d, r, c, o = heapq.heappop(pq)
        if (r, c, o) in best: continue
        best[(r, c, o)] = d
        for no in ((o + 1) % 4, (o + 3) % 4):
            if (r, c, no) not in best: heapq.heappush(pq, (d + 3, r, c, no))
        pr, pc = r - DR[o][0], c - DR[o][1]
        if 0 <= pr < H and 0 <= pc < W and g[pr][pc] == '.' and (pr, pc, o) not in best:
            heapq.heappush(pq, (d + 3, pr, pc, o))
    out = {}
    for (r, c, o), d in best.items():
        out[(r, c)] = min(out.get((r, c), 1e18), d)
    return out


def cut_latency_free(mapf, leg1=25):
    """每个割、每个进入方向的模型时延（拍）。"""
    g = RG.read_map(mapf); G = RG.analyse(mapf); lab = flow.room_lookup(mapf)
    res = []
    for c in flow.cut_list(G):
        cells = [tuple(x) for d in c['doors'] for x in G['doors'][d]['cells']]
        tt = time_to_cells(g, cells)
        sides = {}
        for s in set(c['side'].values()):
            src = [v for v, rm in lab.items() if c['side'].get(rm) != s and v in tt]   # 取货点在另一侧
            sides[s] = leg1 + statistics.mean(tt[v] for v in src)
        res.append(dict(kind=c['kind'], doors=c['doors'], small=c['small'], T_into=sides, side=c['side']))
    return res
