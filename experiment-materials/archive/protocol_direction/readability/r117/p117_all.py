"""列生成重解 128 张，对 r116 的 λ 和割。"""
import json,pickle,sys
import numpy as np, p117_cg as Q
det=pickle.load(open('../r116/p116_det.pkl','rb'))
old={r['k']:r for r in json.load(open('../../../repo/protocol_direction/readability/r116/p116_class.json',encoding='utf-8'))}
out=[]
for k,d in det.items():
    G=Q.RG.analyse(d['mp'])
    if len(G['rooms'])<2 or not G['connected']: out.append(dict(k=k,note='无网络'));continue
    lam,ub,y,it=Q.solve(G);S=sorted(G['doors'][i]['id'] for i in range(len(y)) if y[i]>1e-7)
    o=old.get(k,{});out.append(dict(k=k,lam=lam*500,gap=(ub-lam)*500,it=it,cut=S,old=o.get('lam'),oldcut=o.get('cut'),cls=o.get('cls')))
    json.dump(out,open('p117_all.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
print('done',len(out))
