import json, random, statistics as st, sys
from collections import defaultdict
def load(path, ticks=None):
    R=[json.loads(l) for l in open(path)]
    R=[r for r in R if 'completed' in r and (ticks is None or r['ticks']==ticks)]
    return R
def pairs(R, method, mp, base='baseline'):
    b={(r['seed'],r['pseed'],r['ticks']):r for r in R if r['map']==mp and r['method']==base}
    return [(r,b[(r['seed'],r['pseed'],r['ticks'])]) for r in R if r['map']==mp and r['method']==method and (r['seed'],r['pseed'],r['ticks']) in b]
def rel(ps): return [100*(a['completed']/b['completed']-1) for a,b in ps]
def boot_ci(groups, n=4000, seed=0):
    rnd=random.Random(seed); ms=[]
    for _ in range(n):
        ms.append(st.mean(st.mean(rnd.choice(g) for _ in g) for g in groups))
    ms.sort(); return ms[int(.025*n)], ms[int(.975*n)]
def signflip(groups, n=10000, seed=0):
    rnd=random.Random(seed); obs=st.mean(st.mean(g) for g in groups); hits=0
    for _ in range(n):
        t=st.mean(st.mean(x if rnd.random()<.5 else -x for x in g) for g in groups); hits+= abs(t)>=abs(obs)-1e-12
    return (hits+1)/(n+1)
def holm(ps):
    idx=sorted(range(len(ps)),key=lambda i:ps[i]); out=[0]*len(ps); m=len(ps); run=0
    for k,i in enumerate(idx): run=max(run,min(1,(m-k)*ps[i])); out[i]=run
    return out
def table(R, methods, maps, base='baseline'):
    rows=[]
    for m in methods:
        cells=[]; groups=[]
        for mp in maps:
            ps=pairs(R,m,mp,base)
            if not ps: cells.append('—'); continue
            g=rel(ps); groups.append(g)
            cells.append(f"{st.mean(g):+.1f}% ({sum(x>0 for x in g)}/{sum(x<0 for x in g)})")
        if groups:
            ov=st.mean(st.mean(g) for g in groups); lo,hi=boot_ci(groups); p=signflip(groups)
            rows.append((m,cells,ov,lo,hi,p))
    return rows
def fmt(rows, maps):
    out=['| method | '+' | '.join(maps)+' | overall | 95% CI | p |','|'+'---|'*(len(maps)+4)]
    for m,cells,ov,lo,hi,p in rows: out.append(f"| {m} | "+' | '.join(cells)+f" | {ov:+.2f}% | [{lo:+.2f}, {hi:+.2f}] | {p:.4f} |")
    return '\n'.join(out)
def tel(R, method, mp, ticks=1200):
    rs=[r for r in R if r['map']==mp and r['method']==method and r['ticks']==ticks and r.get('tel')]
    if not rs: return {}
    f=lambda g: st.mean(g(r) for r in rs)
    return dict(n=len(rs), completed=f(lambda r:r['completed']), admitted=f(lambda r:r['tel']['win']['admittedTotal']),
        acked=f(lambda r:r['tel']['win']['ackedTotal']), mark=f(lambda r:r['tel']['win']['markFraction']), win=f(lambda r:r.get('winMean',0)),
        unassigned=f(lambda r:r['tel']['fair']['unassigned']), maxAge=f(lambda r:r['tel']['fair']['maxAge']), meanAge=f(lambda r:r['tel']['fair']['meanAge']),
        latMean=f(lambda r:r['tel']['fair']['latMean']), latP95=f(lambda r:r['tel']['fair']['latP95']), gate=rs[0]['tel']['gate'], sec=f(lambda r:r['sec']))
