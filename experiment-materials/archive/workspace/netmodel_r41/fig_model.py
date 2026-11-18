"""第 41 轮（网络建模第 3、4 步）的图：
  fig_r41_flow.png      每个割的流量份额：均匀假设（只用地图） vs 任务文件
  fig_r41_capacity.png  完成速度随时间，和最大并发流给出的稳态上限（4 张地图）
  fig_r41_latency.png   时延：实测 vs 自由流最短时间，斜线 = 变慢倍数 2.23"""
import json, sys, statistics, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0, '/home/claude/r40')
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = ['Noto Sans CJK SC', 'DejaVu Sans']
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'

def style(ax):
    ax.set_facecolor(SURF)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)

# 1. 流量份额
fl = json.load(open('/home/claude/r40/batch/flow.json'))
fig, ax = plt.subplots(figsize=(5.2, 5))
x = [e['leg2_uniform'] for e in fl]; y = [e['leg2_task'] for e in fl]
ax.plot([0, 0.55], [0, 0.55], color=INK2, lw=0.8, ls=(0, (4, 3)))
ax.scatter(x, y, s=22, color=BLUE, edgecolor='white', linewidth=0.8, zorder=3)
style(ax); ax.set_xlim(0, 0.55); ax.set_ylim(0, 0.55)
ax.set_xlabel('均匀假设：2p(1−p)（只用地图）', fontsize=9, color=INK2); ax.set_ylabel('任务文件：第 2 段穿越这个割的比例', fontsize=9, color=INK2)
err = max(abs(a - b) for a, b in zip(x, y))
ax.set_title(f'每单任务穿越某个割的概率（11 张开发地图，{len(fl)} 个割）\n最大偏差 {err:.3f}；虚线 = 完全一致', fontsize=9.5, color=INK, loc='left')
fig.tight_layout(); fig.savefig('/home/claude/r40/fig_r41_flow.png', dpi=160); plt.close(fig)

# 2. 完成速度 vs 稳态上限
pr = json.load(open('/home/claude/r40/batch/profiles.json'))
caps = {'room200': 69.2, 'roomBF_240': 60.7, 'roomAD_189': 52.2, 'roomCD_194': 243.8}
names = {'room200': '官方 room200', 'roomBF_240': 'roomBF_240', 'roomAD_189': 'roomAD_189', 'roomCD_194': 'roomCD_194'}
fig, axs = plt.subplots(1, 4, figsize=(13, 3.6), sharey=False)
for ax, k in zip(axs, caps):
    t = [250 + 500 * i for i in range(10)]
    ax.plot(t, pr[f'{k}|C24CF'], '-o', color=BLUE, lw=2, ms=4.5, label='C24CF', markeredgecolor='white')
    ax.plot(t, pr[f'{k}|N2F'], '-o', color=ORANGE, lw=2, ms=4.5, label='N2F', markeredgecolor='white')
    ax.axhline(caps[k], color=INK2, lw=1, ls=(0, (4, 3)))
    ax.text(100, caps[k] - 4, f'模型稳态上限 {caps[k]:.0f}', ha='left', va='top', fontsize=8, color=INK2, bbox=dict(boxstyle='square,pad=0.15', fc=SURF, ec='none'))
    style(ax); ax.set_ylim(0, max(250, caps[k] * 1.15) if k == 'roomCD_194' else 200)
    ax.set_title(names[k], fontsize=9.5, color=INK, loc='left'); ax.set_xlabel('时间（拍）', fontsize=8.5, color=INK2)
axs[0].set_ylabel('每 500 拍完成单数（5 个种子平均）', fontsize=8.5, color=INK2)
axs[0].legend(fontsize=8, frameon=False, loc='upper right')
fig.suptitle('完成速度随时间下降，后段贴近最大并发流算出的稳态上限（roomCD 除外：它的门带宽远没用满）', fontsize=10, color=INK, x=0.01, ha='left')
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig('/home/claude/r40/fig_r41_capacity.png', dpi=150); plt.close(fig)

# 3. 时延
lp = json.load(open('/home/claude/r40/batch/latency_pairs.json'))
fig, ax = plt.subplots(figsize=(5.4, 5))
for meth, nd, col, lab in [('C24CF', False, BLUE, 'C24CF 有故障'), ('C24CF', True, AQUA, 'C24CF 无故障')]:
    v = [p for p in lp if p['method'] == meth and p['inst'].endswith('_nd') == nd]
    ax.scatter([p['T_free'] for p in v], [p['T_meas'] for p in v], s=18, color=col, edgecolor='white', linewidth=0.6, label=lab, zorder=3)
for a, t in [(2.23, '× 2.23'), (1.33, '× 1.33')]:
    ax.plot([0, 450], [0, 450 * a], color=INK2, lw=0.8, ls=(0, (4, 3))); ax.text(430, 430 * a, t, fontsize=8, color=INK2, ha='right', va='bottom')
style(ax); ax.set_xlim(0, 450); ax.set_ylim(0, 1100)
ax.set_xlabel('模型：领任务到走到割的门，自由流最短时间（拍）', fontsize=8.5, color=INK2); ax.set_ylabel('实测平均时延（拍）', fontsize=8.5, color=INK2)
ax.set_title('割的时延：实测 ≈ 自由流 × 常数（每点 = 一个割的一个方向）', fontsize=9.5, color=INK, loc='left')
ax.legend(fontsize=8, frameon=False, loc='upper left')
fig.tight_layout(); fig.savefig('/home/claude/r40/fig_r41_latency.png', dpi=160); plt.close(fig)
print('ok')
