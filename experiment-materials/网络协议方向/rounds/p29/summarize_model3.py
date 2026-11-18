# 协议第 29 轮：汇总 model_measure3.json。用法：python summarize_model3.py model_measure3.json model_summary3.json
import json, sys, collections
rows = json.load(open(sys.argv[1], encoding='utf8')); n = len(rows)
idle = collections.defaultdict(collections.Counter); dist = collections.defaultdict(collections.Counter); nc = collections.Counter()
for r in rows:
    for k, v in r['idle_hol'].items(): idle[k].update(v)
    for k, v in r['idle_dist'].items(): dist[k].update({int(a): b for a, b in v.items()})
    for k, v in r['ncross_kind'].items(): nc[k] += v
print('门空着、却有车要过（离门 1–3 步）时，离门最近那台车在干什么（17 图合计）：')
out = {}
for k in sorted(idle):
    c = idle[k]; t = sum(c.values())
    print(f'  {k}：共 {t} 门·拍（每次过门 {t/max(1,nc[k]):.1f} 拍）  最近那台离门 ' + '，'.join(f'{d}步 {dist[k][d]/t*100:.0f}%' for d in sorted(dist[k])))
    for s, v in sorted(c.items(), key=lambda x: -x[1]): print(f'      {s:24s} {v/t*100:5.1f}%')
    out[k] = dict(total=t, per_cross=t / max(1, nc[k]), share={s: v / t for s, v in c.items()}, dist={d: v / t for d, v in dist[k].items()})
print('\n每张图：最忙门（种类）门空着却有车要过时，最近那台车的状态')
for r in rows:
    c = r['idle_hol_busiest']; t = max(1, sum(c.values()))
    print(f"  {r['inst']:12s} {r['busiest_kind']:6s} " + '，'.join(f'{s} {v/t*100:.0f}%' for s, v in sorted(c.items(), key=lambda x: -x[1])[:4]))
print('\n更正后的“有货过门”和载货 / 空车前进（占全部车·拍）：')
for r in rows:
    g = r['goodput_all']; gt = max(1, sum(g.values())); m = r['move_split']
    print(f"  {r['inst']:12s} 有货过门 {g.get('有货', 0)/gt*100:5.1f}%  空车去取货 {g.get('空车去取货', 0)/gt*100:5.1f}%  载货前进 {m.get('载货前进', 0)*100:5.1f}%  空车前进 {m.get('空车前进', 0)*100:5.1f}%  "
          f"每任务过门 {r['hops']['actual']:.2f} 最少 {r['hops']['minimum']:.2f}（多 {(r['hops']['actual']/max(0.01, r['hops']['minimum'])-1)*100:.0f}%）")
mv = {k: sum(r['move_split'].get(k, 0) for r in rows) / n for k in ('载货前进', '空车前进')}
ha = sum(r['hops']['actual'] for r in rows) / n; hm = sum(r['hops']['minimum'] for r in rows) / n
print(f'\n17 图平均：载货前进 {mv["载货前进"]*100:.1f}%  空车前进 {mv["空车前进"]*100:.1f}%  每任务过门 {ha:.2f}，最少 {hm:.2f}')
json.dump(dict(idle=out, move_mean=mv, hops_actual=ha, hops_min=hm), open(sys.argv[2], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
