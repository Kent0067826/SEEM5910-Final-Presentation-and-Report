"""Figure for the supplementary comparison: mean completions per official instance for DEF, N2, N2F, LCAP (20 runs each)."""
import json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Noto Sans CJK SC'
A = json.load(open('/home/claude/proj/v10/analysis_r52b.json'))['mean_completed']
K = ['room200', 'room250', 'room300', 'maze40', 'maze60', 'random200', 'random300', 'warehouse100']
M = [('DEF', '官方默认程序', '#b9b8b2'), ('N2', '+ 冠军任务分配', '#8fb6e8'), ('N2F', '+ 修好执行器', '#2a78d6'), ('LCAP', '+ 本文方法（LCAP）', '#e8743b')]
fig, ax = plt.subplots(figsize=(11, 4.2)); w = 0.2
for i, (m, lab, c) in enumerate(M):
    ys = [A[m][k] / A['DEF'][k] for k in K]
    ax.bar([j + (i - 1.5) * w for j in range(len(K))], ys, w, color=c, label=lab)
ax.axhline(1, color='#3b3b38', lw=.8)
ax.set_xticks(range(len(K))); ax.set_xticklabels(K, fontsize=9); ax.set_ylabel('完成数 / 官方默认程序', fontsize=9.5)
for s in ['top', 'right']: ax.spines[s].set_visible(False)
ax.set_facecolor('#fafaf8'); ax.grid(axis='y', color='#e3e2de', lw=.8); ax.set_axisbelow(True)
ax.legend(fontsize=8.5, frameon=False, ncol=4, loc='upper left')
ax.set_title('官方 8 个实例、同一组新种子（每实例 20 次）：一步步相对官方默认程序', loc='left', fontsize=10.5)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=170)
