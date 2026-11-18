# 第 77 轮两张图：p77_mech.png（转身按离门几步分档，基线 vs k=2，4 张图同一局）；p77_result.png（第一段筛选每实例变化）
import json, collections, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Microsoft YaHei'; plt.rcParams['axes.unicode_minus'] = False
D = json.load(open('rounds/p77/diag.json', encoding='utf8'))
lab = ['门格里', '门前 1 步', '2 步', '3 步', '4 步以外']
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
for j, (tag, name, c) in enumerate((('base', '基线', '#9E9E9E'), ('k2', '门前 2 步内拐弯加价（k=2）', '#4C78A8'))):
    s = [sum(D[m][tag]['turns_by_dist'][str(b)] for m in D) / 1000 for b in range(5)]
    ax[0].bar([b + (j - .5) * .38 for b in range(5)], s, .38, label=name, color=c)
ax[0].set_xticks(range(5)); ax[0].set_xticklabels(lab); ax[0].set_ylabel('转身占的车·拍（千），4 张图同一局合计')
ax[0].set_title('转身发生在哪：门口那一格没少，门前 2–3 步反而多了'); ax[0].legend(fontsize=9)
ms = sorted(D); x = range(len(ms))
ax[1].bar([i - .2 for i in x], [D[m]['base']['share']['转身'] for m in ms], .4, color='#9E9E9E', label='基线')
ax[1].bar([i + .2 for i in x], [D[m]['k2']['share']['转身'] for m in ms], .4, color='#4C78A8', label='k=2')
for i, m in enumerate(ms):
    ch = 100 * (D[m]['k2']['completed'] / D[m]['base']['completed'] - 1)
    ax[1].text(i, max(D[m]['base']['share']['转身'], D[m]['k2']['share']['转身']) + .3, f'完成 {ch:+.1f}%', ha='center', fontsize=9)
ax[1].set_xticks(list(x)); ax[1].set_xticklabels(ms, fontsize=9); ax[1].set_ylabel('转身占全部车·拍（%）'); ax[1].set_ylim(0, 16)
ax[1].set_title('全图转身份额（同一局）'); ax[1].legend(fontsize=9, loc='upper left')
fig.tight_layout(); fig.savefig('报告源/图/p77_mech.png', dpi=130)

B = {(d['map'], d['seed'], d['pseed']): d['completed'] for d in map(json.loads, open('rounds/baseline_v2_LCAPWD/dev_p103_104.jsonl', encoding='utf8'))}
res = {}
for k in (2, 3):
    per = collections.defaultdict(lambda: [0, 0])
    for d in map(json.loads, open(f'rounds/p77/dev1_k{k}.jsonl', encoding='utf8')):
        key = (d['map'], d['seed'], d['pseed']); per[d['map']][0] += B[key]; per[d['map']][1] += d['completed']
    res[k] = {m: 100 * (n / b - 1) for m, (b, n) in per.items()}
insts = sorted(res[2]); fig, ax = plt.subplots(figsize=(8.5, 7.6))
for g, (k, c) in enumerate(((2, '#4C78A8'), (3, '#F58518'))):
    mean = sum(res[k].values()) / len(insts)
    ax.barh([i + (g - .5) * .4 for i in range(len(insts))], [res[k][m] for m in insts], .38, color=c,
            label=f'k={k}（按实例平均 {mean:+.2f}%，最差 {min(res[k].values()):+.2f}%）')
ax.axvline(0, color='k', lw=.8); ax.axvline(-3, color='r', lw=.8, ls='--')
ax.set_yticks(range(len(insts))); ax.set_yticklabels(insts); ax.invert_yaxis()
ax.set_xlabel('完成数相对 LCAPWD 的变化（%），种子 9700 × 规划 103、104；红虚线 = 单实例 −3% 判据线')
ax.set_title('第一段筛选：两个取值的平均都低于 −1%，没有进第二段'); ax.legend(fontsize=9, loc='lower left')
fig.tight_layout(); fig.savefig('报告源/图/p77_result.png', dpi=130)
json.dump(res, open('rounds/p77/stage1_per_inst.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
