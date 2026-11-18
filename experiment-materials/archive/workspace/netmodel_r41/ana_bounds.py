import json, sys, statistics, collections
sys.path.insert(0, '/home/claude/r40')
import bounds
from batch_measure import INST, mapfile
rows = [json.loads(l) for l in open('/home/claude/r40/batch/rows.jsonl')]
act = collections.defaultdict(list)
for r in rows: act[(r['inst'], r['method'])].append(r['completed'])
out = []
for inst in ['room200', 'room250', 'room300', 'roomT_199', 'roomQ_254', 'roomAD_189', 'roomP_254', 'roomS_247', 'roomBA_254', 'roomBF_240', 'roomCD_194']:
    N = INST[inst][1]; b = bounds.bounds(mapfile(inst), N)
    a1 = statistics.mean(act[(inst, 'C24CF')]); a2 = statistics.mean(act[(inst, 'N2F')])
    t = b['cuts'][0] if b['cuts'] else None
    out.append(dict(inst=inst, N=N, Tleg2=b['Tleg2'], free=b['free'], cut_bound=t['bound'] if t else None, cut=t, bound=b['bound'], C24CF=a1, N2F=a2))
    print(f"{inst:11s} N={N} 第2段最短{b['Tleg2']:.0f}拍 自由流上限{b['free']:.0f} 最紧的割{(t['kind']+str(t['doors'])) if t else '-'} f={t['f'] if t else 0:.2f} C={t['C500'] if t else 0:.0f} 割上限{t['bound'] if t else float('nan'):.0f} | 上限{b['bound']:.0f} C24CF {a1:.0f}（{a1/b['bound']:.0%}） N2F {a2:.0f}（{a2/b['bound']:.0%}）")
    for k in ('room200', 'room250', 'room300'):
        pass
for k in ('room200', 'room250', 'room300'):
    N = INST[k][1]; b = bounds.bounds(mapfile(k), N, cdoor=bounds.C_DOOR_ND)
    print(k, '无故障: 上限', round(b['bound']), '自由流', round(b['free']), '割', round(b['cuts'][0]['bound']), 'C24CF', statistics.mean(act[(k + '_nd', 'C24CF')]), 'N2F', statistics.mean(act[(k + '_nd', 'N2F')]))
json.dump(out, open('/home/claude/r40/batch/bounds.json', 'w'), ensure_ascii=False, indent=1)
