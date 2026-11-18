"""Generalization test maps: random-door 4x4 room maps (64x64, walls every 16 cells = 4x4 rooms, like the official room map).

The door generator is the project's own `sparse_room_map` (copied unchanged from
experiment-materials/网络协议方向/harness/data/maps_r29/gen_r29.py): the 16 rooms are joined by a random spanning tree
plus extra adjacencies (prob 0.25); each joined wall gets 1 door cell, or 2 door cells (prob 0.6), at random positions.
Every seed is kept (no filtering), so the maps are not picked to suit the method.
Starts and tasks are random free cells, written the same way as maps_p75/gen_p75.py; robot counts follow the official
room map's density (200 and 250 robots on 3646 free cells)."""
import json, random, sys
from collections import deque
from pathlib import Path
OUT = Path(__file__).resolve().parent / 'maps_gen4x4'

def connected(G):
    W = len(G[0]); F = [r * W + c for r in range(len(G)) for c in range(W) if G[r][c] == '.']; S = set(F)
    seen = {F[0]}; q = deque([F[0]])
    while q:
        v = q.popleft(); r, c = divmod(v, W)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u = (r + dr) * W + (c + dc)
            if 0 <= r + dr < len(G) and 0 <= c + dc < W and u in S and u not in seen: seen.add(u); q.append(u)
    return len(seen) == len(F)

def sparse_room_map(N, S, seed, extra=0.25, p2=0.6):          # copied from maps_r29/gen_r29.py
    rnd = random.Random(seed)
    G = [['.'] * N for _ in range(N)]
    walls = list(range(0, N, S))
    for w in walls:
        for i in range(N): G[w][i] = '@'; G[i][w] = '@'
    k = len(walls)
    edges = [((i, j), (i + 1, j)) for i in range(k - 1) for j in range(k)] + [((i, j), (i, j + 1)) for i in range(k) for j in range(k - 1)]
    rnd.shuffle(edges); parent = {}
    def find(x):
        while parent.get(x, x) != x: x = parent[x]
        return x
    chosen = []
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb; chosen.append((a, b))
        elif rnd.random() < extra: chosen.append((a, b))
    for (i, j), (i2, j2) in chosen:
        nd = 2 if rnd.random() < p2 else 1
        if i2 == i + 1:
            w = walls[i + 1]; lo, hi = walls[j] + 1, min(walls[j] + S, N) - 1
            for c in rnd.sample(range(lo, hi + 1), nd): G[w][c] = '.'
        else:
            w = walls[j + 1]; lo, hi = walls[i] + 1, min(walls[i] + S, N) - 1
            for r in rnd.sample(range(lo, hi + 1), nd): G[r][w] = '.'
    assert connected(G)
    return G

TPL = {"numTasksReveal": 1.5, "version": "2026 LoRR", "agentCounter": 3, "agentSize": 1.0,
       "delayConfig": {"seed": 0, "minDelay": 10, "maxDelay": 30, "eventModel": "poisson", "pDelay": 0.01,
                       "durationModel": "uniform", "gaussMeanRatio": 0.5, "gaussStdRatio": 0.22}}   # same as official room250.json

def main(n_maps=8, seed0=2611001):
    OUT.mkdir(exist_ok=True); inst = {}
    for i in range(n_maps):
        name = f'roomGen{chr(65 + i)}'; seed = seed0 + i
        G = sparse_room_map(64, 16, seed)
        W = len(G[0]); F = [r * W + c for r in range(64) for c in range(W) if G[r][c] == '.']
        (OUT / f'{name}.map').write_text('type octile\nheight 64\nwidth 64\nmap\n' + '\n'.join(''.join(r) for r in G) + '\n')
        rnd = random.Random(seed + 1000)
        counts = [round(200 / 3646 * len(F)), round(250 / 3646 * len(F))]
        starts = rnd.sample(F, max(counts))
        (OUT / f'{name}.agents').write_text('# version for LoRR 2026\n%d\n' % len(starts) + '\n'.join(map(str, starts)) + '\n')
        tasks = []
        for _ in range(4000):
            a = rnd.choice(F); b = rnd.choice(F)
            while b == a: b = rnd.choice(F)
            tasks.append(f'{a},{b}')
        (OUT / f'{name}.tasks').write_text('# version for LoRR 2026\n4000\n' + '\n'.join(tasks) + '\n')
        doors = sum(1 for r in range(64) for c in range(64) if G[r][c] == '.' and (r % 16 == 0 or c % 16 == 0))
        for n in counts:
            t = dict(TPL, mapFile=f'{name}.map', agentFile=f'{name}.agents', taskFile=f'{name}.tasks', teamSize=n)
            (OUT / f'{name}_{n}.json').write_text(json.dumps(t, indent=1))
            inst[f'{name}_{n}'] = dict(mapfile=str(OUT / f'{name}_{n}.json'), team=n, seed=seed, free=len(F), door_cells=doors)
        print(name, seed, 'free', len(F), 'door cells', doors, 'robots', counts)
    (OUT / 'instances.json').write_text(json.dumps(inst, indent=1))

if __name__ == '__main__':
    main()
