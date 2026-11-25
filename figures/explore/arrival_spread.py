"""Why booking (A) and direction phases (B) by expected arrival time cannot work well: how far off is the expected time of
arrival at door 6? DoorFlow, task seed 11700 x planner 145 on room200/250/300 (one run each; the simulator with
figures/explore/explore.patch, ROBOT_EX_LOG=1, which only logs). For every crossing of door 6:
  ticks  = ticks from the moment the robot is counted on the way until it crosses (measured)
  pred   = the arrival time A and B estimated at that moment: 2.23 x 3 ticks x steps (formula estimate; same function as A/B)
  error  = ticks - pred
Writes figures/explore/arrival_spread.json (per map and direction: statistics and every (ticks, pred) pair) and prints a summary.
Run 'completed' must equal the DF rows of runs_main.jsonl for the same seeds (logging does not change behaviour)."""
import json, os, re, subprocess
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', '/home/user/sim_explore/sim/build-linux/lifelong'); WORK = Path(os.environ.get('EX_WORK', '/home/user/sim_explore/runs')) / 'spread'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV'); res = {'runs': {}, 'per_side': {}}
allerr = []
for mp in ['room200', 'room250', 'room300']:
    d = WORK / mp; d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = 11700; tpl['teamSize'] = CFG[mp]['team']; (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(ROBOT_PLANNER_SEED='145', ROBOT_EX_LOG='1')
    p = subprocess.run([PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
                        '-p', '30000', '-c', '3', '-d', '3'], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    res['runs'][mp] = dict(seed=11700, planner_seed=145, completed=json.loads((d / 'out.json').read_text())['numTaskFinished'])
    for s in ('0', '1'):
        pr = [(int(t), int(q)) for b, ss, t, q in re.findall(r'\[exa\] (\d+) (\d+) (\d+) (-?\d+)', p.stderr) if b == '0' and ss == s]
        x = np.array([t for t, _ in pr]); ok = [(t, q) for t, q in pr if q >= 0]
        e = np.array([t - q for t, q in ok]); allerr += e.tolist()
        res['per_side'][f'{mp} side{s}'] = dict(
            n=len(x), mean=round(float(x.mean()), 1), sd=round(float(x.std()), 1), p10=int(np.percentile(x, 10)), median=int(np.median(x)),
            p90=int(np.percentile(x, 90)), n_with_estimate=len(ok), error_mean=round(float(e.mean()), 1), error_sd=round(float(e.std()), 1),
            error_p10=int(np.percentile(e, 10)), error_p90=int(np.percentile(e, 90)), pairs=pr)
a = np.array(allerr)
res['all'] = dict(n=len(a), error_mean=round(float(a.mean()), 1), error_sd=round(float(a.std()), 1), error_median=int(np.median(a)),
                  error_p10=int(np.percentile(a, 10)), error_p90=int(np.percentile(a, 90)),
                  share_within_50=round(float(np.mean(np.abs(a) <= 50)), 3), share_within_100=round(float(np.mean(np.abs(a) <= 100)), 3),
                  share_within_150=round(float(np.mean(np.abs(a) <= 150)), 3),
                  # booking compares robots with each other, so a lateness shared by all does not matter: remove the median first
                  share_within_50_after_removing_median=round(float(np.mean(np.abs(a - np.median(a)) <= 50)), 3),
                  share_within_100_after_removing_median=round(float(np.mean(np.abs(a - np.median(a)) <= 100)), 3),
                  share_within_150_after_removing_median=round(float(np.mean(np.abs(a - np.median(a)) <= 150)), 3))
(HERE / 'arrival_spread.json').write_text(json.dumps(res, indent=1))
print(res['runs']); print(res['all'])
for k, v in res['per_side'].items(): print(k, {kk: vv for kk, vv in v.items() if kk != 'pairs'})
