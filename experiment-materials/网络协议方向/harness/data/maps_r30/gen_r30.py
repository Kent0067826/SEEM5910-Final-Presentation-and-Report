"""Round 30: held-out maps for the round-30 confirmation, generated before any round-30 development run.
Sparse room maps (same generator as round 29: random spanning tree of the room graph + extra adjacencies with prob 0.25,
each adjacency 2 doors with prob p2 else 1 door, 1-cell doors), NOT conditioned on having a cut: whatever the seed gives is kept.
Seeds are taken in order; nothing is rejected."""
import sys, json; sys.path.insert(0, '/home/claude/proj/v10/maps_new'); sys.path.insert(0, '/home/claude/proj/v10/maps_r29')
from gen_maps import write_instance
from gen_r29 import sparse_room_map, bridges
if __name__ == '__main__':
    specs = {}; log = {}
    for name, S, sd, p2 in [('roomT', 16, 30001, 0.6), ('roomU', 16, 30002, 0.6), ('roomV', 13, 30003, 0.6),
                            ('roomW', 13, 30004, 0.6), ('roomX', 16, 30005, 0.3), ('roomY', 11, 30006, 0.6)]:
        G = sparse_room_map(64, S, sd, p2=p2); B = bridges(G)
        log[name] = {'seed': sd, 'S': S, 'p2': p2, 'bridge_cells': [[list(v), p] for v, p in B]}
        free = sum(r.count('.') for r in G); specs[name] = write_instance(name, G, [round(0.055 * free), round(0.07 * free)], 30500 + len(specs), ntasks=4000)
    json.dump(specs, open('instances.json', 'w'), indent=1); json.dump(log, open('generation_log.json', 'w'), indent=1)
    print(json.dumps(specs)); print({k: (v['seed'], len(v['bridge_cells'])) for k, v in log.items()})
