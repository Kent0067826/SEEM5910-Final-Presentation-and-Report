"""Round 29: held-out maps WITH single-lane cuts (bridges), generated before the round-29 development batch was run on them
(they are never used for development). Two families:
  room*: room maps like the official room-64-64-16 (walls every S cells, 1-cell doors), but the room graph is sparse:
         a random spanning tree plus extra adjacencies (prob 0.25); each adjacency gets 2 doors (prob 0.6) or 1 door.
         A tree adjacency with a single door is a single-lane cut. The first seed (from a fixed list) whose map has at
         least one bridge with both parts >= 5% of the free cells is kept; the number of rejected seeds is recorded.
  zone*: open areas with 10% random obstacles, separated by solid walls and joined only by 1-cell-wide corridors."""
import sys, json, random; sys.path.insert(0, '/home/claude/proj/v10/maps_new'); sys.path.insert(0, '/home/claude/proj/v10/maps_r25')
from gen_maps import write_instance, connected, free_cells
from collections import deque

def bridges(G, frac=0.05):
    H, W = len(G), len(G[0]); F = [(r, c) for r in range(H) for c in range(W) if G[r][c] == '.']; S = set(F); N = len(F)
    def parts_without(block):
        seen = set(block); sizes = []
        for s in F:
            if s in seen: continue
            q = deque([s]); seen.add(s); n = 0
            while q:
                r, c = q.popleft(); n += 1
                for u in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                    if u in S and u not in seen: seen.add(u); q.append(u)
            sizes.append(n)
        return sorted(sizes, reverse=True)
    out = []
    for v in F:   # brute force is fine for 64x64 (only cells with <= 2 opposite free neighbours can be cuts here)
        r, c = v; nb = [u for u in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)) if u in S]
        if len(nb) > 3: continue
        p = parts_without({v})
        if len(p) >= 2 and p[1] >= frac * N: out.append((v, p[:3]))
    return out

def sparse_room_map(N, S, seed, extra=0.25, p2=0.6):
    rnd = random.Random(seed)
    G = [['.'] * N for _ in range(N)]
    walls = list(range(0, N, S))
    for w in walls:
        for i in range(N): G[w][i] = '@'; G[i][w] = '@'
    k = len(walls)                      # rooms are (i, j), i, j in 0..k-1
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
        if i2 == i + 1:   # horizontal wall at row walls[i+1], columns of room j
            w = walls[i + 1]; lo, hi = walls[j] + 1, min(walls[j] + S, N) - 1
            for c in rnd.sample(range(lo, hi + 1), nd): G[w][c] = '.'
        else:             # vertical wall at column walls[j+1], rows of room i
            w = walls[j + 1]; lo, hi = walls[i] + 1, min(walls[i] + S, N) - 1
            for r in rnd.sample(range(lo, hi + 1), nd): G[r][w] = '.'
    assert connected(G)
    return G

def zone_map(N, cuts, corridor_len, seed, p=0.10):
    """cuts: column positions where a solid wall of thickness corridor_len starts; each wall gets one 1-cell corridor."""
    rnd = random.Random(seed)
    G = [['@' if rnd.random() < p else '.' for _ in range(N)] for _ in range(N)]
    for c0 in cuts:
        for r in range(N):
            for c in range(c0, c0 + corridor_len): G[r][c] = '@'
        row = rnd.randint(4, N - 5)
        for c in range(c0 - 1, c0 + corridor_len + 1): G[row][c] = '.'
        for dc in (-2, -1, corridor_len, corridor_len + 1):     # keep both corridor mouths open
            for dr in (-1, 0, 1): G[row + dr][c0 + dc] = '.'
    # keep the largest connected component
    F = [(r, c) for r in range(N) for c in range(N) if G[r][c] == '.']; best = set(); seen = set()
    for s in F:
        if s in seen: continue
        comp = {s}; q = deque([s]); seen.add(s)
        while q:
            r, c = q.popleft()
            for u in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if 0 <= u[0] < N and 0 <= u[1] < N and G[u[0]][u[1]] == '.' and u not in seen: seen.add(u); comp.add(u); q.append(u)
        if len(comp) > len(best): best = comp
    for r in range(N):
        for c in range(N):
            if G[r][c] == '.' and (r, c) not in best: G[r][c] = '@'
    assert connected(G); return G

if __name__ == '__main__':
    specs = {}; log = {}
    for name, S, seeds in [('roomP', 16, range(29001, 29100)), ('roomQ', 16, range(29101, 29200)),
                           ('roomR', 13, range(29201, 29300)), ('roomS', 13, range(29301, 29400))]:
        for k, sd in enumerate(seeds):
            G = sparse_room_map(64, S, sd); B = bridges(G)
            if B: break
        log[name] = {'seed': sd, 'rejected_seeds': k, 'bridge_cells': [[list(v), p] for v, p in B]}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.055 * free), round(0.07 * free)], 29500 + len(specs), ntasks=4000)
    for name, cuts, L, sd in [('zoneA', [26], 4, 29601), ('zoneB', [20, 42], 2, 29602)]:
        G = zone_map(64, cuts, L, sd); B = bridges(G)
        log[name] = {'seed': sd, 'rejected_seeds': 0, 'bridge_cells': [[list(v), p] for v, p in B]}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.05 * free), round(0.07 * free)], 29700 + len(specs), ntasks=4000)
    json.dump(specs, open('instances.json', 'w'), indent=1); json.dump(log, open('generation_log.json', 'w'), indent=1)
    print(json.dumps(specs)); print(json.dumps({k: (v['seed'], v['rejected_seeds'], len(v['bridge_cells'])) for k, v in log.items()}))
