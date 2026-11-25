"""Why a fixed window computed from averages, not one adjusted live? Reruns three "live" ideas from the experiment log
(report, table of stage-1 attempts that were not kept) on top of today's DoorFlow, on the official room map:

  DF     DoorFlow as submitted: door 6's window fixed from the formula (15 in / 10 out), robots on the way counted every round
  JAM    round-34 idea, "limit only after a jam is seen": the window of a door applies only while the congestion monitor's rule
         sees a jam there (>= 8 stuck robots within 5 steps; a robot is stuck when it holds an order and has not moved for
         12+ ticks), and is released when the jam clears (<= 2 stuck)
  LATCH  same, but once switched on the window stays on for the rest of the run
  AIMD   round-38 idea, "adjust the window by the measured delay": start from the formula values; every 250 ticks measure the
         delay at the door (robot-ticks within 3 cells per crossing); above 250 ticks halve the window (not below 8), otherwise
         add 2 where the window refused an order (not above 48) -- the rule of ROBOT_CUT2_AIMD, applied to door 6
  PHYS   round-42 idea, "use the door's physical capacity": the formula with 49 robots per 500 ticks (the most a one-cell door
         can pass when it switches direction) instead of the measured 26, i.e. windows 27 / 18 instead of 15 / 10

JAM, LATCH and AIMD need the small planner patch figures/deck/demo/live_window.patch (switched off unless ROBOT_LIVE_MODE is
set); PHYS only sets ROBOT_NET_C1. Everything else is the formal DoorFlow setting (harness/lcap_env17_wd.json).
Runs: room200 / room250 / room300, task seeds 11700-11709 x planner seeds 145, 146 (the 60 seed pairs of the formal evaluation,
round 52b), 5,000 ticks. Every variant is compared with DF on the same seed pair.
Build: copy experiment-materials/网络协议方向/src/dev_src_p78 to a folder outside the repo, apply demo_dump.patch (see
run_demo.py) and   patch -p0 < figures/deck/demo/live_window.patch   in that folder, then build with build_unix.sh.
Usage (repo root):  LIVE_SIM=<simulator> LIVE_WORK=<work dir> python3 figures/deck/demo/live_control.py
Writes figures/deck/demo/live_control.json (+ live_control_rows.jsonl) and figures/deck/fig_live_control.png."""
import json, os, random, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('LIVE_SIM', str(Path.home() / 'doorflow_live' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('LIVE_WORK', Path.home() / 'doorflow_live' / 'runs'))
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
MAPS = ['room200', 'room250', 'room300']
PAIRS = [(s, p) for s in range(11700, 11710) for p in (145, 146)]
VARIANTS = {'DF': {}, 'JAM': {'ROBOT_LIVE_MODE': '1'}, 'LATCH': {'ROBOT_LIVE_MODE': '1', 'ROBOT_LIVE_LATCH': '1'},
            'AIMD': {'ROBOT_LIVE_MODE': '2'}, 'PHYS': {'ROBOT_NET_C1': '0.098'}}
R52B = REPO / 'experiment-materials/archive/workspace/batches/r52b-baseline/rows.jsonl'
TRACE_RE = re.compile(r'\[live\] t=(\d+) mode=\d on=(\d) stuck=(\d+) \| side0 L=(-?\d+) K=(-?\d+) \| side1 L=(-?\d+) K=(-?\d+)')


def run(job):
    mp, var, seed, pseed = job
    d = WORK / mp / var / f'{seed}_{pseed}'; d.mkdir(parents=True, exist_ok=True)
    if (d / 'row.json').exists(): return json.loads((d / 'row.json').read_text())
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[mp]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(VARIANTS[var])
    env['ROBOT_PLANNER_SEED'] = str(pseed); env['ROBOT_LIVE_TRACE'] = '1'
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time()
    p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    if p.returncode != 0: sys.exit(f'{job}: simulator stopped with code {p.returncode}\n' + p.stderr[-1500:])
    out = json.loads((d / 'out.json').read_text())
    tr = [list(map(int, m.groups())) for m in TRACE_RE.finditer(p.stderr)]   # t, on, stuck, L0, K0, L1, K1 (side1 = into the lower-left)
    row = dict(map=mp, variant=var, seed=seed, pseed=pseed, completed=out['numTaskFinished'], sec=round(time.time() - t0, 1),
               errors=len(out.get('errors', [])), trace=tr)
    (d / 'row.json').write_text(json.dumps(row)); (d / 'out.json').unlink()
    return row


def boot(r, n=4000, seed=1):
    rnd = random.Random(seed); m = sorted(np.mean([rnd.choice(r) for _ in r]) for _ in range(n))
    return m[int(.025 * n)], m[int(.975 * n)]


def main():
    jobs = [(mp, v, s, p) for v in VARIANTS for mp in MAPS for s, p in PAIRS]
    with ThreadPoolExecutor(int(os.environ.get('LIVE_WORKERS', '4'))) as ex: rows = list(ex.map(run, jobs))
    with open(HERE / 'live_control_rows.jsonl', 'w') as fh:
        for r in rows: fh.write(json.dumps({k: v for k, v in r.items() if k != 'trace'}) + '\n')
    got = {(r['map'], r['variant'], r['seed'], r['pseed']): r for r in rows}
    arch = {(r['map'], r['seed'], r['pseed']): r['completed'] for r in map(json.loads, open(R52B)) if r['method'] == 'LCAP'}
    df_vs_arch = {mp: [round(float(np.mean([got[(mp, 'DF', s, p)]['completed'] for s, p in PAIRS])), 1),
                       round(float(np.mean([arch[(mp, s, p)] for s, p in PAIRS])), 1)] for mp in MAPS}
    res = dict(runs=len(rows), errors=sum(r['errors'] for r in rows),
               df_mean_vs_formal_evaluation=df_vs_arch,   # [this rerun (final program), round 52b (round-51 program)], same seeds
               seeds='task 11700-11709 x planner 145, 146; room200/250/300', variants={})
    for v in VARIANTS:
        rat = [got[(mp, v, s, p)]['completed'] / got[(mp, 'DF', s, p)]['completed'] - 1 for mp in MAPS for s, p in PAIRS]
        lo, hi = boot(rat)
        tr = [np.array(got[(mp, v, s, p)]['trace']) for mp in MAPS for s, p in PAIRS]
        onway = [float(np.mean(t[:, 3] + t[:, 5])) for t in tr if len(t)]
        peak = [int(np.max(t[:, 3] + t[:, 5])) for t in tr if len(t)]
        res['variants'][v] = dict(
            mean_orders={mp: round(float(np.mean([got[(mp, v, s, p)]['completed'] for s, p in PAIRS])), 1) for mp in MAPS},
            change_vs_DF_pct=round(100 * float(np.mean(rat)), 2), ci95_pct=[round(100 * lo, 2), round(100 * hi, 2)],
            per_size_pct={mp: round(100 * float(np.mean([got[(mp, v, s, p)]['completed'] / got[(mp, 'DF', s, p)]['completed'] - 1
                                                         for s, p in PAIRS])), 2) for mp in MAPS},
            worse_runs=sum(x < 0 for x in rat), better_runs=sum(x > 0 for x in rat), worst_pct=round(100 * min(rat), 1),
            robots_on_the_way_door6_mean=round(float(np.mean(onway)), 1), robots_on_the_way_door6_peak_median=int(np.median(peak)))
        if v in ('JAM', 'LATCH'):
            res['variants'][v]['share_of_time_window_on'] = round(float(np.mean([t[:, 1].mean() for t in tr if len(t)])), 3)
            res['variants'][v]['first_switch_on_tick_median'] = int(np.median([t[np.argmax(t[:, 1] > 0), 0] if t[:, 1].any() else 5000 for t in tr if len(t)]))
        res['variants'][v]['window_in'] = int(np.median([np.median(t[:, 6]) for t in tr if len(t)]))
        if v == 'AIMD':
            k = [t[:, 6] for t in tr if len(t)]
            res['variants'][v]['window_in_range'] = [int(min(x.min() for x in k)), int(max(x.max() for x in k))]
    (HERE / 'live_control.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    plot(got, res)


def plot(got, res):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    INK, GREY, TEAL, ORG, RED, BLUE, PUR = '#1B2631', '#5D6D7E', '#0F6E7E', '#E39B2D', '#C0392B', '#2a78d6', '#7B5EA7'
    COL = {'DF': TEAL, 'JAM': RED, 'LATCH': ORG, 'AIMD': PUR, 'PHYS': BLUE}
    win = res['variants']['PHYS']['window_in']
    LAB = {'DF': 'DoorFlow: fixed quota from averages', 'JAM': 'Limit only while a jam is seen',
           'LATCH': 'Limit from the first jam on', 'AIMD': 'Adjust the quota by measured delay',
           'PHYS': f'Quota from physical capacity ({win} in)'}
    fig = plt.figure(figsize=(7.6, 6.0), dpi=220)
    a1 = fig.add_subplot(fig.add_gridspec(1, 1, left=0.12, right=0.975, top=0.765, bottom=0.53)[0])
    a2 = fig.add_subplot(fig.add_gridspec(1, 1, left=0.42, right=0.975, top=0.39, bottom=0.11)[0])
    key = ('room250', 11700, 145)
    for v in ['JAM', 'AIMD', 'PHYS', 'DF']:
        tr = np.array(got[(key[0], v, key[1], key[2])]['trace'])
        a1.plot(tr[:, 0], tr[:, 5], color=COL[v], lw=2.6 if v == 'DF' else 1.3, label=LAB[v], zorder=5 if v == 'DF' else 3)
    a1.set_xlabel('tick', fontsize=9.5, color=GREY); a1.set_ylabel('robots on the way', fontsize=9.5, color=GREY)
    a1.set_title(f'One run (250 robots, seeds {key[1]} / {key[2]}): robots heading into the lower-left through door 6', fontsize=10.5, color=INK, loc='left', x=-0.1, pad=46)
    a1.legend(fontsize=8.6, frameon=False, loc='lower left', bbox_to_anchor=(-0.02, 1.0), ncol=2, columnspacing=1.2, handlelength=1.8)
    a1.set_ylim(0, 36)
    a1.spines[['top', 'right']].set_visible(False); a1.tick_params(labelsize=9)
    order = ['JAM', 'LATCH', 'AIMD', 'PHYS']
    ys = np.arange(len(order))[::-1]
    for y, v in zip(ys, order):
        r = res['variants'][v]; m, (lo, hi) = r['change_vs_DF_pct'], r['ci95_pct']
        a2.barh(y, m, color=COL[v], height=0.58)
        a2.plot([lo, hi], [y, y], color=INK, lw=1.2)
        a2.text(max(hi, 0) + 0.25, y, f'{m:+.1f}%  ({r["worse_runs"]} of 60 runs worse)', ha='left', va='center', fontsize=9.2, color=INK)
    a2.axvline(0, color=INK, lw=1.0)
    a2.set_yticks(ys); a2.set_yticklabels([LAB[v] for v in order], fontsize=9.6)
    lo_all = min(res['variants'][v]['ci95_pct'][0] for v in order)
    a2.set_xlim(min(-4, lo_all * 1.25), 11)
    a2.set_xlabel('orders finished vs DoorFlow (%), same seeds; black line = 95% interval', fontsize=9.2, color=GREY)
    a2.set_title('Each alternative vs DoorFlow: 60 paired runs (200 / 250 / 300 robots, 20 seed pairs each)', fontsize=10.5, color=INK, loc='left', x=-0.66)
    a2.spines[['top', 'right']].set_visible(False); a2.tick_params(labelsize=9)
    fig.suptitle('Live alternatives to the fixed quota, rerun on the official room map', fontsize=12, color=INK, x=0.02, ha='left', fontweight='bold')
    fig.text(0.02, 0.012, f"{res['runs']} runs of 5,000 ticks, {res['errors']} errors. Script: figures/deck/demo/live_control.py (planner patch live_window.patch).",
             fontsize=8, color=GREY, style='italic')
    fig.savefig(REPO / 'figures/deck/fig_live_control.png', facecolor='white'); plt.close(fig)


def plot_only():
    """redraw the figure from live_control.json: reruns only the four runs of the example panel (room250, 11700 / 145)"""
    res = json.loads((HERE / 'live_control.json').read_text())
    got = {(j[0], j[1], j[2], j[3]): run(j) for j in [('room250', v, 11700, 145) for v in ('DF', 'JAM', 'AIMD', 'PHYS')]}
    plot(got, res)


if __name__ == '__main__':
    t0 = time.time(); (plot_only if sys.argv[1:] == ['plot'] else main)(); print('seconds', round(time.time() - t0, 1))
