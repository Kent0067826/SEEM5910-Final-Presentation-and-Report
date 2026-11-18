"""Round 22: generate NEW maps of the same families (never used for tuning).
Room maps follow the MovingAI/LoRR room layout: walls every S cells (including row/col 0), doors in wall segments.
Mazes are random perfect mazes with corridor width w and wall thickness 1. Starts/tasks are random free cells (2 errands)."""
import random, json, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.chdir(HERE)   # 生成的文件写在本文件夹
from collections import deque

def write_map(name, G):
    H, W = len(G), len(G[0])
    open(f'{name}.map', 'w').write('type octile\nheight %d\nwidth %d\nmap\n' % (H, W) + '\n'.join(''.join(r) for r in G) + '\n')

def free_cells(G): return [r * len(G[0]) + c for r in range(len(G)) for c in range(len(G[0])) if G[r][c] == '.']

def connected(G):
    F = free_cells(G); W = len(G[0]); S = set(F)
    if not F: return False
    seen = {F[0]}; q = deque([F[0]])
    while q:
        v = q.popleft(); r, c = divmod(v, W)
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            u = (r+dr) * W + (c+dc)
            if 0 <= r+dr < len(G) and 0 <= c+dc < W and u in S and u not in seen: seen.add(u); q.append(u)
    return len(seen) == len(F)

def room_map(N, S, door_w, seed, extra_door_p=0.3):
    rnd = random.Random(seed)
    G = [['.'] * N for _ in range(N)]
    walls = list(range(0, N, S))
    for w in walls:
        for i in range(N): G[w][i] = '@'; G[i][w] = '@'
    # each wall segment between two crossings gets 1 door (sometimes 2), door_w cells wide
    for w in walls:
        for a in walls:
            lo, hi = a + 1, min(a + S, N) - 1          # segment cells lo..hi
            if hi - lo + 1 < door_w: continue
            for _ in range(1 + (rnd.random() < extra_door_p)):
                p = rnd.randint(lo, hi - door_w + 1)
                for k in range(door_w):
                    G[w][p + k] = '.'                   # door in the horizontal wall at row w
            for _ in range(1 + (rnd.random() < extra_door_p)):
                p = rnd.randint(lo, hi - door_w + 1)
                for k in range(door_w):
                    G[p + k][w] = '.'                   # door in the vertical wall at column w
    assert connected(G)
    return G

def maze_map(N, w, seed):
    rnd = random.Random(seed); pitch = w + 1; n = (N - 1) // pitch
    G = [['@'] * N for _ in range(N)]
    def carve(cr, cc):
        r0, c0 = 1 + cr * pitch, 1 + cc * pitch
        for r in range(r0, r0 + w):
            for c in range(c0, c0 + w): G[r][c] = '.'
    seen = {(0, 0)}; stack = [(0, 0)]; carve(0, 0)
    while stack:
        cr, cc = stack[-1]
        nb = [(cr+dr, cc+dc) for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if 0 <= cr+dr < n and 0 <= cc+dc < n and (cr+dr, cc+dc) not in seen]
        if not nb: stack.pop(); continue
        nr, nc = rnd.choice(nb); seen.add((nr, nc)); carve(nr, nc)
        # open the wall between (cr,cc) and (nr,nc)
        if nr != cr:
            r = 1 + max(cr, nr) * pitch - 1
            for c in range(1 + cc * pitch, 1 + cc * pitch + w): G[r][c] = '.'
        else:
            c = 1 + max(cc, nc) * pitch - 1
            for r in range(1 + cr * pitch, 1 + cr * pitch + w): G[r][c] = '.'
        stack.append((nr, nc))
    assert connected(G)
    return G

def write_instance(name, G, agent_counts, seed, ntasks=2000):
    write_map(name, G); F = free_cells(G); rnd = random.Random(seed)
    starts = rnd.sample(F, max(agent_counts))
    open(f'{name}.agents', 'w').write('# version for LoRR 2026\n%d\n' % len(starts) + '\n'.join(map(str, starts)) + '\n')
    tasks = []
    for _ in range(ntasks):
        a = rnd.choice(F); b = rnd.choice(F)
        while b == a: b = rnd.choice(F)
        tasks.append(f'{a},{b}')
    open(f'{name}.tasks', 'w').write('# version for LoRR 2026\n%d\n' % ntasks + '\n'.join(tasks) + '\n')
    tpl = json.load(open(HERE.parent / 'room' / 'room250.json'))   # 沿用官方房间实例的故障设置
    out = {}
    for n in agent_counts:
        t = dict(tpl); t.update(mapFile=f'{name}.map', agentFile=f'{name}.agents', taskFile=f'{name}.tasks', teamSize=n)
        json.dump(t, open(f'{name}_{n}.json', 'w'), indent=1); out[f'{name}_{n}'] = n
    return len(F), out

if __name__ == '__main__':
    specs = {}
    for name, G in [('roomA', room_map(64, 16, 1, 22001)),      # same family as the official room map, new random doors
                    ('roomB', room_map(64, 8, 1, 22002)),       # smaller rooms (64 rooms), 1-cell doors
                    ('roomC', room_map(64, 16, 3, 22003))]:     # same room size, doors 3 cells wide (wider bottlenecks)
        free = sum(r.count('.') for r in G)
        specs[name] = write_instance(name, G, [round(0.055 * free), round(0.07 * free)], 22100 + len(specs))
    for name, G in [('mazeA', maze_map(32, 2, 22011)),          # same family as the official maze: 2-cell corridors
                    ('mazeB', maze_map(32, 3, 22012))]:         # wider corridors (3 cells)
        free = sum(r.count('.') for r in G)
        specs[name] = write_instance(name, G, [round(0.06 * free), round(0.09 * free)], 22200 + len(specs))
    json.dump(specs, open('instances.json', 'w'), indent=1); print(json.dumps(specs))
