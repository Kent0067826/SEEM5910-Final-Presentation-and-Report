"""Round 44 (wait-v34): link credit with routes learned from observed crossings. Program bin/lifelong-v31a (source dev_src_v31)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r43_common import *
BIN44 = V + 'bin/lifelong-v31a'
LINKR = dict(LINK, ROBOT_LINK_ROUTE='1')
LINKRU = dict(LINKR, ROBOT_LINK_ONLY='1')
CANDS44 = {'LINKr': LINKR, 'LINKru': LINKRU}
DEV44 = DEV43
