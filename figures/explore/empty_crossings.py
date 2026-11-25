"""Round 1 measurement ("先量"): of all door-6 crossings, how many are made by robots carrying nothing yet?
kind 0 = robot has no order; 1 = on the way to the first errand of its order (empty); 2 = between errands (carrying).
DoorFlow, task seeds 11700-11702 x planner 145, room200/250/300 (9 runs), logging only (ROBOT_EX_LOG=1).
Crossings are seen when DoorFlow recounts (every 15 ticks), so the times are rounded to 15 ticks: do not use them for gaps
between robots (figures/deck/demo/door_timing.json has per-tick gaps). Writes figures/explore/empty_crossings.json."""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', '/home/user/sim_explore/sim/build-linux/lifelong'); WORK = Path(os.environ.get('EX_WORK', '/home/user/sim_explore/runs')) / 'empty'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
def run(job):
    mp, seed = job; d = WORK / mp / str(seed); d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[mp]['team']; (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(ROBOT_PLANNER_SEED='145', ROBOT_EX_LOG='1')
    p = subprocess.run([PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
                        '-p', '30000', '-c', '3', '-d', '3'], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    c = [tuple(map(int, m)) for m in re.findall(r'\[exc\] (\d+) (\d+) (\d+)', p.stderr)]
    return dict(map=mp, seed=seed, completed=json.loads((d / 'out.json').read_text())['numTaskFinished'], crossings=len(c),
                by_kind={k: sum(x[2] == k for x in c) for k in (0, 1, 2)},
                by_kind_dir={f'{k},{s}': sum(x[2] == k and x[1] == s for x in c) for k in (0, 1, 2) for s in (0, 1)},
                times=[[x[0], x[1]] for x in c])   # tick seen, side entered (seen at DoorFlow's recount, every 15 ticks)
jobs = [(mp, s) for mp in ['room200', 'room250', 'room300'] for s in (11700, 11701, 11702)]
with ThreadPoolExecutor(4) as ex: rows = list(ex.map(run, jobs))
tot = sum(r['crossings'] for r in rows); k = {i: sum(r['by_kind'][i] for r in rows) for i in (0, 1, 2)}
res = dict(runs=rows, total_crossings=tot, share={'no_order': round(k[0] / tot, 3), 'to_first_errand_empty': round(k[1] / tot, 3), 'between_errands_carrying': round(k[2] / tot, 3)},
           by_kind_dir={key: sum(r['by_kind_dir'][key] for r in rows) for key in rows[0]['by_kind_dir']})
(HERE / 'empty_crossings.json').write_text(json.dumps(res, indent=1)); print({kk: v for kk, v in res.items() if kk != 'runs'}); print([(r['map'], r['seed'], r['completed'], r['crossings']) for r in rows])
