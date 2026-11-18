# 协议第 35 轮看得懂的总结用图：网络里的 PFC 暂停死锁和看门狗 ↔ 仓库门口僵局和超时放行（示意）。用法：python plot_p35_simple.py
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
FIG = Path(__file__).resolve().parent.parent.parent / '报告源' / '图'
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
def box(ax, x, y, t, c):
    ax.add_patch(FancyBboxPatch((x - .9, y - .35), 1.8, .7, boxstyle='round,pad=0.05', fc=c, ec='k', lw=.8)); ax.text(x, y, t, ha='center', va='center', fontsize=10)
def arr(ax, a, b, t, rad=.3, at=None):
    ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f'arc3,rad={rad}', arrowstyle='-|>', mutation_scale=14, lw=1.2, color='#c0392b'))
    x, y = at if at else ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    ax.text(x, y, t, ha='center', va='center', fontsize=8.5, color='#c0392b', bbox=dict(fc='white', ec='none', pad=1))
ax = axs[0]; box(ax, 1, 2.2, '交换机 A', '#d6e6f5'); box(ax, 4, 2.2, '交换机 B', '#d6e6f5'); box(ax, 2.5, .3, '交换机 C', '#d6e6f5')
arr(ax, (1.9, 2.4), (3.1, 2.4), '“先别发”', -.3, (2.5, 2.95)); arr(ax, (4.2, 1.85), (3.2, .5), '“先别发”', -.3, (4.25, .9)); arr(ax, (1.8, .4), (.9, 1.85), '“先别发”', -.3, (.75, .9))
ax.text(2.5, -.75, '互相喊“先别发”，绕成一圈，谁也发不出去\n看门狗：停得太久，就暂时不理“先别发”，放包出去', ha='center', fontsize=9.5)
ax.set_xlim(-.3, 5.3); ax.set_ylim(-1.3, 3.2); ax.axis('off'); ax.set_title('网络里：无损以太网的暂停死锁和看门狗', fontsize=11)
ax = axs[1]; box(ax, 1, 2.2, '车 150\n（北门里）', '#f6d5d3'); box(ax, 4, 2.2, '车 19\n（东门里）', '#f6d5d3'); box(ax, 2.5, .3, '车 206\n（两门之间）', '#f6d5d3')
arr(ax, (1.3, 1.85), (1.9, .65), '等 206 让开', .2, (.95, 1.2)); arr(ax, (3.7, 1.85), (3.1, .65), '等 206 让开', .2, (3.05, 1.35)); arr(ax, (3.4, .3), (4.3, 1.85), '等 19 先出', .45, (4.75, .75))
ax.text(2.5, -.75, '206 旁边明明有空格，门口规则却不许它挪\n超时放行：站满 100 或 300 拍，这一步不管门口规则', ha='center', fontsize=9.5)
ax.set_xlim(-.3, 5.3); ax.set_ylim(-1.3, 3.2); ax.axis('off'); ax.set_title('仓库里：两扇门挨着时，门口规则互相锁住', fontsize=11)
fig.tight_layout(); fig.savefig(FIG / 'p35_simple_idea.png', dpi=150); print('ok')
