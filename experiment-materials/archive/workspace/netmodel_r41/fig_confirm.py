"""第 41 轮确认：NETcap（模型名额）相对 C24CF（手调名额）的逐实例差异，点 = 20 对的平均，横线 = 自助法 95% 区间。"""
import json, sys, random, statistics as st, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if 'NotoSansCJK-Regular' in f: font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = ['Noto Sans CJK SC', 'DejaVu Sans']
INK, INK2, GRID, SURF, BLUE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb', '#2a78d6'
V = '/home/claude/proj/v10/'
Z = json.load(open(V + 'test_freeze_v31.json')); A = json.load(open(V + 'analysis_r41.json'))
R = [json.loads(l) for l in open(V + 'batches/r41-test/rows.jsonl')]
b = {(r['map'], r['seed'], r['pseed']): r['completed'] for r in R if r['method'] == 'C24CF'}
insts = Z['instances']; ys, lo, hi = [], [], []
rnd = random.Random(0)
for k in insts:
    g = [100 * (r['completed'] / b[(k, r['seed'], r['pseed'])] - 1) for r in R if r['map'] == k and r['method'] == 'NETcap']
    ys.append(st.mean(g)); bs = sorted(st.mean(rnd.choice(g) for _ in g) for _ in range(2000)); lo.append(bs[50]); hi.append(bs[1949])
fig, ax = plt.subplots(figsize=(7.2, 7.4))
pos = list(range(len(insts)))[::-1]
ax.axvline(0, color=INK2, lw=0.9); ax.axvline(-1, color=INK2, lw=0.8, ls=(0, (4, 3)))
ax.text(-1.15, len(insts) - 0.3, '−1% 不差于的界', fontsize=8, color=INK2, ha='right', va='bottom')
for p, y, l, h in zip(pos, ys, lo, hi):
    ax.plot([l, h], [p, p], color=BLUE, lw=1.6, alpha=0.55, solid_capstyle='round'); ax.plot([y], [p], 'o', color=BLUE, ms=6, markeredgecolor='white', markeredgewidth=1)
ax.set_yticks(pos); ax.set_yticklabels(insts, fontsize=8, color=INK2)
o = A['H1|NETcap']
ax.set_title(f"模型推出的名额 vs 手调名额（确认：20 个实例 × 20 对）\n总体 {o['mean']:+.2f}% [{o['lo']:+.2f}, {o['hi']:+.2f}]：不差于成立，更好不显著（p = {o['p']:.2f}）",
             fontsize=9.5, color=INK, loc='left')
ax.set_facecolor(SURF)
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
ax.spines['bottom'].set_color(GRID); ax.tick_params(colors=INK2, labelsize=8); ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.set_xlabel('NETcap 相对 C24CF 的完成数差异（%）', fontsize=9, color=INK2)
ax.axhline(len(insts) - 8.5, color=GRID, lw=0.8)
ax.text(ax.get_xlim()[1], len(insts) - 8.5 + 0.15, '官方 8 个 ↑  留出 12 个 ↓', fontsize=7.5, color=INK2, ha='right', va='bottom')
fig.tight_layout(); fig.savefig('/home/claude/r41/fig_r41_confirm.png', dpi=160); print('ok')
