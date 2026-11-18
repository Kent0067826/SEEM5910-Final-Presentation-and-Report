# 第 68 轮机制图：自动带宽式调割名额（示意）+ 两种采样口径在 3 张图上每 600 拍窗口的最高比例（诊断实测）
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={'width_ratios': [1.5, 1]})
# 左：示意
f = [0.02, 0.07, 0.08, 0.03, 0.01, 0.06, 0.02, 0.00]
K = [0]; 
for x in f:
    k = K[-1]
    if x > 0.05 and k < 2: k += 1
    elif x <= 0.025 and k > 0: k -= 1
    K.append(k)
xs = range(1, len(f) + 1)
a.bar(xs, [100 * x for x in f], color='#d9822b', alpha=0.8, label='这一窗口里“门空着且有车被名额挡着”的比例')
a.axhline(5, color='r', ls='--', lw=1); a.text(0.55, 5.3, '上调线 5%', color='r', fontsize=9)
a.axhline(2.5, color='gray', ls=':', lw=1); a.text(0.55, 2.8, '回调线 2.5%', color='gray', fontsize=9)
a.set_xlabel('窗口（每个 600 拍 = 200 步）'); a.set_ylabel('比例（%）'); a.set_ylim(0, 11)
a2 = a.twinx(); a2.step([0.5 + i for i in range(len(K))], K, where='post', color='#2a6fbb', lw=2, label='名额加成（0 = 原值，最多 +2）')
a2.set_ylim(-0.2, 3.2); a2.set_yticks([0, 1, 2]); a2.set_ylabel('名额加成（台）')
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels(); a.legend(h1 + h2, l1 + l2, loc='upper right', fontsize=8)
a.set_title('机制示意：按窗口实测，高就加一台，低就退一台')
# 右：诊断（9700 × 规划 103，每 600 拍窗口里最高的一个方向）
maps = ['room250', 'roomFF', 'room200']; orig = [0.3, 1.7, 0.7]; new = [5.0, 7.5, 2.5]
import numpy as np; y = np.arange(len(maps))
b.barh(y - 0.2, orig, height=0.4, color='#999999', label='原口径：这一拍刚被拒、门正为这方向服务')
b.barh(y + 0.2, new, height=0.4, color='#d9822b', label='补充口径（同第 67 轮）：被挡着没放行、门两侧都空')
b.axvline(5, color='r', ls='--', lw=1); b.set_yticks(y); b.set_yticklabels(maps); b.invert_yaxis()
b.set_xlabel('一局里窗口比例的最高值（%）'); b.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.5, -0.17)); b.set_xlim(0, 10)
b.set_title('原口径几乎碰不到 5% 线')
fig.tight_layout(); fig.savefig('报告源/图/p68_mech.png', dpi=150); print('ok')
