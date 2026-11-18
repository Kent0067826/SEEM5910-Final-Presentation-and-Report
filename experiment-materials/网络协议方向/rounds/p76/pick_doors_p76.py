# 协议第 76 轮（C-3）：第 34 轮挑门规则 + “门两侧都是真房间”：门格四邻接到的房间区里，至少两个、且全部 >= MIN_ROOM 格。
# 房间区用第 27 轮 ipfix_account.doors_rooms 的房间标号（去掉门格后 4 连通的空地）。迷宫的“房间”是 4 格路口，随机图是 2–20 格小角落，房间图 >= 33 格。
# 用法：python -I -B pick_doors_p76.py 实例表.json 完整输出目录 输出.json 清单目录
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE.parent / 'p29')); sys.path.insert(0, str(HERE.parent / 'p34'))
import ipfix_account as A
MIN_ROOM = 25   # 5×5，事先写定
cfg, d, outp, ld = sys.argv[1], Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
A.CFG = json.loads((A.H / cfg).read_text(encoding='utf8')); A.CFG.pop('_COMMON_ENV', None)
import pick_doors as P
ld.mkdir(parents=True, exist_ok=True); res = {}
for f in sorted(d.glob('*_LCAP_9700_101.json')):
    inst = f.name.split('_LCAP_')[0]
    if inst not in A.CFG: continue
    r = P.one(inst, f)
    h, w, free = A.load_map(inst); _, _, rlab, _, _ = A.doors_rooms(h, w, free); size = collections.Counter(rlab.values())
    for x in r['doors']:
        adj = {rlab[u] for (a, b) in map(tuple, x['cells']) for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if u in rlab}
        x['side_rooms'] = sorted(size[k] for k in adj)
        x['picked34'] = x['picked']
        x['picked'] = x['picked34'] and len(adj) >= 2 and min(size[k] for k in adj) >= MIN_ROOM
    r['picked'] = [x['door'] for x in r['doors'] if x['picked']]; res[inst] = r
    pk = [x for x in r['doors'] if x['picked']]
    if pk:
        (ld / f'{inst}.txt').write_text(''.join(f'{c[0]} {c[1]}\n' for x in pk for c in x['cells']), encoding='utf8')
    print(f"{inst:12s} 第34轮规则选 {sum(x['picked34'] for x in r['doors']):2d}  加房间条件后 {len(pk):2d}", flush=True)
json.dump(dict(rule=dict(minor_share=P.MINOR, top_fraction='1/3 向上取整，至少 1', min_room=MIN_ROOM), maps=res), open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
