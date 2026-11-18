# 协议第 75 轮：第 34 轮挑门规则原样用在确认实例上（只把实例表换成 lcap_env_p75confirm_wd.json）。
# 用法：python -I -B pick_doors_p75.py 完整输出目录 输出.json 清单目录
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27')); sys.path.insert(0, str(HERE.parent / 'p29')); sys.path.insert(0, str(HERE.parent / 'p34'))
import ipfix_account as A
A.CFG = json.loads((A.H / 'lcap_env_p75confirm_wd.json').read_text(encoding='utf8')); A.CFG.pop('_COMMON_ENV')
import pick_doors as P
sys.argv = [sys.argv[0]] + sys.argv[1:]
d, outp, ld = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); ld.mkdir(parents=True, exist_ok=True); res = {}
for f in sorted(d.glob('*_LCAP_9700_101.json')):
    inst = f.name.split('_LCAP_')[0]; r = P.one(inst, f); res[inst] = r
    pk = [x for x in r['doors'] if x['picked']]
    if pk:
        (ld / f'{inst}.txt').write_text(''.join(f'{c[0]} {c[1]}\n' for x in pk for c in x['cells']), encoding='utf8')
    print(f"{inst:12s} 2格门 {r['two_cell_doors']:2d} 前1/3={r['top_n']} 选中 {len(pk)}", flush=True)
json.dump(dict(rule=dict(minor_share=P.MINOR, top_fraction='1/3 向上取整，至少 1'), maps=res), open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
