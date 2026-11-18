# 第69轮机制图：新生成的 6 张留出地图（确认用，开发和以前确认都没用过）
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np, os, json
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'); D = os.path.join(H, 'harness', 'data', 'maps_p69')
inst = json.load(open(os.path.join(D, 'instances.json')))
fig, axs = plt.subplots(2, 3, figsize=(10, 7.8))
for ax, name in zip(axs.flat, ['roomMA', 'roomMB', 'roomMC', 'roomMD', 'roomME', 'roomMF']):
    L = open(os.path.join(D, name + '.map')).read().split('\n'); i = L.index('map')
    G = np.array([[0 if c == '.' else 1 for c in r] for r in L[i + 1:] if r])
    ax.imshow(G, cmap='Greys', interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([])
    n = list(inst[name][1].values()); ax.set_title('%s：空格 %d，车 %d / %d 台' % (name, inst[name][0], n[0], n[1]), fontsize=10)
fig.suptitle('第 69 轮确认用的 6 张新地图（黑 = 墙，白 = 可走；每张图有一扇 2 格宽的“桥门”）', fontsize=12)
fig.tight_layout(h_pad=2.5); fig.savefig(os.path.join(H, '报告源', '图', 'p69_maps.png'), dpi=110)
