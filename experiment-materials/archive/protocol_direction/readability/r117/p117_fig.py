import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='Microsoft YaHei'
rows=json.load(open('C:/Users/RETN_kwang/robotnet-lab/repo/protocol_direction/readability/r113/cuts_agg.json',encoding='utf-8'))
s=[r for r in rows if r['kind']=='单门割' and not r['inst'].endswith('_nd') and r['w']==[1]]
nar={('room200',6),('room250',6),('room300',6),('roomAD_189',25),('roomBF_240',30),('roomP_254',3),('roomP_254',17),('roomS_247',21),('roomT_199',3)}
big=[r for r in s if (r['inst'],r['doors'][0]) in nar]; sm=[r for r in s if (r['inst'],r['doors'][0]) not in nar]
print(len(s),len(big),len(sm))
fig,ax=plt.subplots(figsize=(6.6,3.8),dpi=200)
ax.plot([0,30],[0,30],color='#B8BEC6',lw=1.5,zorder=1)
ax.text(23.2,24.6,'两边一样多',color='#5B6470',fontsize=10,rotation=35,ha='center')
ax.scatter([r['cb'] for r in sm],[r['ca'] for r in sm],s=46,color='#7A8594',edgecolor='white',lw=1,zorder=3,label='不是所在图最窄的割（14 道）')
ax.scatter([r['cb'] for r in big],[r['ca'] for r in big],s=64,color='#D9772B',edgecolor='white',lw=1,zorder=4,label='正好是所在图最窄的割（9 道）')
ax.annotate('最窄的门管住后都到 21–28 台，\n其他门没有跑满',xy=(7.0,25.6),xytext=(10.2,27.0),fontsize=10,color='#2A2F36',va='center',arrowprops=dict(arrowstyle='-',color='#7A8594',lw=1))
ax.set_xlim(0,30);ax.set_ylim(0,30)
ax.set_xlabel('不管门：每 500 拍过门台数',fontsize=11,color='#2A2F36')
ax.set_ylabel('本文较早版本：每 500 拍过门台数',fontsize=11,color='#2A2F36')
ax.grid(color='#E8EAED',lw=.8);ax.set_axisbelow(True)
for k in('top','right'):ax.spines[k].set_visible(False)
for k in('left','bottom'):ax.spines[k].set_color('#B8BEC6')
ax.tick_params(colors='#5B6470')
ax.legend(loc='lower right',frameon=False,fontsize=10)
fig.tight_layout();fig.savefig('演讲_最窄门与其他门.png')
