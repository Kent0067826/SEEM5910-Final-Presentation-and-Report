# 2026-11-13：短版报告 11 张图的英文版（给做 PPT 用）。数据和原图相同，不跑模拟。
# 输出到 报告源/图/en/，文件名按演讲顺序编号。
import json, collections, statistics as st
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont
plt.rcParams['font.family'] = ['Arial']
plt.rcParams['mathtext.fontset'] = 'cm'
plt.rcParams['axes.unicode_minus'] = False

BASE = Path('C:/Users/RETN_kwang/Downloads/BaiduSyncdisk/5910 实验')
R = BASE / '网络协议方向'
G = R / '报告源/图'
OUT = G / 'en'; OUT.mkdir(exist_ok=True)
SHOT = BASE / 'outputs/talk-replay-door6/截图'
REPO = Path('C:/Users/RETN_kwang/robotnet-lab/repo')
WT = Path('C:/Users/RETN_kwang/robotnet-lab/work/talk')
INK, MUT, GRID = '#1f2d3a', '#66737f', '#e8ecef'
BLUE, RED, ORG, LAV, CAR = '#1f5fa8', '#c8452f', '#d9731a', '#e9e2f7', '#8fa3b3'
OURS, NONE = 'Our method', 'No door control'


def sty(ax):
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color('#c9d4db')
    ax.tick_params(colors=MUT, length=0, labelsize=9.5); ax.grid(axis='y', color=GRID, lw=.8); ax.set_axisbelow(True)


# ---------- replay data (room250, no-control vs ours) ----------
s = open(BASE / 'outputs/talk-replay-door6/data/cases/room250-n2f-lcap.js', encoding='utf-8').read()
D = json.loads(s[s.index('{'):s.rindex('}') + 1])
rows = D['map']['rows']; H, W = len(rows), len(rows[0])
free = np.array([[c != '@' for c in r] for r in rows])
RUN = {r['id']: {f['t']: f for f in r['frames']} for r in D['runs']}
base_img = np.where(free[..., None], np.array([1, 1, 1.]), np.array([0xc9, 0xd4, 0xdb]) / 255.)
RG = json.load(open(REPO / 'tools/replay_report/region_graph_room64.json', encoding='utf-8'))
small_rooms = set(next(p for p in RG['bridges'][0]['parts'] if len(p['rooms']) == 4)['rooms'])
box = dict(boxstyle='round,pad=.35', fc='white', ec='#c9d4db', lw=.8)


def map_axes(ax):
    ax.imshow(base_img, interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)


# ---------- 01 problem ----------
def fig01():
    info = json.load(open(WT / 'w1/task_example.json', encoding='utf-8'))
    DIRS = [(0, 1), (1, 0), (0, -1), (-1, 0)]

    def bfs(s0, so, g):
        st0 = (s0[0], s0[1], so); par = {st0: None}; q = collections.deque([st0])
        while q:
            c = q.popleft(); y, x, o = c
            if (y, x) == tuple(g):
                p = []
                while c: p.append(c); c = par[c]
                return p[::-1]
            ny, nx = y + DIRS[o][0], x + DIRS[o][1]
            nb = [(y, x, (o + 1) % 4), (y, x, (o + 3) % 4)]
            if 0 <= ny < H and 0 <= nx < W and free[ny, nx]: nb.insert(0, (ny, nx, o))
            for n in nb:
                if n not in par: par[n] = c; q.append(n)
    S, P, Q = info['start'], info['pickup'], info['delivery']
    p1 = bfs(S, 0, P); p2 = bfs(P, p1[-1][2], Q)
    fig = plt.figure(figsize=(10.4, 5.5), dpi=180)
    axs = [fig.add_axes([.005, .01, .49, .91]), fig.add_axes([.505, .01, .49, .91])]
    for ax in axs: map_axes(ax)
    ax = axs[0]; f = RUN['N2F'][0]
    ax.scatter([q[1] for q in f['positions']], [q[0] for q in f['positions']], s=7, c=CAR, zorder=2, lw=0)
    ax.plot([c[1] for c in p1], [c[0] for c in p1], color=ORG, lw=2.6, zorder=3)
    ax.plot([c[1] for c in p2], [c[0] for c in p2], color=BLUE, lw=2.6, zorder=3)
    ax.scatter([S[1]], [S[0]], s=70, c=INK, zorder=5)
    ax.scatter([P[1]], [P[0]], s=90, c=ORG, marker='s', zorder=5, edgecolors='white')
    ax.scatter([Q[1]], [Q[0]], s=170, c=BLUE, marker='*', zorder=5, edgecolors='white')
    ax.text(S[1] - 2, S[0] + .2, 'robot', fontsize=11.5, color=INK, zorder=6, bbox=box, ha='right', va='center')
    ax.text(P[1] + 2, P[0] - .2, 'pickup', fontsize=11.5, color=ORG, zorder=6, bbox=box, va='center')
    ax.text(Q[1] + 2, Q[0] + 2.2, 'delivery', fontsize=11.5, color=BLUE, zorder=6, bbox=box, va='center')
    ax.text(42, 8.2, 'Blue path: this task crosses 8 doors', fontsize=11, color=BLUE, zorder=6, bbox=box, ha='center', va='center')
    ax.set_title('The job: 250 robots (grey) keep picking up and delivering', loc='left', fontsize=11.5, color=INK, fontweight='bold')
    ax = axs[1]; f = RUN['N2F'][3000]; stl = set(f['stalled']); pos = f['positions']
    ax.scatter([q[1] for i, q in enumerate(pos) if i not in stl], [q[0] for i, q in enumerate(pos) if i not in stl], s=9, c=CAR, zorder=2, lw=0)
    ax.scatter([q[1] for i, q in enumerate(pos) if i in stl], [q[0] for i, q in enumerate(pos) if i in stl], s=11, c=RED, zorder=3, lw=0)
    ax.add_patch(Circle((1, 16), 3.2, fill=False, ec=INK, lw=1.8, zorder=5))
    ax.annotate('One-cell door: one robot at a time.\nRight now 97 robots are waiting to\ncross it into the lower-left rooms.',
                xy=(4.2, 16.4), xytext=(24, 28.5), fontsize=11, color=INK, zorder=6, bbox=box, va='center',
                arrowprops=dict(arrowstyle='-', color=INK, lw=1.1))
    ax.set_title('The difficulty: tick 3000, robots jam at a narrow door (red = stuck)', loc='left', fontsize=11.5, color=INK, fontweight='bold')
    fig.savefig(OUT / 'en_01_problem.png', facecolor='white'); plt.close(fig)


# ---------- 02 steps ----------
def fig02():
    rows_ = [('Official starter program', None), ('+ champion task assignment', 27.0), ('+ fixed executor', 63.0), ('+ our door control', 113.6)]
    fig, ax = plt.subplots(figsize=(8.0, 2.8), dpi=180)
    for i, (n, v) in enumerate(rows_):
        y = len(rows_) - 1 - i
        if v is None: ax.text(1.5, y, 'baseline', color=INK, fontsize=10.5, va='center')
        else:
            last = i == len(rows_) - 1
            ax.barh(y, v, height=.52, color=BLUE if last else '#c6d8ec', zorder=2)
            ax.text(v + 1.5, y, f'+{v:.1f}%', color=INK, fontsize=11, va='center', fontweight='bold' if last else 'normal')
    ax.set_yticks(range(len(rows_))); ax.set_yticklabels([r[0] for r in rows_][::-1], fontsize=10.5, color=INK)
    ax.set_xlim(0, 132); ax.set_xticks([]); ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
    fig.suptitle('Tasks completed vs. the official starter program (8 official instances, 20 runs each)', x=.02, ha='left', fontsize=10.5, color=MUT)
    fig.tight_layout(pad=.4, rect=(0, 0, 1, .92)); fig.savefig(OUT / 'en_02_steps.png', facecolor='white'); plt.close(fig)


# ---------- 03 map to network ----------
def fig03():
    im = Image.open(SHOT / 'fig01_map_rooms_doors.png').convert('RGB'); w, h = im.size
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(.955 * h), int(.26 * w), h], fill=(247, 249, 251))   # cover the Chinese corner label
    img = np.asarray(im)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 5.4), dpi=170, gridspec_kw=dict(width_ratios=[1, 1.02]))
    a.imshow(img); a.axis('off')
    a.set_title('Grid view: 3646 cells, 31 doors (replay screenshot)', fontsize=12.5, color=INK, pad=6)
    pos = {r['id']: (r['id'] % 4, 3 - r['id'] // 4) for r in RG['rooms']}
    pairs = collections.defaultdict(list)
    for dd in RG['doors']: pairs[tuple(sorted(dd['rooms']))].append(dd)
    for (u, v), ds in pairs.items():
        (x1, y1), (x2, y2) = pos[u], pos[v]; isdoor6 = any(dd['id'] == 6 for dd in ds); n = len(ds)
        for i, dd in enumerate(ds):
            rad = 0 if n == 1 else (0.16 if i == 0 else -0.16)
            lw = 4.2 if isdoor6 else (3.2 if dd['width'] == 2 else 1.6)
            b.add_patch(FancyArrowPatch((x1, y1), (x2, y2), connectionstyle=f'arc3,rad={rad}', arrowstyle='-', lw=lw,
                                        color=RED if isdoor6 else '#7f8c97', zorder=1, shrinkA=0, shrinkB=0))
    for i, (x, y) in pos.items():
        b.scatter([x], [y], s=620, c=LAV if i in small_rooms else '#dbe8f5', edgecolors=INK, linewidths=1.0, zorder=3)
        b.text(x, y, str(i), ha='center', va='center', fontsize=12, color=INK, zorder=4)
    b.text(-0.14, 2.5, 'Door 6', fontsize=12.5, color=RED, ha='right', va='center', fontweight='bold')
    b.text(-0.4, -0.62, 'Lavender: 4 lower-left rooms, joined to the rest only by door 6. Thick grey: the only 2-cell door.', fontsize=10, color=MUT, ha='left', va='center')
    b.set_xlim(-0.75, 3.55); b.set_ylim(-0.8, 3.5); b.set_aspect('equal'); b.axis('off')
    b.set_title('Network view: 16 nodes (rooms), 31 edges (doors)', fontsize=12.5, color=INK, pad=6)
    fig.tight_layout(); fig.savefig(OUT / 'en_03_map_to_network.png', facecolor='white'); plt.close(fig)


# ---------- 04 collapse curve ----------
def fig04():
    ROWS = REPO / 'workspace/batches/r31-test/rows.jsonl'
    Rw = [json.loads(l) for l in open(ROWS, encoding='utf-8')]
    OFF = ('room200', 'room250', 'room300')
    def prof(m):
        rs = [r for r in Rw if r['map'] in OFF and r['method'] == m]
        return [st.mean(r['prof'][k] for r in rs) for k in range(9)]
    N, Gv = prof('N2'), prof('G6'); X = list(range(500, 4501, 500))
    fig, ax = plt.subplots(figsize=(8.6, 3.5), dpi=180)
    ax.axhline(69.2, color=MUT, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.plot(X, Gv, color=BLUE, lw=2, marker='o', ms=5.5, mec='white', mew=1, zorder=3, label=OURS + ' (early version)')
    ax.plot(X, N, color=RED, lw=2, marker='o', ms=5.5, mec='white', mew=1, zorder=3, label='Champion, ' + NONE.lower())
    ax.text(4560, Gv[-1] + 7, OURS, color=INK, fontsize=10.5, va='center', fontweight='bold')
    ax.text(4560, N[-1], 'No door control', color=INK, fontsize=10.5, va='center', fontweight='bold')  # 第 66 轮：叫法统一
    ax.text(4560, 59, 'model bound 69', color=MUT, fontsize=9.5, va='center')
    ax.annotate(f'start: {N[0]:.0f}', xy=(500, N[0]), xytext=(330, 80), color=INK, fontsize=10, arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.annotate(f'late: {N[-1]:.0f}', xy=(4500, N[-1]), xytext=(3560, 14), color=INK, fontsize=10, arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.set_xlim(300, 4500); ax.set_ylim(0, 175); ax.set_xticks(X)
    ax.set_xlabel('tick', color=MUT, fontsize=10); ax.set_ylabel('tasks completed per 500 ticks', color=MUT, fontsize=10)
    sty(ax); ax.legend(loc='upper right', frameon=False, fontsize=9.5, ncol=2, labelcolor=INK)
    fig.subplots_adjust(left=.085, right=.86, top=.97, bottom=.155)
    fig.savefig(OUT / 'en_04_collapse.png', facecolor='white'); plt.close(fig)


# ---------- 05 PIBT ring vs door ----------
def fig05():
    B2, O2, GR, R2, GRN, WALL = '#2F6DB5', '#D9722B', '#8A8F98', '#C0392B', '#2E8B57', '#3C4048'
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.9), dpi=170, gridspec_kw={'width_ratios': [1, 1.5]})
    def cell(a, x, y, c='white'): a.add_patch(Rectangle((x, y), 1, 1, fc=c, ec='#B8BCC4', lw=1))
    def car(a, x, y, t, c):
        a.add_patch(Circle((x + .5, y + .5), .33, fc=c, ec='none', zorder=3)); a.text(x + .5, y + .5, t, color='white', ha='center', va='center', fontsize=11, zorder=4, fontweight='bold')
    def arr(a, p, q, c): a.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=14, color=c, lw=2, zorder=5))
    a = ax[0]; ring = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
    for x, y in ring: cell(a, x, y)
    a.add_patch(Rectangle((1, 1), 1, 1, fc=WALL, ec=WALL))
    for (x, y), n in zip(ring, '12345678'): car(a, x, y, n, O2 if n == '1' else GR)
    for i in range(8):
        x, y = ring[i]; X, Y = ring[(i + 1) % 8]
        arr(a, (x + .5 + (X - x) * .32, y + .5 + (Y - y) * .32), (X + .5 - (X - x) * .32, Y + .5 - (Y - y) * .32), GRN)
    a.set_xlim(-.2, 3.2); a.set_ylim(-.3, 3.2); a.set_aspect('equal'); a.axis('off')
    a.set_title('On a ring: full, yet everyone moves\n1 pushes 2, the push goes round to the cell 1 left', fontsize=11.5, color=GRN)
    a = ax[1]
    for x in list(range(0, 3)) + list(range(4, 7)):
        for y in range(0, 3): cell(a, x, y)
    cell(a, 3, 1, '#FFF3C4')
    for y in (0, 2): a.add_patch(Rectangle((3, y), 1, 1, fc=WALL, ec=WALL))
    for x in range(0, 3):
        for y in range(0, 3):
            if (x, y) != (2, 1): car(a, x, y, '', B2)
    for x in range(4, 7):
        for y in range(0, 3): car(a, x, y, '', GR)
    car(a, 2, 1, '1', O2); car(a, 3, 1, '2', GR)
    arr(a, (2.82, 1.5), (3.2, 1.5), O2); arr(a, (3.84, 1.5), (4.2, 1.5), R2)
    a.text(4.02, 1.86, '×', color=R2, fontsize=20, ha='center', va='center', zorder=6, fontweight='bold')
    a.text(3.5, -.28, 'door cell', ha='center', fontsize=11)
    a.set_xlim(-.2, 7.2); a.set_ylim(-.5, 3.2); a.set_aspect('equal'); a.axis('off')
    a.set_title('At a door: no ring, so priority cannot push through\n2 cannot swap with 1 and the cells behind are full', fontsize=11.5, color=R2)
    fig.tight_layout(); fig.savefig(OUT / 'en_05_pibt_ring_vs_door.png', facecolor='white'); plt.close(fig)


# ---------- 06 door rule, three steps ----------
def fig06():
    B2, O2, GREY, WALL, APR, GR = '#2f6db5', '#d9822b', '#b4bcc4', '#3b4650', '#fbeecf', '#66727d'
    Wd, Hd, DC, DR = 13, 7, 6, 3
    def panel(ax, title, blue, org, grey, arrows, note):
        ax.set_xlim(-0.3, Wd + 0.3); ax.set_ylim(-0.3, Hd + 0.3); ax.set_aspect('equal'); ax.axis('off')
        for r in range(Hd):
            for c in range(Wd):
                if c == DC and r != DR: ax.add_patch(Rectangle((c, r), 1, 1, fc=WALL, ec=WALL)); continue
                dd = abs(r - DR) + abs(c - DC)
                ax.add_patch(Rectangle((c, r), 1, 1, fc=APR if 0 < dd <= 4 else 'white', ec='#d8dde2', lw=0.6))
        ax.add_patch(Rectangle((DC, DR), 1, 1, fc='#ffffff', ec=INK, lw=1.8))
        for pts, col in ((blue, B2), (org, O2), (grey, GREY)):
            for (c, r) in pts: ax.add_patch(Circle((c + .5, r + .5), .36, fc=col, ec='none', zorder=3))
        for (p, q, col) in arrows:
            ax.add_patch(FancyArrowPatch((p[0] + .5, p[1] + .5), (q[0] + .5, q[1] + .5), arrowstyle='-|>', mutation_scale=13, lw=2, color=col, zorder=4))
        ax.set_title(title, fontsize=12.5, color=INK, pad=8, fontweight='bold')
        ax.text(Wd / 2, -0.75, note, fontsize=10, color=GR, ha='center', va='top', linespacing=1.45)
    fig, axs = plt.subplots(1, 3, figsize=(11.4, 4.1), dpi=200)
    panel(axs[0], '1. Serve the left side', [(6, 3), (5, 3), (4, 3), (3, 2)], [(12, 3), (11, 1), (12, 5)], [(8, 4), (2, 5)],
          [((6, 3), (8, 3), B2), ((11, 1), (11, 0), O2)],
          'Left-side crossers go through back to back.\nRight-side crossers must back out of the\napproach zone and yield to other robots.')
    panel(axs[1], '2. Left side drained: wind down', [(6, 3), (0, 1)], [(12, 3), (11, 1), (12, 5), (11, 5)], [(8, 4), (2, 5)],
          [((6, 3), (8, 3), B2)],
          'No left crosser within 8 cells, right side waiting.\nNo new robot may enter the left approach zone;\nwait for the door cell and zone to empty.')
    panel(axs[2], '3. Switch: serve the right side', [(0, 3), (1, 1)], [(6, 3), (7, 3), (8, 3), (9, 2)], [(10, 5), (2, 5)],
          [((6, 3), (4, 3), O2)],
          'Right crossers go through back to back,\nthe left side now waits. Switch back only when\nthe right drains, so the rule has no timer.')
    hs = [Circle((0, 0), 1, fc=B2), Circle((0, 0), 1, fc=O2), Circle((0, 0), 1, fc=GREY), Rectangle((0, 0), 1, 1, fc=APR, ec='#d8dde2')]
    fig.legend(hs, ['crossing to the right', 'crossing to the left', 'not crossing this door (unmanaged)', 'approach zone: within 4 cells of the door'],
               loc='upper center', ncol=4, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 0.995), handler_map={Circle: matplotlib.legend_handler.HandlerPatch()})
    fig.subplots_adjust(left=0.01, right=0.99, top=0.83, bottom=0.2, wspace=0.05)
    fig.savefig(OUT / 'en_06_door_rule.png', facecolor='white'); plt.close(fig)


# ---------- 07 door-6 filmstrip: relabel the existing replay strip ----------
def fig07():
    im = Image.open(G / '演讲_回放_门6连拍.png').convert('RGB'); w, h = im.size
    px = im.load(); d = ImageDraw.Draw(im)
    fb = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(.0185 * w))
    ft = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', int(.0185 * w))
    fs = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', int(.0105 * w))
    # panel titles: find the orange underline segments on one row
    y_line = next(y for y in range(0, int(.08 * h)) if sum(1 for x in range(w) if px[x, y][0] > 180 and px[x, y][1] < 140 and px[x, y][2] < 80) > w * .3)
    xs = [x for x in range(w) if px[x, y_line][0] > 180 and px[x, y_line][1] < 140 and px[x, y_line][2] < 80]
    segs = []; s0 = xs[0]; prev = xs[0]
    for x in xs[1:]:
        if x - prev > 6: segs.append((s0, prev)); s0 = x
        prev = x
    segs.append((s0, prev))
    d.rectangle([0, 0, w, y_line - 2], fill='white')
    for (x0, x1), t in zip(segs, (2963, 2972, 2981, 2990, 2999)):
        d.text((x0, y_line - 6), f'tick {t}', font=fb, fill=INK, anchor='ls')
    # left row labels
    lx = segs[0][0] - 4
    d.rectangle([0, int(.2 * h), lx, int(.4 * h)], fill='white'); d.rectangle([0, int(.6 * h), lx, int(.85 * h)], fill='white')
    d.text((int(.006 * w), int(.297 * h)), 'Our\nmethod', font=fb, fill='#222222', anchor='lm')
    d.text((int(.006 * w), int(.75 * h)), 'No door\ncontrol', font=fb, fill='#222222', anchor='lm')
    # "门 6" labels: orange text just right of the door box, inside the grey band
    isor = lambda x, y: px[x, y][0] > 180 and px[x, y][1] < 140 and px[x, y][2] < 80
    for (x0, x1) in segs:
        for (ya, yb) in ((int(.2 * h), int(.4 * h)), (int(.66 * h), int(.86 * h))):
            # the door box is the only orange thing with a long vertical run: find its right edge and its rows
            runs = {}
            for x in range(x0, x1):
                best = cur = 0; y_start = None; by = None
                for y in range(ya, yb):
                    if isor(x, y):
                        if cur == 0: y_start = y
                        cur += 1
                        if cur > best: best = cur; by = (y_start, y)
                    else: cur = 0
                if best >= 25: runs[x] = by
            bxr = max(runs); r0, r1 = runs[bxr]
            # the label sits in the grey band just right of the box; repaint that stretch of band and write the English label
            bg = px[bxr + 60, (r0 + r1) // 2]
            d.rectangle([bxr + 4, r0 + 2, bxr + 74, r1 - 2], fill=bg)
            d.text((bxr + 9, (r0 + r1) // 2), 'door 6', font=fs, fill=(217, 115, 26), anchor='lm')
    im.save(OUT / 'en_07_door6_filmstrip.png')
    print('filmstrip', w, h, y_line, segs)


# ---------- 08 four numbers ----------
def fig08():
    # 2026-11-13 第 66 轮（Y-2）：听众看不懂字母，每行加“where”一行解释符号，并把代入的数写出来。
    fig = plt.figure(figsize=(9.6, 6.2), dpi=170); ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    rows_ = [
        ('Bound', 'max-flow / min-cut',
         r'$X^{*}=\dfrac{C}{f}=\dfrac{26}{0.376}\approx 69$', 'tasks per 500 ticks;\nrerouting cannot raise it',
         'C = effective door bandwidth, 26 robots per 500 ticks (measured);\nf = share of tasks that must cross door 6, 0.376 (from the map)'),
        ('Quota', "Little's law + bandwidth-delay product",
         r'$K=\left\lceil\, \alpha\, T\, \dfrac{C}{2}\,\right\rceil=\left\lceil 2.23\times\dfrac{247}{500}\times 13\right\rceil=15$', 'door 6: 15 inbound,\n10 outbound (T = 158)',
         'T = travel time to the door without congestion, 247 ticks inbound / 158 outbound;  C/2 = two directions share one door;\nα = 2.23 = slowdown from breakdowns (measured)'),
        ('Door rule', 'polling system',
         r'$U(n)=\dfrac{nh}{(n-1)h+s}=\dfrac{9n}{9(n-1)+21}$', 'door utilisation:\nbatch of 1: 43%\nbatch of 10: 88%',
         'n = robots let through per batch;  h = 9 ticks between two robots in the same direction;\ns = 21 ticks to switch direction (h and s measured)'),
        ('Admission', "Little's law + max concurrent flow",
         r'$A=\left\lfloor\, \beta\, X^{*}\alpha\,(T_1+T_2)\,\right\rfloor=\left\lfloor 1.76\times\dfrac{69.2}{500}\times 2.23\times 255\right\rfloor=138$', 'official room maps:\n138 robots is enough',
         r'$T_1+T_2$ = 255 ticks = one task from pickup to delivery without congestion;  β = 1.76 = measured safety margin;' + '\n' + r'$X^*$ and α as above'),
    ]
    for y, (name, law, f, res, where) in zip([.875, .625, .375, .125], rows_):
        ax.text(.02, y + .07, name, fontsize=14.5, color=INK, fontweight='bold', va='center')
        ax.text(.02, y - .005, law, fontsize=9, color=MUT, va='center')
        ax.text(.225, y + .04, f, fontsize=13.5, color=INK, va='center')
        ax.text(.775, y + .04, res, fontsize=9.5, color=INK, va='center')
        ax.text(.225, y - .055, 'where  ' + where, fontsize=8.6, color=MUT, va='top', linespacing=1.45)
    for y in (.75, .5, .25): ax.plot([.02, .98], [y, y], color='#dfe5ea', lw=1)
    fig.savefig(OUT / 'en_08_four_numbers.png', facecolor='white'); plt.close(fig)


# ---------- 09 knee ----------
def fig09():
    d = json.load(open(WT / 'mfd/mfd.json', encoding='utf-8'))
    B2, R2 = '#2a6fdb', '#c8452f'
    fig, ax = plt.subplots(figsize=(8.4, 4.4), dpi=170)
    ax.axhline(26, color=MUT, lw=1, ls=(0, (4, 3)), zorder=1)
    # 2026-11-13 第 66 轮（Y-2）：横轴写清“在途”是什么，标出拐点，说明 26 是怎么来的。
    ax.text(216, 26.7, 'effective door bandwidth C = 26 (mean of our method after the first 500 ticks)', ha='right', va='bottom', color=MUT, fontsize=9.5)
    ax.axvline(25, color=B2, lw=1, ls=(0, (2, 3)), zorder=1, alpha=.7)
    ax.text(27, 1.2, 'knee: about 25 in flight = quota 15 + 10', color=B2, fontsize=9.5, va='bottom', ha='left')
    n, l = d['N2F'], d['LCAP']
    ax.plot([w['L'] for w in n], [w['X'] for w in n], '-o', color=R2, lw=2, ms=7, mec='white', mew=1.2, label=NONE, zorder=3)
    ax.plot([w['L'] for w in l], [w['X'] for w in l], 'o', color=B2, ms=8, mec='white', mew=1.2, label=OURS, zorder=3)
    ax.annotate('Our method: the quota holds in-flight at about 25,\nso the door runs full (21 to 30 per 500 ticks)', (25.5, 30), xytext=(50, 31.5), color=INK, fontsize=10, va='center', arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.annotate('first 500 ticks', (10.8, 15), xytext=(18, 12.3), color=MUT, fontsize=9.5, va='center', arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.annotate('No door control: 59 in flight at the start,\nthen more and more in flight, fewer and fewer cross', (95.2, 8), xytext=(105, 16), color=INK, fontsize=10, va='center', arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.annotate('end: 211 in flight,\n3 cross per 500 ticks', (210.9, 3), xytext=(178, 9.5), color=MUT, fontsize=9.5, va='center', ha='left', arrowprops=dict(arrowstyle='-', color=MUT, lw=.8))
    ax.set_xlim(0, 220); ax.set_ylim(0, 36)
    ax.set_xlabel('robots in flight: current task still has to cross door 6 (average per 500 ticks)', color=INK); ax.set_ylabel('robots crossing door 6 per 500 ticks', color=INK)
    sty(ax); ax.legend(loc='upper right', frameon=False, bbox_to_anchor=(1, 1.02), ncol=2)
    fig.tight_layout(); fig.savefig(OUT / 'en_09_knee.png', facecolor='white'); plt.close(fig)


# ---------- 10 tick 3000, side by side ----------
def fig10():
    fig = plt.figure(figsize=(10.4, 5.9), dpi=180)
    axs = [fig.add_axes([.005, .035, .49, .83]), fig.add_axes([.505, .035, .49, .83])]
    for ax, run, title, sub, col in ((axs[0], 'N2F', NONE, 'champion assignment + fixed executor', RED), (axs[1], 'LCAP', OURS, 'quota + door rule + admission', BLUE)):
        map_axes(ax); f = RUN[run][3000]; pos = f['positions']; sm = set(f['small']); bg = set(f['big'])
        for r in RG['rooms']:
            if r['id'] in small_rooms:
                a, b, c, d2 = r['bbox']; ax.add_patch(Rectangle((b - .5, a - .5), d2 - b + 1, c - a + 1, fc=LAV, ec='none', zorder=1, alpha=.9))
        ax.scatter([q[1] for i, q in enumerate(pos) if i not in sm and i not in bg], [q[0] for i, q in enumerate(pos) if i not in sm and i not in bg], s=9, c=CAR, zorder=2, lw=0)
        ax.scatter([q[1] for i, q in enumerate(pos) if i in bg], [q[0] for i, q in enumerate(pos) if i in bg], s=12, c=BLUE, zorder=3, lw=0)
        ax.scatter([q[1] for i, q in enumerate(pos) if i in sm], [q[0] for i, q in enumerate(pos) if i in sm], s=12, c=ORG, zorder=4, lw=0)
        ax.add_patch(Circle((1, 16), 3.0, fill=False, ec=INK, lw=1.6, zorder=5))
        ax.text(6.0, 11.2, 'door 6', fontsize=10.5, color=INK, zorder=6, bbox=box, va='center')
        ax.text(0.0, 1.055, title, transform=ax.transAxes, fontsize=12.5, color=col, fontweight='bold', va='bottom', ha='left')
        ax.text(0.0, 1.01, sub, transform=ax.transAxes, fontsize=9.5, color=MUT, va='bottom', ha='left')
        ax.text(1.0, 1.01, f"{f['completed']} tasks done", transform=ax.transAxes, fontsize=13, color=INK, fontweight='bold', va='bottom', ha='right')
        ax.text(0.5, -0.03, f"tick 3000 · via door 6: {len(sm)} inbound, {len(bg)} outbound · {len(f['stalled'])} holding a task but stuck",
                transform=ax.transAxes, fontsize=8.8, color=MUT, va='top', ha='center')
    hs = [plt.Line2D([], [], marker='o', ls='', color=ORG, ms=6), plt.Line2D([], [], marker='o', ls='', color=BLUE, ms=6), plt.Line2D([], [], marker='o', ls='', color=CAR, ms=6)]
    fig.legend(hs, ['task crosses door 6 into the lower-left rooms', 'task crosses door 6 outward', 'other robots'], loc='upper center', ncol=3, frameon=False, fontsize=10, bbox_to_anchor=(.5, .995))
    fig.savefig(OUT / 'en_10_tick3000.png', facecolor='white'); plt.close(fig)


# ---------- 11 roadmap ----------
def fig11():
    PANEL = '#f4f3ef'
    fig, ax = plt.subplots(figsize=(11.5, 3.5), dpi=170); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    S = [('1. Find the root cause', 'one-cell doors cause\ncongestion collapse', 'quota + door rule\n+53.8% vs champion'),
         ('2. Dig to the bottom', 'door stuck at 22 per\n500 ticks: the executor', '3 lines changed\nchampion itself +16.7%'),
         ('3. Explain the numbers', 'hand-tuned parameters\nreplaced by three laws', 'no worse than tuning\nexhaustive service +1.1%'),
         ('4. Port protocols', '75 network mechanisms,\nmeasure before building', '1 confirmed\nwatchdog +1.73%'),
         ('5. Combine and verify', 'four mechanisms\nswitched on together', 'dev +3.15%\nnew maps +0.05%')]
    for i, (a, b, c) in enumerate(S):
        X = .008 + i * .1985; w = .178
        ax.add_patch(FancyBboxPatch((X, .05), w, .9, boxstyle='round,pad=0,rounding_size=0.012', fc=PANEL, ec='none'))
        ax.text(X + w / 2, .84, a, ha='center', va='center', fontsize=11, fontweight='bold', color=INK)
        ax.text(X + w / 2, .57, b, ha='center', va='center', fontsize=10, color=MUT, linespacing=1.4)
        ax.text(X + w / 2, .24, c, ha='center', va='center', fontsize=10.5, color=INK, fontweight='bold', linespacing=1.4)
        if i < 4: ax.annotate('', (X + w + .0195, .5), (X + w + .002, .5), arrowprops=dict(arrowstyle='->', color=MUT, lw=1.4))
    plt.savefig(OUT / 'en_11_roadmap.png', dpi=170, bbox_inches='tight', facecolor='white'); plt.close()


if __name__ == '__main__':
    import sys
    which = sys.argv[1:] or ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
    for k in which:
        globals()['fig' + k](); print('ok', k)
