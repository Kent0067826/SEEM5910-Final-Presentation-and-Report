"""第二部分配图：仓库=网络的对照示意图、成批放行的门利用率曲线。

运行：python3 figures/part2/make_figs.py
数字来源：
  - 门口区 8 步、4.2 倍 / 2.9 倍 / 1.1 倍：experiment-materials/网络协议方向/报告源/网络建模研究_第29轮.md 第四节
  - h = 9 拍、s = 21 拍、U(1)=43%、U(10)=88%：报告源/图/en/en_08_four_numbers.png；数字核对表第 86 行
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch

OUT = Path(__file__).resolve().parent
for f in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
plt.rcParams["axes.unicode_minus"] = False

INK = "#1f2933"
MUTED = "#6b7785"
BLUE = "#2f6fdb"
RED = "#c8453a"
GREEN = "#2e8b57"
PURPLE = "#7a5cc4"
ORANGE = "#e08a1e"


def analogy_figure():
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=200)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 62)
    ax.axis("off")

    # two rooms separated by a wall with a one-cell door
    for x0, name in [(6, "房间 A"), (64, "房间 B")]:
        ax.add_patch(FancyBboxPatch((x0, 10), 50, 40, boxstyle="round,pad=0,rounding_size=2",
                                    fc="#f4f7fb", ec="#b8c4d2", lw=1.5))
        ax.text(x0 + 3, 46.5, name, fontsize=12, color=MUTED, va="top")
    # wall
    ax.add_patch(Rectangle((56, 10), 8, 40, fc="#8f9bab", ec="none"))
    # door gap
    ax.add_patch(Rectangle((56, 28), 8, 4, fc="white", ec=RED, lw=2.2))

    # router port zones (门口区) on both sides
    for x0 in (44, 64):
        ax.add_patch(Rectangle((x0, 22), 12, 16, fc=PURPLE, alpha=0.13, ec=PURPLE, lw=1.2, ls="--"))

    # hosts: pickup / delivery points
    ax.add_patch(Rectangle((12, 36), 3.2, 3.2, fc=ORANGE, ec="none"))
    ax.text(16.5, 37.6, "取货点", fontsize=10, color=ORANGE, va="center")
    ax.plot([102], [17], marker="*", ms=18, color=BLUE)
    ax.text(104.5, 17, "送货点", fontsize=10, color=BLUE, va="center")

    # robots queueing toward the door (packets)
    for (x, y) in [(20, 30), (30, 29), (38, 31), (46, 30), (50, 29.5), (53, 30.5)]:
        ax.add_patch(Circle((x, y), 1.3, fc=INK, ec="white", lw=0.8))
    for (x, y) in [(70, 31), (80, 24), (92, 20)]:
        ax.add_patch(Circle((x, y), 1.3, fc=GREEN, ec="white", lw=0.8))
    ax.add_patch(FancyArrowPatch((16, 37), (100, 18), connectionstyle="arc3,rad=0.25",
                                 arrowstyle="-|>", mutation_scale=14, color=BLUE, lw=1.4, ls=":"))

    def note(xy, xytext, text, color=INK):
        ax.annotate(text, xy=xy, xytext=xytext, fontsize=10.5, color=color,
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.9),
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=color, lw=0.9))

    note((60, 32), (56, 57), "门 ＝ 链路\n一格宽，一次只走一个方向", RED)
    note((50, 23), (36, 4), "门口两侧约 8 步 ＝ 路由器端口\n排队、转身、交接都在这里", PURPLE)
    note((24, 22), (12, 4), "房间内部 ＝ 局域网\n基本畅通", MUTED)
    note((53, 31.5), (98, 57), "机器人 ＝ 数据包\n但不能丢、排队时还占着格子", INK)
    note((92, 21), (100, 4), "一单任务 ＝ 一条流\n从取货“主机”到送货“主机”", BLUE)
    note((13.6, 39.2), (14, 57), "派单中心 ＝ 发送端\n在源头决定放不放", ORANGE)

    fig.tight_layout()
    fig.savefig(OUT / "p2_01_warehouse_as_network.png", bbox_inches="tight")
    plt.close(fig)


def batch_figure():
    h, s = 9, 21  # 同向相邻两车间隔 9 拍；换一次方向 21 拍（实测）
    ns = list(range(1, 21))
    u = [n * h / ((n - 1) * h + s) for n in ns]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
    ax.plot(ns, [x * 100 for x in u], color=BLUE, lw=2.2, marker="o", ms=4)
    for n, c in [(1, RED), (10, GREEN)]:
        v = u[n - 1] * 100
        ax.scatter([n], [v], s=90, color=c, zorder=5)
        ax.annotate(f"每次放 {n} 台：门忙 {v:.0f}%", xy=(n, v),
                    xytext=(n + (2.2 if n == 1 else -0.5), v + (6 if n == 1 else -16)),
                    fontsize=11, color=c, arrowprops=dict(arrowstyle="-", color=c))
    ax.set_xlabel("一个方向一次连续放行的车数")
    ax.set_ylabel("门真正在过车的时间占比（%）")
    ax.set_ylim(30, 100)
    ax.set_xlim(0, 21)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.grid(alpha=0.25)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("换一次方向要花 21 拍，攒成一批再换，门就闲得少", fontsize=12, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "p2_02_batch_utilization.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    analogy_figure()
    batch_figure()
    print("done")
