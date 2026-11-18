"""Analysis of the supplementary comparison (protocol_r52b_baseline.md): every method against the official default (DEF),
and the adjacent steps of the chain, official 8 instances, 20 pairs each; same table code as all earlier rounds (ana.table)."""
import sys, json; sys.path.insert(0, '/home/claude/proj/v10/scripts'); import ana
V = '/home/claude/proj/v10/'
OFF8 = ['room200', 'room250', 'room300', 'maze40', 'maze60', 'random200', 'random300', 'warehouse100']
ROOM = OFF8[:3]; OTHER = OFF8[3:]
R = ana.load(V + 'batches/r52b-baseline/rows.jsonl', ticks=5000)
out = {}; L = ['# 补充对比：官方默认程序 → 冠军任务分配 → 修好执行器 → LCAP（官方 8 实例，种子 11700–11709 × 145、146，5000 步）', '']
def tab(title, methods, insts, base, key):
    t = ana.table(R, methods, insts, base=base); L.extend([f'## {title}', '', ana.fmt(t, insts), ''])
    for r in t: out[f'{key}|{r[0]}|{base}'] = dict(mean=r[2], lo=r[3], hi=r[4], p=r[5])
    return t
tab('相对官方默认程序 DEF（8 个实例）', ['N2', 'N2F', 'LCAP'], OFF8, 'DEF', 'all')
tab('链上相邻两步：N2 对 DEF', ['N2'], OFF8, 'DEF', 'step')
tab('链上相邻两步：N2F 对 N2（修执行器）', ['N2F'], OFF8, 'N2', 'step')
tab('链上相邻两步：LCAP 对 N2F（本文方法）', ['LCAP'], OFF8, 'N2F', 'step')
for g, ins in [('官方房间 3', ROOM), ('官方其他 5', OTHER)]:
    for m, b in [('LCAP', 'DEF'), ('N2F', 'DEF'), ('LCAP', 'N2F')]:
        r = ana.table(R, [m], ins, base=b)[0]; out[f'G|{g}|{m}|{b}'] = dict(mean=r[2], lo=r[3], hi=r[4])
L += ['分组（等权平均 [95% 区间]）：'] + [f"- {g}：" + '；'.join(f"{m} 对 {b} {out[f'G|{g}|{m}|{b}']['mean']:+.1f}% [{out[f'G|{g}|{m}|{b}']['lo']:+.1f}, {out[f'G|{g}|{m}|{b}']['hi']:+.1f}]" for m, b in [('LCAP', 'DEF'), ('N2F', 'DEF'), ('LCAP', 'N2F')]) for g in ['官方房间 3', '官方其他 5']]
RAW = [json.loads(l) for l in open(V + 'batches/r52b-baseline/rows.jsonl')]
err = {m: sum(r.get('plannerErrors') or 0 for r in RAW if r['method'] == m) for m in ['DEF', 'N2', 'N2F', 'LCAP']}; out['plannerErrors'] = err
mean = {m: {k: sum(r['completed'] for r in RAW if r['map'] == k and r['method'] == m) / max(1, sum(1 for r in RAW if r['map'] == k and r['method'] == m)) for k in OFF8} for m in ['DEF', 'N2', 'N2F', 'LCAP']}
out['mean_completed'] = mean
L += ['', '每实例平均完成数：', '| 实例 | DEF | N2 | N2F | LCAP |', '|---|---|---|---|---|'] + [f"| {k} | " + ' | '.join(f'{mean[m][k]:.0f}' for m in ['DEF', 'N2', 'N2F', 'LCAP']) + ' |' for k in OFF8]
L += ['', '模拟器报告的碰撞/非法动作数：' + json.dumps(err), f"运行数：{len(RAW)}"]
open(V + 'analysis_r52b.md', 'w').write('\n'.join(L)); json.dump(out, open(V + 'analysis_r52b.json', 'w'), ensure_ascii=False, indent=1); print('\n'.join(L))
