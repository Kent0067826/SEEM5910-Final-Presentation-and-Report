"""第 116 轮离线计算（只读地图，不跑模拟）：第 48 轮 73 个实例（72 张不同地图）解最大并发流，读出对偶落在哪个割上，
再和第 48 轮的“程序漏掉的割”清单比。"""
import sys,json,time,os,glob
from multiprocessing import Pool
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
A=sys.argv; sys.argv=A[:1]
import p115_dual as P
RG=P.RG
W=P.W
def comps(G,rm):
    n=len(G['rooms']);p=list(range(n))
    def f(x):
        while p[x]!=x:p[x]=p[p[x]];x=p[x]
        return x
    for d in G['doors']:
        if d['id'] in rm:continue
        a,b=d['rooms'];p[f(a)]=f(b)
    return [f(i) for i in range(n)]
def one(a):
    k,mp=a
    t=time.time();G=RG.analyse(mp)
    if len(G['rooms'])<2 or not G['connected']: return dict(k=k,note='nonet',rooms=len(G['rooms']),connected=G['connected'])
    lam,y,load,w,it,res=P.solve(G)
    rm=[G['doors'][i]['id'] for i in range(len(y)) if y[i]>1e-7]
    c=comps(G,set(rm));A_=sum(r['size'] for r in G['rooms']);ww=[r['size']/A_ for r in G['rooms']]
    f=sum(ww[s]*ww[t2] for s in range(len(ww)) for t2 in range(len(ww)) if c[s]!=c[t2])
    dd={d['id']:d for d in G['doors']}
    Cc=sum(P.C_DOOR[min(2,dd[i]['width'])] for i in rm)
    sizes={}
    for i,r in enumerate(G['rooms']): sizes[c[i]]=sizes.get(c[i],0)+r['size']
    return dict(k=k,rooms=len(G['rooms']),doors=len(G['doors']),lam=lam*500,cut=sorted(rm),widths=[dd[i]['width'] for i in sorted(rm)],cells=[dd[i]['cells'] for i in sorted(rm)],
      prices=sorted({round(float(v),3) for v in y if v>1e-7}),ncomp=len(set(c)),parts=sorted(sizes.values()),f=f,Cf=Cc/f*500 if f else None,cert=P.certify(G,y,w),free=G['free'],sec=round(time.time()-t,1),
      lvl=[dd[i]['cut_level'] for i in sorted(rm)])
if __name__=='__main__':
    miss=json.load(open(W+'/netmodel_r48/missed_r48.json',encoding='utf-8'))
    todo=[]
    for k in miss:
        if k=='room300':continue
        b=k.split('_')[0]
        todo.append((k,P.OFF if k=='room200' else P.findmap(b)))
    # 小图先解
    out=[]
    with Pool(5) as pool:
        for o in pool.imap_unordered(one,todo):
            out.append(o);print(json.dumps({x:o.get(x) for x in('k','rooms','lam','cut','widths','f','sec')},ensure_ascii=False),flush=True)
            json.dump(out,open('p116_dual73.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
