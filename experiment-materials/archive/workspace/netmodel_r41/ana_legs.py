"""每单任务的两段用时：领任务 -> 取货（第 1 段），取货 -> 送货（第 2 段），和地图上的自由流最短时间比。"""
import json, gzip, sys, statistics, random, collections
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG, bounds
from batch_measure import mapfile
rows = [json.loads(l) for l in open('/home/claude/r40/batch/rows.jsonl')]
out = {}
for inst in ['room250', 'roomCD_194', 'roomBF_240', 'roomS_247', 'room250_nd']:
    g = RG.read_map(mapfile(inst)); W = len(g[0])
    rng = random.Random(1)
    D, cells = bounds.free_time_sampler(g, rng, n_src=40)
    for m in ('C24CF', 'N2F'):
        l1, l2, f2, early1, early2 = [], [], [], [], []
        for r in rows:
            if r['inst'] != inst or r['method'] != m: continue
            o = json.load(gzip.open(f"/home/claude/r40/batch/replays/{inst}_{m}_{r['seed']}_{r['pseed']}.json.gz"))
            locs = {t[0]: [(t[2][i], t[2][i + 1]) for i in range(0, len(t[2]), 2)] for t in o['tasks']}
            ev = collections.defaultdict(dict)
            for t, a, tid, seq in o['events']: ev[tid][seq] = (t, a)
            asg = {}
            for a, s in enumerate(o['actualSchedule']):
                for part in s.split(','):
                    if part:
                        t, k = map(int, part.split(':'))
                        if k >= 0: asg[(a, k)] = t
            for tid, e in ev.items():
                if 1 in e and 2 in e:
                    t1, a = e[1]; t2, _ = e[2]; ta = asg.get((a, tid))
                    if ta is None: continue
                    l1.append(t1 - ta); l2.append(t2 - t1)
                    if ta < 1000: early1.append(t1 - ta); early2.append(t2 - t1)
        out[f'{inst}|{m}'] = dict(leg1_mean=statistics.mean(l1), leg2_mean=statistics.mean(l2), leg1_med=statistics.median(l1), leg2_med=statistics.median(l2),
                                  early_leg1=statistics.mean(early1), early_leg2=statistics.mean(early2), n=len(l1))
        print(inst, m, {k: round(v) for k, v in out[f'{inst}|{m}'].items()})
    ts = [d[t] for s, d in D.items() for t in rng.sample(cells, 200) if t in d]
    print(inst, '第 2 段自由流最短（均匀随机）', round(statistics.mean(ts)))
json.dump(out, open('/home/claude/r40/batch/legs.json', 'w'), indent=1)
