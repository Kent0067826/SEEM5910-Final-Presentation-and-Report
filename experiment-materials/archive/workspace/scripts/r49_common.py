"""Round 49 (wait-v39): credit for the network's bottleneck cut only (ROBOT_RG_CUTS=2, bin/lifelong-v34a, source dev_src_v34)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r48_common import *
import r47_common as _r47
_r47._CACHE = V + 'netmodel_r48/little_r49.json'   # round 49 keeps its own cache (round 47's file stays as committed)
BIN49 = V + 'bin/lifelong-v34a'
def bnc_env(k): return dict(lcap_env(k), ROBOT_RG_CUTS='2')
DEV49 = DEV48
AFF49 = open(V + 'netmodel_r48/maplist.txt').read().split()
_hit = {l.split(' ', 1)[0] for l in open(V + 'netmodel_r48/count49_all.txt') if l.split(' ', 1)[1].startswith('(1') or l.split(' ', 1)[1].startswith('(2')}
AFF49 = [k for k in AFF49 if k in _hit]
assert len(AFF49) == 27, len(AFF49)
