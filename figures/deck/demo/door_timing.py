"""Measure how long door 6 takes per robot, from simulation runs (slides on the door rule).

Runs the formal DoorFlow settings (harness/lcap_env17_wd.json, room250) for planner seed 101 and task seeds 9700-9704,
5,000 ticks each, with the position dump of the demo build (ROBOT_DUMP_POS; see run_demo.py for how that simulator is built).
From every robot's cell at every tick it finds each crossing of door 6 (a robot leaves one of the two rooms that door 6 joins
and next appears in the other one; the crossing time is the tick it enters the other room), and measures:
  same-direction gap  = time between two crossings in the same direction, one right after the other
  switch gap          = time between the last crossing in one direction and the first crossing in the other direction
  move time           = ticks between two consecutive cell changes of the same robot (the fastest one is a plain move)
Writes figures/deck/demo/door_timing.json and figures/deck/fig_door_timing.png.
Usage (repo root):  DEMO_SIM=<simulator> DEMO_WORK=<work dir> python3 figures/deck/demo/door_timing.py
Runs that already have a dump in <work dir>/timing/<seed>/ are not run again."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_demo as bd   # map, room labels and dump reader of the demo

REPO = Path(__file__).resolve().parents[3]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('DEMO_SIM', str(Path.home() / 'doorflow_demo' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('DEMO_WORK', Path.home() / 'doorflow_demo' / 'runs')) / 'timing'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
MAP, PSEED, TICKS, SEEDS = 'room250', 101, 5000, [9700, 9701, 9702, 9703, 9704]


def run(seed):
    d = WORK / str(seed); d.mkdir(parents=True, exist_ok=True)
    if (d / 'pos.bin').exists() and (d / 'out.json').exists():
        return json.loads((d / 'out.json').read_text())['numTaskFinished']
    f = H / 'data' / CFG[MAP]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[MAP]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[MAP]['env'])
    env['ROBOT_PLANNER_SEED'] = str(PSEED); env['ROBOT_DUMP_POS'] = str(d / 'pos.bin')
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', str(TICKS), '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    if p.returncode != 0: sys.exit(f'seed {seed}: simulator stopped with code {p.returncode}\n' + p.stderr[-1500:])
    return json.loads((d / 'out.json').read_text())['numTaskFinished']


def events(loc, lab, a, b):
    """(tick, direction) of every crossing between rooms a and b; direction 0 = a -> b, 1 = b -> a."""
    last = lab[loc[0]].copy(); out = []
    for t in range(1, len(loc)):
        cur = lab[loc[t]]; m = cur >= 0
        for r in np.nonzero(m & (last >= 0) & (cur != last))[0]:
            if (last[r], cur[r]) == (a, b): out.append((t, 0))
            elif (last[r], cur[r]) == (b, a): out.append((t, 1))
        last = np.where(m, cur, last)
    return out


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex: done = dict(zip(SEEDS, ex.map(run, SEEDS)))
    Hh, Ww, free = bd.load_map(); rg = json.loads(bd.RG.read_text())
    lab = bd.room_labels(free, rg); door6 = [d for d in rg['doors'] if d['id'] == 6][0]; a, b = door6['rooms']
    same, switch, moves, n_cross = [], [], [], 0
    for s in SEEDS:
        t, fin, loc, has = bd.load_dump(WORK / str(s) / 'pos.bin')
        ev = events(loc, lab, a, b); n_cross += len(ev)
        for (t0, d0), (t1, d1) in zip(ev, ev[1:]):
            (same if d0 == d1 else switch).append(t1 - t0)
        ch = loc[1:] != loc[:-1]                                  # a robot changed cell between tick t and t+1
        for r in range(loc.shape[1]):
            ts = np.nonzero(ch[:, r])[0]
            moves += np.diff(ts).tolist()
    same, switch, moves = np.array(same), np.array(switch), np.array(moves)
    vals, cnt = np.unique(moves, return_counts=True)
    res = dict(runs=[dict(seed=s, planner_seed=PSEED, map=MAP, ticks=TICKS, orders=done[s]) for s in SEEDS],
               door6_crossings=int(n_cross),
               same_direction_gap=dict(n=int(len(same)), median=float(np.median(same)), min=int(same.min()),
                                       p25=float(np.percentile(same, 25)), p75=float(np.percentile(same, 75))),
               switch_gap=dict(n=int(len(switch)), median=float(np.median(switch)), min=int(switch.min()),
                               p25=float(np.percentile(switch, 25)), p75=float(np.percentile(switch, 75))),
               robots_per_turn=round(n_cross / (len(switch) + len(SEEDS)), 1),
               move_time=dict(fastest=int(moves.min()), most_common=int(vals[cnt.argmax()]),
                              share_most_common=round(float(cnt.max() / cnt.sum()), 3)))
    (Path(__file__).resolve().parent / 'door_timing.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    plot(same, switch, res)


def plot(same, switch, res):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    INK, TEAL, ORG, GREY = '#1B2631', '#0F6E7E', '#E39B2D', '#5D6D7E'
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.9), dpi=220)
    for ax, data, key, col, title in ((axs[0], same, 'same_direction_gap', TEAL, 'Next robot, same direction'),
                                       (axs[1], switch, 'switch_gap', ORG, 'First robot after the door switches')):
        r = res[key]; top = int(np.percentile(data, 95)) + 3
        ax.hist(np.clip(data, 0, top), bins=np.arange(0, top + 2) - 0.5, color=col, alpha=0.85)
        ax.axvline(r['median'], color=INK, lw=1.6, ls='--')
        ax.text(r['median'] + 0.6, ax.get_ylim()[1] * 0.92, f"median {r['median']:g} ticks", color=INK, fontsize=10, fontweight='bold', va='top')
        ax.set_title(f"{title}\n({r['n']} gaps)", fontsize=11.5, color=INK, loc='left')
        if key == 'same_direction_gap':
            ax.annotate('6 or 9 ticks = 2 or 3 moves\n(3 ticks per move): robots\nfollowing back to back', xy=(9, ax.get_ylim()[1] * 0.55),
                        xytext=(17, ax.get_ylim()[1] * 0.55), fontsize=9, color=TEAL, va='center',
                        arrowprops=dict(arrowstyle='-|>', color=TEAL, lw=1.0))
        else:
            ax.text(41, ax.get_ylim()[1] * 0.62, 'the door and the 4-cell\nbuffer must empty first', fontsize=9, color=ORG, va='center')
        ax.set_xlabel('ticks between two crossings of door 6', fontsize=9.5, color=GREY)
        ax.spines[['top', 'right']].set_visible(False); ax.tick_params(labelsize=8.5)
    axs[0].set_ylabel('count', fontsize=9.5, color=GREY)
    n = len(res['runs'])
    fig.suptitle(f"Measured in {n} simulation runs: official room map, 250 robots, DoorFlow,\n5,000 ticks each, "
                 f"{res['door6_crossings']:,} crossings of door 6", fontsize=11, color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.01, f"A move takes {res['move_time']['most_common']} ticks ({res['move_time']['share_most_common']:.0%} of all moves; "
             "agentCounter = 3).\nGaps above the 95th percentile are drawn in the last bar.",
             fontsize=8.6, color=GREY, style='italic')
    fig.tight_layout(rect=(0, 0.08, 1, 0.88))
    fig.savefig(REPO / 'figures/deck/fig_door_timing.png', facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    t0 = time.time(); main(); print('seconds', round(time.time() - t0, 1))
