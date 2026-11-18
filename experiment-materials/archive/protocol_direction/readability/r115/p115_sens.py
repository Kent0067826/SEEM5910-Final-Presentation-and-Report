import sys,json
import numpy as np
sys.argv=['x']
import p115_dual as P
RG=P.RG
G=RG.analyse(P.OFF); D=G['doors']
C=np.array([P.C_DOOR[min(2,d['width'])] for d in D])
lam0,y,load,w,it,res=P.solve(G)
print('lam',lam0*500,'nd',len(D))
i6=[k for k,d in enumerate(D) if d['id']==6][0]
i3=[k for k,d in enumerate(D) if d['id']==3][0]
print('door6',D[i6]['rooms'],D[i6]['width'],'door3',D[i3]['rooms'],D[i3]['width'])
# 单道门 +-1% 的单边导数
eps=0.01
rows=[]
for k,d in enumerate(D):
    c=C.copy();c[k]*=1+eps;up=P.solve(G,c)[0]
    c=C.copy();c[k]*=1-eps;dn=P.solve(G,c)[0]
    rows.append((d['id'],(up-lam0)/(C[k]*eps),(lam0-dn)/(C[k]*eps)))
print('nonzero',[r for r in rows if abs(r[1])>1e-6 or abs(r[2])>1e-6])
# 每道门能缩到多少而 lambda 不变（二分）
sl={}
for k,d in enumerate(D):
    if k==i6: continue
    lo,hi=0.0,1.0
    for _ in range(14):
        m=(lo+hi)/2;c=C.copy();c[k]*=m
        try: l=P.solve(G,c)[0]
        except Exception: l=0
        if l>=lam0*(1-1e-9):hi=m
        else:lo=m
    sl[d['id']]=round(hi,3)
print('shrink',sl)
# 门 6 带宽扫描
curve=[]
for c6 in [26,28,30,32,34,36,38,40,41,42,43,44,45,46,48,50,52,56,60,70,80,100,1000]:
    c=C.copy();c[i6]=c6/500
    l,yy,ld,_,_,_=P.solve(G,c)
    curve.append((c6,round(l*500,2),{D[k]['id']:round(float(yy[k]),3) for k in range(len(D)) if yy[k]>1e-7}))
    print(curve[-1])
json.dump(dict(lam=lam0*500,rows=rows,shrink=sl,curve=curve),open('p115_sens.json','w'),ensure_ascii=False,indent=1)
