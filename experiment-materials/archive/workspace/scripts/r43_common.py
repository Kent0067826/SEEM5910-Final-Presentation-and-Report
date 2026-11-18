"""Round 43 (wait-v33): link credit on every room-to-room link replaces the hand-set global cap. Program bin/lifelong-v30a
(source dev_src_v30 = dev_src_v29 + default_planner/link_credit.{h,cpp}; ROBOT_LINK unset -> identical to v29a)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r42_common import *
BIN43 = V + 'bin/lifelong-v30a'
LINK = dict(NOCAP(NETCAP), ROBOT_LINK='1')          # all credits from the network model, no global cap
LINKCAP = dict(NETCAP, ROBOT_LINK='1')              # diagnostic: link credit + the hand-set cap
CANDS43 = {'LINK': LINK}
DIAG43 = {'LINKcap': LINKCAP}
DEV43 = DEV42
EXTRA43 = [('roomCD_194', 5000)]                    # descriptive only (the map where the cap hurts); not used for selection
