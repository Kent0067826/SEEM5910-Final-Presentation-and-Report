"""Round 50 (wait-v40), measurement only: how long is "assignment -> crossing" on the cuts the old detector misses (2-cell doors,
far-apart door pairs), compared with the model alpha * T_free? bin/lifelong-v35a (source dev_src_v35 = v34 + ROBOT_RG_DRY, ROBOT_CUT_MEAS).
LCAPM = LCAP + every region-graph cut counted but never denying + measurement: behaviour identical to LCAP (checked)."""
import sys, json, os, subprocess, time, hashlib, re
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r49_common import *
from pathlib import Path
BIN50 = V + 'bin/lifelong-v35a'
def lcapm_env(k): return dict(lcap_env(k), ROBOT_RG_CUTS='1', ROBOT_RG_DRY='1', ROBOT_CUT_MEAS='1', ROBOT_BRIDGE_TRACE='1')
def bncm_env(k): return dict(lcap_env(k), ROBOT_RG_CUTS='2', ROBOT_CUT_MEAS='1', ROBOT_BRIDGE_TRACE='1')
CM = re.compile(r'\[cutmeas\] t=(\d+) cut (\d+) (\w+) (.*)')
SIDE = re.compile(r'side(\d+) K=(-?\d+) Tfree=(-?\d+) L=([\d.]+) X=(\d+) T=(-?[\d.]+)')
RGC = re.compile(r'\[rgcut\] doors (.*?) parts: (.*?) K:')
def run_meas(j, work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    d = work / ('job_' + hashlib.md5(r10.key(j).encode()).hexdigest()[:10]); d.mkdir(exist_ok=True)
    prob = r10.make_custom(j, d)
    env = dict(os.environ); env.update(r10.R.COMMON_ENV); env.update(j['env']); env['ROBOT_PLANNER_SEED'] = str(j['pseed'])
    cmd = [str(j['program']), '-i', prob.name, '-o', 'out.json', '-s', str(j['ticks']), '-a', '10', '-n', '1000', '-t', '150', '-x', '100', '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    row = dict(map=j['map'], method=j['method'], seed=j['seed'], pseed=j['pseed'], ticks=j['ticks'], sec=round(time.time() - t0, 2))
    out = json.loads((d / 'out.json').read_text()); row['completed'] = out['numTaskFinished']; row['plannerErrors'] = out.get('numPlannerErrors')
    last = {}; rg = []
    for l in p.stderr.splitlines():
        m = CM.match(l)
        if m: last[int(m.group(2))] = dict(t=int(m.group(1)), kind=m.group(3), sides=[dict(side=int(a), K=int(b), Tfree=int(c), L=float(e), X=int(f), T=float(g)) for a, b, c, e, f, g in SIDE.findall(m.group(4))])
        m = RGC.match(l)
        if m: rg.append(dict(doors=m.group(1), parts=[int(x) for x in m.group(2).split()]))
    row['cuts'] = [last[b] for b in sorted(last)]; row['rgcuts'] = rg
    for f in d.iterdir(): f.unlink()
    d.rmdir(); return row
def run_batch_meas(jobs, out_jsonl, workers=2):
    out = Path(out_jsonl); out.parent.mkdir(parents=True, exist_ok=True); done = set()
    if out.exists(): done = {r10.key(json.loads(l)) for l in out.read_text().splitlines()}
    todo = [j for j in jobs if r10.key(j) not in done]; print(len(jobs), 'jobs,', len(todo), 'to run', flush=True)
    import threading; from concurrent.futures import ThreadPoolExecutor; lock = threading.Lock()
    def go(j):
        r = run_meas(j, out.parent / (out.stem + '_work'))
        with lock, open(out, 'a') as fh: fh.write(json.dumps(r) + '\n')
        return r
    with ThreadPoolExecutor(workers) as ex:
        for n, r in enumerate(ex.map(go, todo), 1):
            if n % 20 == 0: print(n, r['map'], r['method'], r['completed'], flush=True)
