"""第 40 轮 / 第 1 步测量批次：开发种子上跑完整回放，逐门统计带宽和时延。
只用开发种子（9700-9704，规划种子 101），不碰确认用的种子和留出地图。"""
import sys, os, json, gzip, shutil, time
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/claude/r40')
from runfull import run_full, INST, V
import measure, regiongraph as RG

OUT = '/home/claude/r40/batch'
os.makedirs(OUT + '/replays', exist_ok=True)
for k, n in [('room200', 200), ('room250', 250), ('room300', 300)]:
    INST[k + '_nd'] = (V + f'maps_nodelay/{k}.json', n)

ROOMS = ['room200', 'room250', 'room300', 'roomT_199', 'roomQ_254', 'roomAD_189', 'roomP_254', 'roomS_247', 'roomBA_254',
         'roomBF_240', 'roomCD_194']
JOBS = [(k, m, s, 101, 5000) for k in ROOMS for m in ('C24CF', 'N2F') for s in range(9700, 9705)]
JOBS += [(k + '_nd', m, 9700, p, 5000) for k in ('room200', 'room250', 'room300') for m in ('C24CF', 'N2F') for p in (101, 102)]


def mapfile(inst):
    d = json.load(open(INST[inst][0])); return os.path.normpath(os.path.join(os.path.dirname(INST[inst][0]), d['mapFile']))


def one(job):
    inst, m, s, p, ticks = job
    key = f'{inst}|{m}|{s}|{p}|{ticks}'
    wd = f'/home/claude/r40/work/{inst}_{m}_{s}_{p}'
    f, sec = run_full(inst, m, s, p, ticks, wd)
    G = RG.analyse(mapfile(inst))
    lvl = {d['id']: d['cut_level'] for d in G['doors']}
    o, P, chk, D, cr, bo, T = measure.analyse_run(f, G)
    st = measure.door_stats(D, cr, bo, T)
    for did in st: st[did]['cut_level'] = lvl[did]
    row = dict(key=key, inst=inst, method=m, seed=s, pseed=p, ticks=ticks, completed=o['numTaskFinished'], sec=round(sec, 1),
               check=chk, plannerErrors=o['numPlannerErrors'], doors=st,
               crossings=[[c['agent'], c['door'], c['a'], c['b'], c['t_apron'], c['t_in'], c['t_out'], c['t_assign']] for c in cr])
    with open(f, 'rb') as fi, gzip.open(f'{OUT}/replays/{inst}_{m}_{s}_{p}.json.gz', 'wb') as fo: shutil.copyfileobj(fi, fo)
    shutil.rmtree(wd)
    return row


if __name__ == '__main__':
    rows_f = OUT + '/rows.jsonl'
    done = set()
    if os.path.exists(rows_f):
        for l in open(rows_f): done.add(json.loads(l)['key'])
    todo = [j for j in JOBS if f'{j[0]}|{j[1]}|{j[2]}|{j[3]}|{j[4]}' not in done]
    print(len(JOBS), 'jobs,', len(todo), 'to run', flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as ex:
        for i, r in enumerate(ex.map(one, todo)):
            with open(rows_f, 'a') as fh: fh.write(json.dumps(r) + '\n')
            print(i + 1, r['key'], r['completed'], r['check'], round(time.time() - t0), flush=True)
