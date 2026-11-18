# 第 78 轮：给 measure_d1.json 里选中的门写门口区清单（每行 "行 列 离门步数"，门格 0，门口区 1–2）。
# 用法：python -I -B voq_zone_p78.py 门清单目录 measure_d1.json 输出目录
import json, sys
from pathlib import Path
from collections import deque
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
import ipfix_account as A
ld, mj, od = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')), Path(sys.argv[3])
APR = 2
od.mkdir(parents=True, exist_ok=True)
for m in mj['maps']:
    inst = m['inst']; picked = {r['door'] for r in m['rows'] if r['pick']}
    lines = []
    if picked:
        h, w, free = A.load_map(inst); dlab, nd, rlab, apron3, F = A.doors_rooms(h, w, free)
        real = {tuple(map(int, l.split())) for l in (ld / f'{inst}.txt').read_text().split('\n') if l.strip()}
        gid = {v: dlab[v] for v in real if v in dlab}
        near = {v: (0, g) for v, g in gid.items()}; q = deque(gid)
        while q:   # 和 measure_d1.py 同一个 BFS：门口区归最近的那扇门
            v = q.popleft(); d, g = near[v]
            if d >= APR: continue
            a, b = v
            for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                if F(*u) and u not in near and u not in dlab: near[u] = (d + 1, g); q.append(u)
        lines = [f'{v[0]} {v[1]} {d}' for v, (d, g) in sorted(near.items()) if g in picked]
    (od / f'{inst}.txt').write_text('\n'.join(lines) + ('\n' if lines else ''))
    print(inst, len(picked), len(lines))
