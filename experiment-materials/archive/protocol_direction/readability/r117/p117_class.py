"""第 117 轮：列生成解 第 29 轮 12 张新图+官方、第 71 轮 6 张 L 系、第 40 轮 7 张图、roomB、roomC，并按最窄割分类。
全部 128 张再用列生成复算一次，和第 115、116 轮的 λ 对。"""
import json,pickle,time,sys,glob,os
import numpy as np
import p116_detect as D, p117_cg as Q
RG=Q.RG
W='C:/Users/RETN_kwang/robotnet-lab/repo/workspace/'
OFF='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/outputs/robot-windowlab/source/example_problems/room.domain/maps/'
det=pickle.load(open('../r116/p116_det.pkl','rb'))
old={r['k']:r for r in json.load(open('../../../repo/protocol_direction/readability/r116/p116_class.json',encoding='utf-8'))}
def comps(G,rm):
    n=len(G['rooms']);p=list(range(n))
    def f(x):
        while p[x]!=x:p[x]=p[p[x]];x=p[x]
        return x
    for d in G['doors']:
        if d['id'] in rm:continue
        a,b=d['rooms'];p[f(a)]=f(b)
    return [f(i) for i in range(n)]
def one(k,mp,dd=None):
    t=time.time();G=RG.analyse(mp)
    if len(G['rooms'])<2 or not G['connected']: return dict(k=k,note='无网络',rooms=len(G['rooms']),connected=G['connected'])
    lam,ub,y,it=Q.solve(G)
    ids=[G['doors'][i]['id'] for i in range(len(y)) if y[i]>1e-7]
    S=sorted(ids);DD={x['id']:x for x in G['doors']}
    c=comps(G,set(S));A=sum(r['size'] for r in G['rooms']);w=[r['size']/A for r in G['rooms']]
    f=sum(w[s]*w[u] for s in range(len(w)) for u in range(len(w)) if c[s]!=c[u])
    Cc=sum(Q.C_DOOR[min(2,DD[i]['width'])] for i in S)
    d=dd if dd is not None else D.detect(mp)
    cuts=d['cuts']
    g=RG.read_map(mp);Fs={(yy,x) for yy in range(len(g)) for x in range(len(g[0])) if RG.free(g,yy,x)}
    rem={tuple(cc) for i in S for cc in DD[i]['cells']}
    lab,sz=D.parts_without(g,Fs,rem);sig=D.sig_of(lab,sz,d['thr'])
    def cs(c_): return c_['sig'] if 'sig' in c_ else D.sig_of(c_['lab'],c_['sizes'],d['thr'])
    seen=[c_['kind'] for c_ in cuts if sig and D.same(sig,cs(c_))]
    wd=[DD[i]['width'] for i in S]
    dist=None
    if len(S)==2: dist=min(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in DD[S[0]]['cells'] for b in DD[S[1]]['cells'])
    if seen: cls='管到'
    elif len(S)>=3: cls='三道以上'
    elif any(x>=2 for x in wd): cls='含两格门'
    elif len(S)==2: cls='一格门对太远'
    else: cls='一格其他'
    return dict(k=k,rooms=len(G['rooms']),doors=len(G['doors']),lam=lam*500,ub=ub*500,it=it,cut=S,widths=wd,dist=dist,cls=cls,seen=seen,nb=sum(c_['kind']=='bridge' for c_ in cuts),np=sum(c_['kind']=='pair' for c_ in cuts),f=f,div=(Cc/f*500 if f else None),prices={int(i):round(float(y[[x['id'] for x in G['doors']].index(i)]),4) for i in S},sec=round(time.time()-t,2),sizes=sorted(sum(r['size'] for i,r in enumerate(G['rooms']) if c[i]==q) for q in set(c)))
out={}
todo=[('room',OFF.replace('maps/','')+'maps/room-64-64-16.map')]
for b in 'PQRS': todo.append(('room'+b,W+'maps_r29/room%s.map'%b))
for b in 'AB': todo.append(('zone'+b,W+'maps_r29/zone%s.map'%b))
for b in 'ABCDEF': todo.append(('L'+b,W+'maps_r70/roomL%s.map'%b))
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
A=sys.argv;sys.argv=A[:1]
import p115_dual as P
for b in ['roomAD','roomBF','roomT','roomB','roomC']:
    todo.append((b,P.findmap(b)))
for k,mp in todo:
    try: o=one(k,mp)
    except Exception as e: o=dict(k=k,err=repr(e))
    out[k]=o;print(json.dumps(o,ensure_ascii=False)[:420],flush=True)
    json.dump(out,open('p117_class.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
