# 第 71 轮图：p71_mech.png（追链到队头的示意）、p71_result.png（按队头原因拆，17 图平均 + 每实例）
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
OUT = '../../报告源/图/'
# 图 1：示意
fig, ax = plt.subplots(figsize=(10, 3.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 4); ax.axis('off')
ax.add_patch(Rectangle((5.5, 0.6), 1, 1.6, color='#444'))
ax.add_patch(Rectangle((5.5, 1.0), 1, 0.8, color='#ffffff', ec='#2e86ab', lw=2)); ax.text(6.0, 1.4, '门格\n空着', ha='center', va='center', fontsize=9)
for k, x in enumerate((4.5, 3.5, 2.5)):
    ax.add_patch(Rectangle((x - 0.4, 1.0), 0.8, 0.8, color=['#d1495b', '#9aa5b1', '#9aa5b1'][k]))
    ax.text(x, 1.4, ['队头', '车2', '车3'][k], ha='center', va='center', color='white', fontsize=9)
ax.add_patch(Rectangle((7.1, 1.0), 0.8, 0.8, color='#edae49')); ax.text(7.5, 1.4, '对面车', ha='center', va='center', fontsize=9)
ax.annotate('', xy=(3.1, 1.4), xytext=(2.9, 1.4), arrowprops=dict(arrowstyle='->'))
ax.annotate('', xy=(4.1, 1.4), xytext=(3.9, 1.4), arrowprops=dict(arrowstyle='->'))
ax.text(3.5, 2.3, '后面两台“被前车挡”：顺着挡它的车往前追', ha='center', fontsize=10)
ax.text(6.0, 3.4, '整条队的 3 个车·拍都记到队头的原因上：', ha='center', fontsize=11, fontweight='bold')
ax.text(6.0, 2.85, '让对面车先进（软抢占能管） / 让同侧车先进（只换先后） / 自己下一个进却站着（控制延迟） / 队头不在门口（转身、故障、去别处）', ha='center', fontsize=9)
ax.text(6.0, 0.25, '网络里的对应：RSVP-TE 每一跳的接纳控制 + RFC 5712 软抢占；链路空着时先接纳谁', ha='center', fontsize=10, color='#555')
fig.savefig(OUT + 'p71_mech.png', dpi=150, bbox_inches='tight'); plt.close(fig)
# 图 2：结果
d = json.load(open('g1d_measure.json', encoding='utf8')); m = d['mean_17']; per = d['per_inst']
ks = ['O', 'N', 'Q', 'X_turn', 'X_fault', 'X_else']
lab = {'O': '让对面车\n(软抢占)', 'N': '自己下一个\n(预判放行)', 'Q': '让同侧车\n(只换先后)', 'X_turn': '队头转身', 'X_fault': '队头故障', 'X_else': '队头去别处等'}
cl = {'O': '#2e86ab', 'N': '#66a182', 'Q': '#9aa5b1', 'X_turn': '#edae49', 'X_fault': '#d1495b', 'X_else': '#bbbbbb'}
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1, 1.6]))
a1.bar(range(len(ks)), [100 * m[k] for k in ks], color=[cl[k] for k in ks])
for i, k in enumerate(ks): a1.text(i, 100 * m[k] + 0.03, f'{100 * m[k]:.2f}%', ha='center', fontsize=9)
a1.axhline(1.0, color='k', ls='--', lw=1); a1.text(5.4, 1.03, '事先写定的线 1.0%', ha='right', fontsize=9)
a1.set_xticks(range(len(ks))); a1.set_xticklabels([lab[k] for k in ks], fontsize=8.5); a1.set_ylabel('占全部车·拍 %（17 图平均）'); a1.set_ylim(0, 1.25)
a1.set_title('按队头原因拆：没有一类过线', fontsize=11)
per = sorted(per, key=lambda r: -r['S']); x = range(len(per)); b = [0] * len(per)
for k in ks:
    v = [100 * r[k] for r in per]; a2.bar(x, v, bottom=b, color=cl[k], label=lab[k].replace('\n', '')); b = [p + q for p, q in zip(b, v)]
a2.set_xticks(list(x)); a2.set_xticklabels([r['inst'] for r in per], rotation=60, fontsize=8); a2.set_ylabel('占全部车·拍 %')
a2.set_title('每张图：门空着、要过这扇门却站着的车·拍', fontsize=11); a2.legend(fontsize=8, ncol=2)
fig.tight_layout(); fig.savefig(OUT + 'p71_result.png', dpi=150); plt.close(fig)
