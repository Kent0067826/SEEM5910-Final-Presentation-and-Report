# 协议第 35 轮：分道门格上的长时间占用（谁、从哪拍到哪拍、朝向、旁边是什么），以及分道门每 250 拍过门数。
# 用法：python -I -B diag_door.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim

def one(f, pickdir):
    name = Path(f).stem; inst = name.split('_LCAP')[0].split('_PICK')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    pick = set()
    for l in (Path(pickdir) / f'{inst}.txt').read_text().split('\n'):
        if l.strip(): a, b = map(int, l.split()); pick.add((a, b))
    pickg = sorted({dlab[v] for v in pick if v in dlab})
    gcells = {g: sorted(v for v in dlab if dlab[v] == g) for g in pickg}
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    P = [sim(o, i) for i in range(N)]
    # 门格 + 两侧 3 步内的格子
    near = {}
    for g, cs in gcells.items():
        s = set(cs); fr = set(cs)
        for _ in range(3):
            fr = {u for (a, b) in fr for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if F(*u)} - s; s |= fr
        near[g] = s
    long_occ = []; passes = collections.defaultdict(lambda: [0] * (T // 250)); wait_near = collections.defaultdict(lambda: [0] * (T // 250))
    for i in range(N):
        pos, dirs = P[i]; t = 0
        while t < T:
            v = pos[t]
            if v in dlab and dlab[v] in gcells:
                g = dlab[v]; t0 = t
                while t < T and pos[t] in dlab and dlab[pos[t]] == g: t += 1
                b = pos[t0 - 1] if t0 else None; a = pos[t] if t < T else None
                if b and a and b not in dlab and a not in dlab and b != a: passes[g][t0 // 250] += 1
                if t - t0 >= 60: long_occ.append(dict(agent=i, door=g, t0=t0, t1=t, cells=sorted(set(pos[t0:t])), dir_end=dirs[t - 1]))
                continue
            t += 1
        for t in range(1, T):
            if pos[t] == pos[t - 1]:
                for g in gcells:
                    if pos[t] in near[g]: wait_near[g][t // 250] += 1
    return dict(run=name, completed=o['numTaskFinished'], pick_doors={g: gcells[g] for g in pickg},
                passes={g: passes[g] for g in pickg}, wait_near={g: wait_near[g] for g in pickg},
                long_occ=sorted(long_occ, key=lambda x: -(x['t1'] - x['t0']))[:15])

if __name__ == '__main__':
    d = Path(sys.argv[1]); pickdir = HERE.parent / 'p34' / 'pick'
    res = [one(f, pickdir) for f in sorted(d.glob('*.json')) if '9700_10' in f.name and 'roomW' in f.name or '9702_104' in f.name and 'room250' in f.name]
    Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf8')
    for r in res:
        print(r['run'], r['completed'])
        for g in r['passes']: print('  door', g, 'passes', r['passes'][g]); print('  door', g, 'waitnear', r['wait_near'][g])
        for x in r['long_occ'][:8]: print('   long', x['agent'], x['door'], x['t0'], x['t1'], x['t1'] - x['t0'], x['cells'], x['dir_end'])
