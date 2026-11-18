"""Round 46 (wait-v36): A. exhaustive service at the doors (EXH); B. global-cap sweep (saturation point). bin/lifelong-v32a."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r45_common import *
BIN46 = V + 'bin/lifelong-v32a'
_R = V + 'maps_r45/'
for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items():
    for _k, _v in _d.items(): INST[_k] = (_R + _k + '.json', _v)
HELD['r45'] = sorted(k for _n, (_f, _d) in json.load(open(_R + 'instances.json')).items() for k in _d)
EXH = dict(NETCAP, ROBOT_BMAC_HOLD='100000')
DEV46 = DEV45
SWEEP_MAPS = ['room200', 'room250', 'room300', 'roomT_199', 'roomQ_254', 'roomAD_189', 'roomP_254', 'roomS_247', 'roomBA_254', 'roomBF_240', 'roomCD_194']
SWEEP_CAPS = ['0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9', 'off']
def cap_env(c): return NOCAP(NETCAP) if c == 'off' else dict(NETCAP, ROBOT_ACTIVE_CAP=c)
