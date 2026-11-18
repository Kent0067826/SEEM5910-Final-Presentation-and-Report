# 第69轮：S-4 B2 的确认结果。左：开发（第68轮 B2）vs 确认（本轮），旁边放第63轮那次确认作对照；右：确认里每个实例的变化
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, json, os
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..', '..')
L = lambda *p: json.load(open(os.path.join(R, 'rounds', *p), encoding='utf-8'))
pts = [('开局实测收名额\n开发（第62轮）', L('p62', 'dev_compare_A.json'), '#9bbbe0'), ('开局实测收名额\n确认（第63轮）', L('p63', 'confirm_compare.json'), '#2a6fbb'),
       ('自动带宽调割名额\n开发（第68轮）', L('p68', 'dev_compare_B2.json'), '#f0c08a'), ('自动带宽调割名额\n确认（本轮）', L('p69', 'confirm_compare.json'), '#d9822b')]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.8), gridspec_kw={'width_ratios': [1.1, 1.4]})
for i, (lab, d, c) in enumerate(pts):
    m = 100 * d['mean']; lo, hi = 100 * d['ci'][0], 100 * d['ci'][1]
    a1.bar(i, m, color=c, width=0.6); a1.errorbar(i, m, yerr=[[m - lo], [hi - m]], color='k', capsize=5)
    a1.text(i, hi + 0.15, '%+.2f%%\n最差 %+.1f%%' % (m, 100 * d['worst']), ha='center', fontsize=8)
a1.axhline(0, color='k', lw=0.8); a1.set_xticks(range(4)); a1.set_xticklabels([p[0] for p in pts], fontsize=8)
a1.set_ylim(-1.6, 2.4); a1.set_ylabel('按实例平均的变化（%），竖线 = 95% 区间'); a1.set_title('开发 vs 确认（左两根是第 62/63 轮作对照）')
rows = sorted(pts[3][1]['per_inst'], key=lambda r: r['mean'])
for j, r in enumerate(rows):
    col = '#d9822b' if r['inst'].startswith('roomM') else '#2a6fbb'
    a2.barh(j, 100 * r['mean'], color=col, xerr=[[100 * (r['mean'] - r['lo'])], [100 * (r['hi'] - r['mean'])]], error_kw={'lw': 0.7, 'alpha': 0.6})
a2.set_yticks(range(len(rows))); a2.set_yticklabels([r['inst'] for r in rows], fontsize=8)
a2.axvline(0, color='k', lw=0.8); a2.axvline(-3, color='r', lw=0.8, ls='--')
a2.set_xlabel('确认里每个实例的变化（%），横线 = 95% 区间；红虚线 = −3% 判据线')
a2.set_title('确认每个实例（橙 = 本轮新画的留出图，蓝 = 官方图）', fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(R, '报告源', '图', 'p69_confirm.png'), dpi=110)
