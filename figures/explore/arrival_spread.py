"""Why booking / phases by expected arrival time cannot work well: how spread out is the time from being counted on the way
to door 6 until crossing? DoorFlow, task seed 11700 x planner 145 on room200/250/300 (one run each), every crossing of door 6.
Writes figures/explore/arrival_spread.json (statistics of the measured times, per direction)."""
import json, os, re, subprocess
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]; H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('EX_SIM', '/home/user/sim_explore/sim/build-linux/lifelong'); WORK = Path(os.environ.get('EX_WORK', '/home/user/sim_explore/runs')) / 'spread'
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV'); res = {}
for mp in ['room200', 'room250', 'room300']:
    d = WORK / mp; d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[mp]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = 11700; tpl['teamSize'] = CFG[mp]['team']; (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[mp]['env']); env.update(ROBOT_PLANNER_SEED='145', ROBOT_EX_LOG='1')
    p = subprocess.run([PROG, '-i', 'prob.json', '-o', 'out.json', '-s', '5000', '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
                        '-p', '30000', '-c', '3', '-d', '3'], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    for s in ('0', '1'):
        x = np.array([int(t) for b, ss, t in re.findall(r'\[exa\] (\d+) (\d+) (\d+)', p.stderr) if b == '0' and ss == s])
        res[f'{mp} side{s}'] = dict(n=len(x), mean=round(float(x.mean()), 1), sd=round(float(x.std()), 1), cv=round(float(x.std() / x.mean()), 2),
                                    p10=int(np.percentile(x, 10)), median=int(np.median(x)), p90=int(np.percentile(x, 90)))
(HERE / 'arrival_spread.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
