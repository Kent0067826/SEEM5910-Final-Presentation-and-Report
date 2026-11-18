# 协议第 36 轮配图：① RoCE 里 ECN/DCQCN、PFC、看门狗的分工，以及搬到机器人上；② 先量：门口拥挤度——平时过门 vs 僵局开始前；
# ③ 加条件 vs 不加条件的看门狗（同样种子，每图平均变化）。开发对比图用 harness/plot_dev.py。用法：python plot_p36.py（不加 -I）
import json
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
RD = Path(__file__).resolve().parent; FIG = RD.parents[1] / '报告源' / '图'
INK, MUTED, BLUE, ORANGE, RED, GREEN = '#222222', '#888888', '#2a6fbb', '#d9822b', '#c0392b', '#3a8f4a'

# ① 分工
fig, ax = plt.subplots(figsize=(11, 4.6)); ax.set_xlim(0, 11); ax.set_ylim(-0.45, 4.6); ax.axis('off')
ax.text(2.6, 4.3, '数据中心 RoCE 网络', ha='center', fontsize=11, weight='bold')
ax.text(8.2, 4.3, '机器人仓库（这一轮）', ha='center', fontsize=11, weight='bold')
rows = [('ECN + DCQCN', '队列变长、但一直在走（拥塞）\n→ 打标记，发送端降速', '门口排队、门一直在过车（拥塞）\n先量：僵局前门口并不挤 → 降速管不到僵局', MUTED),
        ('PFC 暂停', '下游缓冲快满 → 让上游停发\n（只在拥挤时才发）', '门口方向规则：不是你这边的回合不准进\n（轻载时也在起作用）', BLUE),
        ('PFC 看门狗', '被暂停 并且 很久一个包都没发出去\n→ 判死锁，暂时不理暂停', '站了 K 拍 并且 门 K 拍一台都没过\n→ 判僵局，这一拍不管门口规则', ORANGE)]
for k, (name, dc, rb, col) in enumerate(rows):
    y = 3.2 - 1.25 * k
    for x0, txt in ((0.2, dc), (5.8, rb)):
        ax.add_patch(FancyBboxPatch((x0, y - 0.45), 4.9, 0.95, boxstyle='round,pad=0.03', fc='white', ec=col, lw=1.4))
        ax.text(x0 + 0.15, y + 0.33, name, fontsize=9.5, color=col, weight='bold', va='center')
        ax.text(x0 + 0.15, y - 0.08, txt, fontsize=8.6, va='center', color=INK)
    ax.annotate('', xy=(5.75, y), xytext=(5.15, y), arrowprops=dict(arrowstyle='->', color=MUTED))
ax.text(5.5, -0.3, '第 35 轮的看门狗只看“站了 K 拍”；这一轮补上交换机看门狗的第二个条件：“门 K 拍一台都没过”（门还在过车 = 拥塞，不是僵局）',
        ha='center', fontsize=8.8, color=RED)
fig.tight_layout(); fig.savefig(FIG / 'p36_mechanism.png', dpi=150); plt.close(fig)

# ② 先量
d = json.load(open(RD / 'ecn_signal.json', encoding='utf8')); s1 = d['signals']['S1']
cd = dict((int(k), v) for k, v in s1['crossing_dist']); tot = sum(cd.values()); ons = s1['onset_vals']
xs = list(range(0, 11))
fig, ax = plt.subplots(figsize=(8.6, 3.8)); w = 0.4
ax.bar([x - w / 2 for x in xs], [100 * cd.get(x, 0) / tot for x in xs[:-1]] + [100 * sum(v for k, v in cd.items() if k >= 10) / tot], width=w, color=MUTED,
       label='平时：每次过门时门口有几台车（%d 次过门）' % tot)
ax.bar([x + w / 2 for x in xs], [100 * sum(1 for v in ons if v == x) / len(ons) for x in xs[:-1]] + [100 * sum(1 for v in ons if v >= 10) / len(ons)], width=w,
       color=RED, label='门口僵局开始前 10 拍，门口有几台车（%d 次僵局）' % len(ons))
ax.axvline(s1['K'] - 0.5, color=BLUE, ls='--', lw=1)
ax.text(s1['K'] - 0.4, 33, 'ECN 标记线（K=%d）：\n右边 = “挤”，占过门的 %.0f%%\n僵局只有 %d/%d 次在右边' % (s1['K'], 100 * s1['mark_frac'], sum(1 for v in ons if v >= s1['K']), len(ons)),
        fontsize=8.5, color=BLUE, va='top')
ax.set_xticks(xs); ax.set_xticklabels([str(x) for x in xs[:-1]] + ['≥10'])
ax.set_xlabel('门格 + 门口区（3 步内）里的车数'); ax.set_ylabel('占比 %'); ax.set_ylim(0, 45)
ax.set_title('僵局不是挤出来的：开始前门口一般只有 2–4 台车，和平时过门一样', fontsize=10)
ax.legend(fontsize=8.3, frameon=False, loc='upper right'); ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / 'p36_premeasure.png', dpi=150); plt.close(fig)

# ③ 加条件 vs 不加条件（同样种子）
pairs = [('dev_compare_d100.json', 'ref_compare_k100.json', 'K=100'), ('dev_compare_d300.json', 'ref_compare_k300.json', 'K=300')]
if all((RD / a).exists() and (RD / b).exists() for a, b, _ in pairs):
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharex=True, sharey=True)
    for ax, (a, b, lab) in zip(axs, pairs):
        A = {r['inst']: 100 * r['mean'] for r in json.load(open(RD / a, encoding='utf8'))['per_inst']}
        B = {r['inst']: 100 * r['mean'] for r in json.load(open(RD / b, encoding='utf8'))['per_inst']}
        ks = sorted(A); ax.scatter([B[k] for k in ks], [A[k] for k in ks], color=BLUE, s=22)
        for k in ks:
            if abs(A[k]) > 3 or abs(B[k]) > 3: ax.annotate(k, (B[k], A[k]), fontsize=7.5, xytext=(3, 3), textcoords='offset points')
        lim = [-12, 12]; ax.plot(lim, lim, color=MUTED, lw=0.8, ls=':'); ax.axhline(-3, color=RED, ls='--', lw=0.8); ax.axvline(-3, color=RED, ls='--', lw=0.8)
        ax.set_xlim(lim); ax.set_ylim(lim); ax.set_title(lab, fontsize=10)
        ax.set_xlabel('不加条件（第 35 轮做法）的变化 %'); ax.spines[['top', 'right']].set_visible(False)
    axs[0].set_ylabel('加“门还在过车就不放行”后的变化 %')
    fig.suptitle('同样 170 局：每个点是一张图。点在虚对角线上 = 加不加条件差不多', fontsize=10)
    fig.tight_layout(); fig.savefig(FIG / 'p36_gate_vs_plain.png', dpi=150); plt.close(fig)
print('saved')
