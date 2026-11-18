"""Round 51 (wait-v41): BBR-style in-flight cap on the region-graph cuts (ROBOT_RG_CUTS=1 + ROBOT_RG_BBR=1), bin/lifelong-v36a
(source dev_src_v36 = v35 + rg_bbr in window_control.cpp; switches unset -> identical to v32a)."""
import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r49_common import *
BIN51 = V + 'bin/lifelong-v36a'
def bbrc_env(k): return dict(lcap_env(k), ROBOT_RG_CUTS='1', ROBOT_RG_BBR='1')
DEV51 = DEV49; AFF51 = AFF49
def rgcount(k):     # how many region-graph cuts BBRC switches on for instance k (structure only)
    return _RGN.get(k)
try: _RGN = {l.split()[0]: int(l.split()[1]) for l in open(V + 'netmodel_r48/rgcount_r51.txt')}
except FileNotFoundError: _RGN = {}
