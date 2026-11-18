# 协议第 73 轮 Q-2：看门狗放行后 R 拍内同一车又被放行（再卡）的车·拍（定义见 先量_Q2_恢复计时_事先写定.md）
# 用法：python -I -B measure_q2.py 完整输出目录 输出.json
import json, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p35')); sys.path.insert(0, str(R / 'rounds' / 'p39'))
from diag_collapse import sim
from measure_idle_block import task_series
K = 300; RR = 300

def one(f):
    inst = Path(f).stem.split('_LCAPWD')[0]
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    rel = re = 0; gaps = []
    for i in range(N):
        P = sim(o, i)[0]; S = task_series(o['actualSchedule'][i], T)
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        s = 0; fired = False; last_move = None   # last_move: 上一次放行后第一次挪动的拍
        pending = False
        for t in range(1, T):
            if P[t] != P[t-1]:
                if fired: pending = True; last_move = t
                s = t; fired = False
            if not fired and t - s >= K and S[t] >= 0 and not dl[t]:
                fired = True; rel += 1
                if pending and last_move is not None:
                    gaps.append(s - last_move)
                    if s - last_move < RR: re += 1
                pending = False
    return dict(inst=inst, completed=o['numTaskFinished'], N=N, T=T, releases=rel, restuck=re,
                restuck_share=re * K / (N * T), release_share=rel * K / (N * T), gaps_lt_RR=sum(g < RR for g in gaps), gaps=len(gaps))

if __name__ == '__main__':
    fs = sorted(str(f) for f in Path(sys.argv[1]).glob('*_LCAPWD_*.json'))
    with ProcessPoolExecutor(6) as ex: res = list(ex.map(one, fs))
    avg = {k: sum(r[k] for r in res) / len(res) for k in ('restuck_share', 'release_share')}
    tot_rel = sum(r['releases'] for r in res); tot_re = sum(r['restuck'] for r in res)
    Path(sys.argv[2]).write_text(json.dumps(dict(K=K, R=RR, mean_17=avg, releases=tot_rel, restuck=tot_re, skip=avg['restuck_share'] < 0.005, per_inst=res), ensure_ascii=False, indent=1), encoding='utf8')
    for r in res: print(r['inst'].ljust(12), r['completed'], r['releases'], r['restuck'], round(100 * r['restuck_share'], 3), round(100 * r['release_share'], 3))
    print('17 图平均 再卡%', round(100 * avg['restuck_share'], 3), '放行%', round(100 * avg['release_share'], 3), '放行', tot_rel, '再卡', tot_re, '→', '跳过' if avg['restuck_share'] < 0.005 else '不跳过')
