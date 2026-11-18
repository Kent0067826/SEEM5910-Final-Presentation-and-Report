"""Round 48 (wait-v38): region-graph cuts get the bandwidth-delay credit too (ROBOT_RG_CUTS=1, bin/lifelong-v33a, source
dev_src_v33 = dev_src_v32 + rg_detect/rg_activate in default_planner/window_control.cpp; switch unset -> identical to v32a).
Registers the held-out maps maps_r48 (generated before any round-48 development run)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts'); sys.path.insert(0, '/home/claude/r40'); sys.path.insert(0, '/home/claude/proj/v10/netmodel_r41')
from r47_common import *
BIN48 = V + 'bin/lifelong-v33a'
_R = V + 'maps_r48/'
for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items():
    for _k, _v in _d.items(): INST[_k] = (_R + _k + '.json', _v)
HELD['r48'] = sorted(k for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items() for k in _d)
RG = {'ROBOT_RG_CUTS': '1'}
def rgc_env(k): return dict(lcap_env(k), **RG)          # candidate: LCAP + region-graph cuts
def rgcnc_env(k): return dict(NOCAP(EXH), **RG)         # diagnostic only: region-graph cuts, no global cap
DEV48 = DEV47
R47 = HELD['r47']                                        # used up in round 47: descriptive dev set here (where the failure was found)
