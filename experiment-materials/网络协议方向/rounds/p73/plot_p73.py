# 第 73 轮机制图：左，看门狗 2685 次放行里真 / 假（按是否在门口附近）；右，三项先量和各自跳过线
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
H = Path(__file__).resolve().parent
b = json.loads((H / 'q2b_measure.json').read_text(encoding='utf8'))['total']
q2 = json.loads((H / 'q2_measure.json').read_text(encoding='utf8'))['mean_17']['restuck_share']
q4 = json.loads((H / 'q4e_measure.json').read_text(encoding='utf8'))['mean_17']['else_nofault']
fig, (a, c) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'width_ratios': [1.4, 1]})
lab = ['假放行\n（站着时多半没任务，\n刚领到任务）', '真放行\n（站满 300 拍\n一直有任务）']
far = [b['fake'] - b['fake_near'], b['real'] - b['real_near']]; near = [b['fake_near'], b['real_near']]
a.bar(lab, far, color='#b0bec5', label='离门较远（门口规则管不到）')
a.bar(lab, near, bottom=far, color='#c62828', label='在门格或门口区（规则起作用）')
for i in range(2): a.text(i, far[i] + near[i] + 30, f'{far[i]+near[i]} 次（门口附近 {near[i]}）', ha='center', fontsize=10)
a.set_ylabel('次数（17 图 × 1 局）'); a.set_title('看门狗放行 2685 次：97% 是假的'); a.legend(fontsize=9); a.set_ylim(0, 3000)
names = ['Q-2 放开后\n又卡住', 'Q-4 门外长时间\n站着（改正后）']; vals = [100 * q2, 100 * q4]; lines = [0.5, 2.0]
c.bar(names, vals, color=['#1565c0', '#1565c0'], width=0.5)
for i, (v, l) in enumerate(zip(vals, lines)):
    c.plot([i - 0.3, i + 0.3], [l, l], 'k--'); c.text(i, l + 0.06, f'跳过线 {l}%', ha='center', fontsize=9)
    c.text(i, v + 0.06, f'{v:.2f}%', ha='center', fontsize=10, color='#1565c0')
c.set_ylim(0, 2.6); c.set_ylabel('占全部车·拍 %'); c.set_title('两项先量：都不到线')
fig.tight_layout(); fig.savefig(H.parents[1] / '报告源' / '图' / 'p73_mech.png', dpi=150)
