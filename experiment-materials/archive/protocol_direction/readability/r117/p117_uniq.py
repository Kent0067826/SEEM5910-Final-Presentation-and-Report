"""每道门带宽减 1%，看 λ 变不变：变了说明这道门在某个最优对偶解里有价格（在某个最紧的割上）；不变说明所有最优解里它的价格都是 0。"""
import json,pickle,sys
import numpy as np, p117_cg as Q
det=pickle.load(open('../r116/p116_det.pkl','rb'))
def solve_c(G,C,maxit=3000,tol=1e-9):
    R=G['rooms'];D=G['doors'];A=sum(r['size'] for r in R);w=[r['size']/A for r in R]
    cols=[Q.routing(G,np.ones(len(D)),w)];best=1e18
    for it in range(maxit):
        lam,y=Q.master(cols,C);L=Q.routing(G,y,w);g=float(L@y);ub=float(C@y)/g if g>0 else 1e18
        best=min(best,ub)
        if best-lam<=tol*lam:break
        cols.append(L)
    return lam
out=[]
for k,d in det.items():
    G=Q.RG.analyse(d['mp'])
    if len(G['rooms'])<2 or not G['connected'] or len(G['rooms'])>40: 
        out.append(dict(k=k,skip=True));continue
    C=np.array([Q.C_DOOR[min(2,x['width'])] for x in G['doors']]);l0=solve_c(G,C);tight=[]
    for i,dd in enumerate(G['doors']):
        C2=C.copy();C2[i]*=.99
        if solve_c(G,C2)<l0*(1-1e-7): tight.append(dd['id'])
    out.append(dict(k=k,lam=l0*500,tight=tight))
    json.dump(out,open('p117_uniq.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print('done')
