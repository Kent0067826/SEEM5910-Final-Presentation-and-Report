"""第 41 轮 / 第 4a 步：用网络模型算 5000 步内完成数的上限，和实测对照。

两类上限：
  (A) 自由流上限：N 台机器人互不干扰、每单只走第 2 段（取货 -> 送货）的最短时间。
      最短时间按 MAPF_T 动作模型精确算：前进一格 3 拍，原地转 90° 3 拍（带朝向的 Dijkstra）。
      D_free = N * H / E[第 2 段最短时间]。
  (B) 割的上限：割 c 的有效带宽 C_c（每拍可穿越几次），每单要穿越它的概率 f_c（均匀假设，只用地图）。
      任务池里始终有 B = 1.5N 个已公开的任务，可以先做不过割的任务、把过割的攒在池里（缓冲）。
      设 H 步内完成 D 单，其中过割的 X 单 <= C_c*H；公开过的任务 D+B 里有 (1-f_c) 比例不过割，
      所以 D - X <= (1-f_c)(D+B)，得 D <= (C_c*H + (1-f_c)*B) / f_c。
  上限 = min(A, 所有割的 B)。
门的有效带宽用第 40 轮实测的平台值：1 格门 26、2 格门 32（每 500 拍，C24CF、有故障）。"""
import json, sys, heapq, random, os, collections
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG, flow

C_DOOR = {1: 26 / 500, 2: 32 / 500}
C_DOOR_ND = {1: 43 / 500, 2: 50 / 500}     # 无故障时（门 6 实测 42.7；2 格门粗估，见说明）
DR = [(0, 1), (1, 0), (0, -1), (-1, 0)]


def free_time_sampler(g, rng, n_src=60):
    """带朝向的最短时间（拍）。从 n_src 个随机起点各做一次 Dijkstra，返回 {起点: 到各格的最短时间}。"""
    H, W = len(g), len(g[0]); cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] == '.']
    out = {}
    for s in rng.sample(cells, n_src):
        dist = {}
        pq = [(0, s[0], s[1], o) for o in range(4)]
        best = {}
        while pq:
            d, r, c, o = heapq.heappop(pq)
            if best.get((r, c, o), 1e18) <= d: continue
            best[(r, c, o)] = d
            if (r, c) not in dist: dist[(r, c)] = d
            for no in ((o + 1) % 4, (o + 3) % 4):
                if best.get((r, c, no), 1e18) > d + 3: heapq.heappush(pq, (d + 3, r, c, no))
            rr, cc = r + DR[o][0], c + DR[o][1]
            if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == '.' and best.get((rr, cc, o), 1e18) > d + 3:
                heapq.heappush(pq, (d + 3, rr, cc, o))
        out[s] = dist
    return out, cells


def bounds(mapf, N, H=5000, reveal=1.5, cdoor=C_DOOR, seed=0):
    g = RG.read_map(mapf); G = RG.analyse(mapf)
    rng = random.Random(seed)
    D, cells = free_time_sampler(g, rng)
    ts = [d[t] for s, d in D.items() for t in rng.sample(cells, 200) if t in d]
    Tleg2 = sum(ts) / len(ts)
    free = N * H / Tleg2
    B = reveal * N
    cuts = []
    for c in flow.cut_list(G):
        p = c['small_cells'] / (c['small_cells'] + c['big_cells']); f = 2 * p * (1 - p)
        C = sum(cdoor[min(2, G['doors'][d]['width'])] for d in c['doors'])
        cuts.append(dict(kind=c['kind'], doors=c['doors'], p=p, f=f, C500=C * 500, bound=(C * H + (1 - f) * B) / f,
                         bound_noB=C * H / f))
    cuts.sort(key=lambda x: x['bound'])
    return dict(N=N, Tleg2=Tleg2, free=free, B=B, cuts=cuts, bound=min([free] + [c['bound'] for c in cuts]),
                tight=(cuts[0] if cuts and cuts[0]['bound'] < free else None))
