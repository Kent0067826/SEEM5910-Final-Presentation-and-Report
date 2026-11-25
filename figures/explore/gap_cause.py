"""Round 1 measurement ("先量"): when the next robot of the same direction is late at door 6 (gap to the previous crossing
longer than 10 ticks), where is it? Sampled at DoorFlow's recounts (every 15 ticks), for every sample inside such a gap beyond
its first 10 ticks:
  near : some robot counted on the way in that direction is within 6 walking steps of the door (it is close but not through:
         faults, turning, queue order, waiting for the exit)
  far  : none is within 6 steps but some are further away (it is still walking: a waiting spot near the door could help)
  none : no robot is on the way in that direction at all (nothing to call)
DoorFlow, task seed 11700 x planner 145, room200/250/300; logging only (ROBOT_EX_LOG=2). Writes figures/explore/gap_cause.json."""
import json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', '/home/user/sim_explore/sim/build-linux/lifelong'); WORK = Path(os.environ.get('EX_WORK', '/home/user/sim_explore/runs')) / 'gapcause'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
def run(job):
    mp, seed = job; d = WORK / mp / str(seed); d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = seed; tpl['teamSize'] = CFG[mp]['team']; (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(ROBOT_PLANNER_SEED='145', ROBOT_EX_LOG='2')
    p = subprocess.run([PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
                        '-p', '30000', '-c', '3', '-d', '3'], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    cr = [tuple(map(int, m)) for m in re.findall(r'\[exc\] (\d+) (\d+) (\d+)', p.stderr)]
    nb = {int(m[0]): tuple(map(int, m[1:])) for m in re.findall(r'\[exn\] (\d+) (\d+) (\d+) (\d+) (\d+)', p.stderr)}
    tally = {'near': 0, 'far': 0, 'none': 0}
    for (t0, s0, _), (t1, s1, _) in zip(cr, cr[1:]):
        if s1 != s0: continue
        for t in range(t0 + 11, t1):
            if t not in nb: continue
            near, far = (nb[t][0], nb[t][1]) if s0 == 0 else (nb[t][2], nb[t][3])
            tally['near' if near else 'far' if far else 'none'] += 1
    return dict(map=mp, seed=seed, completed=json.loads((d / 'out.json').read_text())['numTaskFinished'], crossings=len(cr), tally=tally)
rows = list(ThreadPoolExecutor(3).map(run, [(mp, 11700) for mp in ['room200', 'room250', 'room300']]))
tot = {k: sum(r['tally'][k] for r in rows) for k in ('near', 'far', 'none')}; n = sum(tot.values())
res = dict(runs=rows, ticks=tot, share={k: round(v / n, 3) for k, v in tot.items()})
(HERE / 'gap_cause.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res))
