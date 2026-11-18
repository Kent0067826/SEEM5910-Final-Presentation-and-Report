# 第 78 轮机制图：左 = 门口区示意（过门车单调走，横穿/探进又退出的加代价）；右 = 选中门上的队首阻塞（基线 vs p=2，同一局完整轨迹）
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw=dict(width_ratios=[1, 1.1]))
for r in range(7):
    for c in range(7):
        wall = c == 3 and r != 3
        d = abs(r - 3) + abs(c - 3)
        col = '#555' if wall else ('#f2c14e' if d == 0 else ('#f7e1a1' if d <= 2 else '#ffffff'))
        a.add_patch(Rectangle((c, 6 - r), 1, 1, fc=col, ec='#bbb'))
a.annotate('', xy=(6.5, 3.5), xytext=(0.5, 3.5), arrowprops=dict(arrowstyle='->', lw=2.5, color='#2a6fbb'))
a.text(0.0, -1.3, '过门车：离门 3→2→1→0→1→2→3\n一路单调，不加代价', color='#2a6fbb', fontsize=10)
a.annotate('', xy=(2.5, 1.5), xytext=(2.5, 5.5), arrowprops=dict(arrowstyle='->', lw=2.5, color='#c0392b', connectionstyle='arc3,rad=-0.5'))
a.text(0.0, 7.25, '不过门的车贴着门口横穿 / 探进又退出：加代价 p\n→ 改走门口区外面，不在过门车的路上停', color='#c0392b', fontsize=10)
a.text(3.2, 4.05, '门', fontsize=11)
a.set_xlim(-0.2, 7.2); a.set_ylim(-1.5, 8.4); a.set_aspect('equal'); a.axis('off')
a.set_title('机制：等待格和通行格分开（黄 = 门口区 2 步）', fontsize=12)
doors = ['roomFE 门14', 'roomGB 门0', 'roomZ3 门8', 'roomZ3 门14']
base = [1567, 2245, 3728, 2116]; new = [2141, 2026, 2962, 1596]
x = range(len(doors)); w = 0.38
b.bar([i - w/2 for i in x], [v/1000 for v in base], w, label='基线 LCAPWD', color='#999')
b.bar([i + w/2 for i in x], [v/1000 for v in new], w, label='VOQ p=2', color='#d9822b')
for i in x: b.text(i + w/2, new[i]/1000 + 0.05, f'{100*(new[i]-base[i])/base[i]:+.0f}%', ha='center', fontsize=10)
b.set_xticks(list(x)); b.set_xticklabels(doors); b.set_ylabel('门口队首阻塞（千 车·拍，一局）')
b.set_title('选中门上的队首阻塞（种子 9700 × 规划 103 同一局）', fontsize=12); b.legend()
fig.tight_layout(); import sys; fig.savefig(sys.argv[1] if len(sys.argv) > 1 else '报告源/图/p78_mech.png', dpi=130)
