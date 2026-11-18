"""把每张图的最窄割（对偶落的割）和程序找到的割对照。输出 p116_class.json。"""
import json,sys,pickle,collections
import p116_detect as D
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
sys.argv=sys.argv[:1]
import p115_dual as P
RG=P.RG
R115='C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115/'
det=pickle.load(open('p116_det.pkl','rb'))
dual={}
for r in json.load(open('p116_dual73.json',encoding='utf-8')):
    dual[r['k']]=r
for r in json.load(open(R115+'p115_dual.json',encoding='utf-8')):
    nm=r['map']
    if nm in('roomKA','roomKB','roomKC','roomKD','roomKE','roomKF'):
        dual[nm]=dict(k=nm,cut=sorted(int(x) for x in r['prices']),lam=r['lam500'],rooms=r['rooms'])
for r in json.load(open(R115+'p115_p2.json',encoding='utf-8')):
    if 'prices' in r: dual[r['tag']]=dict(k=r['tag'],cut=sorted(int(x) for x in r['prices']),lam=r['lam'],rooms=r['rooms'],f=r['f'])
miss=json.load(open(P.W+'/netmodel_r48/missed_r48.json',encoding='utf-8'))
out=[]
for k,d in det.items():
    r=dual.get(k)
    if r is None or not r.get('cut'):
        out.append(dict(k=k,cls='无网络或未解',prog=len(d['cuts'])));continue
    G=RG.analyse(d['mp']);dd={x['id']:x for x in G['doors']}
    g=RG.read_map(d['mp']);Fs={(y,x) for y in range(len(g)) for x in range(len(g[0])) if RG.free(g,y,x)}
    S=r['cut'];rem={tuple(c) for i in S for c in dd[i]['cells']}
    lab,sz=D.parts_without(g,Fs,rem);sig=D.sig_of(lab,sz,d['thr'])
    seen=any(D.same(sig,c['sig']) for c in d['cuts']) if sig else False
    w=[dd[i]['width'] for i in S]
    # 这个割是否也在“1–2 道门的区域网络割”里
    b={x['door'] for x in G['bridges']};pp={tuple(sorted(x['doors'])) for x in G['door_pairs']}
    inrg=(len(S)==1 and S[0] in b) or (len(S)==2 and tuple(S) in pp)
    dist=None
    if len(S)==2:
        dist=min(abs(a[0]-c[0])+abs(a[1]-c[1]) for a in dd[S[0]]['cells'] for c in dd[S[1]]['cells'])
    if seen: cls='管到'
    elif len(S)>=3: cls='三道以上'
    elif any(x>=2 for x in w): cls='含两格门'
    elif len(S)==2: cls='一格门对太远'
    else: cls='一格其他'
    missed=None
    if k in miss: missed=any(sorted(m[0])==S for m in miss[k]['missed'])
    out.append(dict(k=k,rooms=r.get('rooms'),lam=r['lam'],cut=S,widths=w,inrg=inrg,sig_ok=sig is not None,dist=dist,cls=cls,prog=len(d['cuts']),r48_prog=miss[k]['prog'] if k in miss else None,in_missed=missed,nmiss=len(miss[k]['missed']) if k in miss else None))
json.dump(out,open('p116_class.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(collections.Counter(o['cls'] for o in out))
bad=[(o['k'],o['prog'],o['r48_prog']) for o in out if o.get('r48_prog') is not None and o['prog']!=o['r48_prog']]
print('prog mismatch',bad)
for o in out:
    if o.get('in_missed') is not None and ((o['cls']=='管到')==o['in_missed']): print('conflict',o)
