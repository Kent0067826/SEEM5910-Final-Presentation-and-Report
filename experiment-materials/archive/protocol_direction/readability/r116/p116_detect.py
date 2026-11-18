"""把程序找割的那段（dev_src_v33/default_planner/window_control.cpp 200–265 行）用 Python 抄一遍，只读地图。
返回每个割的被删格子和分块集合。用第 48 轮 missed_r48.json 的 prog 数验证。"""
import sys
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/workspace/netmodel_r41')
import regiongraph as RG
sys.setrecursionlimit(100000)
def parts_without(g,F,removed):
    lab={};sizes=[]
    for v in F:
        if v in removed or v in lab: continue
        q=[v];lab[v]=len(sizes)
        for (y,x) in q:
            for u in ((y+1,x),(y,x+1),(y-1,x),(y,x-1)):
                if u in F and u not in removed and u not in lab: lab[u]=len(sizes);q.append(u)
        sizes.append(len(q))
    return lab,sizes
def detect(path,frac=0.05,cap=16):
    g=RG.read_map(path);H=len(g);W=len(g[0])
    F=[(r,c) for r in range(H) for c in range(W) if RG.free(g,r,c)];Fs=set(F);N=len(F);thr=frac*N
    def nb(v):
        y,x=v;return [u for u in ((y+1,x),(y,x+1),(y-1,x),(y,x-1)) if u in Fs]
    # 关节点：去掉这格后至少两块够大
    cut=set()
    for v in F:
        if len(nb(v))>=4: continue
        n_=nb(v)
        if len(n_)<2: continue
        # 只在邻格之间局部不连通时才可能是关节点：直接 BFS
        lab,s=parts_without(g,Fs,{v})
        if sum(x>=thr for x in s)>=2: cut.add(v)
    cuts=[];done=set()
    for v0 in F:
        if len(cuts)>=cap: break
        if v0 not in cut or v0 in done: continue
        ch=[v0];done.add(v0)
        for q in ch:
            for u in nb(q):
                if u in cut and u not in done: done.add(u);ch.append(u)
        lab,s=parts_without(g,Fs,set(ch))
        if sum(x>=thr for x in s)<2: continue
        cuts.append(dict(kind='bridge',cells=ch,lab=lab,sizes=s))
    def passage(v):
        if v in cut: return False
        n_=nb(v)
        return len(n_)==2 and n_[0][0]+n_[1][0]==2*v[0] and n_[0][1]+n_[1][1]==2*v[1]
    def open_end(e,pv):
        er,ec=e
        for r0 in range(er-2,er+1):
            for c0 in range(ec-2,ec+1):
                if r0<0 or c0<0 or r0+2>=H or c0+2>=W: continue
                if all(((r0+a,c0+b) in Fs and (r0+a,c0+b)!=pv) for a in range(3) for b in range(3)): return True
        return False
    cand=[v for v in F if passage(v) and all(open_end(e,v) for e in nb(v))]
    sigs=[]
    if len(cand)<=400:
        for i in range(len(cand)):
            if len(cuts)>=cap: break
            for j in range(i+1,len(cand)):
                if len(cuts)>=cap: break
                u,w=cand[i],cand[j]
                if abs(u[0]-w[0])+abs(u[1]-w[1])>12: continue
                lab,s=parts_without(g,Fs,{u,w})
                big=[k for k,x in enumerate(s) if x>=thr]
                if len(big)<2: continue
                first={}
                for v,k in lab.items(): first.setdefault(k,v)
                sig=sorted((first[k],s[k]) for k in big)
                if sig in sigs: continue
                sigs.append(sig);cuts.append(dict(kind='pair',cells=[u,w],lab=lab,sizes=s))
    return dict(g=g,F=Fs,N=N,thr=thr,cuts=cuts,ncand=len(cand))
def sig_of(lab,sizes,thr):
    big=[k for k,x in enumerate(sizes) if x>=thr]
    if len(big)<2: return None
    P={k:set() for k in big}
    for v,k in lab.items():
        if k in P: P[k].add(v)
    return sorted(P.values(),key=len)
def same(a,b):
    if a is None or b is None or len(a)!=len(b): return False
    x,y=a[0],b[0];return len(x&y)/len(x|y)>=0.9
