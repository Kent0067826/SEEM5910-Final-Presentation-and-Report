"""Where "door 6 passes about 26 robots per 500 ticks" comes from: count it.

Uses the 5 DoorFlow runs of door_timing.py (official room map, 250 robots, formal settings, task seeds 9700-9704, planner seed
101, 5,000 ticks each; run door_timing.py first, it writes the position dumps). For every run, counts the robots that cross
door 6 (leave one of the two rooms it joins and next appear in the other) in each 500-tick period. The first 500 ticks are
left out: at the start no robot is near the door yet, so that period is low (14-17) for a reason that has nothing to do
with the door. Door rate = all crossings in the remaining periods / number of periods.
Writes figures/deck/demo/door6_rate.json.   Usage (repo root):  DEMO_WORK=<work dir> python3 figures/deck/demo/door6_rate.py"""
import json, sys
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_demo as bd
import door_timing as dt

H, W, free = bd.load_map(); rg = json.loads(bd.RG.read_text()); lab = bd.room_labels(free, rg)
d6 = [d for d in rg['doors'] if d['id'] == 6][0]
per = {}
for s in dt.SEEDS:
    t, fin, loc, has = bd.load_dump(dt.WORK / str(s) / 'pos.bin')
    per[s] = bd.crossings(loc, lab, d6['rooms'], t)[:10].tolist()      # 10 periods of 500 ticks
A = np.array(list(per.values())); steady = A[:, 1:]
res = dict(runs='official room map, 250 robots, DoorFlow formal settings, task seeds 9700-9704, planner seed 101',
           crossings_per_500_ticks=per,
           first_period_left_out=[int(x) for x in A[:, 0]],
           crossings_after_first_500=int(steady.sum()), periods=int(steady.size),
           rate_per_500=round(float(steady.sum() / steady.size), 2), median_period=float(np.median(steady)),
           range_period=[int(steady.min()), int(steady.max())],
           whole_run_incl_start=round(float(A.sum() / A.size), 2),
           formula=f'{int(steady.sum())} / {int(steady.size)} = {steady.sum() / steady.size:.2f}')
(HERE / 'door6_rate.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
