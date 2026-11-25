"""Still figures in the congestion monitor's own look (same colours, same rules as congestion_monitor.html and demo.gif),
so every congestion picture in the deck comes from our program's view, not a separate chart style.
  python3 figures/deck/demo/monitor_style.py jam      -> figures/deck/fig_jam_monitor.png   (slide "Robots jam at one narrow door")
  python3 figures/deck/demo/monitor_style.py narrow   -> figures/deck/fig_narrow_spots.png  (slide "Two safety nets")
Needs the position dumps: run_demo.py none (official map, seed 9700 / 101) and narrow_spots.py (GenH 249, seeds 11901 / 172).
Rules, as in the monitor: a robot is STUCK when it holds an order and has not changed cell for >= 12 ticks; a door is
JAMMED (glows red) when >= 8 stuck robots stand within 5 steps of it; the red floor shading is recent stuck time
(decays by 3% per tick), exactly as the monitor draws it."""
import json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_demo as bd

REPO = HERE.parents[2]
BG, FLOOR, WALL, DOOR, GOLD = bd.BG, bd.FLOOR, bd.WALL, bd.DOOR, bd.GOLD
IDLE, MOVE, STUCK = bd.IDLE, bd.MOVE, bd.STUCK
TXT, SUB = (235, 240, 245), (150, 165, 180)


def room_doors(free, step=16, max_len=3):
    """door cells of a 4x4 room map: short runs of free cells on the wall lines (every 16 cells)"""
    H, W = free.shape; doors = []
    for r in range(step, H, step):
        c = 0
        while c < W:
            if free[r, c]:
                c0 = c
                while c < W and free[r, c]: c += 1
                if c - c0 <= max_len: doors.append([[r, x] for x in range(c0, c)])
            c += 1
    for c in range(step, W, step):
        r = 0
        while r < H:
            if free[r, c]:
                r0 = r
                while r < H and free[r, c]: r += 1
                if r - r0 <= max_len: doors.append([[y, c] for y in range(r0, r)])
            r += 1
    return doors


def heat_upto(loc, st, ti, n):
    h = np.zeros(n)
    for tj in range(ti + 1):
        h *= 0.97; np.add.at(h, loc[tj][st[tj]], 0.04)
    return h


def jam_counts(free, doors, loc, st, ti):
    H, W = free.shape; out = []
    for cells in doors:
        z = set()
        for rc in cells: z |= set(bd.bfs_zone(free, tuple(rc), bd.RADIUS))
        out.append(int(sum(1 for i in np.nonzero(st[ti])[0] if int(loc[ti][i]) in z)))
    return out


def panel(img, free, doors, jam, loc, has, st, heat, ox, oy, cell, title, labels=(), circles=()):
    """one map panel, drawn like bd.draw_panel (the monitor's frame)"""
    H, W = free.shape
    d = ImageDraw.Draw(img, 'RGBA')
    d.rounded_rectangle([ox - 8, oy - 8, ox + W * cell + 8, oy + H * cell + 8], 10, fill=BG + (255,), outline=(44, 60, 76), width=2)
    for r in range(H):
        for c in range(W):
            d.rectangle([ox + c * cell, oy + r * cell, ox + c * cell + cell - 1, oy + r * cell + cell - 1], fill=(FLOOR if free[r, c] else WALL))
    hm = heat.reshape(H, W)
    for r, c in zip(*np.nonzero(hm > 0.35)):
        a = int(min(1.0, (hm[r, c] - 0.35) / 0.65) * 110 + 25)
        d.rectangle([ox + c * cell, oy + r * cell, ox + c * cell + cell - 1, oy + r * cell + cell - 1], fill=(220, 40, 30, a))
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
    for cells, n in zip(doors, jam):
        r, c = cells[0]; cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        if n >= bd.JAM_MIN:
            rad = cell * (2.2 + min(n, 30) / 6)
            g.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 40, 30, 120))
        for rr, cc in cells:
            d.rectangle([ox + cc * cell, oy + rr * cell, ox + cc * cell + cell - 1, oy + rr * cell + cell - 1],
                        fill=((255, 80, 60) if n >= bd.JAM_MIN else DOOR))
    for i in np.nonzero(st)[0]:
        r, c = divmod(int(loc[i]), W); cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        g.ellipse([cx - cell * 1.1, cy - cell * 1.1, cx + cell * 1.1, cy + cell * 1.1], fill=(255, 50, 40, 90))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(cell * 0.9)))
    d = ImageDraw.Draw(img, 'RGBA')
    for i in range(len(loc)):
        r, c = divmod(int(loc[i]), W); cx, cy = ox + c * cell + cell / 2, oy + r * cell + cell / 2
        col = STUCK if st[i] else (MOVE if has[i] else IDLE); rr = cell * (0.46 if st[i] else 0.38)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (255,))
    for (r, c, rad) in circles:                     # dashed ring around a jam
        cx, cy, R = ox + c * cell + cell / 2, oy + r * cell + cell / 2, rad * cell
        for k in range(0, 360, 16):
            d.arc([cx - R, cy - R, cx + R, cy + R], k, k + 9, fill=(235, 240, 245, 230), width=max(2, cell // 4))
    f = bd.tfont(bd.FONTB, int(cell * 2.0))
    for (r, c, text) in labels:
        d.text((ox + c * cell + cell * 1.6, oy + r * cell - cell * 0.9), text, font=f, fill=GOLD, stroke_width=max(2, cell // 2), stroke_fill=BG)
    d.text((ox, oy - cell * 4.6), title, font=bd.tfont(bd.FONTB, int(cell * 2.3)), fill=TXT)


def legend(d, x, y, size, maxw=10 ** 6):
    """the monitor's legend; wraps to a new line when it would pass maxw pixels"""
    f = bd.tfont(bd.FONT, size); x0 = x
    for kind, col, text in (('dot', STUCK, 'stuck: holds an order, not moved for 12+ ticks'), ('dot', MOVE, 'moving with an order'),
                            ('dot', IDLE, 'no order'), ('box', (255, 80, 60), 'jammed door: 8+ stuck robots within 5 steps')):
        w = d.textlength(text, font=f) + size * 1.2
        if x + w > x0 + maxw: x, y = x0, y + size * 1.7
        if kind == 'dot': d.ellipse([x, y + size * 0.2, x + size * 0.8, y + size], fill=col + (255,))
        else: d.rectangle([x, y + size * 0.15, x + size * 0.85, y + size], fill=col)
        d.text((x + size * 1.2, y), text, font=f, fill=SUB)
        x += w + size * 1.4


def jam():
    """official room map, no door control (seed 9700 / 101), tick 3000: the same run as the monitor's first panel and the demo"""
    H, W, free = bd.load_map(); rg = json.loads(bd.RG.read_text())
    t, fin, loc, has = bd.load_dump(bd.WORK / 'none' / 'pos.bin'); st = bd.stuck_mask(loc, has)
    ti = int(np.searchsorted(t, 3000))
    doors = [d['cells'] for d in rg['doors']]; ids = [d['id'] for d in rg['doors']]
    jamn = jam_counts(free, doors, loc, st, ti); i6 = ids.index(6)
    cell = 11; pw = W * cell; top, bottom, side = 70, 112, 26
    img = Image.new('RGBA', (pw + 2 * side, H * cell + top + bottom), BG + (255,))
    r6, c6 = doors[i6][0]
    panel(img, free, doors, jamn, loc[ti], has[ti], st[ti], heat_upto(loc, st, ti, H * W), side, top, cell,
          'No door control · tick 3,000 of 5,000', labels=[(r6, c6, 'door 6')])
    d = ImageDraw.Draw(img); fb = bd.tfont(bd.FONTB, 19)
    y = top + H * cell + 16
    d.text((side, y), f'orders finished {int(fin[ti])}', font=fb, fill=TXT)
    d.text((side + pw, y), f'stuck robots {int(st[ti].sum())}', font=fb, fill=STUCK, anchor='ra')
    legend(d, side, y + 36, 13, maxw=pw)
    out = REPO / 'figures/deck/fig_jam_monitor.png'; img.convert('RGB').save(out)
    res = dict(run='official room map, 250 robots, seeds 9700 / 101, no door control (champion assignment + fixed executor)',
               tick=int(t[ti]), orders_finished=int(fin[ti]), stuck_robots=int(st[ti].sum()), stuck_within_5_steps_of_door6=jamn[i6],
               jammed_doors=[ids[j] for j, n in enumerate(jamn) if n >= bd.JAM_MIN], final_orders=int(fin[-1]))
    (HERE / 'jam_monitor.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res)); print('wrote', out, img.size)


def narrow():
    """random-door map GenH, 249 robots, seeds 11901 / 172: without vs with the global cap, at the tick with the most stuck
    robots in the run without the cap (the same snapshot as narrow_spots.json)"""
    import narrow_spots as ns
    free = ns.load_map(); H, W = free.shape; doors = room_doors(free)
    snap = json.loads((HERE / 'narrow_spots.json').read_text())
    data = {}
    for k in ('noGlobal', 'FULL'):
        t, fin, loc, has = bd.load_dump(ns.WORK / k / 'pos.bin', n=ns.TEAM); data[k] = (t, fin, loc, has, bd.stuck_mask(loc, has))
    tk = int(data['noGlobal'][4].sum(1).argmax()); assert tk == snap['snapshot_tick'], (tk, snap['snapshot_tick'])
    cell = 8; pw = W * cell; gap, top, bottom = 46, 70, 96
    img = Image.new('RGBA', (2 * pw + 3 * gap, H * cell + top + bottom), BG + (255,))
    out = {}
    for j, (k, name) in enumerate((('noGlobal', 'Without the global cap'), ('FULL', 'With the global cap'))):
        t, fin, loc, has, st = data[k]; ox = gap + j * (pw + gap)
        jamn = jam_counts(free, doors, loc, st, tk)
        circles = [(r, c, 9) for r, c in snap.get('jam_centres_noGlobal', [])] if k == 'noGlobal' else []
        panel(img, free, doors, jamn, loc[tk], has[tk], st[tk], heat_upto(loc, st, tk, H * W), ox, top, cell, name, circles=circles)
        d = ImageDraw.Draw(img); fb = bd.tfont(bd.FONTB, 17)
        y = top + H * cell + 16
        d.text((ox, y), f'orders (whole run) {int(fin[-1])}', font=fb, fill=TXT)
        d.text((ox + pw, y), f'stuck now {int(st[tk].sum())}', font=fb, fill=STUCK, anchor='ra')
        out[k] = dict(orders=int(fin[-1]), stuck_now=int(st[tk].sum()), holding_orders_now=int(has[tk].sum()),
                      jammed_doors=int(sum(n >= bd.JAM_MIN for n in jamn)))
    d = ImageDraw.Draw(img)
    d.text((gap, top + H * cell + 44), f'Random-door map GenH, 249 robots, same seeds (11901 / 172), tick {tk}.   '
           'Dashed rings: the two biggest jams of the run without the cap, both at narrow doorways.', font=bd.tfont(bd.FONT, 13), fill=SUB)
    legend(d, gap, top + H * cell + 68, 12, maxw=2 * pw + gap)
    img.convert('RGB').save(REPO / 'figures/deck/fig_narrow_spots.png')
    (HERE / 'narrow_monitor.json').write_text(json.dumps(dict(tick=tk, runs=out, doors_found=len(doors)), indent=1))
    print(json.dumps(out), 'tick', tk, 'doors', len(doors), img.size)


if __name__ == '__main__':
    for a in sys.argv[1:] or ['jam', 'narrow']:
        {'jam': jam, 'narrow': narrow}[a]()
