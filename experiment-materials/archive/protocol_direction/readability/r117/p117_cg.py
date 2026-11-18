"""第 117 轮离线计算（只读地图，不跑模拟）：列生成解最大并发流。
主问题：max sum a_k，s.t. sum a_k L_k(e) <= C_e，a>=0。L_k 是“所有房间对各走一条路”的门负载。
定价：门的对偶价 y 当长度，走最短路，得新路由；g(y)=L·y<=1 即最优。小线性规划，所以 64 房间的图也解得动。"""
import sys,heapq
import numpy as np
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/workspace/netmodel_r41')
import regiongraph as RG
C_DOOR={1:26/500,2:32/500}
def routing(G,y,w):
    R=G['rooms'];D=G['doors'];n=len(R);adj=[[] for _ in range(n)]
    for k,d in enumerate(D):
        a,b=d['rooms'];adj[a].append((b,k));adj[b].append((a,k))
    L=np.zeros(len(D))
    for s in range(n):
        dist=[1e18]*n;dist[s]=0;pe=[None]*n;hop=[1e9]*n;hop[s]=0;pq=[(0,0,s)]
        while pq:
            dd,h,v=heapq.heappop(pq)
            if (dd,h)>(dist[v],hop[v]):continue
            for x,k in adj[v]:
                nd=dd+max(y[k],0)+1e-9
                if nd<dist[x]-1e-13:
                    dist[x]=nd;hop[x]=h+1;pe[x]=(v,k);heapq.heappush(pq,(nd,h+1,x))
        for t in range(n):
            if t==s:continue
            v=t
            while v!=s:
                u,k=pe[v];L[k]+=w[s]*w[t];v=u
    return L
def master(cols,C):
    m=len(C);n=len(cols);T=np.zeros((m+1,n+m+1))
    T[:m,:n]=np.array(cols).T;T[:m,n:n+m]=np.eye(m);T[:m,-1]=C;T[m,:n]=-1
    basis=list(range(n,n+m));it=0
    while it<200000:
        it+=1
        r=T[m,:-1];j=int(np.argmin(r)) if it<5000 else int(np.nonzero(r<-1e-11)[0][0]) if (r<-1e-11).any() else -1
        if j<0 or r[j]>-1e-11:break
        col=T[:m,j];pos=col>1e-11
        if not pos.any():raise RuntimeError('unbounded')
        ratio=np.full(m,np.inf);ratio[pos]=T[:m,-1][pos]/col[pos]
        mn=ratio.min();ties=np.nonzero(ratio<=mn+1e-13)[0];i=min(ties,key=lambda q:basis[q])
        T[i]/=T[i,j];c=T[:,j].copy();c[i]=0;T-=np.outer(c,T[i]);basis[i]=j
    return T[m,-1],T[m,n:n+m].copy()
def solve(G,maxit=4000,tol=1e-7):
    R=G['rooms'];D=G['doors'];A=sum(r['size'] for r in R);w=[r['size']/A for r in R]
    C=np.array([C_DOOR[min(2,d['width'])] for d in D])
    cols=[routing(G,np.ones(len(D)),w)]
    best_ub=1e18;y_best=None
    for it in range(maxit):
        lam,y=master(cols,C)
        L=routing(G,y,w);g=float(L@y)
        ub=float(C@y)/g if g>0 else 1e18
        if ub<best_ub:best_ub=ub;y_best=y.copy()/g
        if best_ub-lam<=tol*lam:break
        cols.append(L)
    return lam,best_ub,y_best,it+1
