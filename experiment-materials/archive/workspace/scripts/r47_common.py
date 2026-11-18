"""Round 47 (wait-v37): global admission ratio from the network model instead of the hand-set 0.6.
ratio = min(1, KAPPA x Little prediction); Little prediction = lambda_max x 2.23 x (25 + T_leg2) / N, where lambda_max is the
maximum-concurrent-flow steady-state throughput (round 41 model, measured door bandwidths) and T_leg2 the mean free-flow time of the
second leg (round 41 bounds). KAPPA = 1.76 is the median measured ratio saturation-point / prediction of the round-46 sweep.
The ratio is computed from the map and the robot count only (preprocessing) and passed as ROBOT_ACTIVE_CAP; ratio >= 1 -> no cap.
The structural switch ROBOT_ACTIVE_CAP_GATE=2 is kept (the room network model only exists on room-type maps)."""
import sys, json, os
sys.path.insert(0, '/home/claude/proj/v10/scripts'); sys.path.insert(0, '/home/claude/r40'); sys.path.insert(0, '/home/claude/proj/v10/netmodel_r41')
from r46_common import *
_R = V + 'maps_r47/'
for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items():
    for _k, _v in _d.items(): INST[_k] = (_R + _k + '.json', _v)
HELD['r47'] = sorted(k for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items() for k in _d)
KAPPA = 1.76
ROOMLIKE = lambda k: k.startswith('room')
_CACHE = V + 'netmodel_r43/data/little_r47.json'
def little(k):
    c = json.load(open(_CACHE)) if os.path.exists(_CACHE) else {}
    if k in c: return c[k]
    import regiongraph as RG, netlp, bounds
    mf = json.load(open(INST[k][0]))['mapFile']; mp = mf if os.path.isabs(mf) else os.path.join(os.path.dirname(INST[k][0]), mf)
    G = RG.analyse(mp); N = INST[k][1]; lam = netlp.max_concurrent_flow(G)['lam']; T2 = bounds.bounds(mp, N)['Tleg2']
    c[k] = dict(N=N, lam=lam, Tleg2=T2, little=lam * 2.23 * (25 + T2) / N)
    json.dump(c, open(_CACHE, 'w'), indent=1); return c[k]
def lcap_env(k):
    if not ROOMLIKE(k): return dict(EXH)                       # cap gate is off there anyway (no single-lane links)
    r = KAPPA * little(k)['little']
    return NOCAP(EXH) if r >= 1 else dict(EXH, ROBOT_ACTIVE_CAP=f'{r:.3f}')
DEV47 = DEV46
