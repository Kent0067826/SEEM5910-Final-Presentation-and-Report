import p117_cg as Q,glob,json,time
W='C:/Users/RETN_kwang/robotnet-lab/repo/workspace/'
G=Q.RG.analyse(W+'maps_r29/roomQ.map');print([ (d['id'],d['width'],d['cells']) for d in G['doors'] if d['id'] in (1,)])
G=Q.RG.analyse(W+'maps_r29/zoneA.map');print(G['connected'],len(G['rooms']),len(G['doors']))
B='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/outputs/robot-windowlab/source/example_problems/'
for m in glob.glob(B+'*/maps/*.map'):
    if 'room-64' in m: continue
    t=time.time()
    try:
        G=Q.RG.analyse(m);print(m[-30:],len(G['rooms']),len(G['doors']),G['connected'],round(time.time()-t,1),flush=True)
    except Exception as e: print(m[-30:],'err',repr(e)[:100],flush=True)
