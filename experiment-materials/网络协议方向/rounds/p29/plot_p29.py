# 协议第 29 轮（建模研究）画图。用法：python plot_p29.py 图目录
# 读本目录的 model_measure*.json、model_summary*.json、collapse.json；画 6 张：
# p29_model_map.png（真实网络和仓库地图一一对应的示意）、p29_room250.png（room250 的房间图和最忙门两侧的分区）、
# p29_distance.png（去最忙门的车每次过门在各距离带花的拍数）、p29_door_idle.png（门空着却有车要过时最近那台车在干什么）、
# p29_mouth_wait.png（门口 3 步内等待被谁挡着）、p29_stakes.png（各方向能管的损失上限）
import sys, json, collections
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']; plt.rcParams['axes.unicode_minus'] = False
HERE = Path(__file__).resolve().parent; OUT = Path(sys.argv[1])
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from model_measure import structure, nb
M1 = json.load(open(HERE / 'model_measure.json', encoding='utf8'))
M2 = json.load(open(HERE / 'model_measure2.json', encoding='utf8'))
M3 = json.load(open(HERE / 'model_measure3.json', encoding='utf8'))
M4 = json.load(open(HERE / 'model_measure4.json', encoding='utf8'))
S3 = json.load(open(HERE / 'model_summary3.json', encoding='utf8'))
COL = json.load(open(HERE / 'collapse.json', encoding='utf8'))
C = {'前进': '#4c9a5b', '转身': '#e0a030', '等': '#d9534f', '故障': '#9a9a9a'}

# ---------- 1. 对应关系示意 ----------
fig, ax = plt.subplots(figsize=(12, 5.2)); ax.set_xlim(0, 12); ax.set_ylim(0, 5.2); ax.axis('off')
net = ['主机\n（收发数据）', '局域网', '路由器端口\n（缓冲+调度+发送）', '链路', '路由器端口', '局域网', '主机']
rob = ['取货点', '房间开阔地\n离门 8 步以外', '门口区\n核心 1–3 步\n排队 4–8 步', '门格\n（墙上 1–2 格缺口）', '门口区', '房间开阔地', '送货点']
note = ['', '开销/前进 ≈ 1.1\n（基本畅通）', '开销/前进 4.2×（1–3 步）\n2.9×（4–8 步）', '1 格门同一时刻 1 台车\n最忙的 1 格门 53–68% 的\n时间空着却有车要过', '', '', '']
xs = np.linspace(0.85, 11.15, 7); cn = ['#dbe9f6', '#e8f4e4', '#fde2c8', '#f6d0d0', '#fde2c8', '#e8f4e4', '#dbe9f6']
for k, x in enumerate(xs):
    for y, txt, fs in ((4.0, net[k], 9.5), (2.2, rob[k], 9)):
        ax.add_patch(FancyBboxPatch((x - 0.72, y - 0.45), 1.44, 0.9, boxstyle='round,pad=0.03', fc=cn[k], ec='#555'))
        ax.text(x, y, txt, ha='center', va='center', fontsize=fs)
    if k < 6:
        for y in (4.0, 2.2): ax.annotate('', xy=(xs[k + 1] - 0.74, y), xytext=(x + 0.74, y), arrowprops=dict(arrowstyle='->', color='#555'))
    ax.annotate('', xy=(x, 2.68), xytext=(x, 3.53), arrowprops=dict(arrowstyle='<->', color='#999', ls='--'))
    if note[k]: ax.text(x, 1.15, note[k], ha='center', va='center', fontsize=8, color='#a33')
ax.text(0.05, 4.75, '真实网络', fontsize=11, weight='bold'); ax.text(0.05, 2.95, '仓库地图', fontsize=11, weight='bold')
ax.text(6, 0.25, '一个任务 = 一条流，由一台车“装着”走完；平均要过 3.6 扇门（最少 3.3 扇），是多跳网络。车不能丢（无损网络），总车数固定（闭环）。',
        ha='center', fontsize=9)
plt.tight_layout(); plt.savefig(OUT / 'p29_model_map.png', dpi=150); plt.close()

# ---------- 2. room250：房间图 + 最忙门两侧分区 ----------
inst = 'room250'; r1 = next(r for r in M1 if r['inst'] == inst)
h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
S, dcells, big = structure(dlab, nd, rlab)
gset = set(map(tuple, r1['door_cells']))
dist = {v: 0 for v in gset}; q = collections.deque(gset)
while q:
    v = q.popleft()
    for u in nb(v):
        if F(*u) and u not in dist: dist[u] = dist[v] + 1; q.append(u)
img = np.ones((h, w, 3))
for r in range(h):
    for c in range(w):
        if not free[r][c]: img[r, c] = (0.2, 0.2, 0.2)
        elif (r, c) in dlab: img[r, c] = (0.85, 0.1, 0.1)
        elif dist.get((r, c), 99) <= 3: img[r, c] = (0.98, 0.62, 0.3)
        elif dist.get((r, c), 99) <= 8: img[r, c] = (1.0, 0.88, 0.55)
fig, axs = plt.subplots(1, 2, figsize=(13, 6.4))
ax = axs[0]; ax.imshow(img, interpolation='nearest')
zone = [v for v, d in dist.items() if d <= 15]; r0 = max(0, min(v[0] for v in zone) - 2); r1_ = min(h - 1, max(v[0] for v in zone) + 2)
c0 = max(0, min(v[1] for v in zone) - 2); c1 = min(w - 1, max(v[1] for v in zone) + 2)
cw = r1['cellwait']; xsw, ysw, ss = [], [], []
for k, v in cw.items():
    rr, cc = map(int, k.split(',')); n = sum(x for kk, x in v.items() if kk != '没任务')
    if n > 0: ysw.append(rr); xsw.append(cc); ss.append(n)
ss = np.array(ss); ax.scatter(xsw, ysw, s=ss / ss.max() * 60, c='#7a1fa2', alpha=0.55, lw=0)
ax.set_xlim(c0 - 0.5, c1 + 0.5); ax.set_ylim(r1_ + 0.5, r0 - 0.5)
ax.set_title('room250（局部放大）：最忙的门（红格，在一座“桥”上）和它两侧的门口区\n深橙 = 核心 1–3 步，浅黄 = 排队 4–8 步，紫点 = 有任务的车在这里等的拍数', fontsize=9.5)
ax.axis('off')
ax = axs[1]; ax.imshow(np.where(np.array([[free[r][c] for c in range(w)] for r in range(h)])[..., None], 0.97, 0.3) * np.ones((h, w, 3)), interpolation='nearest')
cent = {}
for v, k in rlab.items():
    if k in big: cent.setdefault(k, []).append(v)
cent = {k: (np.mean([p[0] for p in vs]), np.mean([p[1] for p in vs])) for k, vs in cent.items()}
pbd = {int(k): n for k, n in r1['passes_by_door'].items()}; mx = max(pbd.values())
for g, (a, b) in S['door_rooms'].items():
    g = int(g); (ya, xa), (yb, xb) = cent[a], cent[b]; dc = dcells[g]; yd = np.mean([p[0] for p in dc]); xd = np.mean([p[1] for p in dc])
    br = g in S['bridges']; lw = 0.6 + 5 * pbd.get(g, 0) / mx
    ax.plot([xa, xd, xb], [ya, yd, yb], color='#d62728' if br else '#1f77b4', lw=lw, alpha=0.85, zorder=2)
for k, (y, x) in cent.items(): ax.scatter([x], [y], s=150, c='#2ca02c', ec='k', zorder=3)
ax.set_title(f'同一张图当成网络：绿点 = 房间（{S["rooms"]} 个），线 = 门（{S["doors"]} 扇，线越粗过的车越多）\n红线 = 桥（拆掉就把图分成两块），独立环 {S["cyclomatic"]} 个 → 大部分房间之间有不止一条路', fontsize=9.5)
ax.axis('off'); plt.tight_layout(); plt.savefig(OUT / 'p29_room250.png', dpi=140); plt.close()

# ---------- 3. 距离带 ----------
bands = ['远处16步以上', '中间9-15步', '近处4-8步', '门口1-3步']; lab = ['远处\n16 步以上', '中间\n9–15 步', '近处\n4–8 步', '门口\n1–3 步']
vals = {s: [np.mean([r['per_cross_band'].get(b, {}).get(s, 0) for r in M1]) for b in bands] for s in C}
fig, ax = plt.subplots(figsize=(8.5, 4.6)); left = np.zeros(4)
for s in ['前进', '转身', '等', '故障']:
    ax.barh(lab, vals[s], left=left, color=C[s], label=s); left += np.array(vals[s])
for k in range(4):
    ov = left[k] - vals['前进'][k]; ax.text(left[k] + 1, k, f'开销/前进 = {ov/vals["前进"][k]:.1f}×', va='center', fontsize=9)
ax.set_xlabel('每次过门花的拍数（去最忙门的车，同一任务内、进门前最多 150 拍；17 图平均）')
ax.set_title('离门越近，花在“不前进”上的时间越多：8 步以内是“路由器”，再往外是畅通的局域网', fontsize=10)
ax.legend(loc='lower right', fontsize=8.5); ax.set_xlim(0, max(left) * 1.35); plt.tight_layout(); plt.savefig(OUT / 'p29_distance.png', dpi=150); plt.close()

# ---------- 4. 门空着却有车要过 ----------
order = ['在路上（还没到）', '故障', '转身对准', '等：前面空着（规则或执行器扣着）', '其他（被别的车挡）']
cols = ['#8fbbd9', '#9a9a9a', '#e0a030', '#d9534f', '#c7c7c7']
kinds = ['1格·不管', '1格·管', '2格·不管']; kl = ['1 格门\n（LCAP 门规则不管）', '1 格门\n（LCAP 门规则管）', '2 格门\n（不管）']
fig, ax = plt.subplots(figsize=(9.5, 3.8)); left = np.zeros(3)
for s, c in zip(order, cols):
    v = []
    for k in kinds:
        sh = S3['idle'][k]['share']
        v.append(sum(x for kk, x in sh.items() if kk.startswith('等：被')) * 100 if s.startswith('其他') else sh.get(s, 0) * 100)
    ax.barh(kl, v, left=left, color=c, label=s)
    for j in range(3):
        if v[j] > 5: ax.text(left[j] + v[j] / 2, j, f'{v[j]:.0f}%', ha='center', va='center', fontsize=8.5)
    left += np.array(v)
for j, k in enumerate(kinds): ax.text(101, j, f'每次过门\n{S3["idle"][k]["per_cross"]:.1f} 拍', va='center', fontsize=8.5)
ax.set_xlim(0, 115); ax.set_xlabel('“门空着、离门 1–3 步却有车要过”的时间里，离门最近那台车在干什么（%，17 图合计）')
ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.45, -0.25), ncol=3); plt.tight_layout(); plt.savefig(OUT / 'p29_door_idle.png', dpi=150); plt.close()

# ---------- 5. 门口等待被谁挡 ----------
blk = collections.defaultdict(collections.Counter); npass = collections.Counter()
for r in M4:
    for k, v in r['blockers'].items(): blk[k].update(v)
    npass.update(r['npass'])
grp = [('前面空着（规则或执行器扣着）', ['前面空着（规则或执行器扣着）'], '#d9534f'),
       ('同去这扇门的车（排队）', ['同去这扇门的车（它在等）', '同去这扇门的车（它在前进）', '同去这扇门的车（它在转身）'], '#e0a030'),
       ('前车在故障', ['前车在故障'], '#9a9a9a'), ('门里的车', ['门里的车'], '#8c564b'),
       ('别的车 / 刚出门的车 / 没任务的车', ['别的车', '刚出这扇门的车', '没任务的车'], '#c7c7c7')]
fig, ax = plt.subplots(figsize=(9.5, 3.8)); left = np.zeros(3)
for name, ks, c in grp:
    v = [sum(blk[k][x] for x in ks) / max(1, sum(blk[k].values())) * 100 for k in kinds]
    ax.barh(kl, v, left=left, color=c, label=name)
    for j in range(3):
        if v[j] > 5: ax.text(left[j] + v[j] / 2, j, f'{v[j]:.0f}%', ha='center', va='center', fontsize=8.5)
    left += np.array(v)
for j, k in enumerate(kinds): ax.text(101, j, f'每次过门\n等 {sum(blk[k].values())/npass[k]:.1f} 拍', va='center', fontsize=8.5)
ax.set_xlim(0, 115); ax.set_xlabel('去这扇门的车在门口 3 步内等的时候，挡它的是什么（%，17 图合计）')
ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.45, -0.25), ncol=3); plt.tight_layout(); plt.savefig(OUT / 'p29_mouth_wait.png', dpi=150); plt.close()

# ---------- 6. 各方向能管的损失上限（占全部车·拍 %） ----------
n = len(M2); over = collections.defaultdict(float)
for r in M2:
    for k, v in r['over'].items():
        key, zone = k.split('|')
        if zone != '3步内': continue
        for s, x in v.items(): over[(key, s)] += x / r['robot_ticks'] / n
wait3 = {k: over[(k, '等')] for k in kinds}
share = lambda k, names: sum(blk[k][x] for x in names) / max(1, sum(blk[k].values()))
hold = sum(wait3[k] * share(k, ['前面空着（规则或执行器扣着）']) for k in kinds)
queue = sum(wait3[k] * share(k, ['同去这扇门的车（它在等）', '同去这扇门的车（它在前进）', '同去这扇门的车（它在转身）', '门里的车']) for k in kinds)
fwait = sum(wait3[k] * share(k, ['前车在故障']) for k in kinds)
turn3 = sum(over[(k, '转身')] for k in kinds); fault3 = sum(over[(k, '故障')] for k in kinds)
# 多过的门：每任务多过的门 × 完成数 × 每次过门门口 3 步内的时间 ÷ 总车·拍
hop = []; empty = []
for r2, r3 in zip(M2, M3):
    per = sum(sum(v.values()) for k, v in r2['over'].items() if k.endswith('3步内')) / max(1, r2['passes_all'])
    hop.append(max(0, r3['hops']['actual'] - r3['hops']['minimum']) * r2['completed'] * per / r2['robot_ticks'])
    g = r3['goodput_all']; empty.append(g.get('空车去取货', 0) * per / r2['robot_ticks'])
cross = 0.0
for r in M2:
    for k, v in r['waits'].items():
        bd, rl, bt = k.split('|')
        if bd in ('门口1-3步', '近处4-8步') and ((rl == '房间里干活的车' and bt == '去这扇门的车') or (rl == '去这扇门的车' and bt == '房间里干活的车')):
            cross += v / r['robot_ticks'] / n
opp = 0.0
for r1_, r2 in zip(M1, M2):
    m = r2['mouth_wait_state']; t = max(1, sum(m.values()))
    opp += m.get('门在放对面', 0) / (r1_['robots'] * r1_['T']) / n   # 最忙门：去这扇门的车在门口 3 步内等、门正放对面方向的车·拍
items = [('门口：前面空着却被扣着等\n（规划 / 执行器 / 门规则）', hold, '#d9534f'), ('门口：排队等前车进门', queue, '#e0a030'),
         ('门口：转身对准门', turn3, '#f0c070'), ('门口：被故障车挡', fwait, '#b0b0b0'),
         ('多过的门（比房间图最少多 8%）', float(np.mean(hop)), '#1f77b4'), ('空车过门（取货要先过门）', float(np.mean(empty)), '#6baed6'),
         ('门口附近过路车和排队车互相挡\n（802.1Qcz 拥塞隔离能管的）', cross, '#9ecae1'), ('整片堵死（死锁）', COL['lost_frac'], '#c6dbef'),
         ('最忙门：等对面方向放完', opp, '#deebf7')]
fig, ax = plt.subplots(figsize=(9.5, 5.2))
ys = np.arange(len(items))[::-1]
ax.barh(ys, [v * 100 for _, v, _ in items], color=[c for _, _, c in items])
for y, (nm, v, _) in zip(ys, items): ax.text(v * 100 + 0.03, y, f'{v*100:.2f}%', va='center', fontsize=8.5)
ax.set_yticks(ys); ax.set_yticklabels([nm for nm, _, _ in items], fontsize=8.5)
ax.set_xlabel('占全部车·拍 %（上限：假设这一类全部消除；17 图平均）'); ax.set_xlim(0, max(v for _, v, _ in items) * 100 * 1.25)
ax.set_title(f'按新模型算账：大头在每扇门的“端口”里（另有门口故障 {fault3*100:.1f}%，和在那里待多久成正比）', fontsize=10)
plt.tight_layout(); plt.savefig(OUT / 'p29_stakes.png', dpi=150); plt.close()
json.dump(dict(hold=hold, queue=queue, turn3=turn3, fwait=fwait, fault3=fault3, hop=float(np.mean(hop)), empty=float(np.mean(empty)), cross=cross,
               collapse=COL['lost_frac'], opp=opp), open(HERE / 'stakes.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('ok')
