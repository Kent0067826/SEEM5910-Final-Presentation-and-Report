"""Why none of ideas A-D helped: completed orders follow door-6 crossings, and no idea made door 6 pass more robots.
For every run of a new idea vs DoorFlow on the same seed pair (figures/explore/runs_main.jsonl): change in door-6 crossings vs
change in completed orders (correlation, least-squares slope); per idea, mean crossings, how often the window was full and
how many robots were stuck near the door. Writes figures/explore/why_no_gain.json."""
import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
R = [json.loads(l) for l in open(HERE / 'runs_main.jsonl')]
df = {(r['map'], r['seed'], r['pseed']): r for r in R if r['variant'] == 'DF'}
pairs = [(r, df[(r['map'], r['seed'], r['pseed'])]) for r in R if r['variant'] != 'DF']
dx = np.array([a['door6_crossings'] - b['door6_crossings'] for a, b in pairs]); dy = np.array([a['completed'] - b['completed'] for a, b in pairs])
res = dict(pairs=len(pairs), corr_crossings_vs_orders=round(float(np.corrcoef(dx, dy)[0, 1]), 3),
           orders_per_extra_crossing=round(float(np.polyfit(dx, dy, 1)[0]), 2),
           runs_with_more_crossings=int((dx > 0).sum()), mean_order_change_when_more_crossings=round(float(dy[dx > 0].mean()), 1),
           mean_order_change_when_fewer_crossings=round(float(dy[dx < 0].mean()), 1), per_variant={})
for v in sorted({r['variant'] for r in R}):
    rs = [r for r in R if r['variant'] == v]
    res['per_variant'][v] = dict(door6_crossings=round(float(np.mean([r['door6_crossings'] for r in rs])), 1),
                                 window_full_share=[round(float(np.mean([r['full_share'][s] for r in rs])), 3) for s in (0, 1)],
                                 stuck_near_door=round(float(np.mean([r['stuck_mean'] for r in rs])), 2))
(HERE / 'why_no_gain.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
