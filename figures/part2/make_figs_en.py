"""English figures for Part 2 and the English talk.

Run from the repo root:  python3 figures/part2/make_figs_en.py
Writes figures/part2/en/ : three new figures plus copies of the existing English figures,
numbered in the order the talk uses them.

Sources for the numbers are the same as for the Chinese figures (see make_figs.py), plus
experiment-materials/网络协议方向/报告源/通读/前人工作笔记.md for the prior-work comparison.
"""
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "en"
OUT.mkdir(exist_ok=True)
EN_SRC = ROOT / "experiment-materials/网络协议方向/报告源/图/en"

plt.rcParams["font.family"] = "DejaVu Sans"

INK = "#1f2933"
MUTED = "#6b7785"
BLUE = "#2f6fdb"
RED = "#c8453a"
GREEN = "#2e8b57"
PURPLE = "#7a5cc4"
ORANGE = "#e08a1e"


def prior_work_figure():
    rows = [
        ("What is counted?",
         "Planned routes on each edge;\ncars in a whole region;\ncars already at the door",
         "Robots in flight: task assigned,\nstill has to cross this door\nin this direction"),
        ("Where does control act?",
         "Route choice (edge costs);\nregion entry;\nat the door itself",
         "At the source:\nthe task-assignment step"),
        ("What about the narrow door?",
         "Soft congestion cost, or\none robot / one side at a time,\ndecided separately",
         "Half-duplex link: serve one side\nin batches, keep the exit clear;\nwatchdog against deadlock"),
        ("Works best when…",
         "There are other roads\nto spread the flow over",
         "There is one shared link\nno one can route around"),
    ]
    fig, ax = plt.subplots(figsize=(12.5, 6.6), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    x_q, x_a, x_b, w = 1, 25, 63, 36
    ax.add_patch(FancyBboxPatch((x_a, 84), w, 12, boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#eef1f5", ec="#b8c4d2"))
    ax.add_patch(FancyBboxPatch((x_b, 84), w, 12, boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#e4edfb", ec=BLUE, lw=1.6))
    ax.text(x_a + w / 2, 90, "Earlier work: traffic & flow networks\n(route guidance, guidance graphs,\nperimeter control, AGV zones)",
            ha="center", va="center", fontsize=10.5, color=INK)
    ax.text(x_b + w / 2, 90, "Our view: a computer network\n(door = link, door mouth = router port,\ntask assignment = sender)",
            ha="center", va="center", fontsize=10.5, color=BLUE, weight="bold")
    y = 78
    for q, a, b in rows:
        ax.plot([x_q, x_b + w], [y + 1, y + 1], color="#d5dbe3", lw=0.8)
        ax.text(x_q, y - 8, q, fontsize=11, color=INK, weight="bold", va="center")
        ax.text(x_a + w / 2, y - 8, a, fontsize=10, color=MUTED, ha="center", va="center", linespacing=1.4)
        ax.text(x_b + w / 2, y - 8, b, fontsize=10, color=INK, ha="center", va="center", linespacing=1.4)
        y -= 19
    ax.text(50, 0.5, "Earlier work already used network ideas. What was missing is the computer-network model: "
            "count in-flight load at the source.", ha="center", fontsize=9.5, color=MUTED, style="italic")
    fig.savefig(OUT / "e02_prior_work_vs_ours.png", bbox_inches="tight")
    plt.close(fig)


def analogy_figure():
    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=200)
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 62)
    ax.axis("off")
    for x0, name in [(6, "Room A"), (64, "Room B")]:
        ax.add_patch(FancyBboxPatch((x0, 10), 50, 40, boxstyle="round,pad=0,rounding_size=2",
                                    fc="#f4f7fb", ec="#b8c4d2", lw=1.5))
        ax.text(x0 + 3, 46.5, name, fontsize=12, color=MUTED, va="top")
    ax.add_patch(Rectangle((56, 10), 8, 40, fc="#8f9bab", ec="none"))
    ax.add_patch(Rectangle((56, 28), 8, 4, fc="white", ec=RED, lw=2.2))
    for x0 in (44, 64):
        ax.add_patch(Rectangle((x0, 22), 12, 16, fc=PURPLE, alpha=0.13, ec=PURPLE, lw=1.2, ls="--"))
    ax.add_patch(Rectangle((12, 36), 3.2, 3.2, fc=ORANGE, ec="none"))
    ax.text(16.5, 37.6, "pickup", fontsize=10, color=ORANGE, va="center")
    ax.plot([102], [17], marker="*", ms=18, color=BLUE)
    ax.text(104.5, 17, "delivery", fontsize=10, color=BLUE, va="center")
    for (x, y) in [(20, 30), (30, 29), (38, 31), (46, 30), (50, 29.5), (53, 30.5)]:
        ax.add_patch(Circle((x, y), 1.3, fc=INK, ec="white", lw=0.8))
    for (x, y) in [(70, 31), (80, 24), (92, 20)]:
        ax.add_patch(Circle((x, y), 1.3, fc=GREEN, ec="white", lw=0.8))
    ax.add_patch(FancyArrowPatch((16, 37), (100, 18), connectionstyle="arc3,rad=0.25",
                                 arrowstyle="-|>", mutation_scale=14, color=BLUE, lw=1.4, ls=":"))

    def note(xy, xytext, text, color=INK):
        ax.annotate(text, xy=xy, xytext=xytext, fontsize=10.5, color=color,
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.9), ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=color, lw=0.9))

    note((60, 32), (56, 57), "Door = link\none cell wide, one direction at a time", RED)
    note((50, 23), (48, 4), "~8 steps around the door = router port\nqueueing, turning, hand-over", PURPLE)
    note((24, 22), (14, 4), "Room = local network\nmostly free-flowing", MUTED)
    note((53, 31.5), (99, 57), "Robot = packet\nbut it cannot be dropped,\nand it blocks a cell while it waits", INK)
    note((92, 21), (100, 4), "One task = one flow\nfrom pickup 'host' to delivery 'host'", BLUE)
    note((13.6, 39.2), (14, 57), "Task assignment = sender\ndecides at the source", ORANGE)
    fig.tight_layout()
    fig.savefig(OUT / "e04_warehouse_as_network.png", bbox_inches="tight")
    plt.close(fig)


def batch_figure():
    h, s = 9, 21  # 9 ticks between robots in one direction; 21 ticks to switch direction (measured)
    ns = list(range(1, 21))
    u = [n * h / ((n - 1) * h + s) for n in ns]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=200)
    ax.plot(ns, [x * 100 for x in u], color=BLUE, lw=2.2, marker="o", ms=4)
    for n, c in [(1, RED), (10, GREEN)]:
        v = u[n - 1] * 100
        ax.scatter([n], [v], s=90, color=c, zorder=5)
        label = f"{n} robot per batch: door busy {v:.0f}%" if n == 1 else f"{n} robots per batch: door busy {v:.0f}%"
        ax.annotate(label, xy=(n, v), xytext=(n + (2.2 if n == 1 else -0.5), v + (6 if n == 1 else -16)),
                    fontsize=11, color=c, arrowprops=dict(arrowstyle="-", color=c))
    ax.set_xlabel("robots let through in one direction before switching")
    ax.set_ylabel("share of time the door is actually used (%)")
    ax.set_ylim(30, 100)
    ax.set_xlim(0, 21)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.grid(alpha=0.25)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title("A direction switch costs 21 ticks, so serve each side in batches", fontsize=12,
                 color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "e07_batch_utilization.png", bbox_inches="tight")
    plt.close(fig)


REUSED = {
    "e01_collapse.png": "en_04_collapse.png",
    "e03_map_to_network.png": "en_03_map_to_network.png",
    "e05_four_numbers.png": "en_08_four_numbers.png",
    "e06_knee.png": "en_09_knee.png",
    "e08_door_rule.png": "en_06_door_rule.png",
    "e09_results.png": "en_02_steps.png",
}

if __name__ == "__main__":
    prior_work_figure()
    analogy_figure()
    batch_figure()
    for dst, src in REUSED.items():
        shutil.copy(EN_SRC / src, OUT / dst)
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
