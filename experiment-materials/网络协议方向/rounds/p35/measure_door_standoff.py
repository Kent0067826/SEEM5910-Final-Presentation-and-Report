# 协议第 35 轮第二项先量：门口长时间对峙（跳过线见 先量_门口对峙_事先写定.md）。
# 用法：python -I -B measure_door_standoff.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim
from diag_deadlock import one as standoffs

def near_door(v, dlab, F):
    # 离 v 最近的门（BFS ≤ APRON 步），返回门号或 None
    if v in dlab: return dlab[v]
    seen = {v}; fr = [v]
    for _ in range(A.APRON):
        nf = []
        for (a, b) in fr:
            for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                if u in dlab: return dlab[u]
                if F(*u) and u not in seen: seen.add(u); nf.append(u)
        fr = nf
    return None

def one(f):
    name = Path(f).stem; inst = name.split('_LCAP')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    r = standoffs(f, HERE / 'none', 100)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    ds = []
    for s in r['standoffs']:
        a, b = map(tuple, s['cells']); g = near_door(a, dlab, F)
        if g is None: g = near_door(b, dlab, F)
        if g is not None: ds.append(dict(s, door=g))
    # 门口对峙期间那扇门一台都没过的拍数
    passt = collections.defaultdict(list)
    for i in range(N):
        pos, _ = sim(o, i); t = 0
        while t < T:
            v = pos[t]
            if v in dlab:
                g = dlab[v]; t0 = t
                while t < T and pos[t] in dlab and dlab[pos[t]] == g: t += 1
                bb = pos[t0 - 1] if t0 else None; aa = pos[t] if t < T else None
                if bb and aa and bb not in dlab and aa not in dlab and bb != aa: passt[g].append(t0)
                continue
            t += 1
    cover = set(); dead = 0
    for s in ds:
        cover |= set(range(s['t0'], s['t1']))
        ps = sorted(passt[s['door']]); gaps = [s['t0']] + [x for x in ps if s['t0'] < x < s['t1']] + [s['t1']]
        dead += max(gaps[k+1] - gaps[k] for k in range(len(gaps) - 1))   # 对峙期间最长的一段“门没过车”
    return dict(inst=inst, completed=o['numTaskFinished'], standoffs=len(r['standoffs']), door_standoffs=len(ds),
                frac_time=len(cover) / T, longest=max([s['dur'] for s in ds], default=0), door_dead_ticks=dead,
                list=[(s['agents'], s['t0'], s['dur'], s['door'], s['kinds']) for s in ds])

if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*.json'))
    with ProcessPoolExecutor(9) as ex: res = list(ex.map(one, fs))
    Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=list), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], '对峙', r['standoffs'], '门口', r['door_standoffs'], '时间占比 %.1f%%' % (100 * r['frac_time']), '最长', r['longest'], '门停', r['door_dead_ticks'])
    print('平均时间占比 %.2f%%' % (100 * sum(r['frac_time'] for r in res) / len(res)), '最长', max(r['longest'] for r in res))
