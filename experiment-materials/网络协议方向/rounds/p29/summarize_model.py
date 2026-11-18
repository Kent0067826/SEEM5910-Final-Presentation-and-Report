# 协议第 29 轮：汇总 model_measure.json（打印表格 + 写 model_summary.json）。用法：python summarize_model.py model_measure.json model_summary.json
import json, sys, collections
rows = json.load(open(sys.argv[1], encoding='utf8'))
BANDS = ['门口1-3步', '近处4-8步', '中间9-15步', '远处16步以上']
out = []
print(f"{'实例':12s} {'宽':>2s} {'过门':>5s} {'门忙%':>6s} {'每次占门拍':>8s} {'批长':>5s} {'有货%':>6s} {'直来%':>6s} {'侧来%':>6s} {'直来门口拍':>8s} {'侧来门口拍':>8s} {'侧来转身拍':>8s}")
for r in rows:
    print(f"{r['inst']:12s} {r['door_width']:2d} {r['passes_busiest']:5d} {r['door_busy']*100:6.1f} {r['occ_mean']:8.1f} {r['batch_mean']:5.1f} "
          f"{r['goodput'].get('有货', 0)*100:6.1f} {r['side'].get('直着来', 0)*100:6.1f} {r['side'].get('从侧面来', 0)*100:6.1f} "
          f"{r['side_apron'].get('直着来', 0):8.1f} {r['side_apron'].get('从侧面来', 0):8.1f} {r['side_turn'].get('从侧面来', 0):8.1f}")
print()
# 等待按（距离带, 等的车是谁, 挡它的是谁）汇总：占全部车·拍的比例，17 图按图平均
agg = collections.defaultdict(float); aggt = collections.defaultdict(float)
for r in rows:
    tot = r['robots'] * r['T']
    for k, v in r['waits'].items(): agg[k] += v / tot / len(rows)
    for k, v in r['ticks'].items(): aggt[k] += v / tot / len(rows)
print('门附近的等待（占全部车·拍 %，17 图平均）：')
for bd in BANDS[:3]:
    sub = {k: v for k, v in agg.items() if k.startswith(bd + '|')}
    print(f'  {bd}: 合计 {sum(sub.values())*100:.2f}%')
    by_rel = collections.defaultdict(float)
    for k, v in sub.items(): by_rel[k.split('|')[1]] += v
    for rl, v in sorted(by_rel.items(), key=lambda x: -x[1]):
        bl = {k.split('|')[2]: vv for k, vv in sub.items() if k.split('|')[1] == rl}
        print(f'    等的是{rl} {v*100:.2f}%  挡它的: ' + '，'.join(f'{b} {x*100:.2f}' for b, x in sorted(bl.items(), key=lambda x: -x[1])))
# 区域面积、没任务的车停在哪
print('\n各距离带：面积占比 / 没任务的车·拍占比（17 图平均）')
for bd in ['门格'] + BANDS:
    a = sum(r['area'].get(bd, 0) / sum(r['area'].values()) for r in rows) / len(rows)
    idl = sum(r['idle_band'].get(bd, 0) / max(1, sum(r['idle_band'].values())) for r in rows) / len(rows)
    print(f'  {bd:10s} 面积 {a*100:5.1f}%  没任务车 {idl*100:5.1f}%')
# 过门车每次过门在各距离带花的拍数（17 图平均）
print('\n去最忙门的车，每次过门前（同一任务内，最多 150 拍）在各距离带花的拍数（17 图平均）')
for bd in BANDS:
    st = collections.defaultdict(float)
    for r in rows:
        for s, v in r['per_cross_band'].get(bd, {}).items(): st[s] += v / len(rows)
    print(f'  {bd:10s} ' + '  '.join(f'{s} {v:.1f}' for s, v in sorted(st.items())))
# 房间图
print('\n房间图：')
for r in rows:
    S = r['structure']
    print(f"  {r['inst']:12s} 房间 {S['rooms']:2d} 门 {S['doors']:2d} 宽度 {S['widths']} 独立环 {S['cyclomatic']:2d} 桥 {len(S['bridges']):2d} 最忙门是桥 {r['busiest_is_bridge']} 最忙门占全部过门 {r['passes_share']*100:.1f}%")
# 利特尔定律
print('\n车 = 窗口：W（有任务的车，平均）、λ（每拍完成）、周期 = W/λ')
for r in rows:
    L = r['little']; print(f"  {r['inst']:12s} 车 {L['robots']:3d} W {L['W']:6.1f}（{L['W']/L['robots']*100:4.1f}%） λ {L['lam']:.3f} 周期 {L['cycle']:6.1f} 拍")
s = dict(waits_mean=agg, ticks_mean=aggt)
json.dump(s, open(sys.argv[2], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
