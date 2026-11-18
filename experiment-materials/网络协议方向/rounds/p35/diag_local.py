# 协议第 35 轮：对峙车周围 5 格的局部图（@=车，D=门格，.=空，#=墙）和每台车的朝向、是否在故障中、有没有任务。
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE))
import ipfix_account as A
from diag_collapse import sim
f, r0, c0, t = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
inst = Path(f).stem.split('_LCAP')[0].split('_PICK')[0]
h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
o = json.loads(Path(f).read_text()); N = len(o['start'])
P = [sim(o, i) for i in range(N)]; at = {P[i][0][t]: i for i in range(N)}
for r in range(r0 - 3, r0 + 4):
    print('%3d ' % r + ' '.join(('%3d' % at[(r, c)] if (r, c) in at else ('  D' if (r, c) in dlab else ('  .' if F(r, c) else '  #'))) for c in range(c0 - 4, c0 + 5)))
print('cols', c0 - 4, '..', c0 + 4)
for v, i in sorted(at.items()):
    if abs(v[0] - r0) <= 3 and abs(v[1] - c0) <= 4:
        dl = any(a <= t <= b for a, b in o['delayIntervals'][i]) if o['delayIntervals'][i] else False
        print(i, v, 'ESWN'[P[i][1][t]], 'delayed' if dl else '', 'moved_last50' if len(set(P[i][0][t-50:t+1])) > 1 else 'still50')
