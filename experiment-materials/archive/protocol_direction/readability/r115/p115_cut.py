"""把对偶价格读成割：去掉有价的门，图分成几块；f = 跨块房间对占比；核 lambda* = sum C / f。"""
import sys,json
import numpy as np
sys.argv=['x']
import p115_dual as P
RG=P.RG
def comps(G,rm):
    n=len(G['rooms']);p=list(range(n))
    def f(x):
        while p[x]!=x:p[x]=p[p[x]];x=p[x]
        return x
    for d in G['doors']:
        if d['id'] in rm: continue
        a,b=d['rooms'];p[f(a)]=f(b)
    return [f(i) for i in range(n)]
rows=json.load(open('p115_dual.json',encoding='utf-8'))
out=[]
for r in rows:
    mp=P.OFF if r['map']=='OFF' else P.findmap(r['map']);G=RG.analyse(mp)
    rm={int(k) for k in r['prices']}
    c=comps(G,rm);ncomp=len(set(c))
    A=sum(x['size'] for x in G['rooms']);w=[x['size']/A for x in G['rooms']]
    f=sum(w[s]*w[t] for s in range(len(w)) for t in range(len(w)) if c[s]!=c[t])
    Cc=sum(P.C_DOOR[min(2,d['width'])] for d in G['doors'] if d['id'] in rm)*500
    cross=[d['id'] for d in G['doors'] if c[d['rooms'][0]]!=c[d['rooms'][1]]]
    o=dict(map=r['map'],lam=round(r['lam500'],2),G=round(r['G']*100,1),prices=r['prices'],ncomp=ncomp,crossing=cross,Ccut=Cc,f=round(f,4),Cf=round(Cc/f,2),widths=[d['width'] for d in G['doors'] if d['id'] in rm])
    out.append(o);print(o)
json.dump(out,open('p115_cut.json','w'),ensure_ascii=False,indent=1)
