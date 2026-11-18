import sys,json
sys.argv=sys.argv[:1]
import numpy as np, p115_dual as P
RG=P.RG
G=RG.analyse(P.OFF);D=G['doors']
for sp in [26,36.2,55.6,83]:
    c=np.array([(sp/500)*(32/26 if d['width']>=2 else 1) for d in D]);c2=np.array([(max(sp,32)/500 if d['width']>=2 else sp/500) for d in D])
    a=P.solve(G,c);b=P.solve(G,c2)
    print(sp,round(a[0]*500,1),{D[k]['id']:round(float(a[1][k]),3) for k in range(len(D)) if a[1][k]>1e-7},round(b[0]*500,1))
print([ (d['id'],d['width']) for d in D if d['width']>=2])
