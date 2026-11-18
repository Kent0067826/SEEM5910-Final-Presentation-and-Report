# 把 run_dev.py --compare 写出的 json 变成 Markdown 表格。用法：python compare_table.py 对比.json [方法名]
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8')); name = sys.argv[2] if len(sys.argv) > 2 else '新'
print('| 实例 | LCAP | %s | 变化 | 95%% 区间 | 赢/10 |' % name); print('|---|---|---|---|---|---|')
for r in d['per_inst']:
    print('| %s | %.1f | %.1f | %+.2f%% | [%+.2f, %+.2f] | %d |' % (r['inst'], r['base'], r['new'], 100 * r['mean'], 100 * r['lo'], 100 * r['hi'], r['wins']))
print({k: v for k, v in d.items() if k != 'per_inst'})
