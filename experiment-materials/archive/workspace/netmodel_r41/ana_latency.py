import json, sys, statistics, collections
sys.path.insert(0, '/home/claude/r40')
import latency
from batch_measure import mapfile
cuts = json.load(open('/home/claude/r40/batch/cuts.json'))
meas = collections.defaultdict(lambda: collections.defaultdict(list))
for c in cuts:
    if c['small_cells'] < 0.05 * c['free']: continue
    k = (c['inst'], c['kind'], tuple(c['doors']))
    for side, v in (('in', c['lat_in_mean']), ('out', c['lat_out_mean'])):
        if v == v: meas[(k, c['method'])][side].append(v)
pairs = []
done = set()
for (k, m) in list(meas):
    inst = k[0]
    if inst in done: continue
    done.add(inst)
    mf = mapfile(inst)
    for x in latency.cut_latency_free(mf):
        kk = (inst, x['kind'], tuple(x['doors']))
        big = [s for s in x['T_into'] if s != x['small']][0]
        for meth in ('C24CF', 'N2F'):
            d = meas.get((kk, meth))
            if not d: continue
            for side, s in (('in', x['small']), ('out', big)):
                if d[side]: pairs.append(dict(inst=inst, kind=x['kind'], doors=x['doors'], method=meth, side=side, T_free=x['T_into'][s], T_meas=statistics.mean(d[side])))
json.dump(pairs, open('/home/claude/r40/batch/latency_pairs.json', 'w'), ensure_ascii=False, indent=1)
for meth in ('C24CF', 'N2F'):
    for grp in (lambda p: not p['inst'].endswith('_nd'), lambda p: p['inst'].endswith('_nd')):
        v = [p['T_meas'] / p['T_free'] for p in pairs if p['method'] == meth and grp(p)]
        if v: print(meth, '变慢倍数 实测/自由流：中位', round(statistics.median(v), 2), '四分位', round(sorted(v)[len(v)//4], 2), round(sorted(v)[3*len(v)//4], 2), 'n', len(v))
for p in pairs:
    if p['inst'] in ('room250', 'room250_nd') and p['method'] == 'C24CF': print(p)
