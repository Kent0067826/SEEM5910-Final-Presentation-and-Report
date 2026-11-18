import p117_cg as Q,glob,numpy as np,time
B='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/outputs/robot-windowlab/source/example_problems/'
for m in glob.glob(B+'*/maps/*.map'):
    if not any(x in m for x in('maze-32','random-64','warehouse_long')): continue
    G=Q.RG.analyse(m);t=time.time();lam,ub,y,it=Q.solve(G,maxit=1500)
    D=G['doors'];S=[(D[i]['id'],D[i]['width'],round(float(y[i]),3)) for i in range(len(y)) if y[i]>1e-7]
    print(m[-28:],len(G['rooms']),len(D),'lam',round(lam*500,2),'ub',round(ub*500,2),'it',it,len(S),S[:10],round(time.time()-t,1),'widths',sorted(set(d['width'] for d in D)),flush=True)
