# 第 74 轮：各单项、组合 C3/C4 相对 LCAPWD 的每实例变化，和“单项相加预测”比（可加性，描述用）
# 用法：python -I -B additivity.py 输出.json   （在 rounds/p74 下运行；本轮输出在 ~/robotnet-lab/work/p74，复制到 dev_*.jsonl）
import json, sys, collections, random
from pathlib import Path
R = Path(__file__).resolve().parents[1]
def load(f, m=None):
    d = collections.defaultdict(dict)
    for l in open(f, encoding='utf8'):
        r = json.loads(l)
        if m and r['method'] != m: continue
        d[r['map']][(r['seed'], r['pseed'])] = r['completed']
    return d
base = load(R / 'baseline_v2_LCAPWD/dev_p103_104.jsonl', 'LCAPWD')
src = {'RFD': R / 'p56/dev_A.jsonl', 'S3': R / 'p62/dev_A.jsonl', 'Q5': R / 'p73/dev_tc.jsonl',
       'PICK': Path('dev_pick.jsonl'), 'C3': Path('dev_c3.jsonl'), 'C4': Path('dev_c4.jsonl')}
D = {k: load(f) for k, f in src.items()}
insts = sorted(base)
def gain(d, i):
    ks = sorted(set(base[i]) & set(d[i]))          # 同 run_dev.py --compare：每对（种子, 规划种子）的变化取平均
    return 100 * sum(d[i][k] / base[i][k] - 1 for k in ks) / len(ks)
def boot(v, n=4000):
    random.seed(1); m = sorted(sum(random.choice(v) for _ in v) / len(v) for _ in range(n)); return m[int(.025 * n)], m[int(.975 * n)]
per = {i: {k: gain(D[k], i) for k in D} for i in insts}
for i in insts:
    per[i]['sum3'] = per[i]['RFD'] + per[i]['S3'] + per[i]['Q5']; per[i]['sum4'] = per[i]['sum3'] + per[i]['PICK']
keys = ['RFD', 'S3', 'Q5', 'PICK', 'sum3', 'C3', 'sum4', 'C4']
mean = {k: sum(per[i][k] for i in insts) / len(insts) for k in keys}
ci = {k: boot([per[i][k] for i in insts]) for k in ('PICK', 'C3', 'C4')}
worst = {k: min((per[i][k], i) for i in insts) for k in ('PICK', 'C3', 'C4')}
verdict = {k: dict(mean=mean[k], ci=ci[k], worst=worst[k], passed=mean[k] > 0 and worst[k][0] >= -3) for k in ('PICK', 'C3', 'C4')}
add = dict(C3_vs_sum3=mean['C3'] / mean['sum3'] if mean['sum3'] else None, C4_vs_sum4=mean['C4'] / mean['sum4'] if mean['sum4'] else None,
           C4_ge_best_single=mean['C4'] >= max(mean[k] for k in ('RFD', 'S3', 'Q5', 'PICK')))
json.dump(dict(mean=mean, verdict=verdict, additivity=add, per_inst=per), open(sys.argv[1], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('实例'.ljust(12), ' '.join(k.rjust(7) for k in keys))
for i in insts: print(i.ljust(12), ' '.join(f'{per[i][k]:+7.2f}' for k in keys))
print('平均'.ljust(12), ' '.join(f'{mean[k]:+7.2f}' for k in keys))
for k, v in verdict.items(): print(k, f"{v['mean']:+.2f}% [{v['ci'][0]:+.2f}, {v['ci'][1]:+.2f}] 最差 {v['worst'][1]} {v['worst'][0]:+.2f}%", '过开发' if v['passed'] else '没过')
print('可加性', add)
