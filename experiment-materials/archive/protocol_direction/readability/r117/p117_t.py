import sys,time
import p117_cg as Q
OFF='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/outputs/robot-windowlab/source/example_problems/room.domain/maps/room-64-64-16.map'
G=Q.RG.analyse(OFF);t=time.time();lam,ub,y,it=Q.solve(G)
print(len(G['rooms']),len(G['doors']),lam*500,ub*500,it,time.time()-t,[ (G['doors'][i]['id'],round(y[i],3)) for i in range(len(y)) if y[i]>1e-7])
