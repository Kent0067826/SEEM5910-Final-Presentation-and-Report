# 第 76 轮机制图：左，各类图上门两侧房间多大；右，老规则 / 新规则在 20 个确认实例上各挑几扇门。
import json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Microsoft YaHei'
P = json.load(open('rounds/p76/pick_doors_p76_confirm.json', encoding='utf8'))['maps']
order = ['room200', 'room250', 'room300', 'maze40', 'maze60', 'random200', 'random300', 'warehouse100'] + sorted(k for k in P if k.startswith('roomP'))
old = {'room200': 1, 'room250': 1, 'room300': 1}; new = dict(old)
mins = {'房间图': [], '迷宫': [], '随机图': []}
for k in order:
    if k in P:
        old[k] = sum(x['picked34'] for x in P[k]['doors']); new[k] = sum(x['picked'] for x in P[k]['doors'])
        for x in P[k]['doors']:
            if x['picked34'] and x['side_rooms']:
                g = '迷宫' if k.startswith('maze') else '随机图' if k.startswith('random') else '房间图'
                mins[g].append(min(x['side_rooms']))
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw=dict(width_ratios=[1, 2.2]))
cols = {'房间图': '#4C78A8', '迷宫': '#E45756', '随机图': '#F58518'}
for i, (g, v) in enumerate(mins.items()):
    ax[0].scatter([i] * len(v), v, s=30, alpha=.6, color=cols[g])
ax[0].axhline(25, ls='--', color='k'); ax[0].text(2.45, 27, '门槛 25 格', ha='right', fontsize=9)
ax[0].set_yscale('log'); ax[0].set_xticks(range(3)); ax[0].set_xticklabels(list(mins)); ax[0].set_xlim(-.5, 2.5)
ax[0].set_ylabel('被老规则挑中的门：两侧较小那个房间（格，对数）'); ax[0].set_title('“门”两侧是不是真房间')
x = range(len(order)); ax[1].bar([i - .2 for i in x], [old.get(k, 0) for k in order], .4, label='老规则（第 34 轮）', color='#BBBBBB')
ax[1].bar([i + .2 for i in x], [new.get(k, 0) for k in order], .4, label='新规则（加“两侧都是 ≥25 格的房间”）', color='#4C78A8')
ax[1].set_xticks(list(x)); ax[1].set_xticklabels(order, rotation=60, ha='right', fontsize=8); ax[1].set_ylabel('分道的门（扇）')
ax[1].set_title('20 个确认实例上各挑中几扇门'); ax[1].legend(fontsize=9)
fig.tight_layout(); fig.savefig('报告源/图/p76_mech.png', dpi=130); print(old, new)
