import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['Microsoft YaHei']; plt.rcParams['mathtext.fontset']='cm'
INK='#1f2933'; MUTE='#5f6c7b'
OUT='C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验/网络协议方向/报告源/图/'
fig=plt.figure(figsize=(9.2,1.5),dpi=200); ax=fig.add_axes([0,0,1,1]); ax.axis('off'); ax.set_xlim(0,100); ax.set_ylim(0,100)
ax.text(2,70,'一道割的上限',fontsize=12,color=MUTE,va='center')
ax.text(22,70,r'$f\,X \leq C \quad\Rightarrow\quad X \leq \dfrac{C}{f}=\dfrac{26}{0.376}\approx 69$',fontsize=16,color=INK,va='center')
ax.text(2,20,'全图的上限',fontsize=12,color=MUTE,va='center')
ax.text(22,20,r'$X^{*}=\min_{S}\ C(S)\,/\,f(S)$',fontsize=16,color=INK,va='center')
ax.text(52,20,'（在这些地图上）',fontsize=11,color=MUTE,va='center')
fig.savefig(OUT+'公式_割的除法.png',facecolor='white')
