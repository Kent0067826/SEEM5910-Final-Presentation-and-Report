# 协议第 36 轮先量：门口拥挤信号（S1 总占用、S2 两头都挤）能不能提前看见门口僵局（跳过线见 先量_ECN信号能不能预见门口僵局_事先写定.md）。
# 用法：python -B measure_ecn_signal.py 完整输出目录 第35轮僵局清单.json 输出.json
import json, sys, collections
from collections import deque
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R = Path(r'C:\Users\RETN_kwang\Downloads\BaiduSyncdisk\5910 实验\网络协议方向')
sys.path.insert(0, str(R / 'rounds' / 'p27')); sys.path.insert(0, str(R / 'rounds' / 'p35'))
import ipfix_account as A
from diag_collapse import sim
LEAD = 10

def door_zones(h, w, free):
    dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    owner = dict(dlab); dist = {v: 0 for v in dlab}; q = deque(dlab)   # 多源 BFS：门口区格归最近的门
    while q:
        v = q.popleft()
        if dist[v] >= A.APRON: continue
        a, b = v
        for u in ((a+1, b), (a-1, b), (a, b+1), (a, b-1)):
            if F(*u) and u not in dist: dist[u] = dist[v] + 1; owner[u] = owner[v]; q.append(u)
    side = {}
    for g in range(nd):
        cells = {v for v, o in owner.items() if o == g and v not in dlab}; k = 0
        for v in cells:
            if v in side: continue
            st = [v]; side[v] = k
            while st:
                a, b = st.pop()
                for u in ((a+1, b), (a-1, b), (a, b+1), (a, b-1)):
                    if u in cells and u not in side: side[u] = k; st.append(u)
            k += 1
    return dlab, nd, owner, side

def one(args):
    f, sts = args
    inst = Path(f).stem.split('_LCAP')[0]
    h, w, free = A.load_map(inst); dlab, nd, owner, side = door_zones(h, w, free)
    o = json.loads(Path(f).read_text()); N = len(o['start']); T = o['makespan']
    P = [sim(o, i)[0] for i in range(N)]
    S1 = [[0] * T for _ in range(nd)]; S2 = [[0] * T for _ in range(nd)]
    for t in range(T):
        c1 = collections.Counter(); c2 = collections.defaultdict(collections.Counter)
        for i in range(N):
            v = P[i][t]; g = owner.get(v)
            if g is None: continue
            c1[g] += 1
            if v not in dlab: c2[g][side[v]] += 1
        for g, n in c1.items(): S1[g][t] = n
        for g, cs in c2.items():
            vals = sorted(cs.values(), reverse=True); S2[g][t] = vals[1] if len(vals) > 1 else 0
    cross = []   # (门, 进门格前一拍的 S1, S2)
    for i in range(N):
        for t in range(1, T):
            v, u = P[i][t], P[i][t-1]
            if v in dlab and u not in dlab: g = dlab[v]; cross.append((g, S1[g][t-1], S2[g][t-1]))
    ons = []
    for (agents, t0, dur, g, kinds) in sts:
        tt = max(0, t0 - LEAD); ons.append(dict(agents=agents, t0=t0, dur=dur, door=g, s1=S1[g][tt], s2=S2[g][tt],
                                                s1_max_before=max(S1[g][max(0, t0-50):t0+1]), s2_max_before=max(S2[g][max(0, t0-50):t0+1])))
    return dict(inst=inst, crossings=[(c[1], c[2]) for c in cross], onsets=ons)

if __name__ == '__main__':
    fs = sorted(Path(sys.argv[1]).glob('*_LCAP_9700_101.json'))
    st = {r['inst']: r['list'] for r in json.loads(Path(sys.argv[2]).read_text(encoding='utf8'))}
    with ProcessPoolExecutor(9) as ex: res = list(ex.map(one, [(f, st.get(Path(f).stem.split('_LCAP')[0], [])) for f in fs]))
    allc = [c for r in res for c in r['crossings']]; allo = [x for r in res for x in r['onsets']]
    out = dict(lead=LEAD, n_crossings=len(allc), n_onsets=len(allo), signals={})
    for k, name in ((0, 'S1'), (1, 'S2')):
        K = 1
        while sum(1 for c in allc if c[k] >= K) / len(allc) > 0.30: K += 1
        mark = sum(1 for c in allc if c[k] >= K) / len(allc)
        hit = sum(1 for x in allo if x[name.lower()] >= K) / max(1, len(allo))
        dist = collections.Counter(c[k] for c in allc)
        out['signals'][name] = dict(K=K, mark_frac=mark, onset_hit=hit, crossing_dist=sorted(dist.items()),
                                    onset_vals=[x[name.lower()] for x in allo])
        print(name, 'K', K, '标记比例 %.1f%%' % (100 * mark), '提前命中 %d/%d = %.0f%%' % (sum(1 for x in allo if x[name.lower()] >= K), len(allo), 100 * hit))
    out['per_inst'] = [dict(inst=r['inst'], n_cross=len(r['crossings']), onsets=r['onsets']) for r in res]
    Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf8')
    for r in res:
        for x in r['onsets']: print('  ', r['inst'].ljust(11), 'door', x['door'], 't0', x['t0'], 'dur', x['dur'], 'S1', x['s1'], 'S2', x['s2'])
