# 协议第 35 轮（项目 110）：M-3c 分道后塌局诊断（只诊断，不改代码）。
# 用法：python -I -B diag_collapse.py 完整输出目录 输出.json
# 对每个完整输出：① 每 250 拍完成数，找塌局起点；② 最后 600 拍一步没动的车：在哪（分道门格 / 其他门格 / 门口区 / 房间），
# 朝向前方那格被谁占（静止车 / 动的车 / 墙 / 空），按“前方那台车”连成等待图，找环；③ 静止车的连通团离分道门格多远。
import json, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'p27'))
import ipfix_account as A

def sim(o, i):
    MC = o['agentMaxCounter']; r, c, d = o['start'][i]; d = A.DIRS[d]; cnt = 0; pos = []; dirs = []
    for a in A.expand(o['actualPaths'][i]):
        if a != 'W':
            cnt += 1
            if cnt == MC:
                cnt = 0
                if a == 'F': r += A.MV[d][0]; c += A.MV[d][1]
                elif a == 'R': d = (d + 1) % 4
                elif a == 'C': d = (d - 1) % 4
        pos.append((r, c)); dirs.append(d)
    return pos, dirs

def one(f, pickdir):
    name = Path(f).stem; inst = name.split('_LCAP')[0].split('_PICK')[0]
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    pick = set()
    pf = Path(pickdir) / f'{inst}.txt'
    if pf.exists():
        for l in pf.read_text().split('\n'):
            if l.strip(): a, b = map(int, l.split()); pick.add((a, b))
    pickg = {dlab[v] for v in pick if v in dlab}
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    fin = [e for ev in o['events'] for e in [ev] if e[3] == 2] if o['events'] and len(o['events'][0]) == 4 else []
    bins = [0] * (T // 250)
    for e in o['events']:
        if e[-1] == 2 and e[0] < T: bins[e[0] // 250] += 1
    P = [sim(o, i) for i in range(N)]
    W0 = T - 600
    still = [i for i in range(N) if len(set(P[i][0][W0:T])) == 1]
    S = set(still); at = {P[i][0][T - 1]: i for i in range(N)}
    def where(v):
        if v in dlab: return '分道门格' if dlab[v] in pickg else '其他门格'
        if v in apron: return '门口区'
        return '房间'
    loc = collections.Counter(where(P[i][0][T - 1]) for i in still)
    front = collections.Counter(); nxt = {}
    for i in still:
        (r, c), d = P[i][0][T - 1], P[i][1][T - 1]
        u = (r + A.MV[d][0], c + A.MV[d][1])
        if not F(*u): front['墙'] += 1
        elif u in at:
            j = at[u]
            if j in S: front['静止车'] += 1; nxt[i] = j
            else: front['动的车'] += 1
        else: front['空'] += 1
    cyc = []; seen = set()
    for s in nxt:
        path = []; x = s; idx = {}
        while x in nxt and x not in seen and x not in idx: idx[x] = len(path); path.append(x); x = nxt[x]
        if x in idx: cyc.append(path[idx[x]:])
        seen.update(path)
    # 静止车连通团（4 邻接）
    comp = []; left = set(P[i][0][T - 1] for i in still)
    while left:
        v = left.pop(); q = [v]; cc = [v]
        while q:
            a, b = q.pop()
            for u in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if u in left: left.remove(u); q.append(u); cc.append(u)
        comp.append(cc)
    comp.sort(key=len, reverse=True)
    def dpick(cc):
        if not pick: return None
        return min(abs(a - p) + abs(b - q) for (a, b) in cc for (p, q) in pick)
    big = [dict(size=len(cc), dist_to_pick=dpick(cc), doors=sorted({dlab[v] for v in cc if v in dlab}),
                pick_doors=sorted({dlab[v] for v in cc if v in dlab and dlab[v] in pickg}),
                cells=sorted(cc)[:6]) for cc in comp[:5]]
    # 静止开始时间：最大团里每台车最后一次移动的拍
    if comp:
        cset = set(comp[0]); ids = [i for i in still if P[i][0][T - 1] in cset]
        last_move = sorted(max([t for t in range(1, T) if P[i][0][t] != P[i][0][t - 1] or P[i][1][t] != P[i][1][t - 1]] or [0]) for i in ids)
    else: last_move = []
    return dict(run=name, completed=o['numTaskFinished'], bins250=bins, stuck_last600=len(still), stuck_where=dict(loc),
                front=dict(front), cycles=[len(c) for c in cyc], cycle_cells=[[P[i][0][T - 1] for i in c] for c in cyc][:3],
                pick_cells=sorted(pick), comps=big, biggest_comp_last_move=last_move)

if __name__ == '__main__':
    d = Path(sys.argv[1]); pickdir = HERE.parent / 'p34' / 'pick'
    res = [one(f, pickdir) for f in sorted(d.glob('*.json'))]
    Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf8')
    for r in res:
        print(r['run'], r['completed'], '静止', r['stuck_last600'], r['stuck_where'], r['front'], '环', r['cycles'],
              '最大团', [(c['size'], c['dist_to_pick'], c['pick_doors']) for c in r['comps'][:3]])
