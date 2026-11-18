"""所有房间图：跑程序找割的 Python 版，存每个割的分块（只存格子集合）。"""
import json,sys,pickle,os
from multiprocessing import Pool
import p116_detect as D
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
sys.argv=sys.argv[:1]
import p115_dual as P
R='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/网络协议方向'
def f(a):
    k,mp=a
    d=D.detect(mp)
    cuts=[dict(kind=c['kind'],cells=c['cells'],sig=D.sig_of(c['lab'],c['sizes'],d['thr'])) for c in d['cuts']]
    return k,mp,d['N'],d['thr'],d['ncand'],cuts
if __name__=='__main__':
    miss=json.load(open(P.W+'/netmodel_r48/missed_r48.json',encoding='utf-8'))
    todo=[]
    for k in miss:
        if k=='room300':continue
        todo.append((k,P.OFF if k=='room200' else P.findmap(k.split('_')[0])))
    for k in ['roomKA','roomKB','roomKC','roomKD','roomKE','roomKF','roomBA2']:
        m=P.findmap(k)
        if m: todo.append((k,m))
    M=P.W+'/maps_r64/room-64-64-16_'
    todo+=[('A6',M+'A6.map'),('W6',M+'W6.map')]
    for b in ['p02','p18','p57','p61','p63','p69','p75','p76']:
        dd=R+'/harness/data/maps_'+b
        for m in json.load(open(dd+'/instances.json',encoding='utf-8')): todo.append((b+'/'+m,dd+'/'+m+'.map'))
    print(len(todo),flush=True)
    out={}
    with Pool(3) as p:
        for k,mp,N,thr,nc,cuts in p.imap_unordered(f,todo):
            out[k]=dict(mp=mp,N=N,thr=thr,ncand=nc,cuts=cuts)
            print(k,len(cuts),nc,flush=True)
            pickle.dump(out,open('p116_det.pkl','wb'))
