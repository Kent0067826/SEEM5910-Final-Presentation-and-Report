"""Round 45 (wait-v35): gated service at the doors (GATE) and link credit with learned routes + measured delay (LINKrm). bin/lifelong-v32a."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r44_common import *
BIN45 = V + 'bin/lifelong-v32a'
GATE = dict(NETCAP, ROBOT_BMAC_GATED='1')
LINKRM = dict(LINKR, ROBOT_LINK_MEAS='2')
CANDS45 = {'GATE': GATE, 'LINKrm': LINKRM}
DEV45 = DEV44
