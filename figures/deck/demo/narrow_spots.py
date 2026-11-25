"""Where do robots jam without the global cap? (slide on the two safety nets)

Reruns one pair from the random-door test (figures/part3/rerun/general.py): map roomGenH, 249 robots, task seed 11901,
planner seed 172 -- archived result FULL 1277 orders, noGlobal 818 (general_gen4x4.jsonl). Same settings as general.py:
the full method with the global cap computed by the program from the map (ROBOT_ADMIT_AUTO=1); "noGlobal" drops the cap.
Uses the demo build with the position dump (see run_demo.py). Counts, for every cell, how many robot-ticks robots spent
there stuck (holding an order, not moved for 12+ ticks), and draws the map for both runs at the tick where the run
without the cap has the most stuck robots.
Writes figures/deck/demo/narrow_spots.json and figures/deck/fig_narrow_spots.png.
Usage (repo root):  DEMO_SIM=<simulator> DEMO_WORK=<work dir> python3 figures/deck/demo/narrow_spots.py"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_demo as bd

REPO = Path(__file__).resolve().parents[3]
H = REPO / 'experiment-materials/网络协议方向/harness'
GEN = REPO / 'figures/part3/rerun/maps_gen4x4'
PROG = os.environ.get('DEMO_SIM', str(Path.home() / 'doorflow_demo' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('DEMO_WORK', Path.home() / 'doorflow_demo' / 'runs')) / 'narrow'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
INST, TEAM, SEED, PSEED, TICKS = 'roomGenH_249', 249, 11901, 172, 5000
ARCHIVED = {'FULL': 1277, 'noGlobal': 818}
BASE = dict(CFG['room250']['env']); BASE.pop('ROBOT_ACTIVE_CAP'); BASE['ROBOT_ADMIT_AUTO'] = '1'
VARIANTS = {'FULL': {}, 'noGlobal': {'ROBOT_ADMIT_AUTO': None, 'ROBOT_ACTIVE_CAP': None}}


def run(name):
    d = WORK / name; d.mkdir(parents=True, exist_ok=True)
    f = GEN / f'{INST}.json'; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = SEED; tpl['teamSize'] = TEAM
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(BASE)
    for k, v in VARIANTS[name].items():
        if v is None: env.pop(k, None)
        else: env[k] = v
    env['ROBOT_PLANNER_SEED'] = str(PSEED); env['ROBOT_DUMP_POS'] = str(d / 'pos.bin')
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', str(TICKS), '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    if p.returncode != 0: sys.exit(f'{name}: simulator stopped with code {p.returncode}\n' + p.stderr[-1500:])
    return json.loads((d / 'out.json').read_text())['numTaskFinished']


def load_map():
    lines = (GEN / 'roomGenH.map').read_text().split('\n'); i = lines.index('map')
    rows = [l for l in lines[i + 1:] if l.strip()]
    return np.array([[c in '.GSE' for c in r[:64]] for r in rows], dtype=bool)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    orders = {k: run(k) for k in VARIANTS}
    free = load_map(); Hh, Ww = free.shape
    res = dict(instance=INST, seed=SEED, planner_seed=PSEED, ticks=TICKS, orders=orders, archived=ARCHIVED, runs={})
    data = {}
    for k in VARIANTS:
        t, fin, loc, has = bd.load_dump(WORK / k / 'pos.bin', n=TEAM)
        st = bd.stuck_mask(loc, has)
        heat = np.bincount(loc[st], minlength=Hh * Ww).reshape(Hh, Ww)
        holding = has.sum(1)
        data[k] = dict(loc=loc, st=st, heat=heat, fin=fin)
        res['runs'][k] = dict(orders=int(fin[-1]), stuck_robot_ticks=int(st.sum()), max_stuck=int(st.sum(1).max()),
                              mean_holding_orders=round(float(holding.mean()), 1), max_holding_orders=int(holding.max()))
    tbad = int(data['noGlobal']['st'].sum(1).argmax())
    res['snapshot_tick'] = tbad
    hot = np.argwhere(data['noGlobal']['heat'] >= np.percentile(data['noGlobal']['heat'][free], 99.5))
    res['hot_cells_noGlobal'] = hot.tolist()[:40]
    plot(free, data, res, tbad)
    (Path(__file__).resolve().parent / 'narrow_spots.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'hot_cells_noGlobal'}, indent=1))


def plot(free, data, res, tk):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    INK, RED, BLUE, GREY = '#1B2631', '#C0392B', '#2a78d6', '#5D6D7E'
    fig, axs = plt.subplots(1, 2, figsize=(10.2, 5.4), dpi=200)
    for ax, k, title in ((axs[0], 'noGlobal', 'Without the global cap'), (axs[1], 'FULL', 'With the global cap')):
        d = data[k]; Hh, Ww = free.shape
        ax.imshow(np.where(free, 1.0, 0.0), cmap='Greys_r', vmin=-0.25, vmax=1.15, interpolation='nearest')
        hm = np.ma.masked_where(d['heat'] == 0, d['heat'])
        ax.imshow(hm, cmap='Reds', alpha=0.55, interpolation='nearest', vmin=0, vmax=np.percentile(data['noGlobal']['heat'][data['noGlobal']['heat'] > 0], 98))
        loc = d['loc'][tk]; st = d['st'][tk]
        r, c = np.divmod(loc, Ww)
        ax.scatter(c[~st], r[~st], s=5, color=BLUE, lw=0)
        ax.scatter(c[st], r[st], s=9, color=RED, lw=0)
        ax.set_title(f"{title}: {res['runs'][k]['orders']} orders\n{int(st.sum())} robots stuck at tick {tk}", fontsize=11, color=INK)
        if k == 'noGlobal':
            from matplotlib.patches import Circle
            hm2 = d['heat'].astype(float).copy()
            for j in range(2):                       # the two biggest jams: peak, then blank 12 cells around it
                r0, c0 = np.unravel_index(hm2.argmax(), hm2.shape)
                ax.add_patch(Circle((c0, r0), 9, fill=False, ec=INK, lw=1.8, ls='--'))
                hm2[max(0, r0 - 12):r0 + 13, max(0, c0 - 12):c0 + 13] = 0
                res.setdefault('jam_centres_noGlobal', []).append([int(r0), int(c0)])
            ax.text(0.98, 0.02, 'dashed circles: the two biggest jams,\nat narrow doorways', transform=ax.transAxes, ha='right', va='bottom',
                    fontsize=8.5, color=INK, bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#d5dde2', lw=0.8))
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"Random-door map GenH, 249 robots, same seeds ({SEED} / {PSEED}): where robots get stuck", fontsize=11.5, color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.015, "Red shading = robot-ticks spent stuck in each cell over the whole run (holding an order, not moved for 12+ ticks). "
             "Dots = robots at the snapshot tick (red = stuck).", fontsize=8, color=GREY, style='italic')
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(REPO / 'figures/deck/fig_narrow_spots.png', facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    main()
