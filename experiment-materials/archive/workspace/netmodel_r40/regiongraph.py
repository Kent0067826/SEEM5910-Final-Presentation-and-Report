"""第 40 轮 / 网络建模第 1 步：把格子地图变成"区域网络图"。

节点 = 房间（区域），链路 = 门。

做法（全部由地图推出，不用任何手调参数）：
  1. 窄格：一个空格如果所在的横向空格串长度 <= 2，或纵向空格串长度 <= 2，就叫"窄格"。
     - 房间内部的横、纵空格串都很长（>= 房间宽度），所以不会被误判；
     - 墙上的 1 格门：沿墙方向两边是墙 -> 串长 1；2 格门 -> 串长 2。
  2. 去掉窄格后，剩下的 4-连通块就是房间。
  3. 窄格按 4-连通分组，每组是一个"门候选"。它连着几个不同的房间：
     - 正好 2 个 -> 一道门（一条链路）；
     - 1 个 -> 只是墙边的凹槽，并回所在房间；
     - 0 个或 >2 个 -> 记为特殊情况（报告里单独列出，不悄悄丢掉）。
  4. 门的宽度 = 垂直于通行方向的格数（1 = 单车道，一次只能一个方向；2 = 两车道）。
  5. 在"房间—门"多重图上找：
     - 桥（单门割）：去掉这一道门地图就分成两半 —— 对应现在方法里的"割点"；
     - 门对（双门割）：单独去掉哪一道都不分开，两道一起去掉才分开 —— 对应"门对"。

用法：python3 regiongraph.py 地图文件 [输出.json]
"""
import sys, json, itertools, collections


def read_map(path):
    L = open(path).read().split('\n')
    i = [k for k, l in enumerate(L) if l.strip() == 'map'][0]
    g = [l.rstrip('\r') for l in L[i + 1:] if l.strip()]
    H = int([l.split()[1] for l in L[:i] if l.startswith('height')][0])
    W = int([l.split()[1] for l in L[:i] if l.startswith('width')][0])
    g = g[:H]
    assert all(len(r) >= W for r in g), path
    return [r[:W] for r in g]


def free(g, r, c):
    return 0 <= r < len(g) and 0 <= c < len(g[0]) and g[r][c] == '.'


def runs(g):
    H, W = len(g), len(g[0])
    hr = [[0] * W for _ in range(H)]; vr = [[0] * W for _ in range(H)]
    for r in range(H):
        c = 0
        while c < W:
            if g[r][c] != '.': c += 1; continue
            e = c
            while e < W and g[r][e] == '.': e += 1
            for k in range(c, e): hr[r][k] = e - c
            c = e
    for c in range(W):
        r = 0
        while r < H:
            if g[r][c] != '.': r += 1; continue
            e = r
            while e < H and g[e][c] == '.': e += 1
            for k in range(r, e): vr[k][c] = e - r
            r = e
    return hr, vr


def components(cells):
    cells = set(cells); seen = set(); out = []
    for s in sorted(cells):
        if s in seen: continue
        q = [s]; seen.add(s)
        for (y, x) in q:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (y + dy, x + dx)
                if v in cells and v not in seen: seen.add(v); q.append(v)
        out.append(sorted(q))
    return out


def build(g, narrow_max=2):
    H, W = len(g), len(g[0])
    hr, vr = runs(g)
    allfree = [(r, c) for r in range(H) for c in range(W) if g[r][c] == '.']
    narrow = {(r, c) for (r, c) in allfree if hr[r][c] <= narrow_max or vr[r][c] <= narrow_max}
    rooms = components([v for v in allfree if v not in narrow])
    room_of = {}
    for i, cs in enumerate(rooms):
        for v in cs: room_of[v] = i
    doors, niches, odd = [], [], []
    for grp in components(narrow):
        touch = set()
        for (y, x) in grp:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (y + dy, x + dx)
                if v in room_of: touch.add(room_of[v])
        if len(touch) == 2:
            a, b = sorted(touch)
            ys = [y for y, _ in grp]; xs = [x for _, x in grp]
            # 通行方向：门两侧房间格所在的方向。横墙上的门 = 竖着走，宽度 = 横向格数。
            vert = any(free(g, y - 1, x) and (y - 1, x) in room_of for (y, x) in grp) and \
                   any(free(g, y + 1, x) and (y + 1, x) in room_of for (y, x) in grp)
            width = (max(xs) - min(xs) + 1) if vert else (max(ys) - min(ys) + 1)
            depth = (max(ys) - min(ys) + 1) if vert else (max(xs) - min(xs) + 1)
            doors.append(dict(id=len(doors), cells=grp, rooms=[a, b], width=width, depth=depth,
                              axis='ns' if vert else 'ew'))
        elif len(touch) == 1:
            niches.append((grp, touch.pop()))
        else:
            odd.append(dict(cells=grp, rooms=sorted(touch)))
    for grp, r in niches:           # 凹槽并回房间
        for v in grp: room_of[v] = r; rooms[r].append(v)
    R = []
    for i, cs in enumerate(rooms):
        ys = [y for y, _ in cs]; xs = [x for _, x in cs]
        R.append(dict(id=i, size=len(cs), bbox=[min(ys), min(xs), max(ys), max(xs)],
                      center=[sum(ys) / len(ys), sum(xs) / len(xs)]))
    return R, doors, odd, room_of


def connected(nr, edges):
    adj = collections.defaultdict(list)
    for a, b in edges: adj[a].append(b); adj[b].append(a)
    if nr == 0: return True
    seen = {0}; q = [0]
    for v in q:
        for w in adj[v]:
            if w not in seen: seen.add(w); q.append(w)
    return len(seen) == nr


def side_sizes(R, doors, removed):
    """去掉 removed 这些门后，各连通块的房间集合与格数。"""
    adj = collections.defaultdict(list)
    for d in doors:
        if d['id'] in removed: continue
        a, b = d['rooms']; adj[a].append(b); adj[b].append(a)
    seen = {}; parts = []
    for s in range(len(R)):
        if s in seen: continue
        q = [s]; seen[s] = len(parts)
        for v in q:
            for w in adj[v]:
                if w not in seen: seen[w] = len(parts); q.append(w)
        parts.append(q)
    return [dict(rooms=sorted(p), cells=sum(R[r]['size'] for r in p)) for p in parts]


def analyse(path):
    g = read_map(path)
    R, D, odd, room_of = build(g)
    E = [tuple(d['rooms']) for d in D]
    nfree = sum(r['size'] for r in R) + sum(len(d['cells']) for d in D) + sum(len(o['cells']) for o in odd)
    out = dict(map=path, H=len(g), W=len(g[0]), free=nfree, rooms=R, doors=[dict(d, cells=[list(c) for c in d['cells']]) for d in D],
               odd=[dict(o, cells=[list(c) for c in o['cells']]) for o in odd])
    base_conn = connected(len(R), E)
    out['connected'] = base_conn
    # 单门割（桥）
    bridges = []
    for d in D:
        if not connected(len(R), [e for k, e in enumerate(E) if k != d['id']]):
            parts = side_sizes(R, D, {d['id']})
            bridges.append(dict(door=d['id'], parts=parts))
    bset = {b['door'] for b in bridges}
    # 双门割（门对）：两道都不是桥，一起去掉才分开
    pairs = []
    if len(D) <= 120:
        for i, j in itertools.combinations([d['id'] for d in D if d['id'] not in bset], 2):
            if not connected(len(R), [e for k, e in enumerate(E) if k not in (i, j)]):
                pairs.append(dict(doors=[i, j], parts=side_sizes(R, D, {i, j})))
    out['bridges'] = bridges; out['door_pairs'] = pairs
    # 门对按"同一条环链"归类：e、f 构成双门割 <=> 它们在同一个类里（这是等价关系），
    # 一个类里任意两道一起去掉都会断开，所以 k 道门的类会贡献 k(k-1)/2 个"门对"。
    par_ = {}
    def find(x):
        while par_.setdefault(x, x) != x: x = par_[x]
        return x
    for p in pairs:
        i, j = p['doors']; par_[find(i)] = find(j)
    cls = collections.defaultdict(list)
    for p in pairs:
        for k in p['doors']:
            if k not in cls[find(k)]: cls[find(k)].append(k)
    out['cut_classes'] = sorted(sorted(v) for v in cls.values())
    # 每道门的"割的级别"：属于桥 = 1；属于某个门对 = 2；否则 >= 3（有绕行）
    lvl = {}
    for d in D: lvl[d['id']] = 3
    for p in pairs:
        for k in p['doors']: lvl[k] = 2
    for b in bset: lvl[b] = 1
    for d in out['doors']: d['cut_level'] = lvl[d['id']]
    # 房间之间的"并联门"数
    par = collections.Counter(tuple(d['rooms']) for d in D)
    for d in out['doors']: d['parallel'] = par[tuple(d['rooms'])]
    out['summary'] = dict(rooms=len(R), doors=len(D), lane1=sum(d['width'] == 1 for d in D), lane2=sum(d['width'] == 2 for d in D),
                          wider=sum(d['width'] > 2 for d in D), bridges=len(bridges), door_pairs=len(pairs),
                          cut_classes=len(out['cut_classes']), odd=len(odd),
                          room_cells=sum(r['size'] for r in R), door_cells=sum(len(d['cells']) for d in D))
    return out


if __name__ == '__main__':
    o = analyse(sys.argv[1])
    if len(sys.argv) > 2: json.dump(o, open(sys.argv[2], 'w'))
    print(json.dumps(o['summary'], ensure_ascii=False))
    for d in o['doors']:
        print(f"门{d['id']:2d} 房间{d['rooms'][0]:2d}-{d['rooms'][1]:2d} 宽{d['width']} 深{d['depth']} 割级{d['cut_level']} 并联{d['parallel']} 格{d['cells'][:3]}")
    for b in o['bridges']: print('桥', b['door'], [p['cells'] for p in b['parts']])
    for p in o['door_pairs']: print('门对', p['doors'], [q['cells'] for q in p['parts']])
