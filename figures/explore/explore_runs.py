"""Speaker-3 explore runs: four new ways to admit orders through door 6, each paired with DoorFlow on the same seeds.
  DF        DoorFlow as submitted (lcap_env17_wd.json)
  A100/A200 (A) time-slot booking: admit a door-6 order only if fewer than ceil(W x 26/500 x 1.5) robots already on the way
            are expected at the door within W/2 ticks of this robot (W = 100 / 200)
  B150/B300 (B) direction phases: an order into side s is admitted only if the robot is expected at the door in a phase of
            side s (phases of P = 150 / 300 ticks, alternating)
  CNEAR/CFAR (C) count apart robots crossing on the leg they walk now and robots crossing after a later errand; cap the near
            (CNEAR) or the far (CFAR) ones at half of the direction's window
  END10/END15 (E, round 2) near the end of the run, start only orders whose estimated time (1.0 / 1.5 x 2.23 x 3 ticks x
            Manhattan steps through the remaining errands) ends by tick 5000
  NMSW1/3/5 (round 6, other direction b) the dispatcher's weight on the walk to the pickup, W = 1 / 3 / 5 instead of the
            formal 2 (W = 2 was picked at 1,200 ticks before the executor fix and never re-scanned; the champion's code uses 5)
  WD150/WD600 (round 7, other direction c) deadlock watchdog time limit 150 / 600 ticks instead of the formal 300 (only
            100 and 300 were tried, on an early version, protocol round 35)
  DALPHA    (D) every single-door cut gets its own measured slow-down (figures/explore/alpha_calib.json, from DoorFlow runs on
            calibration seeds 11720-11724 x planner seed 147) instead of the global 2.23
Simulator: experiment-materials/网络协议方向/src/dev_src_p78 copied outside the repo + figures/deck/demo/live_window.patch +
figures/explore/explore.patch (all switches off by default), built with build_linux.sh.
Seeds: task 11700-11709 x planner 145, 146 on room200/250/300 (the 60 pairs of the round-52b formal evaluation), 5,000 ticks.
Usage (repo root): EX_SIM=<simulator> EX_WORK=<work dir> python3 figures/explore/explore_runs.py [variant ...] [--seeds calib|check]
Writes figures/explore/runs_<set>.jsonl (one row per run); summarise with explore_summary.py."""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', str(Path.home() / 'sim_explore' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('EX_WORK', Path.home() / 'sim_explore' / 'runs'))
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
MAPS = ['room200', 'room250', 'room300']
SEEDS = {'main': [(s, p) for s in range(11700, 11710) for p in (145, 146)],      # formal evaluation, round 52b
         'calib': [(s, 147) for s in range(11720, 11725)],                         # only to measure the slow-downs for D
         'check': [(s, p) for s in range(11730, 11740) for p in (148, 149)]}       # unused seeds to re-check a winner
VARIANTS = {'DF': {}, 'A100': {'ROBOT_EX_MODE': '1', 'ROBOT_EX_W': '100'}, 'A200': {'ROBOT_EX_MODE': '1', 'ROBOT_EX_W': '200'},
            'B150': {'ROBOT_EX_MODE': '2', 'ROBOT_EX_P': '150'}, 'B300': {'ROBOT_EX_MODE': '2', 'ROBOT_EX_P': '300'},
            'CNEAR': {'ROBOT_EX_MODE': '3', 'ROBOT_EX_LEGCAP': '0'}, 'CFAR': {'ROBOT_EX_MODE': '3', 'ROBOT_EX_LEGCAP': '1'},
            'DALPHA': 'alpha',
            'END10': {'ROBOT_EX_MODE': '4', 'ROBOT_EX_ENDK': '1.0'}, 'END15': {'ROBOT_EX_MODE': '4', 'ROBOT_EX_ENDK': '1.5'},
            'NMSW1': {'ROBOT_NMS_W': '1'}, 'NMSW3': {'ROBOT_NMS_W': '3'}, 'NMSW5': {'ROBOT_NMS_W': '5'},
            'WD150': {'ROBOT_PFC_WD': '150'}, 'WD600': {'ROBOT_PFC_WD': '600'}}
TRACE_RE = re.compile(r'\[live\] t=(\d+) mode=\d on=(\d) stuck=(\d+) \| side0 L=(-?\d+) K=(-?\d+) \| side1 L=(-?\d+) K=(-?\d+)')
EXA_RE = re.compile(r'\[exa\] (\d+) (\d+) (\d+)')
EX_RE = re.compile(r'\[ex\] t=\d+ denied=(\d+) admitted=(\d+)')
NET_RE = re.compile(r'\[net\] cut (\d+) \((\w+)\) doors \d+:(.*)')


def var_env(var, mp):
    v = VARIANTS[var]
    if v == 'alpha':
        cal = json.loads((HERE / 'alpha_calib.json').read_text())['alpha'][mp]
        return {'ROBOT_EX_ALPHA': ';'.join(f'{b},{s},{a}' for b, s, a in cal)}
    return v


def run(job):
    mp, var, seed, pseed, tag = job
    d = WORK / tag / mp / var / f'{seed}_{pseed}'; d.mkdir(parents=True, exist_ok=True)
    if (d / 'row.json').exists(): return json.loads((d / 'row.json').read_text())
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[mp]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(var_env(var, mp))
    env['ROBOT_PLANNER_SEED'] = str(pseed); env['ROBOT_LIVE_TRACE'] = '1'; env['ROBOT_EX_LOG'] = '1'; env['ROBOT_BRIDGE_TRACE'] = '1'
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time()
    p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    if p.returncode != 0: sys.exit(f'{job}: simulator stopped with code {p.returncode}\n' + p.stderr[-1500:])
    out = json.loads((d / 'out.json').read_text())
    tr = [list(map(int, m.groups())) for m in TRACE_RE.finditer(p.stderr)]   # t, on, stuck, L0, K0, L1, K1
    ex = EX_RE.findall(p.stderr)
    cross = {}
    for b, s, dur in EXA_RE.findall(p.stderr): cross.setdefault(f'{b},{s}', []).append(int(dur))
    tfree = {}
    for b, kind, rest in NET_RE.findall(p.stderr):
        if kind == 'bridge':
            for s, tf, k in re.findall(r'side(\d+) T_free=(\d+) K=(\d+)', rest): tfree[f'{b},{s}'] = [int(tf), int(k)]
    row = dict(set=tag, map=mp, variant=var, seed=seed, pseed=pseed, completed=out['numTaskFinished'], sec=round(time.time() - t0, 1),
               errors=len(out.get('errors', [])), ex_denied=int(ex[-1][0]) if ex else 0, ex_admitted=int(ex[-1][1]) if ex else 0,
               door6_crossings=len(cross.get('0,0', [])) + len(cross.get('0,1', [])),
               cross_n={k: len(v) for k, v in cross.items()}, cross_sum={k: sum(v) for k, v in cross.items()}, tfree_K=tfree,
               alpha_set=re.findall(r'\[exalpha\] cut (\d+) side (\d+) alpha ([\d.]+) K (\d+) -> (\d+)', p.stderr), trace=tr)
    (d / 'row.json').write_text(json.dumps(row)); (d / 'out.json').unlink()
    return row


def trace_summary(tr):
    """door 6 every 25 ticks: stuck robots near the door, robots counted on the way, and how often a window was full"""
    if not tr: return {}
    n = len(tr)
    return dict(trace_n=n, stuck_mean=round(sum(x[2] for x in tr) / n, 2), stuck_ge8_share=round(sum(x[2] >= 8 for x in tr) / n, 3),
                onway_mean=[round(sum(x[3] for x in tr) / n, 2), round(sum(x[5] for x in tr) / n, 2)],
                window=[tr[-1][4], tr[-1][6]], full_share=[round(sum(x[3] >= x[4] for x in tr) / n, 3), round(sum(x[5] >= x[6] for x in tr) / n, 3)])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tag = 'main'
    if '--seeds' in sys.argv: tag = sys.argv[sys.argv.index('--seeds') + 1]; args = [a for a in args if a != tag]
    variants = args or list(VARIANTS)
    jobs = [(mp, v, s, p, tag) for v in variants for mp in MAPS for s, p in SEEDS[tag]]
    t0 = time.time()
    with ThreadPoolExecutor(int(os.environ.get('EX_WORKERS', '4'))) as ex: rows = list(ex.map(run, jobs))
    for r in rows: r.update(trace_summary(r.pop('trace', [])))
    path = HERE / f'runs_{tag}.jsonl'
    old = [json.loads(l) for l in open(path)] if path.exists() else []
    keep = {(r['map'], r['variant'], r['seed'], r['pseed']): r for r in old}
    for r in rows: keep[(r['map'], r['variant'], r['seed'], r['pseed'])] = r
    with open(path, 'w') as fh:
        for r in sorted(keep.values(), key=lambda r: (r['variant'], r['map'], r['seed'], r['pseed'])): fh.write(json.dumps(r) + '\n')
    print(len(rows), 'runs', round(time.time() - t0), 's')


if __name__ == '__main__':
    main()
