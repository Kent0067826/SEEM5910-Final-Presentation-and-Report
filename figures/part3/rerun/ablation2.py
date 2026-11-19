"""Finer ablation on the official 4x4 room map: remove one kept piece of the final method at a time.
Same seeds as ablation.py, so FULL rows are shared (ablation.jsonl)."""
import sys; sys.path.insert(0, '/home/user/simbuild/run')
from run import batch
V = {
    'noEvac':      {'ROBOT_BMAC_EVAC': None},                 # round 29: exit side must clear the approach zone
    'noDemote':    {'ROBOT_BMAC_DEMOTE': None},               # round 29: robots held by the door rule get the lowest PIBT priority
    'noLMAC':      {'ROBOT_LMAC': None, 'ROBOT_ACTIVE_CAP_GATE': '0'},   # round 30: door rule also on short narrow non-cut links (cap kept on)
    'apron2':      {'ROBOT_BMAC_APRON': '2'},                 # round 33: approach zone 4 cells (program default 2)
    'gated80':     {'ROBOT_BMAC_HOLD': '80'},                 # round 46: exhaustive service instead of "at most 80 steps then switch"
    'noIdleChain': {'ROBOT_BMAC_IDLECHAIN': None},            # rounds 35-36: idle robots parked in a passage do not block the switch
    'noChainFree': {'ROBOT_BMAC_CHAINFREE': None},            # round 37: a robot inside one passage is not held by another passage's rules
    'noCut2':      {'ROBOT_CUT2_CREDIT': None},               # round 38: quotas also for pairs of 1-cell doors
    'handQuota':   {'ROBOT_NET': None},                       # round 41: formula quotas -> back to hand-set 16 / 24
}
jobs = [dict(map=m, method=k, seed=s, pseed=p, env=e) for k, e in V.items() for m in ['room300', 'room250', 'room200']
        for s in range(11900, 11910) for p in (171, 172)]
batch(jobs, '/home/user/simbuild/run/ablation2.jsonl', workers=4)
print('DONE')
