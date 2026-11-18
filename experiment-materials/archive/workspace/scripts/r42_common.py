"""Round 42 (wait-v32): model credit refinements on bin/lifelong-v29a (source dev_src_v29). Registers maps_r41 (held-out)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r41_common import *
BIN42 = V + 'bin/lifelong-v29a'
_R = V + 'maps_r41/'
for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items():
    for _k, _v in _d.items(): INST[_k] = (_R + _k + '.json', _v)
HELD['r41'] = sorted(k for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items() for k in _d)
PHYS = dict(NETCAP, ROBOT_NET_C1='0.098')
AFF = dict(NETCAP, ROBOT_NET_TA='127', ROBOT_NET_TB='1.49')
PA = dict(PHYS, ROBOT_NET_TA='127', ROBOT_NET_TB='1.49')
CANDS42 = {'PHYS': PHYS, 'AFF': AFF, 'PA': PA}
DEV42 = DEV41
