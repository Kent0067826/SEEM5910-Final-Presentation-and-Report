# 第 72 轮 N-1 先量图：每张图最忙门饿着的门时间，拆成“割名额卡着 / 全局名额满 G / 其他”，加 2% 跳过线
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
HERE = Path(__file__).resolve().parent
d = json.loads((HERE / 'n1_measure.json').read_text(encoding='utf8'))
rs = d['per_inst']; names = [r['inst'] for r in rs]
held = [100 * r['held_and_starve'] for r in rs]; G = [100 * r['G'] for r in rs]
other = [max(0, 100 * r['starve'] - h - g) for r, h, g in zip(rs, held, G)]
gf = [100 * r['global_full'] for r in rs]
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [3, 1.2]})
x = range(len(rs))
a.bar(x, held, color='#90a4ae', label='同时割名额卡着（第 67–69 轮已做）')
a.bar(x, G, bottom=held, color='#c62828', label='同时全局名额满 G（本轮）')
a.bar(x, other, bottom=[h + g for h, g in zip(held, G)], color='#e0e0e0', label='其他')
a.plot(x, gf, 'o', color='#1565c0', ms=5, label='全局名额满的时间（不看门）')
a.set_xticks(list(x)); a.set_xticklabels(names, fontsize=8, rotation=45, ha='right')
a.set_ylabel('占时间 %'); a.set_title('最忙门饿着的时间，按当时名额状态拆'); a.legend(fontsize=8, loc='upper left')
m = d['mean_17']
b.bar(['G\n（17 图平均）'], [100 * m['G']], color='#c62828', width=0.5)
b.axhline(2.0, color='k', ls='--'); b.text(0, 2.08, '跳过线 2.0%', ha='center', fontsize=9)
b.text(0, 100 * m['G'] + 0.05, f"{100*m['G']:.2f}%", ha='center', fontsize=10)
b.set_ylim(0, 2.6); b.set_title('N-1 分层名额：先量')
fig.tight_layout(); fig.savefig(HERE.parents[1] / '报告源' / '图' / 'p72_n1.png', dpi=150)
