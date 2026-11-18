import json, random, statistics as st
rows = [json.loads(l) for l in open('/home/user/simbuild/run/ablation.jsonl') if 'completed' in l]
assert all(r['errors'] == 0 and r['plannerErrors'] == 0 for r in rows)
by = {(r['map'], r['method'], r['seed'], r['pseed']): r['completed'] for r in rows}
M = ['room200', 'room250', 'room300']
def groups(a, b):
    return [[by[(m, a, s, p)] / by[(m, b, s, p)] - 1 for (mm, k, s, p) in by if mm == m and k == b and (m, a, s, p) in by] for m in M]
def boot(G, n=4000, seed=0):   # same as archive/workspace/scripts/ana.py boot_ci
    rnd = random.Random(seed); ms = sorted(st.mean(st.mean(rnd.choice(g) for _ in g) for g in G) for _ in range(n))
    return ms[int(.025 * n)], ms[int(.975 * n)]
out = {}
meth = sorted({r['method'] for r in rows})
out['mean'] = {k: {m: st.mean(by[x] for x in by if x[0] == m and x[1] == k) for m in M} for k in meth}
for a, b in [('FULL', 'NONE'), ('FULL', 'noQuota'), ('FULL', 'noDoor'), ('FULL', 'noGlobal'), ('FULL', 'noWD'), ('FULL', 'noSync'),
             ('onlyQuota', 'NONE'), ('onlyDoor', 'NONE'), ('onlyGlobal', 'NONE')]:
    if not all((M[0], a, 11900, 171) in by and (M[0], b, 11900, 171) in by for _ in [0]): continue
    G = groups(a, b); lo, hi = boot(G)
    out[f'{a}/{b}'] = dict(mean=100 * st.mean(st.mean(g) for g in G), lo=100 * lo, hi=100 * hi,
                           per=[100 * st.mean(g) for g in G], n=[len(g) for g in G], wins=[sum(x > 0 for x in g) for g in G])
json.dump(out, open('/home/user/simbuild/run/ablation_summary.json', 'w'), indent=1, ensure_ascii=False)
for k, v in out.items():
    if k == 'mean': 
        for kk, vv in v.items(): print(f'{kk:<11}', {m: round(x, 1) for m, x in vv.items()})
    else: print(f"{k:<20} {v['mean']:+7.2f}% [{v['lo']:+.2f}, {v['hi']:+.2f}]  per {[round(x,1) for x in v['per']]} n {v['n']} wins {v['wins']}")
