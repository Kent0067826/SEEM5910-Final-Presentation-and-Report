# 协议第 35 轮：room250 分道局里“死掉”的门：门格位置、和分道门的距离、门格上每 250 拍的占用者。
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim
f, gs = sys.argv[1], [int(x) for x in sys.argv[2].split(',')]
inst = Path(f).stem.split('_LCAP')[0].split('_PICK')[0]
h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
P = [sim(o, i) for i in range(N)]
for g in gs:
    cs = sorted(v for v in dlab if dlab[v] == g); print('door', g, cs)
    for t in list(range(0, 1500, 50)) + [2000, 3000, 4999]:
        occ = [(i, P[i][0][t], 'ESWN'[P[i][1][t]]) for i in range(N) if P[i][0][t] in cs]
        print('  t', t, occ)
# 地图片段
rs = [v[0] for g in gs for v in dlab if dlab[v] == g]; cs_ = [v[1] for g in gs for v in dlab if dlab[v] == g]
r0, r1, c0, c1 = min(rs) - 4, max(rs) + 4, min(cs_) - 6, max(cs_) + 6
at = {P[i][0][int(sys.argv[3])]: i for i in range(N)}
for r in range(r0, r1 + 1):
    print('%3d ' % r + ''.join(('@' if (r, c) in at else ('D' if (r, c) in dlab else ('.' if F(r, c) else '#'))) for c in range(c0, c1 + 1)))
print('cols', c0, c1)
