import json,sys
from multiprocessing import Pool
import p116_detect as D
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
sys.argv=sys.argv[:1]
import p115_dual as P
def f(k):
    mp=P.OFF if k=='room200' else P.findmap(k.split('_')[0])
    d=D.detect(mp);return k,len(d['cuts']),d['ncand'],[len(c['cells']) for c in d['cuts']]
if __name__=='__main__':
    miss=json.load(open(P.W+'/netmodel_r48/missed_r48.json',encoding='utf-8'))
    ks=['room200','roomAA_199','roomAD_189','roomA_200','roomAC_194','roomCA_200','roomID_194','roomT_199','roomFE_189']
    with Pool(2) as p:
        for k,n,nc,l in p.imap(f,ks): print(k,'port',n,'r48',miss[k]['prog'],'cand',nc,flush=True)
