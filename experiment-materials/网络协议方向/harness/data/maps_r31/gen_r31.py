"""Round 31: held-out maps (mixed families), generated before any round-31 development run.
Rooms: sparse room generator of rounds 29-30 (taken in seed order, nothing rejected). Random: 64x64 with 20% / 10% random
obstacles (largest component). Mazes: perfect mazes with 2- and 3-cell corridors (round-22 generator)."""
import sys, json; sys.path.insert(0, '/home/claude/proj/v10/maps_new'); sys.path.insert(0, '/home/claude/proj/v10/maps_r25'); sys.path.insert(0, '/home/claude/proj/v10/maps_r29')
from gen_maps import write_instance, maze_map
from gen_r25 import random_map
from gen_r29 import sparse_room_map, bridges
if __name__ == '__main__':
    specs = {}; log = {}
    for name, S, sd in [('roomZ1', 16, 31001), ('roomZ2', 16, 31002), ('roomZ3', 13, 31003), ('roomZ4', 11, 31004)]:
        G = sparse_room_map(64, S, sd); log[name] = {'seed': sd, 'S': S, 'bridge_cells': len(bridges(G))}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.055 * free), round(0.07 * free)], 31500 + len(specs), ntasks=4000)
    for name, p, sd in [('randF', 0.20, 31011), ('randG', 0.10, 31012)]:
        G = random_map(64, p, sd); log[name] = {'seed': sd, 'p': p}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.06 * free), round(0.09 * free)], 31600 + len(specs), ntasks=4000)
    for name, w, sd in [('mazeI', 2, 31021), ('mazeJ', 3, 31022)]:
        G = maze_map(32, w, sd); log[name] = {'seed': sd, 'w': w}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.06 * free), round(0.09 * free)], 31700 + len(specs), ntasks=4000)
    json.dump(specs, open('instances.json', 'w'), indent=1); json.dump(log, open('generation_log.json', 'w'), indent=1)
    print(json.dumps(specs)); print(log)
