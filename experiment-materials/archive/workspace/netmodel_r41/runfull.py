"""跑一次 LoRR 仿真并保留完整输出（-c 1，含每台机器人的实际路径），给带宽测量用。
与正式批次相同的命令行和公共环境变量，只是 -c 3 改成 -c 1。"""
import sys, os, json, subprocess, time
sys.path.insert(0, '/home/claude/proj/v10/scripts')
from r39_common import *          # INST, V, CANDS39, N2F, ...
import r10

FREEZE = json.load(open(V + 'test_freeze_v29.json'))
BIN = V + FREEZE['binary']
METHODS = dict(FREEZE['methods'])          # N2F, FL16, C24, C24CF


def run_full(inst, method, seed, pseed, ticks, outdir, extra_env=None, stderr_file=None, env_override=None):
    outdir = os.path.abspath(outdir); os.makedirs(outdir, exist_ok=True)
    j = dict(map=inst, method=method, seed=seed, pseed=pseed, env=METHODS[method] if env_override is None else env_override,
             mapfile=INST[inst][0], team=INST[inst][1], ticks=ticks)
    from pathlib import Path
    d = Path(outdir)
    prob = r10.make_custom(j, d)
    env = dict(os.environ); env.update(r10.R.COMMON_ENV); env.update(j['env']); env['ROBOT_PLANNER_SEED'] = str(pseed)
    if extra_env: env.update(extra_env)
    out = f'out_{inst}_{method}_{seed}_{pseed}_{ticks}.json'
    cmd = [BIN, '-i', prob.name, '-o', out, '-s', str(ticks), '-a', '10', '-n', '1000', '-t', '150',
           '-x', '100', '-p', '30000', '-c', '1', '-d', '3']
    t0 = time.time()
    with open(stderr_file or os.devnull, 'w') as ef:
        subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=ef)
    return str(d / out), time.time() - t0


if __name__ == '__main__':
    inst, method, seed, pseed, ticks, outdir = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    f, s = run_full(inst, method, seed, pseed, ticks, outdir)
    print(f, round(s, 1))
