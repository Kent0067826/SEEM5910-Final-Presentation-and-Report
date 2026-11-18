# 第 74 轮图：p74_mech.png（四项单独在每张图上的变化：各管各的图）、p74_result.png（单项、相加预测、组合）
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
OUT = '../../报告源/图/'
d = json.load(open('additivity.json', encoding='utf8')); per = d['per_inst']; m = d['mean']
insts = sorted(per, key=lambda i: -per[i]['C4'])
cols = [('RFD', '抖动抑制\n（路由层）'), ('S3', '按实测收名额\n（拓扑层准入）'), ('Q5', '看门狗有任务才计时\n（物理层）'), ('PICK', '忙门分两道\n（链路层）')]
M = np.array([[per[i][k] for k, _ in cols] for i in insts])
fig, ax = plt.subplots(figsize=(8.5, 7))
im = ax.imshow(M, cmap='RdBu_r', vmin=-15, vmax=15, aspect='auto')
for r in range(M.shape[0]):
    for c in range(M.shape[1]):
        v = M[r, c]
        if abs(v) >= 0.05: ax.text(c, r, f'{v:+.1f}', ha='center', va='center', fontsize=8, color='white' if abs(v) > 8 else 'black')
ax.set_xticks(range(len(cols))); ax.set_xticklabels([t for _, t in cols], fontsize=9)
ax.set_yticks(range(len(insts))); ax.set_yticklabels(insts, fontsize=9)
plt.colorbar(im, ax=ax, label='单独打开时完成数变化（%）')
ax.set_title('四项单独打开：各自只在几张图上起作用（空白 = 没变化）', fontsize=12)
plt.tight_layout(); plt.savefig(OUT + 'p74_mech.png', dpi=150); plt.close()
fig, axs = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw=dict(width_ratios=[1, 1.6]))
ax = axs[0]
labs = ['抖动\n抑制', '收名额', '看门狗', '分两道', '前三项\n相加', '组合 C3\n实测', '四项\n相加', '组合 C4\n实测']
ks = ['RFD', 'S3', 'Q5', 'PICK', 'sum3', 'C3', 'sum4', 'C4']
colr = ['#9aa5b1'] * 4 + ['#edae49', '#2e86ab', '#edae49', '#2e86ab']
ax.bar(range(8), [m[k] for k in ks], color=colr)
for i, k in enumerate(ks): ax.text(i, m[k] + 0.06, f'{m[k]:+.2f}', ha='center', fontsize=9)
ax.set_xticks(range(8)); ax.set_xticklabels(labs, fontsize=9); ax.set_ylabel('17 图按实例平均（%）')
ax.set_title('单项、相加预测和组合实测（开发 17 图 × 10 局）', fontsize=11)
ax = axs[1]; x = np.arange(len(insts))
ax.bar(x - 0.2, [per[i]['sum4'] for i in insts], 0.4, color='#edae49', label='四项单独变化相加（预测）')
ax.bar(x + 0.2, [per[i]['C4'] for i in insts], 0.4, color='#2e86ab', label='四项一起开（实测）')
ax.axhline(0, color='k', lw=0.8); ax.axhline(-3, color='k', ls='--', lw=0.8); ax.text(len(insts) - 0.5, -2.7, '最差线 −3%', ha='right', fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(insts, rotation=60, fontsize=8); ax.set_ylabel('完成数变化（%）'); ax.legend(fontsize=9)
ax.set_title('每张图：同一张图上两项都起作用时（roomZ3、roomFE、roomGB）相加打折', fontsize=11)
plt.tight_layout(); plt.savefig(OUT + 'p74_result.png', dpi=150); plt.close()
