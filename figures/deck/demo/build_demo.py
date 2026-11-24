"""Build the congestion monitor and the DoorFlow demo from the dumps written by run_demo.py (run from the repo root):
    python3 figures/deck/demo/build_demo.py
Outputs (all in figures/deck/demo/):
    congestion_monitor.html  interactive replay of three routing methods, all without door control (champion routing,
                         HN-SPF link costs, Fortz-Thorup weights); every jam turns red automatically, and a side panel
                         shows the share of the run each door is jammed -> the same doors jam whatever the routing
    monitor_stats.json   the numbers behind it
    doorflow_demo.html   interactive replay, no door control vs DoorFlow, every jam turns red automatically
    demo.gif             the same side by side, for the slide (every 25 ticks; the first frame repeats tick 3000,
                         so a still export of the slide shows the jam, then the loop plays from tick 25)
    demo_t3000.png       a still frame at tick 3000 (Word script / fallback)
    demo_stats.json      numbers shown in the demo (orders, stuck robots, door-6 crossings per 500 ticks)
Rules (same as the tick-3000 figure): a robot is STUCK when it holds an order and has not changed cell for >= 12 ticks;
a door is JAMMED when >= JAM_MIN stuck robots stand within 5 steps (walking distance) of it."""
import base64, json, os
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MAP = REPO / 'experiment-materials/网络协议方向/harness/data/pkg/maps/room/room-64-64-16.map'
RG = REPO / 'experiment-materials/archive/tools/replay_report/region_graph_room64.json'
WORK = Path(os.environ.get('DEMO_WORK', Path.home() / 'doorflow_demo' / 'runs'))   # where run_demo.py wrote the dumps
RUNS = [('none', 'No door control'), ('doorflow', 'DoorFlow')]              # the demo (GIF, still, doorflow_demo.html)
FOOT = 'Simulated with the project\'s own simulator (official room map, 250 robots, seed 9700, planner seed 101).'
VIEWS = {
    'monitor': dict(out='congestion_monitor.html', stats='monitor_stats.json',
                    title='<b>Congestion monitor</b> · where do jams happen?',
                    sub='official room map · 250 robots · same seeds · no door control · only the routing differs',
                    runs=[('none', 'Champion routing', 'guide paths priced by traffic (2024 champion)', 'champion', '#f0463c'),
                          ('hnspf', 'HN-SPF link costs', 'capped, slowly changing costs (round 53, setting A)', 'HN-SPF', '#e39b2d'),
                          ('teft', 'Fortz–Thorup weights', 'measured hot cells cost more (round 28)', 'Fortz–Thorup', '#b48cf2')]),
    'demo': dict(out='doorflow_demo.html', stats=None,
                 title='<b style="color:#e39b2d">DoorFlow</b> replay · every jam turns red automatically',
                 sub='official room map · 250 robots · same seeds for both runs',
                 runs=[('none', 'No door control', 'champion assignment + fixed executor', 'no control', '#f0463c'),
                       ('doorflow', 'DoorFlow', 'quota + door rule + fixes + safety nets', 'DoorFlow', '#40c4d6')]),
}
STUCK_TICKS, RADIUS, JAM_MIN, HTML_STEP, GIF_STEP = 12, 5, 8, 2, 25


def _font_file(bold):
    """DejaVu Sans from the system (Linux) or from matplotlib's own copy; None -> Pillow's built-in font."""
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    cands = ['/usr/share/fonts/truetype/dejavu/' + name]
    try:
        import matplotlib
        cands.append(os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf', name))
    except ImportError:
        pass
    return next((c for c in cands if os.path.exists(c)), None)


FONT, FONTB = _font_file(False), _font_file(True)


def tfont(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def load_map():
    lines = MAP.read_text().split('\n'); i = lines.index('map')
    rows = [l for l in lines[i + 1:] if l.strip()]
    H, W = len(rows), len(rows[0])
    free = np.array([[c in '.GSE' for c in r[:W]] for r in rows], dtype=bool)
    return H, W, free


def load_dump(path, n=250):
    dt = np.dtype([('t', '<i4'), ('fin', '<i4'), ('n', '<i4'), ('r', [('loc', '<i4'), ('o', 'i1'), ('h', 'i1')], (n,))])
    a = np.fromfile(path, dtype=dt)
    assert (a['n'] == n).all()
    return a['t'].copy(), a['fin'].copy(), a['r']['loc'].astype(np.int32), a['r']['h'].astype(bool)


def stuck_mask(loc, has):
    T, N = loc.shape; run = np.zeros(N, np.int32); out = np.zeros((T, N), bool)
    for t in range(T):
        if t: run = np.where(loc[t] == loc[t - 1], run + 1, 0)
        out[t] = has[t] & (run >= STUCK_TICKS)
    return out


def bfs_zone(free, start, R):
    H, W = free.shape; seen = {start: 0}; q = deque([start])
    while q:
        r, c = q.popleft()
        if seen[(r, c)] == R: continue
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and free[rr, cc] and (rr, cc) not in seen:
                seen[(rr, cc)] = seen[(r, c)] + 1; q.append((rr, cc))
    return [r * W + c for r, c in seen]


def room_labels(free, rg):
    H, W = free.shape; door_cells = {tuple(c) for d in rg['doors'] for c in d['cells']}
    lab = -np.ones(H * W, np.int32)
    for room in rg['rooms']:
        r0, c0, r1, c1 = room['bbox']
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if free[r, c] and (r, c) not in door_cells: lab[r * W + c] = room['id']
    return lab


def crossings(loc, lab, rooms_pair, ticks):
    a, b = rooms_pair; last = lab[loc[0]].copy(); cnt = np.zeros(int(ticks.max()) // 500 + 1, np.int32)
    for t in range(1, len(loc)):
        cur = lab[loc[t]]; m = cur >= 0
        hit = m & (last >= 0) & (cur != last) & (((last == a) & (cur == b)) | ((last == b) & (cur == a)))
        cnt[min(int(ticks[t]) // 500, len(cnt) - 1)] += int(hit.sum())
        last = np.where(m, cur, last)
    return cnt


def analyse(keys=None):
    H, W, free = load_map(); rg = json.loads(RG.read_text())
    zones = [bfs_zone(free, tuple(d['cells'][0]), RADIUS) for d in rg['doors']]
    lab = room_labels(free, rg); door6 = [d for d in rg['doors'] if d['id'] == 6][0]
    runs = {}
    for key in (keys or [k for k, _ in RUNS]):
        name = key
        t, fin, loc, has = load_dump(WORK / key / 'pos.bin')
        st = stuck_mask(loc, has)
        sloc = np.where(st, loc, -1)
        jam = np.zeros((len(t), len(zones)), np.int16)
        for j, z in enumerate(zones):
            zs = np.zeros(H * W + 1, bool); zs[z] = True
            jam[:, j] = zs[np.where(sloc >= 0, sloc, H * W)].sum(1)
        x6 = crossings(loc, lab, door6['rooms'], t)
        per500 = [int(fin[min(len(fin) - 1, k * 500 + 499)] - (fin[k * 500 - 1] if k else 0)) for k in range(len(fin) // 500)]
        runs[key] = dict(name=name, t=t, fin=fin, loc=loc, has=has, st=st, jam=jam, x6=x6, per500=per500)
        print(key, 'ticks', int(t[0]), '..', int(t[-1]), 'finished', int(fin[-1]), 'stuck@3000',
              int(st[np.searchsorted(t, 3000)].sum()), 'door6/500', x6.tolist())
    return H, W, free, rg, runs


def jam_share(R):
    """share of the run (ticks) each door is jammed"""
    return (R['jam'] >= JAM_MIN).mean(0)


def pack_html(H, W, free, rg, runs, view):
    data = dict(H=H, W=W, free=''.join('1' if v else '0' for v in free.ravel()), step=HTML_STEP, stuckTicks=STUCK_TICKS,
                radius=RADIUS, jamMin=JAM_MIN, doors=[dict(id=d['id'], r=d['cells'][0][0], c=d['cells'][0][1]) for d in rg['doors']],
                rooms=[dict(id=r['id'], bbox=r['bbox']) for r in rg['rooms']], runs=[],
                title=view['title'], sub=view['sub'], foot=FOOT)
    if view['stats']:   # side panel: the doors that are jammed longest in any run, with every run's share
        sh = np.array([jam_share(runs[k]) for k, *_ in view['runs']])
        top = [j for j in np.argsort(-sh.min(0)) if sh[:, j].max() >= 0.3][:6]   # jammed in every run first
        data['where'] = [dict(id=rg['doors'][j]['id'], share=[round(float(v), 3) for v in sh[:, j]]) for j in top]
    for key, name, desc, tag, color in view['runs']:
        R = runs[key]; idx = np.arange(0, len(R['t']), HTML_STEP)
        word = (R['loc'][idx] & 0x0FFF) | (R['has'][idx].astype(np.int32) << 15) | (R['st'][idx].astype(np.int32) << 14)
        data['runs'].append(dict(key=key, name=name, desc=desc, tag=tag, color=color, ticks=R['t'][idx].tolist(), fin=R['fin'][idx].tolist(),
                                 pos=base64.b64encode(word.astype('<u2').tobytes()).decode(),
                                 jam=base64.b64encode(np.minimum(R['jam'][idx], 255).astype('u1').tobytes()).decode(),
                                 per500=R['per500'], door6=R['x6'].tolist()))
    tpl = (HERE / 'viewer_template.html').read_text(encoding='utf8')
    (HERE / view['out']).write_text(tpl.replace('/*__DATA__*/null', json.dumps(data, separators=(',', ':'))), encoding='utf8')
    if view['stats']:
        ids = [d['id'] for d in rg['doors']]
        st = {k: dict(name=name, finished=int(runs[k]['fin'][-1]), stuck_at_3000=int(runs[k]['st'][int(np.searchsorted(runs[k]['t'], 3000))].sum()),
                      door6_crossings_per_500=runs[k]['x6'].tolist(),
                      jammed_share_by_door={str(i): round(float(v), 3) for i, v in zip(ids, jam_share(runs[k])) if v > 0})
              for k, name, *_ in view['runs']}
        (HERE / view['stats']).write_text(json.dumps(dict(rule=f'door jammed = at least {JAM_MIN} stuck robots within {RADIUS} steps; '
                                                           f'stuck = holds an order and has not moved for {STUCK_TICKS}+ ticks', runs=st), indent=1))


# ---------- GIF / PNG ----------
BG, FLOOR, WALL, GRID = (13, 20, 28), (24, 34, 45), (58, 74, 90), (30, 42, 55)
IDLE, MOVE, STUCK, DOOR, GOLD = (95, 110, 125), (64, 196, 214), (240, 70, 60), (120, 140, 160), (227, 155, 45)


def draw_panel(img, R, ti, ox, oy, cell, H, W, free, rg, heat, title):
    d = ImageDraw.Draw(img, 'RGBA')
    d.rounded_rectangle([ox - 8, oy - 8, ox + W * cell + 8, oy + H * cell + 8], 10, fill=BG + (255,), outline=(44, 60, 76), width=2)
    for r in range(H):
        for c in range(W):
            x, y = ox + c * cell, oy + r * cell
            d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(FLOOR if free[r, c] else WALL))
    # heat (recent stuck time)
    hm = heat.reshape(H, W)
    for r, c in zip(*np.nonzero(hm > 0.35)):
        a = int(min(1.0, (hm[r, c] - 0.35) / 0.65) * 110 + 25)
        d.rectangle([ox + c * cell, oy + r * cell, ox + c * cell + cell - 1, oy + r * cell + cell - 1], fill=(220, 40, 30, a))
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    jam = R['jam'][ti]
    for j, dd in enumerate(rg['doors']):
        r, c = dd['cells'][0]; cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        if jam[j] >= JAM_MIN:
            rad = cell * (2.2 + min(jam[j], 30) / 6)
            g.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 40, 30, 120))
        d.rectangle([ox + c * cell, oy + r * cell, ox + c * cell + cell - 1, oy + r * cell + cell - 1],
                    fill=((255, 80, 60) if jam[j] >= JAM_MIN else DOOR))
    loc, has, st = R['loc'][ti], R['has'][ti], R['st'][ti]
    for i in np.nonzero(st)[0]:
        r, c = divmod(int(loc[i]), W); cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        g.ellipse([cx - cell * 1.1, cy - cell * 1.1, cx + cell * 1.1, cy + cell * 1.1], fill=(255, 50, 40, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(cell * 0.9))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img, 'RGBA')
    for i in range(len(loc)):
        r, c = divmod(int(loc[i]), W); cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        col = STUCK if st[i] else (MOVE if has[i] else IDLE); rr = cell * (0.46 if st[i] else 0.38)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))
    # door 6 label
    r6, c6 = [dd['cells'][0] for dd in rg['doors'] if dd['id'] == 6][0]
    f = tfont(FONTB, int(cell * 2.0))
    d.text((ox + c6 * cell + cell * 1.6, oy + r6 * cell - cell * 0.9), 'door 6', font=f, fill=GOLD,
           stroke_width=max(2, cell // 2), stroke_fill=BG)
    ft = tfont(FONTB, int(cell * 2.6))
    d.text((ox, oy - cell * 5.2), title, font=ft, fill=(235, 240, 245))


def render(runs, H, W, free, rg, ticks_wanted, cell=6):
    pw = W * cell; ph = H * cell; gap = 40; top = 64; bottom = 64
    Wimg, Himg = 2 * pw + 3 * gap, ph + top + bottom
    heat = {k: np.zeros(H * W) for k, _ in RUNS}
    frames = []; idx_prev = 0
    tarr = runs['none']['t']
    for tw in ticks_wanted:
        ti = int(np.searchsorted(tarr, tw)); ti = min(ti, len(tarr) - 1)
        for k, _ in RUNS:
            R = runs[k]
            for tj in range(idx_prev, ti + 1):
                heat[k] *= 0.97
                s = R['loc'][tj][R['st'][tj]]; np.add.at(heat[k], s, 0.04)
        idx_prev = ti + 1
        img = Image.new('RGBA', (Wimg, Himg), BG + (255,))
        for j, (k, name) in enumerate(RUNS):
            ox = gap + j * (pw + gap)
            draw_panel(img, runs[k], ti, ox, top, cell, H, W, free, rg, heat[k], name)
            R = runs[k]; d = ImageDraw.Draw(img, 'RGBA'); f = tfont(FONT, 15); fb = tfont(FONTB, 15)
            ns = int(R['st'][ti].sum()); fin = int(R['fin'][ti])
            d.text((ox, top + ph + 16), f'orders finished {fin:>5}', font=fb, fill=(235, 240, 245))
            lab = 'stuck robots' if pw >= 400 else 'stuck'           # short label in the small GIF panels
            d.text((ox + pw - 4, top + ph + 16), f'{lab} {ns:>3}', font=fb, fill=(STUCK if ns >= 20 else (235, 240, 245)), anchor='ra')
        d = ImageDraw.Draw(img); fb = tfont(FONTB, 15)
        d.text((Wimg / 2, top + ph + 42), f'tick {int(tarr[ti]):>4} / 5000   ·   red = robot holding an order that has not moved for 12+ ticks; '
               'glowing door = jam', font=tfont(FONT, 13), fill=(150, 165, 180), anchor='ma')
        frames.append(img.convert('RGB'))
    return frames


def main():
    keys = []
    for v in VIEWS.values():
        keys += [k for k, *_ in v['runs'] if k not in keys]
    H, W, free, rg, runs = analyse(keys)
    for v in VIEWS.values():
        pack_html(H, W, free, rg, runs, v)
    still = render(runs, H, W, free, rg, list(range(10, 3001, 10)), cell=8)[-1]
    still.save(HERE / 'demo_t3000.png')
    frames = render(runs, H, W, free, rg, list(range(GIF_STEP, 5001, GIF_STEP)), cell=5)
    frames = [frames[3000 // GIF_STEP - 1]] + frames          # poster frame: tick 3000
    pal = [f.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    pal[0].save(HERE / 'demo.gif', save_all=True, append_images=pal[1:], duration=80, loop=0, optimize=True)
    stats = {k: dict(name=name, finished=int(runs[k]['fin'][-1]), orders_per_500=runs[k]['per500'],
                     door6_crossings_per_500=runs[k]['x6'].tolist(),
                     stuck_at_3000=int(runs[k]['st'][int(np.searchsorted(runs[k]['t'], 3000))].sum())) for k, name in RUNS}
    (HERE / 'demo_stats.json').write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
