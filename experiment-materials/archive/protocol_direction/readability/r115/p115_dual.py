"""第 115 轮离线计算：解最大并发流并取出门的对偶价格（只读地图，不跑模拟）。
对偶值从单纯形末表的松弛列读；再用不依赖求解器的办法验证：按门价当长度算最短路，查 sum w_s w_t dist >= 1，且 sum C_e y_e = lambda*。"""
import sys, json, glob, os, heapq, time
import numpy as np
W='C:/Users/RETN_kwang/robotnet-lab/repo/workspace'
sys.path.insert(0, W+'/netmodel_r41')
import regiongraph as RG
C_DOOR={1:26/500,2:32/500}
OFF='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/outputs/robot-windowlab/source/example_problems/room.domain/maps/room-64-64-16.map'

def simplex(A,b,c,ns,maxit=300000):
    m,n=A.shape; T=np.hstack([A,b[:,None]]).astype(float); basis=-np.ones(m,int)
    for i in range(m):
        nz=np.nonzero(A[i,ns:])[0]
        if len(nz)==1: basis[i]=ns+nz[0]
    for i in range(m):
        if basis[i]>=0: continue
        row=T[i,:ns]; j=int(np.argmax(np.abs(row)))
        if abs(row[j])<1e-9: continue
        T[i]/=T[i,j]; col=T[:,j].copy(); col[i]=0; T-=np.outer(col,T[i]); basis[i]=j
    keep=basis>=0; T=T[keep]; basis=basis[keep]
    z=c.astype(float)-c[basis]@T[:,:-1]; z0=c[basis]@T[:,-1]; it=0
    while it<maxit:
        it+=1
        cand=np.nonzero(z>1e-9)[0]
        if len(cand)==0: break
        j=cand[0] if it>20000 else cand[np.argmax(z[cand])]
        colj=T[:,j]; pos=colj>1e-9
        if not pos.any(): raise RuntimeError('unbounded')
        ratio=np.full(len(colj),np.inf); ratio[pos]=np.maximum(T[pos,-1],0)/colj[pos]
        rmin=ratio.min(); ties=np.nonzero(ratio<=rmin+1e-12)[0]; i=ties[np.argmin(basis[ties])]
        T[i]/=T[i,j]; col=T[:,j].copy(); col[i]=0; T-=np.outer(col,T[i])
        zj=z[j]; z=z-zj*T[i,:-1]; z0+=zj*T[i,-1]; basis[i]=j
    x=np.zeros(n); x[basis]=T[:,-1]
    return z0,x,z,it

def build(G,caps=None):
    R=G['rooms'];D=G['doors'];n=len(R);A_=sum(r['size'] for r in R)
    arcs=[]
    for d in D:
        a,b=d['rooms']; arcs+=[(a,b,d['id']),(b,a,d['id'])]
    E=len(arcs);nv=n*E+1;lam=n*E
    w=np.array([r['size']/A_ for r in R])
    rows=n*n+len(D); M=np.zeros((rows,nv+len(D)));rhs=np.zeros(rows);ri=0
    for s in range(n):
        for v in range(n):
            for e,(u,x,_) in enumerate(arcs):
                if u==v:M[ri,s*E+e]+=1
                if x==v:M[ri,s*E+e]-=1
            M[ri,lam]=-(w[s]*(1-w[s]) if v==s else -w[s]*w[v]);ri+=1
    for k,d in enumerate(D):
        for e,a in enumerate(arcs):
            if a[2]==d['id']:
                for s in range(n):M[ri,s*E+e]=1
        M[ri,nv+k]=1;rhs[ri]=(caps[k] if caps is not None else C_DOOR[min(2,d['width'])]);ri+=1
    c=np.zeros(nv+len(D));c[lam]=1
    return M,rhs,c,nv,w,arcs,lam,E

def solve(G,caps=None):
    M,rhs,c,nv,w,arcs,lam,E=build(G,caps)
    z0,x,z,it=simplex(M,rhs,c,nv)
    D=G['doors']; y=np.array([-z[nv+k] for k in range(len(D))])
    load=[]
    for k,d in enumerate(D):
        load.append(sum(x[s*E+e] for s in range(len(G['rooms'])) for e,a in enumerate(arcs) if a[2]==d['id']))
    return float(z0),y,np.array(load),w,it,float(np.abs(M@x-rhs).max())

def certify(G,y,w):
    """独立验证：门价当长度，房间网络最短路"""
    n=len(G['rooms']);adj=[[] for _ in range(n)]
    for k,d in enumerate(G['doors']):
        a,b=d['rooms'];adj[a].append((b,y[k]));adj[b].append((a,y[k]))
    tot=0
    for s in range(n):
        dist=[1e18]*n;dist[s]=0;pq=[(0,s)]
        while pq:
            dd,v=heapq.heappop(pq)
            if dd>dist[v]:continue
            for x,l in adj[v]:
                if dd+max(l,0)<dist[x]-1e-14:dist[x]=dd+max(l,0);heapq.heappush(pq,(dist[x],x))
        tot+=sum(w[s]*w[t]*dist[t] for t in range(n) if t!=s)
    return tot

def findmap(base):
    ps=[]
    for dd in sorted(glob.glob(W+'/maps_*')):
        p=dd+'/'+base+'.map'
        if os.path.exists(p):ps.append(p)
    return ps[0] if ps else None

if __name__=='__main__':
    names=['OFF','roomT','roomS','roomAD','roomBA','roomBF','roomIA','roomIB','roomIC','roomIE','roomKA','roomQ','roomP','roomKC','roomKD','roomID','roomKF','roomKE','roomIF','roomKB']
    gap={r['inst'].split('_')[0]:r for r in json.load(open(W+'/analysis_r60_gap.json',encoding='utf-8')) if 'lam_lp' in r}
    gap['OFF']=gap['room200']
    out=[]
    for nm in names:
        mp=OFF if nm=='OFF' else findmap(nm)
        if not mp: print(nm,'nomap',flush=True);continue
        t=time.time();G=RG.analyse(mp)
        lam,y,load,w,it,res=solve(G)
        Cs=np.array([C_DOOR[min(2,d['width'])] for d in G['doors']])
        cert=certify(G,y,w);dualobj=float(Cs@y)
        pr={int(G['doors'][k]['id']):round(float(y[k]),3) for k in range(len(y)) if y[k]>1e-7}
        tight=[int(G['doors'][k]['id']) for k in range(len(y)) if load[k]>Cs[k]*(1-1e-7)]
        g=gap[nm]
        row=dict(map=nm,rooms=len(G['rooms']),doors=len(G['doors']),lam500=lam*500,lam500_saved=g['lam_lp']*500,dual500=dualobj*500,cert=cert,resid=res,prices=pr,stored_tight=g['lp_tight'],full_doors=tight,G=g['G'],lam_sp500=g['lam_sp']*500,sec=time.time()-t,it=it)
        out.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
        json.dump(out,open('p115_dual.json','w'),ensure_ascii=False,indent=1)
