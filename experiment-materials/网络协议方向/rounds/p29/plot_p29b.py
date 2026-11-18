# 协议第 29 轮补充画图：路由器该划多大、门簇、推荐的“门簇路由器”模型。用法：python plot_p29b.py 图目录
import sys, json, collections
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
import numpy as np
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
HERE = Path(__file__).resolve().parent; OUT = Path(sys.argv[1])
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from model_measure import structure
from model_measure2 import bfs
M6 = json.load(open(HERE / 'model_measure6.json', encoding='utf8')); M1 = {r['inst']: r for r in json.load(open(HERE / 'model_measure.json', encoding='utf8'))}

# ---------- 1. 逐步密度 ----------
D = 13; n = len(M6)
area = [sum(r['area'][str(k)] / sum(r['area'].values()) for r in M6) / n for k in range(D)]
wd = [sum(r['wait'][str(k)] / max(1, r['area'][str(k)]) / r['T'] for r in M6) / n * 1000 for k in range(D)]
td = [sum(r['turn'][str(k)] / max(1, r['area'][str(k)]) / r['T'] for r in M6) / n * 1000 for k in range(D)]
fig, ax = plt.subplots(figsize=(9.5, 4.4)); x = np.arange(D)
ax.axvspan(-0.5, 2.5, color='#fde2c8', zorder=0); ax.axvspan(2.5, 6.5, color='#fff3d6', zorder=0)
ax.bar(x - 0.2, wd, 0.4, color='#d9534f', label='等（每格每千拍）'); ax.bar(x + 0.2, td, 0.4, color='#e0a030', label='转身（每格每千拍）')
for k in range(D): ax.text(k, max(wd[k], td[k]) + 0.8, f'{area[k]*100:.0f}%', ha='center', fontsize=7.5, color='#555')
ax.set_xticks(x); ax.set_xticklabels([str(k) for k in range(D - 1)] + [f'{D-1}+'])
ax.set_xlabel('离最近的门格几步（0 = 门格本身；柱上的小字 = 这一圈占全部空地的比例）')
ax.text(1, 37, '路由器核心\n门格 + 两侧 2 步', ha='center', fontsize=9); ax.text(4.5, 37, '排队、接近', ha='center', fontsize=9)
ax.text(9.5, 37, '路段（线）：基本畅通', ha='center', fontsize=9)
ax.set_ylim(0, 42); ax.legend(loc='center right', fontsize=8.5)
ax.set_title('等待和转身都挤在门格和两侧两三步内，往外迅速变稀（17 图、全部有任务的车平均）', fontsize=10)
plt.tight_layout(); plt.savefig(OUT / 'p29b_density.png', dpi=150); plt.close()

# ---------- 2. room250 的门簇 ----------
inst = 'room250'; h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
S, dcells, big = structure(dlab, nd, rlab); doors = [int(g) for g in S['door_rooms']]
near = collections.defaultdict(set)
for g in doors:
    for v, d in bfs(F, list(dcells[g]), limit=6).items():
        if v in dlab and dlab[v] != g and dlab[v] in doors: near[g].add(dlab[v])
lab = {}; k = 0
for g in doors:
    if g in lab: continue
    st = [g]; lab[g] = k
    while st:
        xx = st.pop()
        for y in near[xx]:
            if y not in lab: lab[y] = k; st.append(y)
    k += 1
size = collections.Counter(lab.values())
img = np.ones((h, w, 3))
for r in range(h):
    for c in range(w):
        if not free[r][c]: img[r, c] = (0.25, 0.25, 0.25)
fig, ax = plt.subplots(figsize=(7.2, 7.2)); ax.imshow(img, interpolation='nearest')
pbd = {int(a): b for a, b in M1[inst]['passes_by_door'].items()}; mx = max(pbd.values())
pal = [c for i, c in enumerate(plt.get_cmap('tab10').colors) if i != 7]; cmap = lambda i: pal[i % len(pal)]; ci = {}   # 去掉灰色，免得和单独的门混
for g in doors:
    cs = dcells[g]; yy = np.mean([p[0] for p in cs]); xx = np.mean([p[1] for p in cs])
    multi = size[lab[g]] > 1
    if multi and lab[g] not in ci: ci[lab[g]] = cmap(len(ci))
    col = ci[lab[g]] if multi else '#999999'
    ax.scatter([xx], [yy], s=30 + 220 * pbd.get(g, 0) / mx, c=[col], ec='k', lw=0.6, zorder=3)
for cl, col in ci.items():
    pts = [p for g in doors if lab[g] == cl for p in dcells[g]]
    cy = np.mean([p[0] for p in pts]); cx = np.mean([p[1] for p in pts]); rad = max(4, max(abs(p[0] - cy) + abs(p[1] - cx) for p in pts) + 3)
    ax.add_patch(Circle((cx, cy), rad, fill=False, ec=col, lw=2, ls='--'))
ax.set_title('room250：彩色虚线圈 = 挨在一起（6 步内）的门簇，灰点 = 单独的门\n点越大过的车越多。17 张图平均 55% 的过门发生在门簇上', fontsize=9.5)
ax.axis('off'); plt.tight_layout(); plt.savefig(OUT / 'p29b_clusters.png', dpi=140); plt.close()

# ---------- 3. 推荐的模型 ----------
fig, ax = plt.subplots(figsize=(12, 4.6)); ax.set_xlim(0, 12); ax.set_ylim(0, 4.6); ax.axis('off')
net = ['主机', '线', '路由器\n（多口交换机）', '线', '路由器', '线', '主机']
rob = ['取货点', '房间里门到门\n的路段', '门簇：一扇门或挨在一起\n的几扇门 + 两侧 2–3 步', '路段', '门簇', '路段', '送货点']
note = ['', '基本畅通\n（每格等待 ≈ 2）', '等待最密（每格 ≈ 30）\n装下 46% 的等待、占 19% 空地\n55% 的过门在多门簇上', '', '', '', '']
xs = np.linspace(0.85, 11.15, 7); cn = ['#dbe9f6', '#e8f4e4', '#fde2c8', '#e8f4e4', '#fde2c8', '#e8f4e4', '#dbe9f6']
for kk, xx in enumerate(xs):
    for y, txt in ((3.6, net[kk]), (1.9, rob[kk])):
        ax.add_patch(FancyBboxPatch((xx - 0.74, y - 0.5), 1.48, 1.0, boxstyle='round,pad=0.03', fc=cn[kk], ec='#555'))
        ax.text(xx, y, txt, ha='center', va='center', fontsize=8.6)
    if kk < 6:
        for y in (3.6, 1.9): ax.annotate('', xy=(xs[kk + 1] - 0.76, y), xytext=(xx + 0.76, y), arrowprops=dict(arrowstyle='->', color='#555'))
    ax.annotate('', xy=(xx, 2.42), xytext=(xx, 3.08), arrowprops=dict(arrowstyle='<->', color='#999', ls='--'))
    if note[kk]: ax.text(xx, 0.65, note[kk], ha='center', va='center', fontsize=8, color='#a33')
ax.text(0.05, 4.3, '真实网络', fontsize=11, weight='bold'); ax.text(0.05, 2.62, '仓库地图', fontsize=11, weight='bold')
plt.tight_layout(); plt.savefig(OUT / 'p29b_model_map.png', dpi=150); plt.close()
print('ok')
