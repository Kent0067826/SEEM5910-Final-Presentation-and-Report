"""v10 research runner: like run_experiment but keeps the last telemetry record and writes one jsonl row per run.
Rows are appended atomically; reruns skip finished (key) rows, so batches can resume."""
import json, os, subprocess, sys, time, threading, hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
PKG = Path('/home/claude/proj/v10/pkg'); sys.path.insert(0, str(PKG))
import run_experiment as R
PROG = PKG / 'planner_src/build-linux/lifelong'
_lock = threading.Lock()

def key(j): return f"{j['map']}|{j['method']}|{j['seed']}|{j['pseed']}|{j.get('ticks',1200)}"

def run_job(j, work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    tag = hashlib.md5(key(j).encode()).hexdigest()[:10]
    d = work / f"job_{tag}"; d.mkdir(exist_ok=True)
    prob = R.make_problem(j['map'], j['seed'], d) if 'mapfile' not in j else make_custom(j, d)
    env = dict(os.environ); env.update(R.COMMON_ENV); env.update(j['env']); env['ROBOT_PLANNER_SEED'] = str(j['pseed'])
    env['ROBOT_TELEMETRY'] = str(d / 'tel.jsonl')
    cmd = [str(j.get('program', PROG)), '-i', prob.name, '-o', 'out.json', '-s', str(j.get('ticks', 1200)), '-a', '10', '-n', '1000', '-t', '150',
           '-x', '100', '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    row = dict(map=j['map'], method=j['method'], seed=j['seed'], pseed=j['pseed'], ticks=j.get('ticks', 1200), sec=round(time.time() - t0, 2))
    try:
        row['completed'] = json.loads((d / 'out.json').read_text())['numTaskFinished']
        lines = (d / 'tel.jsonl').read_text().splitlines() if (d / 'tel.jsonl').exists() else []
        if lines:
            last = json.loads(lines[-1]); row['tel'] = {'gate': last.get('gate'), 'win': last['windows'][0], 'fair': last.get('fair'), 'lines': last.get('lines')}
            ws = [json.loads(l)['windows'][0]['value'] for l in lines]; row['winMean'] = sum(ws) / len(ws)
    except Exception as e:
        row['error'] = (p.stderr or '')[-300:] + repr(e)
    for f in d.iterdir(): f.unlink()
    d.rmdir()
    return row

def make_custom(j, d):
    tpl = json.loads(Path(j['mapfile']).read_text()); base = Path(j['mapfile']).parent
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(base / tpl[k], d)
    tpl['delayConfig']['seed'] = j['seed']
    if 'team' in j: tpl['teamSize'] = j['team']
    f = d / 'prob.json'; f.write_text(json.dumps(tpl)); return f

def run_batch(jobs, out_jsonl, workers=3):
    out = Path(out_jsonl); out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for l in out.read_text().splitlines():
            r = json.loads(l)
            if 'completed' in r: done.add(f"{r['map']}|{r['method']}|{r['seed']}|{r['pseed']}|{r['ticks']}")
    todo = [j for j in jobs if key(j) not in done]
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
    return [json.loads(l) for l in out.read_text().splitlines()]

def load(out_jsonl):
    return [json.loads(l) for l in Path(out_jsonl).read_text().splitlines() if 'completed' in json.loads(l)]
