# 第75轮机制图：6 张新留出地图 + 按第 34 轮规则挑出的分道门（红），以及每个确认实例挑中几扇门
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np, os, json
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
HERE = os.path.dirname(os.path.abspath(__file__)); H = os.path.join(HERE, '..', '..'); D = os.path.join(H, 'harness', 'data', 'maps_p75')
P = os.path.expanduser('~/robotnet-lab/work/p75/pick')
inst = json.load(open(os.path.join(D, 'instances.json'))); pk = json.load(open(os.path.join(HERE, 'pick_doors_p75.json'), encoding='utf8'))['maps']
fig = plt.figure(figsize=(12, 7.6)); gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 1.25])
for j, name in enumerate(['roomNA', 'roomNB', 'roomNC', 'roomND', 'roomNE', 'roomNF']):
    ax = fig.add_subplot(gs[j // 3, j % 3])
    L = open(os.path.join(D, name + '.map')).read().split('\n'); i = L.index('map')
    G = np.array([[0.0 if c == '.' else 1.0 for c in r] for r in L[i + 1:] if r])
    k = [x for x in inst[name][1]][0]; f = os.path.join(P, k + '.txt')
    img = np.stack([1 - G] * 3, -1)
    if os.path.exists(f):
        for ln in open(f):
            r, c = map(int, ln.split()); img[r, c] = [0.85, 0.1, 0.1]
    ax.imshow(img, interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([])
    n = list(inst[name][1].values()); ax.set_title('%s（%d/%d 台）分道门 %d 扇' % (name, n[0], n[1], len(pk[k]['picked'])), fontsize=9.5)
ax = fig.add_subplot(gs[:, 3])
names = ['room200', 'room250', 'room300'] + sorted(pk); cnt = []
for k in names:
    if k in pk: cnt.append(len(pk[k]['picked']))
    else: cnt.append(sum(1 for _ in open(os.path.join(P, k + '.txt'))) // 2)
col = ['#d9822b' if k.startswith(('maze', 'random')) else '#2a6fbb' for k in names]
ax.barh(range(len(names)), cnt, color=col); ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8.5); ax.invert_yaxis()
for y, v in enumerate(cnt): ax.text(v + 0.3, y, str(v), va='center', fontsize=8)
ax.set_xlabel('挑中要分道的门（扇）'); ax.set_title('同一条挑门规则在 20 个确认实例上\n橙 = 迷宫 / 随机图（窄通道也算门）', fontsize=10)
fig.suptitle('第 75 轮确认：新画的 6 张地图（黑 = 墙，红 = 按第 34 轮规则挑中、要分两道的 2 格门）', fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(H, '报告源', '图', 'p75_mech.png'), dpi=110); print('ok')
