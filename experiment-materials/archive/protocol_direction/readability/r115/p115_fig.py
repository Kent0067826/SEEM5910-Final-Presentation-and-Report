import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Microsoft YaHei'; plt.rcParams['axes.unicode_minus']=False
INK='#2b2b2b';MUT='#6b6b6b';LINE='#2a6fb0';GRID='#e6e6e6'
f=0.37569; top=110.78; k=top*f
fig,ax=plt.subplots(figsize=(8.2,4.3),dpi=200)
ax.plot([0,k,62],[0,top,top],color=LINE,lw=2.2,solid_capstyle='round')
pts=[(26,69.21,'现在：26 台 → 69.2 单',(29,56)),(32,85.18,'拓宽门 6：32 台 → 85.2 单（+23.1%）',(35,76)),(52,top,'加一道门：这面墙 52 台 → 110.8 单（+60.1%）',(36,126))]
for x,y,t,p in pts:
    ax.plot([x],[y],'o',ms=8,color=LINE,mec='white',mew=2,zorder=5)
    ax.annotate(t,(x,y),xytext=p,fontsize=10.5,color=INK,va='center',arrowprops=dict(arrowstyle='-',color=MUT,lw=.8,shrinkB=5))
ax.plot([k],[top],'o',ms=8,color='white',mec=LINE,mew=2,zorder=5)
ax.annotate('拐点 41.6 台：下一道割接手',(k,top),xytext=(17,112),fontsize=10.5,color=INK,va='center',arrowprops=dict(arrowstyle='-',color=MUT,lw=.8,shrinkB=5))
ax.text(2,78,'斜率 2.66：门 6 每多过 1 台\n多完成 2.66 单',fontsize=10.5,color=MUT,ha='left',va='center')
ax.text(61.5,100,'门 6 价格 0，门 4、5 各 2.13',fontsize=10.5,color=MUT,ha='right',va='center')
ax.set_xlim(0,62);ax.set_ylim(0,135)
ax.set_xlabel('门 6 这面墙每 500 拍能过的车数（台）',color=INK,fontsize=11);ax.set_ylabel('模型上限（单 / 500 拍）',color=INK,fontsize=11)
ax.grid(axis='y',color=GRID,lw=.8);ax.set_axisbelow(True)
for s in('top','right'):ax.spines[s].set_visible(False)
for s in('left','bottom'):ax.spines[s].set_color('#bbbbbb')
ax.tick_params(colors=MUT,labelsize=10,length=0)
fig.tight_layout();fig.savefig('C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/网络协议方向/报告源/图/演讲_门价格的范围.png')
