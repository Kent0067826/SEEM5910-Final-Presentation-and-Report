"""Round 29 runner: same as r10.run_job / run_batch, plus a per-500-tick completion profile ('prof') read from telemetry."""
import sys, json, os, subprocess, time, threading, hashlib
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r25_common import *          # INST, V, r10
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
R29 = V + 'maps_r29/'
for _name, (_free, _d) in json.load(open(R29 + 'instances.json')).items():
    for _k, _n in _d.items(): INST[_k] = (R29 + _k + '.json', _n)
N2 = {'ROBOT_SCHED': 'nms', 'ROBOT_NMS_W': '2'}
MAC = {'ROBOT_BMAC': '1', 'ROBOT_BMAC_EVAC': '1', 'ROBOT_BMAC_DEMOTE': '1'}
def BC(k): return dict(N2, ROBOT_BRIDGE_CREDIT=str(k))
def BCM(k): return dict(N2, ROBOT_BRIDGE_CREDIT=str(k), **MAC)
OFFICIAL_BRIDGED = ['room200', 'room250', 'room300', 'maze40', 'maze60']
OFFICIAL_UNBRIDGED = ['random200', 'random300', 'warehouse100']
HELDOUT = sorted(k for _n, (_f, _d) in json.load(open(R29 + 'instances.json')).items() for k in _d)
_lock = threading.Lock()

def run_job(j, work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    tag = hashlib.md5(r10.key(j).encode()).hexdigest()[:10]
    d = work / f"job_{tag}"; d.mkdir(exist_ok=True)
    prob = r10.make_custom(j, d)
    env = dict(os.environ); env.update(r10.R.COMMON_ENV); env.update(j['env']); env['ROBOT_PLANNER_SEED'] = str(j['pseed'])
    env['ROBOT_TELEMETRY'] = str(d / 'tel.jsonl')
    cmd = [str(j['program']), '-i', prob.name, '-o', 'out.json', '-s', str(j.get('ticks', 1200)), '-a', '10', '-n', '1000', '-t', '150',
           '-x', '100', '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    row = dict(map=j['map'], method=j['method'], seed=j['seed'], pseed=j['pseed'], ticks=j.get('ticks', 1200), sec=round(time.time() - t0, 2))
    try:
        row['completed'] = json.loads((d / 'out.json').read_text())['numTaskFinished']
        tel = [json.loads(l) for l in (d / 'tel.jsonl').read_text().splitlines()]
        prof, prev, nxt = [], 0, 500
        for r in tel:
            if r['t'] >= nxt: prof.append(r['fair']['doneCount'] - prev); prev = r['fair']['doneCount']; nxt += 500
        row['prof'] = prof; row['fair'] = tel[-1].get('fair')
    except Exception as e:
        row['error'] = (p.stderr or '')[-300:] + repr(e)
    for f in d.iterdir(): f.unlink()
    d.rmdir()
    return row

def run_batch(jobs, out_jsonl, workers=2):
    out = Path(out_jsonl); out.parent.mkdir(parents=True, exist_ok=True); done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            r = json.loads(l)
            if 'completed' in r: done.add(r10.key(r))
    todo = [j for j in jobs if r10.key(j) not in done]
    print(f"{len(jobs)} jobs, {len(todo)} to run", flush=True)
    work = out.parent / (out.stem + '_work')
    def go(j):
        r = run_job(j, work)
        with _lock:
            with open(out, 'a') as fh: fh.write(json.dumps(r) + '\n')
        return r
    n = 0
    with ThreadPoolExecutor(workers) as ex:
        for r in ex.map(go, todo):
            n += 1
            if n % 20 == 0 or 'error' in r: print(n, r.get('map'), r.get('method'), r.get('completed'), r.get('error', ''), flush=True)
