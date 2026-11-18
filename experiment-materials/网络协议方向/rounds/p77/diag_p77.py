# 协议第 77 轮诊断：同一局（种子 9700 × 规划 103）基线和 k=2 的完整轨迹，比较 ① 第 27 轮记账的车·拍份额；② 转身按“离真房间门几步”分档的次数。
# 用法：python -I -B diag_p77.py 基线完整目录 新完整目录 门清单目录 输出.json
import json, sys, collections
from pathlib import Path
from collections import deque
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
import ipfix_account as A
db, dn, ld, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
def turn_bins(inst, f):
    h, w, free = A.load_map(inst); F = lambda r, c: 0 <= r < h and 0 <= c < w and free[r][c]
    cells = [tuple(map(int, l.split())) for l in (ld / f'{inst}.txt').read_text().split('\n') if l.strip()]
    dist = {v: 0 for v in cells}; q = deque(cells)
    while q:
        v = q.popleft(); a, b = v
        for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if F(*u) and u not in dist: dist[u] = dist[v] + 1; q.append(u)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']; bins = collections.Counter()
    for i in range(N):
        acts, pos = A.sim(o, i)
        for t in range(T):
            if acts[t] in 'RC':
                d = dist.get(pos[t], 99); bins[min(d, 4)] += 1
    return {str(k): bins[k] for k in range(5)}, o['numTaskFinished']
res = {}
for fb in sorted(db.glob('*.json')):
    inst = fb.name.split('_LCAP_')[0]; fn = next(dn.glob(f'{inst}_*.json'))
    r = {}
    for tag, f in (('base', fb), ('k2', fn)):
        x = A.one(inst, f); tb, done = turn_bins(inst, f)
        r[tag] = dict(completed=done, share={k: round(v * 100, 2) for k, v in x['share'].items()}, turns_by_dist=tb, passes=x['passes'],
                      apron_wait_per_pass=round(x['apron_wait_per_pass'], 2))
    res[inst] = r
    print(inst, json.dumps(r, ensure_ascii=False), flush=True)
json.dump(res, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
