# 协议第 29 轮：汇总 model_measure2.json。用法：python summarize_model2.py model_measure2.json model_summary2.json
import json, sys, collections
rows = json.load(open(sys.argv[1], encoding='utf8')); n = len(rows)
print(f"{'实例':12s} {'每任务过门':>8s} {'最忙门种类':>14s} {'门空%':>6s} {'有车在门口3步%':>12s} {'门空且有车%':>10s}  等的时候门在干什么（去这扇门、3步内的等待拍）")
for r in rows:
    k = r['busiest_kind']; ks = f"{k['width']}格{'桥' if k['bridge'] else ''}{'·管' if k['managed'] else '·不管'}绕{k['detour']}"
    m = r['mouth_wait_state']; mt = max(1, sum(m.values()))
    print(f"{r['inst']:12s} {r['cross_per_task']:8.2f} {ks:>14s} {r['door_idle']*100:6.1f} {r['demand_ticks']*100:12.1f} {r['demand_idle_ticks']*100:10.1f}  "
          + '，'.join(f'{s} {v/mt*100:.0f}%' for s, v in sorted(m.items(), key=lambda x: -x[1])))
# 等待（离最忙门 15 步内）按 等的车 × 挡它的车，占全部车·拍
agg = collections.defaultdict(float)
for r in rows:
    for k, v in r['waits'].items(): agg[k] += v / r['robot_ticks'] / n
print('\n离最忙门 15 步内的等待（占全部车·拍 %，17 图平均）')
for bd in ['门口1-3步', '近处4-8步', '中间9-15步']:
    sub = {k: v for k, v in agg.items() if k.startswith(bd + '|')}
    print(f'  {bd}: 合计 {sum(sub.values())*100:.2f}%')
    by = collections.defaultdict(float)
    for k, v in sub.items(): by[k.split('|')[1]] += v
    for rl, v in sorted(by.items(), key=lambda x: -x[1]):
        bl = {k.split('|')[2]: x for k, x in sub.items() if k.split('|')[1] == rl}
        print(f'    等的是{rl} {v*100:.2f}%  挡它的: ' + '，'.join(f'{b} {x*100:.2f}' for b, x in sorted(bl.items(), key=lambda x: -x[1]) if x >= 0.00005))
# 所有门的门口开销
print('\n所有门：每次过门前在门口（3 步内 / 4-8 步）花的拍数，按门的种类（17 图合计后平均到每次过门）')
tot = collections.defaultdict(collections.Counter); nc = collections.Counter(); share = collections.defaultdict(float)
for r in rows:
    for k, v in r['ncross'].items(): nc[k] += v
    for k, v in r['over'].items():
        key, zone = k.split('|')
        for s, x in v.items(): tot[(key, zone)][s] += x; share[(key, zone, s)] += x / r['robot_ticks'] / n
for (key, zone), c in sorted(tot.items()):
    print(f'  {key:8s} {zone:5s} 过门 {nc[key]:6d} 次  每次: ' + '  '.join(f'{s} {c[s]/nc[key]:.1f}' for s in ['前进', '转身', '等', '故障']) + f'  合计 {sum(c.values())/nc[key]:.1f}')
print('\n门口开销占全部车·拍 %（17 图平均）：')
for key in sorted({k[0] for k in share}):
    for zone in ['3步内', '4-8步']:
        v = {s: share[(key, zone, s)] for s in ['前进', '转身', '等', '故障']}
        print(f'  {key:8s} {zone:5s} ' + '  '.join(f'{s} {x*100:.2f}' for s, x in v.items()) + f'  合计 {sum(v.values())*100:.2f}')
print('\n过门次数按门的种类占比（17 图合计）：', {k: f'{v/sum(nc.values())*100:.1f}%' for k, v in nc.items()})
json.dump(dict(waits_mean=agg, over_share={'|'.join(k): v for k, v in share.items()}, ncross=dict(nc)), open(sys.argv[2], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
