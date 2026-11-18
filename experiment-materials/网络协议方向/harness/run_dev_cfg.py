# 协议第2轮：run_dev.py 的副本，唯一改动是实例表可用环境变量 LCAP_CFG 指定（默认仍是 lcap_env17.json）。
"""网络协议方向：本机（Windows + 便携 Cygwin）实验运行器。

和云端的 r10.run_batch 做同一件事：同一个题目模板只改故障种子，跑 5000 拍，每次一行 jsonl；已跑完的行自动跳过（可续跑）。
基线 = LCAP（lcap_env17.json，由仓库 r66_common.lcap_env 导出，与第 75 轮协议相同的 17 个开发实例）。

用法（在任何目录）：
  python run_dev.py --prog ..\\bin\\lifelong-v46a.exe --method LCAP --out ..\\rounds\\r76\\dev.jsonl [--extra KEY=VAL ...]
        [--inst room250,room300] [--seeds 9700-9704] [--pseeds 101,102] [--workers 12] [--ticks 5000]
  python run_dev.py --compare ..\\rounds\\r76\\dev.jsonl --base LCAP --new XXX     # 按实例算配对平均变化
"""
import argparse, json, os, subprocess, sys, time, hashlib, threading, shutil, math, random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
TOOLCHAIN = Path(os.environ.get('LORR_TOOLCHAIN', HERE.parent.parent / 'work' / 'lorr-toolchain' / 'portable'))
WORK = Path(os.environ.get('ROBOTNET_WORK', Path.home() / 'robotnet-lab' / 'work'))   # 临时目录放在同步盘外面
CFG = json.loads((HERE / os.environ.get('LCAP_CFG', 'lcap_env17.json')).read_text(encoding='utf8'))
COMMON_ENV = CFG.pop('_COMMON_ENV')
I17 = list(CFG)
OFFICIAL = ['room200', 'room250', 'room300']
_lock = threading.Lock()


def make_problem(inst, seed, d):
    f = DATA / CFG[inst]['mapfile']; tpl = json.loads(f.read_text(encoding='utf8'))
    for k in ('mapFile', 'agentFile', 'taskFile'):
        tpl[k] = os.path.relpath(f.parent / tpl[k], d).replace(os.sep, '/')
    tpl['delayConfig']['seed'] = seed
    tpl['teamSize'] = CFG[inst]['team']
    p = d / 'prob.json'; p.write_text(json.dumps(tpl)); return p


def key(r): return f"{r['map']}|{r['method']}|{r['seed']}|{r['pseed']}|{r['ticks']}"


def run_job(j, keep_full=None):
    tag = hashlib.md5(key(j).encode()).hexdigest()[:10]
    d = WORK / f'job_{tag}'; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
    prob = make_problem(j['map'], j['seed'], d)
    env = dict(os.environ); env.update(COMMON_ENV); env.update(CFG[j['map']]['env']); env.update(j['extra'])
    env['ROBOT_PLANNER_SEED'] = str(j['pseed'])
    env['PATH'] = str(TOOLCHAIN / 'bin') + os.pathsep + env.get('PATH', '')
    cmd = [str(j['prog']), '-i', prob.name, '-o', 'out.json', '-s', str(j['ticks']), '-a', '10', '-n', '1000', '-t', '150',
           '-x', '100', '-p', '30000', '-c', '1' if keep_full else '3', '-d', '3']
    t0 = time.time(); p = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors='replace',
                                    creationflags=getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0))   # 2026-11-02：低于正常优先级，不拖慢用户的电脑
    row = dict(map=j['map'], method=j['method'], seed=j['seed'], pseed=j['pseed'], ticks=j['ticks'], sec=round(time.time() - t0, 1))
    try:
        o = json.loads((d / 'out.json').read_text())
        row.update(completed=o['numTaskFinished'], plannerErrors=o.get('numPlannerErrors'), errors=len(o.get('errors', [])),
                   scheduleErrors=o.get('numScheduleErrors'))
        if keep_full:
            Path(keep_full).mkdir(parents=True, exist_ok=True)
            shutil.copy(d / 'out.json', Path(keep_full) / f"{j['map']}_{j['method']}_{j['seed']}_{j['pseed']}.json")
    except Exception as e:
        row['error'] = (p.stderr or '')[-400:] + repr(e)
    row['stderr_tail'] = (p.stderr or '')[-300:]
    shutil.rmtree(d, ignore_errors=True)
    return row


def run_batch(a):
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    extra = dict(kv.split('=', 1) for kv in (a.extra or []))
    s0, s1 = map(int, a.seeds.split('-'))
    insts = a.inst.split(',') if a.inst else I17
    jobs = [dict(map=k, method=a.method, seed=s, pseed=int(ps), ticks=a.ticks, prog=Path(a.prog).resolve(), extra=extra)
            for k in insts for s in range(s0, s1 + 1) for ps in a.pseeds.split(',')]
    done = set()
    if out.exists():
        done = {key(json.loads(l)) for l in out.read_text(encoding='utf8').splitlines() if l.strip() and 'completed' in json.loads(l)}
    todo = [j for j in jobs if key(j) not in done]
    print(f'{len(jobs)} jobs, {len(todo)} to run, workers={a.workers}', flush=True)
    jobs_sorted = sorted(todo, key=lambda j: -CFG[j['map']]['team'])   # 大的先跑
    n = 0
    def go(j):
        r = run_job(j, a.full)
        with _lock:
            with open(out, 'a', encoding='utf8') as fh: fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        return r
    with ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(go, jobs_sorted):
            n += 1
            bad = r.get('error') or r.get('errors') or r.get('plannerErrors')
            if n % 10 == 0 or bad: print(n, r['map'], r['method'], r.get('completed'), r['sec'], 'BAD' if bad else '', flush=True)


def compare(a):
    rows = [json.loads(l) for f in a.compare.split(',') for l in Path(f).read_text(encoding='utf8').splitlines() if l.strip()]
    rows = [r for r in rows if 'completed' in r]
    by = {}
    for r in rows: by[(r['map'], r['method'], r['seed'], r['pseed'])] = r['completed']
    insts = sorted({r['map'] for r in rows}, key=lambda k: (k not in OFFICIAL, k))
    res = []; allpairs = []
    print(f"{'实例':<12}{a.base:>9}{a.new:>9}{'变化':>9}   95%区间            赢/对")
    for k in insts:
        pr = [(by[(k, a.base, s, p)], by[(k, a.new, s, p)]) for (kk, m, s, p) in by if kk == k and m == a.base and (k, a.new, s, p) in by]
        if not pr: continue
        d = [(y - x) / x for x, y in pr]; m = sum(d) / len(d)
        sd = (sum((v - m) ** 2 for v in d) / (len(d) - 1)) ** .5 if len(d) > 1 else 0; h = 2.262 * sd / len(d) ** .5 if len(d) == 10 else 1.96 * sd / max(1, len(d)) ** .5
        mb = sum(x for x, _ in pr) / len(pr); mn = sum(y for _, y in pr) / len(pr)
        win = sum(y > x for x, y in pr)
        res.append(dict(inst=k, n=len(pr), base=mb, new=mn, mean=m, lo=m - h, hi=m + h, wins=win)); allpairs.append(m)
        print(f'{k:<12}{mb:>9.1f}{mn:>9.1f}{m*100:>+8.2f}%  [{(m-h)*100:+.2f}, {(m+h)*100:+.2f}]   {win}/{len(pr)}')
    if allpairs:
        M = sum(allpairs) / len(allpairs)
        # 实例层面的 bootstrap 区间（每个实例等权）
        random.seed(1); bs = sorted(sum(random.choice(allpairs) for _ in allpairs) / len(allpairs) for _ in range(4000))
        print(f'按实例平均 {M*100:+.2f}%  bootstrap 95% [{bs[100]*100:+.2f}, {bs[3899]*100:+.2f}]  最差实例 {min(allpairs)*100:+.2f}%  ({len(allpairs)} 个实例)')
        if a.json: Path(a.json).write_text(json.dumps(dict(per_inst=res, mean=M, ci=[bs[100], bs[3899]], worst=min(allpairs)), ensure_ascii=False, indent=1), encoding='utf8')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--prog'); ap.add_argument('--method'); ap.add_argument('--out'); ap.add_argument('--extra', nargs='*')
    ap.add_argument('--inst'); ap.add_argument('--seeds', default='9700-9704'); ap.add_argument('--pseeds', default='101,102')
    ap.add_argument('--workers', type=int, default=12); ap.add_argument('--ticks', type=int, default=5000)
    ap.add_argument('--full', help='保存完整输出（-c 1）到这个目录')
    ap.add_argument('--compare'); ap.add_argument('--base', default='LCAP'); ap.add_argument('--new'); ap.add_argument('--json')
    a = ap.parse_args()
    compare(a) if a.compare else run_batch(a)
