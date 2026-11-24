"""Run the two replays used by the demo (no door control vs DoorFlow) and dump every robot's cell at every tick.

The simulator is the project's own source (experiment-materials/网络协议方向/src/dev_src_p78), copied to a build folder
outside the repo with one small patch that only writes positions (demo_dump.patch, next to this file). Build:
    cp -r <repo>/experiment-materials/网络协议方向/src/dev_src_p78 /home/user/simbuild/p78demo
    cd /home/user/simbuild/p78demo && patch -p0 src/CompetitionSystem.cpp < <repo>/figures/deck/demo/demo_dump.patch
    tr -d '\r' < build_linux.sh > build_unix.sh && bash build_unix.sh
Then, from the repo root:  python3 figures/deck/demo/run_demo.py
Settings are the formal ones (harness/lcap_env17_wd.json, room250, seed 9700, planner seed 101 -- the regression pair whose
archived result for the full method is 1130 orders). "none" removes the quota, the door rule, the global cap and the watchdog
(= champion assignment + fixed executor), exactly as figures/part3/rerun/ablation.py defines NONE."""
import json, os, subprocess, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

REPO = Path(__file__).resolve().parents[3]
H = REPO / 'experiment-materials/网络协议方向/harness'
PROG = os.environ.get('DEMO_SIM', '/home/user/simbuild/p78demo/build-linux/lifelong')
WORK = Path(os.environ.get('DEMO_WORK', '/home/user/simbuild/demo'))
CFG = json.loads((H / 'lcap_env17_wd.json').read_text(encoding='utf8')); COMMON = CFG.pop('_COMMON_ENV')
NONE = ['ROBOT_BRIDGE_CREDIT', 'ROBOT_CUT2_CREDIT', 'ROBOT_BMAC', 'ROBOT_LMAC', 'ROBOT_ACTIVE_CAP',
        'ROBOT_PFC_WD', 'ROBOT_PFC_WD_DRAIN', 'ROBOT_NET']
MAP, SEED, PSEED, TICKS = 'room250', 9700, 101, 5000


def run(method):
    d = WORK / method; d.mkdir(parents=True, exist_ok=True)
    f = H / 'data' / CFG[MAP]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'): tpl[k] = os.path.relpath(f.parent / tpl[k], d)
    tpl['delayConfig']['seed'] = SEED; tpl['teamSize'] = CFG[MAP]['team']
    (d / 'prob.json').write_text(json.dumps(tpl))
    env = dict(os.environ); env.update(COMMON); env.update(CFG[MAP]['env'])
    if method == 'none':
        for k in NONE: env.pop(k, None)
    env['ROBOT_PLANNER_SEED'] = str(PSEED); env['ROBOT_DUMP_POS'] = str(d / 'pos.bin')
    cmd = [PROG, '-i', 'prob.json', '-o', 'out.json', '-s', str(TICKS), '-a', '10', '-n', '1000', '-t', '150', '-x', '100',
           '-p', '30000', '-c', '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace')
    o = json.loads((d / 'out.json').read_text())
    return dict(method=method, completed=o['numTaskFinished'], sec=round(time.time() - t0, 1), rc=p.returncode,
                dump_bytes=(d / 'pos.bin').stat().st_size, mapfile=str(f.parent / tpl['mapFile'] if False else (f.parent / json.loads(f.read_text())['mapFile'])))


if __name__ == '__main__':
    WORK.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(2) as ex:
        rows = list(ex.map(run, ['none', 'doorflow']))
    for r in rows: print(json.dumps(r, ensure_ascii=False))
    (WORK / 'runs.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
