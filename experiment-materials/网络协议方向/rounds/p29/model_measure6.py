# 协议第 29 轮补充：按“离最近门格几步”逐步看等待有多密（每格每拍有几台有任务的车在等），用来定“门路由器”该划多大。
# 只读第 27 轮完整轨迹，不跑新运行。全部车、全部拍。距离 0 = 门格本身。
# 用法：python -I -B model_measure6.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ipfix_account as A
from model_measure import sim2
from model_measure2 import bfs
DMAX = 12


def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    dist = bfs(F, list(dlab))
    area = collections.Counter(min(dist.get((r, c), 99), DMAX) for r in range(h) for c in range(w) if free[r][c])
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    wait = collections.Counter(); turn = collections.Counter(); move = collections.Counter()
    for i in range(N):
        acts, pos = sim2(o, i); acts = (acts + ['W'] * T)[:T]; pos = (pos + [pos[-1]] * T)[:T]
        sched = [(int(x.split(':')[0]), int(x.split(':')[1])) for x in o['actualSchedule'][i].split(',') if x]
        cur = [-1] * T; j = 0
        for t in range(T):
            while j + 1 < len(sched) and sched[j + 1][0] <= t: j += 1
            cur[t] = sched[j][1] if sched and sched[0][0] <= t else -1
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        for t in range(T):
            if dl[t] or cur[t] < 0: continue
            d = min(dist.get(pos[t], 99), DMAX)
            if acts[t] == 'W': wait[d] += 1
            elif acts[t] in 'RC': turn[d] += 1
            else: move[d] += 1
    return dict(inst=inst, T=T, area={d: area[d] for d in range(DMAX + 1)}, wait={d: wait[d] for d in range(DMAX + 1)},
                turn={d: turn[d] for d in range(DMAX + 1)}, move={d: move[d] for d in range(DMAX + 1)})


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')): rows.append(one(fp.name.split('_LCAP_')[0], fp))
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    n = len(rows); lines = ['离门步数  面积占比  每格每千拍等待  每格每千拍转身  等÷前进']
    for k in range(DMAX + 1):
        a = sum(r['area'][k] / sum(r['area'].values()) for r in rows) / n
        wd = sum(r['wait'][k] / max(1, r['area'][k]) / r['T'] for r in rows) / n * 1000
        td = sum(r['turn'][k] / max(1, r['area'][k]) / r['T'] for r in rows) / n * 1000
        rw = sum(r['wait'][k] for r in rows) / max(1, sum(r['move'][k] for r in rows))
        lines.append(f"{k if k < DMAX else str(DMAX)+'+':>6}  {a*100:7.1f}%  {wd:12.1f}  {td:12.1f}  {rw:8.2f}")
    open(outp.replace('.json', '_summary.txt'), 'w', encoding='utf8').write('\n'.join(lines))
