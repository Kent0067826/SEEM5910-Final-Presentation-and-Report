"""Summarise figures/explore/runs_<set>.jsonl: for every variant, paired change vs DoorFlow on the same seed pair
(mean of per-run ratios - 1), bootstrap 95% interval, runs better / worse / equal, per map size, and what happened at door 6
(crossings, stuck robots near the door, robots counted on the way, share of time the window was full, orders refused by the
new rule). Usage: python3 figures/explore/explore_summary.py [main|check]  ->  figures/explore/summary_<set>.json"""
import json, random, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
tag = sys.argv[1] if len(sys.argv) > 1 else 'main'
rows = [json.loads(l) for l in open(HERE / f'runs_{tag}.jsonl')]
got = {(r['map'], r['variant'], r['seed'], r['pseed']): r for r in rows}
df = {(m, s, p): r for (m, v, s, p), r in got.items() if v == 'DF'}


def boot(x, n=4000):
    rnd = random.Random(1); m = sorted(np.mean([rnd.choice(x) for _ in x]) for _ in range(n))
    return round(100 * m[int(.025 * n)], 2), round(100 * m[int(.975 * n)], 2)


res = {'set': tag, 'runs': len(rows), 'errors': sum(r['errors'] for r in rows), 'variants': {}}
for v in sorted({r['variant'] for r in rows}, key=lambda v: (v != 'DF', v)):
    pr = [(got[k], df[(k[0], k[2], k[3])]) for k in got if k[1] == v and (k[0], k[2], k[3]) in df]
    rat = [a['completed'] / b['completed'] - 1 for a, b in pr]
    maps = sorted({a['map'] for a, _ in pr})
    def mean(key, sub=None, rs=None):
        rs = rs or [a for a, _ in pr]; xs = [r[key] if sub is None else r[key][sub] for r in rs if key in r]
        return round(float(np.mean(xs)), 3) if xs else None
    res['variants'][v] = dict(
        n=len(pr), change_pct=round(100 * float(np.mean(rat)), 2), ci95_pct=boot(rat),
        better=sum(x > 0 for x in rat), worse=sum(x < 0 for x in rat), equal=sum(x == 0 for x in rat),
        worst_pct=round(100 * min(rat), 2), best_pct=round(100 * max(rat), 2),
        per_map={m: dict(orders=round(float(np.mean([a['completed'] for a, _ in pr if a['map'] == m])), 1),
                         doorflow=round(float(np.mean([b['completed'] for a, b in pr if a['map'] == m])), 1),
                         change_pct=round(100 * float(np.mean([a['completed'] / b['completed'] - 1 for a, b in pr if a['map'] == m])), 2),
                         better=sum(a['completed'] > b['completed'] for a, b in pr if a['map'] == m)) for m in maps},
        door6=dict(crossings_per_run=mean('door6_crossings'), stuck_near_door_mean=mean('stuck_mean'),
                   share_of_time_8plus_stuck=mean('stuck_ge8_share'),
                   counted_on_the_way=[mean('onway_mean', 0), mean('onway_mean', 1)],
                   window=[a['window'] for a, _ in pr[:1]][0] if pr else None,
                   share_of_time_window_full=[mean('full_share', 0), mean('full_share', 1)],
                   new_rule_refused_per_run=mean('ex_denied'), new_rule_admitted_per_run=mean('ex_admitted')))
(HERE / f'summary_{tag}.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))
for v, d in res['variants'].items():
    print(f"{v:7s} {d['change_pct']:+6.2f}% {d['ci95_pct']} better {d['better']}/{d['n']} worst {d['worst_pct']}",
          {m: (x['orders'], x['change_pct']) for m, x in d['per_map'].items()},
          'cross', d['door6']['crossings_per_run'], 'stuck', d['door6']['stuck_near_door_mean'], 'onway', d['door6']['counted_on_the_way'],
          'full', d['door6']['share_of_time_window_full'], 'refused', d['door6']['new_rule_refused_per_run'])
