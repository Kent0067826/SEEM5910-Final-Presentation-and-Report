"""不解线性规划，直接核第 53 轮的过门费：拉格朗日下界 D(y) = sum lam w_s w_t dist_y(s,t) - sum C_e y_e。
任何 y>=0 都是最小费用的下界；最优 y 处等于最优值。图的构造照 netmodel_r53/lbtoll.py。"""
import sys,json,collections,heapq
from collections import deque
sys.argv=sys.argv[:1]
import numpy as np
import p115_dual as P
RG=P.RG;C=P.C_DOOR
def bfs(sources,allowed):
    dist={s:0 for s in sources};q=deque(sources)
    while q:
        y,x=q.popleft()
        for v in ((y+1,x),(y-1,x),(y,x+1),(y,x-1)):
            if v in allowed and v not in dist:dist[v]=dist[(y,x)]+1;q.append(v)
    return dist
def net(mp):
    g=RG.read_map(mp);R,D,odd,room_of=RG.build(g);nR=len(R)
    rc=collections.defaultdict(list)
    for v,r in room_of.items():rc[r].append(v)
    adj=collections.defaultdict(list)
    for d in D:
        a,b=d['rooms'];adj[a].append(d['id']);adj[b].append(d['id'])
    dc={d['id']:[tuple(c) for c in d['cells']] for d in D}
    other=lambda d,r:D[d]['rooms'][1] if D[d]['rooms'][0]==r else D[d]['rooms'][0]
    din={}
    for r in range(nR):
        al=set(rc[r])
        for d in adj[r]:al|=set(dc[d])
        for d in adj[r]:din[(r,d)]=bfs(dc[d],al)
    mt={}
    for (r,d),dm in din.items():
        ds=[dm[v] for v in rc[r] if v in dm];mt[(r,d)]=sum(ds)/len(ds) if ds else 1e9
    d2d={}
    for r in range(nR):
        for d1 in adj[r]:
            for d2 in adj[r]:
                if d1!=d2:d2d[(d1,d2,r)]=min(din[(r,d1)].get(v,10**9) for v in dc[d2])
    A=sum(r['size'] for r in R);w=[r['size']/A for r in R]
    return dict(R=R,D=D,adj=adj,other=other,mt=mt,d2d=d2d,w=w,nR=nR)
def dual(N,y,lam):
    D=N['D'];nR=N['nR'];w=N['w'];mt=N['mt'];oth=N['other']
    out=collections.defaultdict(list)
    for (d1,d2,r),c in N['d2d'].items():
        if c<10**8:out[(d1,r)].append(((d2,oth(d2,r)),c+y.get(d2,0)))
    tot=0
    for s in range(nR):
        dist={};pq=[]
        for d in N['adj'][s]:
            v=(d,oth(d,s));heapq.heappush(pq,(mt[(s,d)]+y.get(d,0),v))
        while pq:
            dd,v=heapq.heappop(pq)
            if v in dist:continue
            dist[v]=dd
            for u,c in out[v]:
                if u not in dist:heapq.heappush(pq,(dd+c,u))
        for t in range(nR):
            if t==s:continue
            best=min(dist[(d,t)]+mt[(t,d)] for d in N['adj'][t] if (d,t) in dist)
            tot+=lam*w[s]*w[t]*best
    return tot-sum(C[min(2,D[k]['width'])]*v for k,v in y.items())
N=net(P.OFF);G=RG.analyse(P.OFF);lam=P.solve(G)[0]
print('lam',lam*500,'D(0)',dual(N,{},lam))
best=max(((dual(N,{3:v/20},lam),v/20) for v in range(0,101)))
print('door3 only best',best)
for v in [0,0.5,1.0,1.5,2.0,3.0]: print(v,round(dual(N,{3:v},lam),4))
print('add door6 toll 5 on top',dual(N,{3:best[1],6:5.0},lam))
print('door6 alone 5',dual(N,{6:5.0},lam))
# 再试其余门：逐门加 0.5 看下界能否再抬高（坐标上升）
y={3:best[1]};b=best[0]
for k in range(len(N['D'])):
    if k==3:continue
    z=dict(y);z[k]=0.5;v=dual(N,z,lam)
    if v>b+1e-6:print('door',k,'raises',v)
fine=max(((dual(N,{3:v/1000},lam),v/1000) for v in range(1300,1700,5)))
print('fine',fine)
