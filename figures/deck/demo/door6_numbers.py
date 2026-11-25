"""Recompute where door 6's numbers come from (slides 8 and 10-11), from the map, the competition settings and the runs.

1. Free trip to door 6: reverse Dijkstra over (cell, heading) from the door-6 cells, a move or a 90-degree turn = 3 ticks
   (competition setting agentCounter = 3) -- the same model as cut_tfree() in window_control.cpp. Mean over every free cell
   on each side of door 6, plus 25 ticks for the first leg (robot -> pickup; measured mean 28, median 21 in round 41,
   archive/workspace/netmodel_r41/model_data/legs.json). The planner uses 247 ticks inward and 158 outward.
2. Breakdowns, from the problem file's delayConfig (poisson events, pDelay, uniform minDelay-maxDelay): new breakdowns per
   tick = N x pDelay, each lasting (min+max)/2 on average, so the share of robots stopped at any time is pDelay x mean
   duration, and a trip that needs T free ticks takes T / (1 - share) -- the slowdown from breakdowns alone.
3. Door rate measured in the 5 timing runs (door_timing.py): crossings per 500 ticks, and how they split by direction.
4. The slowdown 2.23, from the round-40 measurement (experiment-materials/archive/workspace/netmodel_r41/model_data/
   latency_pairs.json): for every cut door and direction, the measured mean time from getting an order that crosses the door
   to reaching it, divided by the free-flow time; median over the runs with breakdowns, and over the same test without.
Writes figures/deck/demo/door6_numbers.json.  Usage (repo root):  python3 figures/deck/demo/door6_numbers.py"""
import heapq, json, os, sys
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_demo as bd
import door_timing as dt

LEG1, TICK = 25, 3


def free_times(free, door_cells):
    H, W = free.shape; n = H * W
    DR = [(0, 1), (1, 0), (0, -1), (-1, 0)]          # heading 0..3: east, south, west, north (as DRo = {1, C, -1, -C})
    INF = 10 ** 9; dist = np.full((n, 4), INF, np.int64); pq = []
    for (r, c) in door_cells:
        for o in range(4):
            dist[r * W + c, o] = 0; heapq.heappush(pq, (0, r * W + c, o))
    while pq:
        d, v, o = heapq.heappop(pq)
        if d != dist[v, o]: continue
        for no in ((o + 1) % 4, (o + 3) % 4):                        # turn on the spot
            if d + TICK < dist[v, no]: dist[v, no] = d + TICK; heapq.heappush(pq, (d + TICK, v, no))
        r, c = divmod(v, W); pr, pc = r - DR[o][0], c - DR[o][1]      # the cell that reaches v by moving forward with heading o
        if 0 <= pr < H and 0 <= pc < W and free[pr, pc]:
            p = pr * W + pc
            if d + TICK < dist[p, o]: dist[p, o] = d + TICK; heapq.heappush(pq, (d + TICK, p, o))
    return dist.min(1).reshape(H, W)


def sides(free, door_cells):
    H, W = free.shape; blocked = set(map(tuple, door_cells)); comp = -np.ones((H, W), int); k = 0
    for r0 in range(H):
        for c0 in range(W):
            if not free[r0, c0] or comp[r0, c0] >= 0 or (r0, c0) in blocked: continue
            st = [(r0, c0)]; comp[r0, c0] = k
            while st:
                r, c = st.pop()
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and free[rr, cc] and comp[rr, cc] < 0 and (rr, cc) not in blocked:
                        comp[rr, cc] = k; st.append((rr, cc))
            k += 1
    return comp


def main():
    H, W, free = bd.load_map(); rg = json.loads(bd.RG.read_text())
    door6 = [d for d in rg['doors'] if d['id'] == 6][0]; cells = [tuple(c) for c in door6['cells']]
    t = free_times(free, cells); comp = sides(free, cells)
    sizes = {k: int((comp == k).sum()) for k in range(comp.max() + 1)}
    small = min(sizes, key=sizes.get)                                   # the lower-left side (cut off by door 6)
    mean_small = float(t[comp == small].mean()); mean_big = float(t[(comp >= 0) & (comp != small)].mean())
    prob = json.loads((Path(os.environ.get('DEMO_WORK', '/home/user/simbuild/demo')) / 'timing' / '9700' / 'prob.json').read_text()) \
        if (Path(os.environ.get('DEMO_WORK', '/home/user/simbuild/demo')) / 'timing' / '9700' / 'prob.json').exists() else None
    dc = (prob or {}).get('delayConfig', {'pDelay': 0.01, 'minDelay': 10, 'maxDelay': 30, 'eventModel': 'poisson', 'durationModel': 'uniform'})
    mean_dur = (dc['minDelay'] + dc['maxDelay']) / 2; share = dc['pDelay'] * mean_dur
    # door rate and direction split from the timing runs
    lab = bd.room_labels(free, rg); a, b = door6['rooms']; nin = nout = 0; ticks = 0
    for s in dt.SEEDS:
        tt, fin, loc, has = bd.load_dump(dt.WORK / str(s) / 'pos.bin')
        ev = dt.events(loc, lab, a, b); ticks += len(tt)
        for _, d in ev: nin, nout = (nin + 1, nout) if d == 0 else (nin, nout + 1)
    lp = json.loads((HERE.parents[2] / 'experiment-materials/archive/workspace/netmodel_r41/model_data/latency_pairs.json').read_text())
    def med(nd):
        r = sorted(p['T_meas'] / p['T_free'] for p in lp if p['method'] == 'C24CF' and p['inst'].endswith('_nd') == nd and p['T_meas'])
        return len(r), round(float(np.median(r)), 2)
    (n_f, m_f), (n_nf, m_nf) = med(False), med(True)
    d6 = {p['inst'] + ' ' + p['side']: [round(p['T_free'], 1), round(p['T_meas'], 1)] for p in lp if p['doors'] == [6] and p['method'] == 'C24CF'}
    lower_left_room = a if (comp[tuple(np.argwhere(lab.reshape(H, W) == a)[0])] == small) else b
    res = dict(
        free_trip=dict(model='reverse Dijkstra over (cell, heading), move or 90-degree turn = 3 ticks, mean over all free cells of a side',
                       inward_from_far_side=round(mean_big, 1), outward_from_lower_left=round(mean_small, 1), leg1=LEG1,
                       T_inward=round(LEG1 + mean_big, 1), T_outward=round(LEG1 + mean_small, 1), cells_far=sizes and int(((comp >= 0) & (comp != small)).sum()),
                       cells_lower_left=sizes[small], planner_uses=dict(inward=247, outward=158)),
        breakdowns=dict(config=dc, robots=250, new_per_tick=250 * dc['pDelay'], mean_duration=mean_dur, share_stopped=round(share, 3),
                        own_stops_slowdown=round(1 / (1 - share), 3)),
        slowdown=dict(source='round 40, champion assignment (C24CF): measured mean time order -> door / free-flow time, per cut door and direction',
                      median_with_breakdowns=m_f, cases_with=n_f, median_without_breakdowns=m_nf, cases_without=n_nf,
                      share_of_extra_time_from_breakdowns=round((m_f - m_nf) / (m_f - 1), 2),
                      door6_free_vs_measured=d6, planner_uses=2.23),
        door_rate=dict(runs=len(dt.SEEDS), ticks=int(ticks), crossings=nin + nout, per_500=round((nin + nout) / ticks * 500, 1),
                       into_lower_left=nin if lower_left_room == b else nout, out_of_lower_left=nout if lower_left_room == b else nin,
                       planner_uses_per_500=26))
    (HERE / 'door6_numbers.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
