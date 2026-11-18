# 协议第 73 轮 Q-2 补充（事后加，不改判）：看门狗放行里有多少是“假放行”——站满 300 拍，但其中有任务的拍不到 300（多半是空闲站着、刚领到任务）。
# 交换机 PFC 看门狗只在“队列被暂停且里面有包”时计时，空队列不算卡死；我们的看门狗从最后一次挪动起计时，不管有没有任务。
# 用法：python -I -B measure_q2b.py 完整输出目录 输出.json
import json, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27')); sys.path.insert(0, str(R / 'rounds' / 'p35')); sys.path.insert(0, str(R / 'rounds' / 'p39'))
import ipfix_account as A
from diag_collapse import sim
from measure_idle_block import task_series
K = 300

def one(f):
    inst = Path(f).stem.split('_LCAPWD')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    c = dict(rel=0, fake=0, fake_near=0, real=0, real_near=0)
    for i in range(N):
        P = sim(o, i)[0]; S = task_series(o['actualSchedule'][i], T)
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        s = 0; fired = False; wt = 0   # wt：本段里有任务的拍数
        for t in range(1, T):
            if P[t] != P[t-1]: s = t; fired = False; wt = 0
            if S[t] >= 0: wt += 1
            if not fired and t - s >= K and S[t] >= 0 and not dl[t]:
                fired = True; c['rel'] += 1; near = P[t] in dlab or P[t] in apron
                k = 'fake' if wt < K else 'real'; c[k] += 1; c[k + '_near'] += near
    return dict(inst=inst, **c)

if __name__ == '__main__':
    fs = sorted(str(f) for f in Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, fs))
    tot = {k: sum(r[k] for r in res) for k in ('rel', 'fake', 'fake_near', 'real', 'real_near')}
    Path(sys.argv[2]).write_text(json.dumps(dict(K=K, total=tot, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r)
    print('TOTAL', tot)
