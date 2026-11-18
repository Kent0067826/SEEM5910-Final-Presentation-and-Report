"""把 LoRR 2026 输出（-c 1）里的 actualPaths 解码成每台机器人每一拍的位置。

编码：'[(t0,r,c,o,k):(F 9,W 18,R 3,...)]' 一段 100 拍；动作后面的数字是拍数。
一个动作要累计 agentMaxCounter 拍（这里是 3 拍）才完成：F = 前进一格，R = 顺时针转 90°，C = 逆时针转 90°，W = 等待。
中途被故障打断时，计数保留（例如 'C 2,W 13,C 1'）。朝向 0=东 1=南 2=西 3=北。
解码结果用 events（每次到达任务点的时刻和机器人）做核对。"""
import re, json

DR = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}
OR = {'E': 0, 'S': 1, 'W': 2, 'N': 3}
SEG = re.compile(r'\[\(([^)]*)\):\(([^)]*)\)\]')


def decode(s, start, mc):
    r, c, o = start[0], start[1], OR[start[2]] if isinstance(start[2], str) else int(start[2])
    pos = [(r, c)]
    cnt, cur = 0, None
    for _, acts in SEG.findall(s):
        if not acts: continue
        for tok in acts.split(','):
            a, n = tok.split(); n = int(n)
            for _ in range(n):
                if a in 'FRC':
                    if cur != a: cur, cnt = a, 0
                    cnt += 1
                    if cnt == mc:
                        if a == 'F': dr, dc = DR[o]; r, c = r + dr, c + dc
                        elif a == 'R': o = (o + 1) % 4
                        else: o = (o + 3) % 4
                        cnt, cur = 0, None
                pos.append((r, c))
    return pos          # pos[t] = 第 t 拍结束时所在格（pos[0] = 起点）


def load(path):
    o = json.load(open(path))
    mc = o['agentMaxCounter']
    P = [decode(e, o['start'][a], mc) for a, e in enumerate(o['actualPaths'])]
    return o, P


def check(o, P):
    """核对：每个任务点到达事件发生时，机器人确实站在该任务点上。"""
    task_locs = {t[0]: [(t[2][i], t[2][i + 1]) for i in range(0, len(t[2]), 2)] for t in o['tasks']}
    ok = bad = 0
    for t, a, tid, seq in o['events']:
        locs = task_locs.get(tid)
        if locs is None or seq < 1 or seq > len(locs): continue
        want = locs[seq - 1]
        got = P[a][min(t, len(P[a]) - 1)]
        if got == want: ok += 1
        else: bad += 1
    return ok, bad
