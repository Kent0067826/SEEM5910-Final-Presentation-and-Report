"""第二阶段 48 张图 + A6、W6：对偶价格读成割；顺带用第 60 轮公式重算走最短路的 lambda_SP 和 G。"""
import sys,json,time,heapq
import numpy as np
sys.argv=sys.argv[:1]
import p115_dual as P
RG=P.RG
R='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/网络协议方向'
C=P.C_DOOR
def lam_sp(G):
    Rm,D=G['rooms'],G['doors'];n=len(Rm);A=sum(r['size'] for r in Rm);w=[r['size']/A for r in Rm]
    adj=[[] for _ in range(n)];links={}
    for k,d in enumerate(D):
        a,b=d['rooms'];(y,x)=d['cells'][0]
        L=3*(abs(Rm[a]['center'][0]-y)+abs(Rm[a]['center'][1]-x)+abs(Rm[b]['center'][0]-y)+abs(Rm[b]['center'][1]-x))
        key=(min(a,b),max(a,b))
        if key in links: lk=links[key];lk['L']=min(lk['L'],L);lk['cap']+=C[min(2,d['width'])];lk['doors'].append(k)
        else: links[key]=dict(a=a,b=b,L=L,cap=C[min(2,d['width'])],doors=[k])
    LK=list(links.values())
    for i,lk in enumerate(LK): adj[lk['a']].append((lk['b'],i,lk['L']));adj[lk['b']].append((lk['a'],i,lk['L']))
    load=[0.0]*len(LK)
    for s in range(n):
        dist=[1e300]*n;pe=[-1]*n;dist[s]=0;pq=[(0,s)];order=[];done=[0]*n
        while pq:
            dd,v=heapq.heappop(pq)
            if done[v]:continue
            done[v]=1;order.append(v)
            for x,k,L in adj[v]:
                if dd+L<dist[x]-1e-9:dist[x]=dd+L;pe[x]=k;heapq.heappush(pq,(dist[x],x))
        sub=[0.0 if v==s else w[s]*w[v] for v in range(n)]
        for v in reversed(order):
            if v==s or pe[v]<0:continue
            k=pe[v];a,b=LK[k]['a'],LK[k]['b'];par=b if a==v else a;load[k]+=sub[v];sub[par]+=sub[v]
    return 1/max(load[i]/LK[i]['cap'] for i in range(len(LK)))
def comps(G,rm):
    n=len(G['rooms']);p=list(range(n))
    def f(x):
        while p[x]!=x:p[x]=p[p[x]];x=p[x]
        return x
    for d in G['doors']:
        if d['id'] in rm:continue
        a,b=d['rooms'];p[f(a)]=f(b)
    return [f(i) for i in range(n)]
def one(tag,mp):
    t=time.time();G=RG.analyse(mp)
    if not G['connected'] or len(G['rooms'])<2: return dict(tag=tag,note='no net')
    lam,y,load,w,it,res=P.solve(G)
    rm={G['doors'][k]['id'] for k in range(len(y)) if y[k]>1e-7}
    c=comps(G,rm);A=sum(x['size'] for x in G['rooms']);ww=[x['size']/A for x in G['rooms']]
    f=sum(ww[s]*ww[t2] for s in range(len(ww)) for t2 in range(len(ww)) if c[s]!=c[t2])
    Cc=sum(C[min(2,d['width'])] for d in G['doors'] if d['id'] in rm)
    ls=lam_sp(G)
    pr=sorted({round(float(v),3) for v in y if v>1e-7})
    return dict(tag=tag,rooms=len(G['rooms']),doors=len(G['doors']),lam=lam*500,prices={int(G['doors'][k]['id']):round(float(y[k]),3) for k in range(len(y)) if y[k]>1e-7},ncomp=len(set(c)),f=f,Cf=Cc/f*500 if f else None,cert=P.certify(G,y,w),G=lam/ls-1,lam_sp=ls*500,distinct=pr,sec=round(time.time()-t,1))
out=[]
M=P.W+'/maps_r64/room-64-64-16_'
todo=[('A6',M+'A6.map'),('W6',M+'W6.map')]
for b in ['p02','p18','p57','p61','p63','p69','p75','p76']:
    dd=R+'/harness/data/maps_'+b
    for m in json.load(open(dd+'/instances.json',encoding='utf-8')): todo.append((b+'/'+m,dd+'/'+m+'.map'))
for tag,mp in todo:
    try:o=one(tag,mp)
    except Exception as e:o=dict(tag=tag,err=str(e))
    out.append(o);print(json.dumps(o,ensure_ascii=False),flush=True)
    json.dump(out,open('p115_p2.json','w'),ensure_ascii=False,indent=1)
