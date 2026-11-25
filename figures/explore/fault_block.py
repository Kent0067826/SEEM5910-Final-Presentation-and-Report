"""Round 3 measurement ("先量"): how often does a broken-down robot stand on door 6 or 1-2 steps from it while other robots
wait to use the door (counted on the way through door 6, within 6 steps)? Sampled at DoorFlow's recounts (every 15 ticks).
d0: on the door cells (nobody can pass); d12: 1-2 steps away (a robot behind might squeeze past in the open room).
DoorFlow, task seeds 11700-11702 x planner 145, room200/250/300 (9 runs), logging only (ROBOT_EX_LOG=3).
Writes figures/explore/fault_block.json."""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', '/home/user/sim_explore/sim/build-linux/lifelong'); WORK = Path(os.environ.get('EX_WORK', '/home/user/sim_explore/runs')) / 'fault'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
def run(job):
    mp, seed = job; d = WORK / mp / str(seed); d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[mp]['team']; (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(ROBOT_PLANNER_SEED='145', ROBOT_EX_LOG='3')
    p = subprocess.run([PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
                        '-p', '30000', '-c', '3', '-d', '3'], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    f = [tuple(map(int, m)) for m in re.findall(r'\[exf\] (\d+) (\d+) (\d+) (\d+) (\d+)', p.stderr)]
    n = len(f)
    return dict(map=mp, seed=seed, completed=json.loads((d / 'out.json').read_text())['numTaskFinished'], samples=n,
                on_door=sum(x[1] > 0 for x in f), on_door_and_waiting=sum(x[1] > 0 and x[3] for x in f),
                near_door=sum(x[2] > 0 for x in f), near_door_and_waiting=sum(x[2] > 0 and x[4] for x in f))
rows = list(ThreadPoolExecutor(4).map(run, [(mp, s) for mp in ['room200', 'room250', 'room300'] for s in (11700, 11701, 11702)]))
N = sum(r['samples'] for r in rows)
res = dict(runs=rows, samples=N, share={k: round(sum(r[k] for r in rows) / N, 3) for k in ('on_door', 'on_door_and_waiting', 'near_door', 'near_door_and_waiting')})
(HERE / 'fault_block.json').write_text(json.dumps(res, indent=1)); print(res['share']); print([(r['map'], r['seed'], r['completed']) for r in rows])
