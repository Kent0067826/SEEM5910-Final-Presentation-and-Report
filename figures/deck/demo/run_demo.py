"""Run the replays used by the demo and the congestion monitor, and dump every robot's cell at every tick.
  none      no door control (champion assignment + fixed executor)                      -> demo, monitor
  doorflow  the formal settings (quota + door rule + fixes + safety nets)                 -> demo
  hnspf     none + HN-SPF link costs (protocol round 53, setting A: ROBOT_HNSPF=2, ROBOT_HNSPF_STEP=1)  -> monitor
  teft      none + Fortz-Thorup cell weights (protocol round 28: ROBOT_TE_FT=1)        -> monitor
The two routing runs only change how guide paths are priced; like "none" they have no door control. They are new runs on
this one map and seed, not the multi-map tests of rounds 28 and 53 (those were on top of the full method of the time).
Usage: python3 figures/deck/demo/run_demo.py [method ...]   (default: all four)

Easiest: run everything with one command from the repo root (Linux or Windows WSL / Ubuntu):
    bash figures/deck/demo/run_all.sh            # builds the simulator once, runs both replays, rebuilds the demo
By hand: the simulator is the project's own source (experiment-materials/网络协议方向/src/dev_src_p78), copied to a build
folder outside the repo with one small patch that only writes positions (demo_dump.patch, next to this file):
    cp -r experiment-materials/网络协议方向/src/dev_src_p78 ~/doorflow_demo/sim
    cd ~/doorflow_demo/sim && patch -p0 src/CompetitionSystem.cpp < <repo>/figures/deck/demo/demo_dump.patch
    tr -d '\r' < build_linux.sh > build_unix.sh && bash build_unix.sh      # needs only g++ (C++17)
Then, from the repo root:  python3 figures/deck/demo/run_demo.py   (DEMO_SIM = simulator, DEMO_WORK = output folder)
Settings are the formal ones (harness/lcap_env17_wd.json, room250, seed 9700, planner seed 101 -- the regression pair whose
archived result for the full method is 1130 orders). "none" removes the quota, the door rule, the global cap and the watchdog
(= champion assignment + fixed executor), exactly as figures/part3/rerun/ablation.py defines NONE."""
import json, os, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

REPO = Path(__file__).resolve().parents[3]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('DEMO_SIM', str(Path.home() / 'doorflow_demo' / 'sim' / 'build-linux' / 'lifelong'))
WORK = Path(os.environ.get('DEMO_WORK', Path.home() / 'doorflow_demo' / 'runs'))
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
NONE = ['ROBOT_BRIDGE_CREDIT', 'ROBOT_CUT2_CREDIT', 'ROBOT_BMAC', 'ROBOT_LMAC', 'ROBOT_ACTIVE_CAP',
        'ROBOT_PFC_WD', 'ROBOT_PFC_WD_DRAIN', 'ROBOT_NET']
MAP, SEED, PSEED, TICKS = 'room250', 9700, 101, 5000


METHODS = {'none': (True, {}), 'doorflow': (False, {}),
           'hnspf': (True, {'ROBOT_HNSPF': '2', 'ROBOT_HNSPF_STEP': '1'}),
           'teft': (True, {'ROBOT_TE_FT': '1'})}


def run(method):
    d = WORK / method; d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[MAP]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = SEED; tpl['teamSize'] = CFG[MAP]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[MAP]['env'])
    strip, extra = METHODS[method]
    if strip:
        for k in NONE: env.pop(k, None)
    env.update(extra)
    env['ROBOT_PLANNER_SEED'] = str(PSEED); env['ROBOT_DUMP_POS'] = str(d / 'pos.bin')
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', str(TICKS), '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    (d / 'out.json').unlink(missing_ok=True)
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    if p.returncode != 0 or not (d / 'out.json').exists():
        sys.exit(f'{method}: the simulator stopped with code {p.returncode}\n' + p.stderr[-2000:])
    o = json.loads((d / 'out.json').read_text())
    return dict(method=method, completed=o['numTaskFinished'], sec=round(time.time() - t0, 1), rc=p.returncode,
                dump_bytes=(d / 'pos.bin').stat().st_size, mapfile=str(f.parent / json.loads(f.read_text())['mapFile']))


if __name__ == '__main__':
    if not os.access(PROG, os.X_OK):
        sys.exit(f'simulator not found: {PROG}\nbuild it with  bash figures/deck/demo/run_all.sh  or set DEMO_SIM to its path')
    WORK.mkdir(parents=True, exist_ok=True)
    todo = sys.argv[1:] or list(METHODS)
    bad = [m for m in todo if m not in METHODS]
    if bad: sys.exit(f'unknown method(s) {bad}; choose from {list(METHODS)}')
    with ThreadPoolExecutor(min(4, len(todo))) as ex:
        rows = list(ex.map(run, todo))
    for r in rows: print(json.dumps(r, ensure_ascii=False))
    old = json.loads((WORK / 'runs.json').read_text()) if (WORK / 'runs.json').exists() else []
    keep = [r for r in old if r['method'] not in todo]
    (WORK / 'runs.json').write_text(json.dumps(keep + rows, ensure_ascii=False, indent=1))
