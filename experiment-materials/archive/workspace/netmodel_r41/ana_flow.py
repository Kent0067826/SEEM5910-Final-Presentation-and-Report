"""第 3 步汇总：每个割的流量份额 f（每完成一单穿越几次），任务文件 vs 均匀假设 vs 回放实测。"""
import json, sys, collections, statistics
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG, flow
from batch_measure import INST, mapfile
rows = [json.loads(l) for l in open('/home/claude/r40/batch/rows.jsonl')]
out = []
for inst in ['room200', 'room250', 'room300', 'roomT_199', 'roomQ_254', 'roomAD_189', 'roomP_254', 'roomS_247', 'roomBA_254', 'roomBF_240', 'roomCD_194']:
    m = mapfile(inst); g = RG.analyse(m); lab = flow.room_lookup(m)
    tf, M, ntask = flow.task_flow(INST[inst][0], g, lab)
    rep = collections.defaultdict(lambda: collections.defaultdict(list))
    for meth in ('C24CF', 'N2F'):
        for r in rows:
            if r['inst'] != inst or r['method'] != meth: continue
            res, done = flow.replay_flow(r, f"/home/claude/r40/batch/replays/{inst}_{meth}_{r['seed']}_{r['pseed']}.json.gz", g, lab)
            for i, x in enumerate(res):
                rep[(meth, i)]['total'].append(x['total'])
                for k in ('第1段', '第2段', '空闲'): rep[(meth, i)][k].append(x['per_task'].get(k, 0))
    for i, x in enumerate(tf):
        e = dict(inst=inst, **x)
        for meth in ('C24CF', 'N2F'):
            d = rep[(meth, i)]
            e[meth] = {k: statistics.mean(v) for k, v in d.items()}
        out.append(e)
    print(inst, '任务数', ntask, '割数', len(tf), flush=True)
json.dump(out, open('/home/claude/r40/batch/flow.json', 'w'), ensure_ascii=False, indent=1)
for e in out:
    if e['inst'] in ('room250',) or e['small_frac'] > 0.15:
        print(f"{e['inst']:11s} {e['kind']} {e['doors']} 小侧{e['small_frac']:.2f} | 第2段 任务文件{e['leg2_task']:.3f} 均匀{e['leg2_uniform']:.3f} | 实测 C24CF 合计{e['C24CF']['total']:.3f}（1段{e['C24CF']['第1段']:.3f} 2段{e['C24CF']['第2段']:.3f} 空{e['C24CF']['空闲']:.3f}） N2F 合计{e['N2F']['total']:.3f}（1段{e['N2F']['第1段']:.3f}）")
