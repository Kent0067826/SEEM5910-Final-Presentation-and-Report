"""(D) Measure each single-door cut's own slow-down from DoorFlow runs on the calibration seeds (11720-11724 x planner 147,
never used for testing). For cut b, direction s: alpha = mean ticks from being counted on the way to crossing / T_free(b, s),
T_free being the model's free-flow delay DoorFlow itself uses (leg 1 + mean free-flow time to the door). Pooled over the 5
runs of each map; a cut-direction with fewer than 30 crossings keeps the global 2.23.
Input figures/explore/runs_calib.jsonl (explore_runs.py DF --seeds calib); output figures/explore/alpha_calib.json."""
import json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in open(HERE / 'runs_calib.jsonl') if json.loads(l)['variant'] == 'DF']
res = {'alpha': {}, 'detail': {}, 'seeds': 'task 11720-11724 x planner 147, DoorFlow, 5,000 ticks', 'c1': 26 / 500}
for mp in sorted({r['map'] for r in rows}):
    rs = [r for r in rows if r['map'] == mp]; out = []; det = {}
    for key, (tf, K) in sorted(rs[0]['tfree_K'].items()):
        n = sum(r['cross_n'].get(key, 0) for r in rs); tot = sum(r['cross_sum'].get(key, 0) for r in rs)
        b, s = map(int, key.split(','))
        a = round(tot / n / tf, 3) if n >= 30 else 2.23
        newK = max(1, math.ceil(a * tf * res['c1'] / 2 - 1e-9))
        det[key] = dict(T_free=tf, K_doorflow=K, crossings=n, mean_ticks_to_cross=round(tot / n, 1) if n else None, alpha=a, K_new=newK)
        out.append([b, s, a])
    res['alpha'][mp] = out; res['detail'][mp] = det
(HERE / 'alpha_calib.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res['detail'], indent=1))
