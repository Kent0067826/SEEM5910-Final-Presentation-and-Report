# 协议第 29 轮（建模研究）第五遍：比较“把什么当路由器”。只读第 27 轮完整轨迹，不跑新运行。
# 把每张图的空地按离最近门格的步数分成三块：门格 + 1–3 步（“门路由器”的核心）、4–8 步（门路由器的排队区）、8 步以外（门到门之间的路段）。
# 对全部车、全部拍（不只去门的车）统计每块地方的面积占比，以及等、转身、故障、前进、没任务各占全部车·拍多少。
# 用来回答：哪一种“路由器”的划法，用最小的地方装下最多的损失（损失越集中，越值得在那里放路由器的功能）。
# 用法：python -I -B model_measure5.py 完整输出目录 输出.json
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ipfix_account as A
from model_measure import sim2
from model_measure2 import bfs


def zone(d):
    return '门格和1-3步' if d <= 3 else ('4-8步' if d <= 8 else '8步以外')


def one(inst, f):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    dist = bfs(F, list(dlab))
    cells = [(r, c) for r in range(h) for c in range(w) if free[r][c]]
    area = collections.Counter(zone(dist.get(v, 99)) for v in cells)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    cnt = collections.Counter()
    for i in range(N):
        acts, pos = sim2(o, i); acts = (acts + ['W'] * T)[:T]; pos = (pos + [pos[-1]] * T)[:T]
        sched = [(int(x.split(':')[0]), int(x.split(':')[1])) for x in o['actualSchedule'][i].split(',') if x]
        cur = [-1] * T; j = 0
        for t in range(T):
            while j + 1 < len(sched) and sched[j + 1][0] <= t: j += 1
            cur[t] = sched[j][1] if sched and sched[0][0] <= t else -1
        dl = [False] * T
        for a, b in o['delayIntervals'][i]:
            for t in range(max(0, a), min(T, b + 1)): dl[t] = True
        for t in range(T):
            z = zone(dist.get(pos[t], 99))
            st = '故障' if dl[t] else ('没任务' if cur[t] < 0 else ('转身' if acts[t] in 'RC' else ('前进' if acts[t] == 'F' else '等')))
            cnt[(z, st)] += 1
    tot = N * T; na = len(cells)
    return dict(inst=inst, area={k: v / na for k, v in area.items()}, share={f'{k[0]}|{k[1]}': v / tot for k, v in cnt.items()},
                completed=o['numTaskFinished'], robots=N, T=T)


if __name__ == '__main__':
    d, outp = Path(sys.argv[1]), sys.argv[2]; rows = []
    for fp in sorted(d.glob('*_LCAP_*.json')):
        rows.append(one(fp.name.split('_LCAP_')[0], fp))
    json.dump(rows, open(outp, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    Z = ['门格和1-3步', '4-8步', '8步以外']; S = ['前进', '转身', '等', '故障', '没任务']; n = len(rows)
    lines = []
    for z in Z:
        a = sum(r['area'].get(z, 0) for r in rows) / n
        sh = {s: sum(r['share'].get(f'{z}|{s}', 0) for r in rows) / n for s in S}
        work = sum(sh[s] for s in ['前进', '转身', '等', '故障'])
        lines.append(f'{z}: 面积 {a*100:.1f}%  有任务的车·拍 {work*100:.1f}%  ' + '  '.join(f'{s} {sh[s]*100:.2f}%' for s in S)
                     + f'  等÷前进 {sh["等"]/max(1e-9, sh["前进"]):.2f}  每 1% 面积装下的等 {sh["等"]/max(1e-9, a):.3f}')
    tw = sum(sum(r['share'].get(f'{z}|等', 0) for z in Z) for r in rows) / n
    lines.append(f'全部“等”占全部车·拍 {tw*100:.2f}%')
    open(outp.replace('.json', '_summary.txt'), 'w', encoding='utf8').write('\n'.join(lines))
