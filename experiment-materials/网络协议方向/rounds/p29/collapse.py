# 协议第 29 轮：基线 LCAP 的“整片堵死局”有多常见、损失多大（无损网络里的死锁）。只读已有运行记录，不跑新运行。
# 堵死局：完成数低于同一实例全部 LCAP 运行中位数的 70%（沿用第 18 轮的定义）。损失 = Σ(中位数 − 完成数)（只算堵死局）÷ Σ 完成数。
# 用法：python collapse.py 输出.json 记录1.jsonl [记录2.jsonl ...]
import json, sys, statistics, collections
out = sys.argv[1]; runs = collections.defaultdict(list)
for f in sys.argv[2:]:
    for l in open(f, encoding='utf8'):
        r = json.loads(l)
        if r['method'] == 'LCAP': runs[(f.split('/')[-2] if '/' in f else f, r['map'])].append(r['completed'])
rows = []; tot = 0; lost = 0; ncol = 0; nrun = 0
for (src, m), xs in sorted(runs.items()):
    med = statistics.median(xs); col = [x for x in xs if x < 0.7 * med]
    l = sum(med - x for x in col); tot += sum(xs); lost += l; ncol += len(col); nrun += len(xs)
    rows.append(dict(src=src, map=m, runs=len(xs), median=med, collapsed=len(col), worst=min(xs), lost_frac=l / sum(xs)))
for r in rows:
    if r['collapsed']: print(f"{r['src']:10s} {r['map']:12s} 运行 {r['runs']:3d} 中位 {r['median']:7.1f} 堵死 {r['collapsed']} 最差 {r['worst']} 损失 {r['lost_frac']*100:.2f}%")
print(f'合计：{nrun} 局里堵死 {ncol} 局（{ncol/nrun*100:.2f}%），损失占总完成数 {lost/tot*100:.2f}%')
json.dump(dict(rows=rows, runs=nrun, collapsed=ncol, lost_frac=lost / tot), open(out, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
