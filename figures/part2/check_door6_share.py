"""核对 37.6%：门 6 两侧各占多少格，取货与送货分在两侧的单有多少。

运行（仓库根目录）：python3 figures/part2/check_door6_share.py
输入：官方房间图 room-64-64-16.map 和官方任务文件 room-example_250.tasks（room200/250/300 共用这一份）。
做法：逐个去掉一个可走格子，看地图是否断成两块；门 6 的门格 (16,1) 去掉后，左下区域和其余区域分开。
"""
from collections import deque
from pathlib import Path

D = Path(__file__).resolve().parents[2] / "experiment-materials/网络协议方向/harness/data/pkg/maps/room"
lines = (D / "room-64-64-16.map").read_text().split("\n")
H, W = int(lines[1].split()[1]), int(lines[2].split()[1])
grid = lines[4:4 + H]
free = {r * W + c for r in range(H) for c in range(W) if grid[r][c] == "."}


def components(removed):
    seen, out = set(), []
    for s in free:
        if s in seen or s == removed:
            continue
        q, comp = deque([s]), {s}
        seen.add(s)
        while q:
            r, c = divmod(q.popleft(), W)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                v = rr * W + cc
                if 0 <= rr < H and 0 <= cc < W and v in free and v != removed and v not in seen:
                    seen.add(v); comp.add(v); q.append(v)
        out.append(comp)
    return out


door = 16 * W + 1  # 门 6 的门格（第 16 行第 1 列）
small, big = sorted(components(door), key=len)
p = len(small) / (len(small) + len(big))
tasks = [list(map(int, x.split(","))) for x in (D / "room-example_250.tasks").read_text().split("\n")[2:] if x.strip()]
cross = sum((t[0] in small) != (t[-1] in small) for t in tasks)
print(f"可走格子 {len(free)}；去掉门 6 后：左下 {len(small)} 格，其余 {len(big)} 格，左下占 {p:.4f}")
print(f"均匀假设：一单两端分在两侧的概率 2p(1-p) = {2 * p * (1 - p):.4f}")
print(f"任务文件：{len(tasks)} 单中取货和送货分在门 6 两侧的有 {cross} 单，占 {cross / len(tasks):.4f}")
