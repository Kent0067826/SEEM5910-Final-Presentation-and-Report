import sys,json
sys.path.insert(0,'C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r115')
sys.argv=sys.argv[:1]
import numpy as np,matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import p115_dual as P, p116_detect as D, pickle
RG=P.RG
plt.rcParams['font.sans-serif']=['Microsoft YaHei']
OUT='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/网络协议方向/报告源/图/演讲_最窄割在哪.png'
d={o['k']:o for o in json.load(open('p116_rho.json',encoding='utf-8'))}
det=pickle.load(open('p116_det.pkl','rb'))
pan=[('room200','程序管到：一道一格门',),('roomAC_194','两道一格门相距 69 格'),('roomZ3_194','一道 2 格门'),('roomHE_189','三道门合起来')]
fig,ax=plt.subplots(1,4,figsize=(12,3.5),dpi=170)
for a,(k,t) in zip(ax,pan):
    o=d[k];mp=det[k]['mp'];G=RG.analyse(mp);g=RG.read_map(mp);H,W=len(g),len(g[0])
    dd={x['id']:x for x in G['doors']}
    rem={tuple(c) for i in o['cut'] for c in dd[i]['cells']}
    Fs={(y,x) for y in range(H) for x in range(W) if RG.free(g,y,x)}
    lab,s=D.parts_without(g,Fs,rem);order=sorted(range(len(s)),key=lambda i:-s[i])
    img=np.ones((H,W,3))*0.25
    cols=[(0.86,0.90,0.96),(0.98,0.88,0.74),(0.85,0.93,0.82)]
    for v,i in lab.items(): img[v]=cols[min(order.index(i),2)]
    for c in det[k]['cuts']:
        for v in c['cells']: img[tuple(v)]=(0.15,0.4,0.8)
    a.imshow(img,interpolation='nearest')
    for v in rem: a.plot(v[1],v[0],'o',ms=10,mfc='none',mec='#c62828',mew=2,clip_on=False)
    a.set_title(t,fontsize=11.5,color='#1f2933');a.axis('off')
    n=len(det[k]['cuts'])
    a.text(0.5,-0.05,f'程序找到 {n} 道割（蓝格）',transform=a.transAxes,ha='center',va='top',fontsize=9.5,color='#5f6c7b')
fig.subplots_adjust(left=0.01,right=0.99,top=0.9,bottom=0.08,wspace=0.04)
fig.savefig(OUT,facecolor='white')
