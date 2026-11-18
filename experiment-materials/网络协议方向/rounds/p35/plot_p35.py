# 协议第 35 轮的图：① 僵局示意（room250 9702×104 第 1000 拍局部）；② 先量：每图门口对峙时间占比 + 塌局那局每 250 拍完成数。
# 用法：python plot_p35.py（不加 -I）
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
H = Path(__file__).resolve().parent; FIG = H.parent.parent / '报告源' / '图'
# ① 局部图（取自 diag_local.py 输出，行 30–36、列 43–51）
grid = ['70 74 202 64 54 # 7 . .', '. 233 43 50 168 # . . .', '# 123 # # 150 # # # #', '34 103 242 223 206 19 . . .',
        '107 . 37 . . # . . .', '171 132 2 57 11 # . . .', '148 . . . 76 # . . .']
face = {150: 'S', 206: 'E', 19: 'W'}; doors = {(32, 44), (32, 47), (33, 48)}
fig, ax = plt.subplots(figsize=(7.6, 5.2))
for r, row in enumerate(grid):
    for c, x in enumerate(row.split()):
        R, C = 30 + r, 43 + c; y = -r
        if x == '#': col = '#555555'
        elif (R, C) in doors: col = '#f3d27a'
        else: col = '#ffffff'
        if (R, C) in {(34, 47), (33, 49)}: col = '#b9e4b0'
        ax.add_patch(Rectangle((c, y), 1, 1, fc=col, ec='#999999', lw=0.6))
        if x not in '#.':
            a = int(x); key = a in face
            ax.add_patch(plt.Circle((c + .5, y + .5), .36, fc='#d9534f' if key else '#9bb7d4', ec='k', lw=0.6))
            if key:
                dx, dy = {'E': (.45, 0), 'W': (-.45, 0), 'S': (0, -.45)}[face[a]]
                ax.add_patch(FancyArrow(c + .5, y + .5, dx, dy, width=.06, head_width=.22, head_length=.15, color='k'))
                ax.text(c + .5, y + .5, str(a), ha='center', va='center', fontsize=8, color='w', weight='bold')
ax.text(3.5, -1.5, '北门→', ha='center', va='center', fontsize=8, color='w')
ax.text(5.5, -3.08, '东门', ha='center', va='top', fontsize=8, color='w')
ax.text(4.5, -7.15, '黄格 = 门格（都只有 1 格宽）；绿格 = 空着、本可以让开的格子（206 往南、19 往后）', ha='center', va='top', fontsize=9)
ax.set_xlim(-0.2, 9.2); ax.set_ylim(-7.8, 1.2); ax.set_aspect('equal'); ax.axis('off')
ax.set_title('room250 第 34 轮分道局第 1000 拍：两扇 1 格门只隔一步\n红色三台车互相等，旁边有空格，但门口规则不让挪；从第 330 拍僵到第 2192 拍', fontsize=10)
fig.tight_layout(); fig.savefig(FIG / 'p35_deadlock.png', dpi=150); plt.close(fig)
# ② 先量
m = json.load(open(H / 'measure_door_standoff.json', encoding='utf8'))
d = json.load(open(H / 'diag_collapse.json', encoding='utf8'))
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={'width_ratios': [1.1, 1]})
names = [r['inst'] for r in m]; v = [100 * r['frac_time'] for r in m]
a1.barh(range(len(names)), v, color=['#d9534f' if x >= 5 else '#9bb7d4' for x in v])
a1.axvline(5, color='r', ls='--', lw=1); a1.text(5.5, len(names) - .3, '跳过线 5%', color='r', fontsize=9)
for i, r in enumerate(m):
    if r['longest'] >= 300: a1.text(v[i] + .6, i, '最长 %d 拍' % r['longest'], va='center', fontsize=8)
a1.set_yticks(range(len(names))); a1.set_yticklabels(names, fontsize=8); a1.invert_yaxis()
a1.set_xlabel('有门口对峙（≥100 拍）在进行的时间占比（%）'); a1.set_title('先量（基线 17 图）：平均 9.0%，roomW 一次 2189 拍 → 不跳过', fontsize=10)
runs = {r['run']: r['bins250'] for r in d}
x = [250 * i + 125 for i in range(20)]
a2.plot(x, runs['room250_LCAP_9702_104'], 'o-', color='#2a6fbb', ms=3, label='原来（LCAP）：1114')
a2.plot(x, runs['room250_PICK_9702_104'], 's-', color='#d9534f', ms=3, label='第 34 轮分道：700')
a2.axvspan(330, 2192, color='#f3d27a', alpha=.4, label='北门旁僵局（第 330–2192 拍）')
a2.set_xlabel('时间（拍）'); a2.set_ylabel('每 250 拍完成数'); a2.legend(fontsize=8)
a2.set_title('塌掉的那一局：僵局一出现，产量就掉下去\n（加看门狗后同一局 700 → 1091，这局事先看过，不算判据）', fontsize=10)
fig.tight_layout(); fig.savefig(FIG / 'p35_measure.png', dpi=150); plt.close(fig)
print('ok')
