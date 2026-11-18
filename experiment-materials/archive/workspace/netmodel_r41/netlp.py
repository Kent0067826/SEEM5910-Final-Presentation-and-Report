"""第 41 轮 / 第 4 步：多商品"最大并发流"——网络里求"在给定流量比例下，整张网每拍最多能完成多少单"的标准线性规划。

  节点 = 房间；每道门 = 一条半双工链路：两个方向的流量合计 <= 门的有效带宽 C_door。
  需求：任务的取货点、送货点在所有房间格里均匀分布（第 3 步已核对与任务文件一致），
        房间 s -> 房间 t 的任务占比 d_st = (|s|/A)(|t|/A)，s != t（同一房间内的任务不过门）。
  变量：按源房间汇总的链路流量 x[s, 弧] 和吞吐 λ（每拍完成几单）。
  目标：max λ，使所有房间对都能按 λ·d_st 送达，且每道门的总流量不超过带宽。
最优解同时给出每道门该分多少流量（按带宽分流的"路由"），以及哪些门是满的（瓶颈）。"""
import numpy as np, sys
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
sys.path.insert(0, '/home/claude/r40')
import regiongraph as RG

C_DOOR = {1: 26 / 500, 2: 32 / 500}


def max_concurrent_flow(G, cdoor=C_DOOR, extra_cap=None):
    R = G['rooms']; D = G['doors']; n = len(R); A = sum(r['size'] for r in R)
    arcs = []
    for d in D:
        a, b = d['rooms']; arcs.append((a, b, d['id'])); arcs.append((b, a, d['id']))
    E = len(arcs); S = n
    nv = S * E + 1                       # x[s, e] ... , λ
    lam = S * E
    rows, cols, vals, beq = [], [], [], []
    r_i = 0
    w = np.array([r['size'] / A for r in R])
    for s in range(S):
        for v in range(n):
            # out - in - (λ * 净需求) = 0 ；源点净供给 = λ*w_s*sum_{t!=s} w_t，汇点 -λ*w_s*w_v
            for e, (u, x, _) in enumerate(arcs):
                if u == v: rows.append(r_i); cols.append(s * E + e); vals.append(1.0)
                if x == v: rows.append(r_i); cols.append(s * E + e); vals.append(-1.0)
            net = w[s] * (1 - w[s]) if v == s else -w[s] * w[v]
            rows.append(r_i); cols.append(lam); vals.append(-net)
            beq.append(0.0); r_i += 1
    Aeq = coo_matrix((vals, (rows, cols)), shape=(r_i, nv)).tocsr()
    # 门容量：两个方向、所有源合计
    rows, cols, vals, bub = [], [], [], []
    for k, d in enumerate(D):
        es = [e for e, a in enumerate(arcs) if a[2] == d['id']]
        for s in range(S):
            for e in es: rows.append(k); cols.append(s * E + e); vals.append(1.0)
        c = cdoor[min(2, d['width'])]
        if extra_cap and d['id'] in extra_cap: c = extra_cap[d['id']]
        bub.append(c)
    Aub = coo_matrix((vals, (rows, cols)), shape=(len(D), nv)).tocsr()
    cobj = np.zeros(nv); cobj[lam] = -1.0
    res = linprog(cobj, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=[(0, None)] * nv, method='highs')
    if res.status != 0: return None
    x = res.x
    load = {}
    for k, d in enumerate(D):
        es = [e for e, a in enumerate(arcs) if a[2] == d['id']]
        load[d['id']] = float(sum(x[s * E + e] for s in range(S) for e in es))
    marg = res.ineqlin.marginals if hasattr(res, 'ineqlin') else None
    tight = [d['id'] for k, d in enumerate(D) if marg is not None and abs(marg[k]) > 1e-9]
    return dict(lam=float(x[lam]), load=load, tight=tight,
                util={d['id']: load[d['id']] / (cdoor[min(2, d['width'])]) for d in D})


if __name__ == '__main__':
    G = RG.analyse(sys.argv[1]); r = max_concurrent_flow(G)
    print('每 500 拍最多', round(r['lam'] * 500, 1), '单；满载的门', r['tight'])
