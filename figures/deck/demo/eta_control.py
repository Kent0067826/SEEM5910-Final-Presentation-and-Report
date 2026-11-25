"""Which robots should the window count? Reruns DoorFlow on the official room map with three other ways of counting the robots
on the way to door 6 (speaker 3, slide on the window):

  DF      DoorFlow as submitted: every robot whose order will take it through the door is counted, from the moment it gets the
          order until it is through (in 15 / out 10)
  NEAR550 count a robot only while its estimated time to the door is <= 550 ticks (slow-down 2.23 x 3 ticks per step x steps;
          550 = one trip of door 6); window unchanged (15 / 10)
  NEAR275 count only robots <= 275 ticks (half a trip) from the door; window = ceil(275 x 26/500 / 2) = 8 per direction
  BOTH    the two directions of the door share one window, 15 + 10 = 25
All need figures/deck/demo/eta_window.patch on top of live_window.patch (off unless ROBOT_ETA_H / ROBOT_BOTHDIR is set).
Runs, seeds and build: as live_control.py (60 seed pairs of the formal evaluation, 5,000 ticks), paired with DF.
Usage (repo root):  LIVE_SIM=<simulator> LIVE_WORK=<work dir> python3 figures/deck/demo/eta_control.py
Writes figures/deck/demo/eta_control.json (+ eta_control_rows.jsonl)."""
import json, os, random, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('LIVE_SIM', str(Path.home() / 'doorflow_eta' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('LIVE_WORK', Path.home() / 'doorflow_eta' / 'runs'))
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
MAPS = ['room200', 'room250', 'room300']
PAIRS = [(s, p) for s in range(11700, 11710) for p in (145, 146)]
VARIANTS = {'DF': {}, 'NEAR550': {'ROBOT_ETA_H': '550'}, 'NEAR275': {'ROBOT_ETA_H': '275'}, 'BOTH': {'ROBOT_BOTHDIR': '1'}}
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
    with open(HERE / 'eta_control_rows.jsonl', 'w') as fh:
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
        res['variants'][v]['window_in'] = int(np.median([np.median(t[:, 6]) for t in tr if len(t)]))
    (HERE / 'eta_control.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    t0 = time.time(); main(); print('seconds', round(time.time() - t0, 1))
