# 协议第 35 轮：找“迎面对峙”——两台车相邻、互相朝着对方、都不动。记每一对从哪拍开始、到哪拍结束、在哪、离门多近、离分道门格多远。
# 用法：python -I -B diag_deadlock.py 完整输出目录 输出.json [最短持续拍数=100]
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim

def one(f, pickdir, LMIN):
    name = Path(f).stem; inst = name.split('_LCAP')[0].split('_PICK')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    pick = set()
    pf = Path(pickdir) / f'{inst}.txt'
    if pf.exists():
        for l in pf.read_text().split('\n'):
            if l.strip(): a, b = map(int, l.split()); pick.add((a, b))
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    P = [sim(o, i) for i in range(N)]
    active = {}; out = []
    for t in range(T):
        at = {P[i][0][t]: i for i in range(N)}; cur = set()
        for i in range(N):
            (r, c), d = P[i][0][t], P[i][1][t]
            j = at.get((r + A.MV[d][0], c + A.MV[d][1]))
            if j is not None and j > i:
                (r2, c2), d2 = P[j][0][t], P[j][1][t]
                if (r2 + A.MV[d2][0], c2 + A.MV[d2][1]) == (r, c) and t > 0 and P[i][0][t-1] == (r, c) and P[j][0][t-1] == (r2, c2):
                    cur.add((i, j))
        for k in cur:
            active.setdefault(k, t)
        for k in list(active):
            if k not in cur:
                if t - active[k] >= LMIN: out.append((k, active[k], t))
                del active[k]
    for k, t0 in active.items():
        if T - t0 >= LMIN: out.append((k, t0, T))
    res = []
    for (i, j), t0, t1 in sorted(out, key=lambda x: x[1]):
        a, b = P[i][0][t0], P[j][0][t0]
        def kind(v): return 'door' if v in dlab else ('apron' if v in apron else 'room')
        dd = min((abs(a[0]-p)+abs(a[1]-q) for (p, q) in pick), default=None)
        res.append(dict(agents=[i, j], t0=t0, t1=t1, dur=t1 - t0, cells=[a, b], kinds=[kind(a), kind(b)], dist_pick=dd, to_end=(t1 == T)))
    return dict(run=name, completed=o['numTaskFinished'], standoffs=res)

if __name__ == '__main__':
    d = Path(sys.argv[1]); LMIN = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    pickdir = HERE.parent / 'p34' / 'pick'
    res = [one(f, pickdir, LMIN) for f in sorted(d.glob('*.json'))]
    Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=list), encoding='utf8')
    for r in res:
        print(r['run'], r['completed'], 'n', len(r['standoffs']), 'lost_ticks', sum(s['dur'] for s in r['standoffs']))
        for s in r['standoffs']: print('   ', s['agents'], s['t0'], s['t1'], s['dur'], s['cells'], s['kinds'], 'dpick', s['dist_pick'], 'END' if s['to_end'] else '')
