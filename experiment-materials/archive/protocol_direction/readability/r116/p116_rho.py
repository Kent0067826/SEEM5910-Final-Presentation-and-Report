"""程序管的割里最紧的一道，离全图最窄差多少（rho = lam / (C/f)，1 就是同样紧）；再算第 49 轮 BNC 选的割是不是真最窄。"""
import json,sys,pickle,collections,re
import p116_detect as D
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
sys.argv=sys.argv[:1]
import p115_dual as P
RG=P.RG
C=P.C_DOOR
det=pickle.load(open('p116_det.pkl','rb'))
cl=json.load(open('p116_class.json',encoding='utf-8'))
def comps(G,rm):
    n=len(G['rooms']);p=list(range(n))
    def f(x):
        while p[x]!=x:p[x]=p[p[x]];x=p[x]
        return x
    for d in G['doors']:
        if d['id'] in rm:continue
        a,b=d['rooms'];p[f(a)]=f(b)
    return [f(i) for i in range(n)]
def Cf(G,rm):
    c=comps(G,rm)
    if len(set(c))<2: return None
    A=sum(x['size'] for x in G['rooms']);w=[x['size']/A for x in G['rooms']]
    f=sum(w[s]*w[t] for s in range(len(w)) for t in range(len(w)) if c[s]!=c[t])
    cc=sum(C[min(2,d['width'])] for d in G['doors'] if c[d['rooms'][0]]!=c[d['rooms'][1]])
    return cc/f*500,f,cc*500
miss=json.load(open(P.W+'/netmodel_r48/missed_r48.json',encoding='utf-8'))
out=[]
for o in cl:
    k=o['k']
    if 'lam' not in o: continue
    d=det[k];G=RG.analyse(d['mp'])
    cellmap={tuple(c):x['id'] for x in G['doors'] for c in x['cells']}
    best=None;unk=0
    for c in d['cuts']:
        rm={cellmap[tuple(v)] for v in c['cells'] if tuple(v) in cellmap}
        if not rm: unk+=1;continue
        r=Cf(G,rm)
        if r is None: unk+=1;continue
        if best is None or r[0]<best[0]: best=r
    o['prog_best']=best[0] if best else None
    o['rho_prog']=o['lam']/best[0] if best else 0.0
    o['unk']=unk
    # BNC: 区域网络 1–2 道门的割里 C/f 最小的（两侧 >=5%）
    res=[]
    for cc in [[b['door']] for b in G['bridges']]+[p['doors'] for p in G['door_pairs']]:
        c_=comps(G,set(cc));sz=collections.Counter()
        for i,r in enumerate(G['rooms']): sz[c_[i]]+=r['size']
        if sum(v>=0.05*G['free'] for v in sz.values())<2: continue
        r=Cf(G,set(cc))
        if r: res.append((r[0],sorted(cc)))
    if res:
        m=min(x[0] for x in res);o['rg_min']=m;o['rg_min_cuts']=[x[1] for x in res if x[0]<=m*(1+1e-9)];o['rho_rg']=o['lam']/m
    out.append(o)
json.dump(out,open('p116_rho.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(len(out))
