"""Linux runner (same command line as harness/run_dev.py), for the room-only ablation."""
import json, os, subprocess, sys, time, shutil, hashlib, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
H = Path('/home/user/SEEM5910-Final-Presentation-and-Report/experiment-materials/网络协议方向/harness')
DATA = H / 'data'; PROG = '/home/user/simbuild/p78/build-linux/lifelong'; WORK = Path('/home/user/simbuild/work')
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
lock = threading.Lock()
def run(j):
    tag = hashlib.md5(json.dumps(j, sort_keys=True).encode()).hexdigest()[:10]
    d = WORK / tag; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    f = DATA / CFG[j['map']]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = j['seed']; tpl['teamSize'] = CFG[j['map']]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[j['map']]['env'])
    for k, v in j['env'].items():
        if v is None: env.pop(k, None)
        else: env[k] = v
    env['ROBOT_PLANNER_SEED'] = str(j['pseed'])
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', str(j.get('ticks', 5000)), '-a', '10', '-n', '1000', '-t', '150', '-x', '100', '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    row = dict(map=j['map'], method=j['method'], seed=j['seed'], pseed=j['pseed'], sec=round(time.time() - t0, 1))
    try:
        o = json.loads((d / 'out.json').read_text()); row.update(completed=o['numTaskFinished'], plannerErrors=o.get('numPlannerErrors'), errors=len(o.get('errors', [])))
    except Exception as e: row['error'] = (p.stderr or '')[-300:] + repr(e)
    row['stderr_tail'] = (p.stderr or '')[-800:]
    shutil.rmtree(d, ignore_errors=True); return row
def batch(jobs, out, workers=4):
    out = Path(out); done = set()
    if out.exists(): done = {(r['map'], r['method'], r['seed'], r['pseed']) for r in map(json.loads, out.read_text().splitlines()) if 'completed' in r}
    todo = [j for j in jobs if (j['map'], j['method'], j['seed'], j['pseed']) not in done]
    print(len(jobs), 'jobs', len(todo), 'todo', flush=True)
    def go(j):
        r = run(j)
        with lock:
            with open(out, 'a') as fh: fh.write(json.dumps(r) + '\n')
        return r
    with ThreadPoolExecutor(workers) as ex:
        for i, r in enumerate(ex.map(go, todo), 1):
            if i % 20 == 0 or 'error' in r: print(i, r, flush=True)
if __name__ == '__main__':
    jobs = [dict(map=m, method='LCAPWD', seed=9700, pseed=101, env={}) for m in ['room250', 'room300']]
    for j in jobs: print(run(j))
