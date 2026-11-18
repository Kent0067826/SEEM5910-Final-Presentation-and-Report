# 画开发对比图：每个实例的变化（%）和 95% 区间，可放几组。用法：python plot_dev.py 输出.png 标题 对比1.json:名字1 [对比2.json:名字2 ...]
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
out, title, groups = sys.argv[1], sys.argv[2], [a.rsplit(':', 1) for a in sys.argv[3:]]
data = [(json.load(open(p, encoding='utf-8')), n) for p, n in groups]
insts = [r['inst'] for r in data[0][0]['per_inst']]
fig, ax = plt.subplots(figsize=(8, 0.42 * len(insts) + 1.6))
colors = ['#2a6fbb', '#d9822b', '#6a9f3a']; h = 0.8 / len(data)
for g, (d, name) in enumerate(data):
    rows = {r['inst']: r for r in d['per_inst']}
    ys = [i + (g - (len(data) - 1) / 2) * h for i in range(len(insts))]
    m = [100 * rows[k]['mean'] for k in insts]
    err = [[100 * (rows[k]['mean'] - rows[k]['lo']) for k in insts], [100 * (rows[k]['hi'] - rows[k]['mean']) for k in insts]]
    ax.barh(ys, m, height=h * 0.9, color=colors[g % 3], xerr=err, error_kw={'lw': 0.8, 'alpha': 0.6},
            label='%s（按实例平均 %+.2f%%，最差 %+.2f%%）' % (name, 100 * d['mean'], 100 * d['worst']))
ax.axvline(0, color='k', lw=0.8); ax.axvline(-3, color='r', lw=0.8, ls='--')
ax.set_yticks(range(len(insts))); ax.set_yticklabels(insts); ax.invert_yaxis()
ax.set_xlabel('完成数相对 LCAP 的变化（%），横线是 95% 区间；红虚线 = −3% 判据线'); ax.set_title(title)
ax.legend(loc='lower right', fontsize=8); fig.tight_layout(); fig.savefig(out, dpi=150)
print('saved', out)
