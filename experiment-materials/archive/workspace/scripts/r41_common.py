"""Round 41 (wait-v31): credits from the network model (ROBOT_NET=1, bin/lifelong-v28a, source dev_src_v28).
Registers the held-out maps maps_r40 (generated before any round-41 dev run)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r39_common import *
BIN41 = V + 'bin/lifelong-v28a'
_R = V + 'maps_r40/'
for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items():
    for _k, _v in _d.items(): INST[_k] = (_R + _k + '.json', _v)
HELD['r40'] = sorted(k for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items() for k in _d)
C24CF = CANDS39['C24CF']
NOCAP = lambda e: {k: v for k, v in e.items() if k not in ('ROBOT_ACTIVE_CAP', 'ROBOT_ACTIVE_CAP_GATE')}
NETCAP = dict(C24CF, ROBOT_NET='1')
NET = NOCAP(NETCAP)
NETF2 = dict(NET, ROBOT_BRIDGE_FRAC='0.02')
C24NC = NOCAP(C24CF)
CANDS41 = {'NET': NET, 'NETcap': NETCAP, 'NETf2': NETF2}
DIAG41 = {'C24nc': C24NC}
DEV41 = DEV39
