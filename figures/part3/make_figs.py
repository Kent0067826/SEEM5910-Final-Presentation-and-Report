# -*- coding: utf-8 -*-
"""Figures for Part 3 (key optimizations and iterations on the room map). All figure text is in English.

Run from the repository root:  python3 figures/part3/make_figs.py
Needs matplotlib.

Data sources
  * Read directly from raw records whenever they are in the repository:
      - experiment-materials/archive/workspace/batches/r52b-baseline/rows.jsonl      (formal evaluation, 640 runs)
      - figures/part3/rerun/ablation_room_4x4.jsonl                                   (re-test 2026-11-18, 600 runs)
      - figures/part3/rerun/general_gen4x4.jsonl                                      (random-door maps, 640 runs)
      - experiment-materials/网络协议方向/rounds/p*/..._compare.json, p72/inventory_p72.json
  * Rounds whose raw result files are not in the repository: numbers copied from
    experiment-materials/网络协议方向/报告源/通读/数字核对表.md and the two read-through notes; the source is noted
    next to each constant.
  * Figures named p3_en_*.png are the project's existing English figures, copied unchanged from
    experiment-materials/网络协议方向/报告源/图/en/.
"""
import json
import os
import random
import shutil
import statistics as st
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch, Rectangle, Circle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "figures", "part3")
EM = os.path.join(ROOT, "experiment-materials")
ROUNDS = os.path.join(EM, "网络协议方向", "rounds")
ENFIG = os.path.join(EM, "网络协议方向", "报告源", "图", "en")
RERUN = os.path.join(OUT, "rerun")

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["savefig.dpi"] = 200

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#ffffff"
BLUE, ORANGE, AQUA, YELLOW, RED, GRAY, LBLUE = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e34948", "#b9b8b2", "#8fb6e8"
OK, FAIL, PEND, INFO = "#008300", RED, YELLOW, BLUE
OFFICIAL = ("room200", "room250", "room300")      # the official 4x4 room map (64x64, 16 rooms) with 200/250/300 robots
CARS = {"room200": "200 robots", "room250": "250 robots", "room300": "300 robots"}


def style(ax, ygrid=True, xgrid=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=9)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, lw=0.8)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print("wrote", name)


def load(rel):
    with open(os.path.join(ROUNDS, rel), encoding="utf-8") as f:
        return json.load(f)


def rows_of(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def paired(by, a, b, maps):
    """Per-map lists of paired relative changes a vs b (same map, seed, planner seed)."""
    return [[by[(m, a, s, p)] / by[(m, b, s, p)] - 1 for (mm, k, s, p) in by if mm == m and k == b and (m, a, s, p) in by]
            for m in maps]


def boot(G, n=4000, seed=0):
    """Same resampling as archive/workspace/scripts/ana.py boot_ci (within-map paired resampling, equal map weights)."""
    rnd = random.Random(seed)
    ms = sorted(st.mean(st.mean(rnd.choice(g) for _ in g) for g in G) for _ in range(n))
    return st.mean(st.mean(g) for g in G), ms[int(.025 * n)], ms[int(.975 * n)]


def by_key(rows):
    return {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in rows if "completed" in r}


R52B = os.path.join(EM, "archive", "workspace", "batches", "r52b-baseline", "rows.jsonl")
ABL = os.path.join(RERUN, "ablation_room_4x4.jsonl")
GEN = os.path.join(RERUN, "general_gen4x4.jsonl")


# ---------------------------------------------------------------------------------------------------------------------
# Re-test (2026-11-18): ablation on the official 4x4 room map
# ---------------------------------------------------------------------------------------------------------------------
def fig_ablation():
    by = by_key(rows_of(ABL))
    left = [("Door rule: half-duplex,\nexhaustive service", "noDoor"), ("Per-door quota\n(bandwidth x delay)", "noQuota"),
            ("Executor: return the\ncell credit on time", "noSync"), ("PFC deadlock watchdog", "noWD"),
            ("Global admission cap\n(max-flow)", "noGlobal")]
    right = [("Door rule only", "onlyDoor"), ("Per-door quota only", "onlyQuota"), ("Global cap only", "onlyGlobal"),
             ("Everything on\n(full method)", "FULL")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.3))
    for ax, items, title, base, col in [
            (a1, left, "Remove one part from the full method", "FULL", ORANGE),
            (a2, right, "Add only this part to the base\n(champion assignment + fixed executor)", "NONE", BLUE)]:
        ys = list(range(len(items)))[::-1]
        for y, (name, k) in zip(ys, items):
            m, lo, hi = (100 * x for x in boot(paired(by, k, base, OFFICIAL)))
            c = col if (lo > 0 or hi < 0) else GRAY
            ax.barh(y, m, color=c, height=0.6)
            ax.plot([lo, hi], [y, y], color=INK, lw=1)
            x = min(m, lo) if m < 0 else max(m, hi)
            ax.text(x + (-1 if m < 0 else 1), y, f"{m:+.1f}%", va="center", ha="right" if m < 0 else "left", fontsize=9, color=INK)
        ax.set_yticks(ys)
        ax.set_yticklabels([n for n, _ in items], fontsize=9)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(title, fontsize=10, color=INK)
        style(ax, ygrid=False, xgrid=True)
    fig.subplots_adjust(wspace=0.6)
    a1.set_xlim(-38, 6)
    a2.set_xlim(0, 92)
    a1.set_xlabel("change in tasks completed (%); black line = 95% interval;\ngrey = interval crosses 0 (no measurable effect)", fontsize=8.5, color=INK2)
    a2.set_xlabel("change in tasks completed (%)", fontsize=8.5, color=INK2)
    fig.suptitle("Re-test on the official 4x4 room map: 200/250/300 robots, 20 runs per version and size (600 runs, 0 errors)",
                 fontsize=10.5, color=INK, y=1.03)
    save(fig, "p3_fig01_ablation.png")


def fig_synergy():
    by = by_key(rows_of(ABL))
    vers = [("Door rule only", "onlyDoor", LBLUE), ("Per-door quota only", "onlyQuota", AQUA),
            ("Door rule + quota\n(+ watchdog, no global cap)", "noGlobal", BLUE)]
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    w = 0.26
    for j, (name, k, c) in enumerate(vers):
        vals = [100 * st.mean(g) for g in paired(by, k, "NONE", OFFICIAL)]
        xs = [i + (j - 1) * w for i in range(3)]
        ax.bar(xs, vals, width=w * 0.92, color=c, label=name)
        for x, v in zip(xs, vals):
            ax.text(x, v + 1, f"+{v:.0f}%", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels([CARS[m] for m in OFFICIAL])
    ax.set_ylabel("gain over the base (%)", fontsize=9, color=INK2)
    ax.set_ylim(0, 95)
    ax.legend(fontsize=8.5, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    ax.set_title("1 + 1 > 2: the door rule matters most with fewer robots, the quota with more robots;\n"
                 "together they give far more than either alone", fontsize=10, color=INK, y=1.17)
    style(ax)
    save(fig, "p3_fig05_synergy.png")


# ---------------------------------------------------------------------------------------------------------------------
# Formal evaluation (r52b, 640 runs) restricted to the official 4x4 room map
# ---------------------------------------------------------------------------------------------------------------------
def fig_ladder():
    acc = defaultdict(list)
    for r in rows_of(R52B):
        acc[(r["map"], r["method"])].append(r["completed"])
    meths = ["DEF", "N2", "N2F", "LCAP"]
    names = ["official starter program", "+ champion task assignment", "+ fixed executor", "+ door rule & quotas (ours)"]
    cols = [GRAY, LBLUE, BLUE, ORANGE]
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    w = 0.2
    for j, (m, nm, c) in enumerate(zip(meths, names, cols)):
        ys = [st.mean(acc[(mp, m)]) for mp in OFFICIAL]
        xs = [i + (j - 1.5) * w for i in range(3)]
        ax.bar(xs, ys, width=w * 0.92, color=c, label=nm)
        for x, y in zip(xs, ys):
            ax.text(x, y + 12, f"{y:.0f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels([CARS[m] for m in OFFICIAL], fontsize=9.5)
    ax.set_ylabel("tasks completed per run (5000 ticks)", fontsize=9, color=INK2)
    ax.set_ylim(0, 1320)
    ax.legend(fontsize=8.5, frameon=False, ncol=2, loc="upper left")
    ax.set_title("Formal evaluation on the official 4x4 room map (20 runs per bar)", fontsize=10, color=INK)
    style(ax)
    save(fig, "p3_fig02_ladder_room.png")


def fig_collapse(with_ours=True):
    acc = defaultdict(list)
    for r in rows_of(R52B):
        acc[(r["map"], r["method"])].append(r["prof"])
    names = {"DEF": "official starter program", "N2": "+ champion assignment", "N2F": "+ fixed executor",
             "LCAP": "+ door rule & quotas (ours)"}
    cols = {"DEF": GRAY, "N2": LBLUE, "N2F": BLUE, "LCAP": ORANGE}
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, m in zip(axes, OFFICIAL):
        for meth in (["DEF", "N2", "N2F", "LCAP"] if with_ours else ["DEF", "N2", "N2F"]):
            P = acc[(m, meth)]
            mean = [st.mean(p[i] for p in P) for i in range(len(P[0]))]
            ax.plot([500 * (i + 1) for i in range(len(mean))], mean, color=cols[meth], lw=2, marker="o", ms=4, label=names[meth])
        ax.set_title(f"official room map, {CARS[m]} (20 runs)", fontsize=10, color=INK)
        ax.set_xlabel("tick (a run is 5000 ticks)", fontsize=9, color=INK2)
        style(ax)
    axes[0].set_ylabel("tasks completed per 500 ticks", fontsize=9, color=INK2)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=4, frameon=False, fontsize=9)
    if with_ours:
        fig.suptitle("With door control the completion rate stays 2-3x higher in the second half of the run",
                     fontsize=10.5, color=INK, y=1.02)
        save(fig, "p3_fig03_collapse.png")
    else:
        axes[0].set_ylim(0, 190)
        fig.suptitle("Without door control the completion rate keeps falling as the run goes on (same programs, more time)",
                     fontsize=10.5, color=INK, y=1.02)
        save(fig, "p3_fig03a_collapse_problem.png")


# ---------------------------------------------------------------------------------------------------------------------
# Mechanism diagrams
# ---------------------------------------------------------------------------------------------------------------------
def _box(ax, x, y, w, h, text, fc="#f3f3f1", ec=MUTED, fs=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal")


def _arrow(ax, a, b, color=INK2, text=None, off=(0, 0.12), rad=0.0, fs=8.5):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.4,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text, ha="center", va="bottom", fontsize=fs, color=color)


def fig_quota_diagram():
    fig, ax = plt.subplots(figsize=(12, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.0)
    ax.axis("off")
    _box(ax, 0.2, 1.6, 2.0, 1.2, "Task pool\n(375 open tasks,\n250 robots)")
    _box(ax, 3.0, 1.6, 2.6, 1.2, "Dispatcher\n(champion assignment:\ncheapest robot-task pair first)")
    _box(ax, 6.4, 1.3, 2.4, 1.8, "Credit check for every\ndoor the task crosses:\nin-flight + 1 <= quota K ?\n\nK = bandwidth x delay\n(door 6 inbound: K = 15)",
         fc="#fdf1ea", ec=ORANGE)
    _box(ax, 9.6, 2.7, 2.2, 1.0, "YES: give the task;\nin-flight += 1", fc="#eaf5ee", ec=OK)
    _box(ax, 9.6, 0.6, 2.2, 1.0, "NO: keep the robot\nwaiting, try its\nnext candidate", fc="#fdecec", ec=RED)
    _arrow(ax, (2.2, 2.2), (3.0, 2.2))
    _arrow(ax, (5.6, 2.2), (6.4, 2.2))
    _arrow(ax, (8.8, 2.5), (9.6, 3.2))
    _arrow(ax, (8.8, 1.9), (9.6, 1.1))
    _arrow(ax, (10.7, 3.7), (4.3, 2.85), color=BLUE, rad=0.35)
    ax.text(7.4, 4.62, "robot passes the door -> the next recount no longer counts it = credit returned (like an ACK)",
            ha="center", va="bottom", fontsize=8.5, color=BLUE)
    ax.text(6.0, 0.15, "Credit-based flow control sized by the bandwidth-delay product: door bandwidth about 26 robots per 500 ticks,\n"
            "delay = measured time from assignment to crossing. No probing, no packet loss, no slow start: K is computed from the map.",
            ha="center", fontsize=8.8, color=INK2)
    save(fig, "p3_fig04_quota_diagram.png")


def fig_executor_diagram():
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.0))
    for ax, fixed in zip(axes, [False, True]):
        ax.set_xlim(0, 11.2)
        ax.set_ylim(-0.55, 1.95)
        ax.axis("off")
        title = ("Official executor (bug): robot 1 has left cell A, but A's visit queue still lists robot 1 first"
                 if not fixed else "Fixed executor (3-line patch): when robot 1 leaves A, it is removed from A's queue at once")
        ax.text(0, 1.8, title, fontsize=9.5, color=RED if not fixed else OK, fontweight="bold")
        panels = [("tick t", 0.2), ("tick t+1", 4.0), ("next plan (one planning cycle later)", 7.8)]
        for t, x0 in panels:
            ax.text(x0, 1.45, t, fontsize=8.5, color=INK2)
            for i, lab in enumerate(["B", "A", "C"]):
                ax.add_patch(Rectangle((x0 + i * 0.95, 0.4), 0.9, 0.9, fc="#f3f3f1", ec=MUTED))
                ax.text(x0 + i * 0.95 + 0.08, 1.18, lab, fontsize=7.5, color=INK2)

        def robot(x0, cell, n, c):
            ax.add_patch(Circle((x0 + cell * 0.95 + 0.45, 0.82), 0.28, fc=c, ec="none"))
            ax.text(x0 + cell * 0.95 + 0.45, 0.82, str(n), ha="center", va="center", fontsize=9, color="white", fontweight="bold")

        def note(x0, text, c):
            ax.text(x0 + 1.4, 0.05, text, ha="center", va="top", fontsize=8, color=c)
        robot(0.2, 1, 1, BLUE); robot(0.2, 0, 2, ORANGE)
        note(0.2, "robot 1 moves A -> C, robot 2 plans B -> A\nqueue(A) = [1, 2]", INK2)
        robot(4.0, 2, 1, BLUE)
        if fixed:
            robot(4.0, 1, 2, ORANGE)
            note(4.0, "queue(A) = [2]: robot 2 enters A", OK)
            note(7.8, "no time lost", OK)
        else:
            robot(4.0, 0, 2, ORANGE)
            note(4.0, "queue(A) = [1, 2]: A looks taken,\nrobot 2's move is cut", RED)
            robot(7.8, 1, 2, ORANGE); robot(7.8, 2, 1, BLUE)
            note(7.8, "robot 2 only moves now", RED)
    save(fig, "p3_fig06_executor_diagram.png")


def fig_executor_data():
    by = by_key(rows_of(R52B))
    gains = [100 * st.mean(g) for g in paired(by, "N2F", "N2", OFFICIAL)]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    labs = ["before the fix", "after the fix\n(with breakdowns)", "after the fix\n(breakdowns off)"]
    v = [22, 26, 45]                                   # read-through notes, wait-v27 (rounds 36-37)
    a1.bar(labs, v, color=[GRAY, BLUE, AQUA], width=0.55)
    for i, x in enumerate(v):
        a1.text(i, x + 0.8, f"{x}", ha="center", fontsize=9.5, color=INK)
    a1.set_ylabel("robots through the key door per 500 ticks", fontsize=9, color=INK2)
    a1.set_title("The key door was stuck at 22 robots per 500 ticks\nuntil the executor was fixed (rounds 36-37)", fontsize=10, color=INK)
    a1.set_ylim(0, 52)
    style(a1)
    a2.bar([CARS[m] for m in OFFICIAL], gains, color=BLUE, width=0.5)
    for i, g in enumerate(gains):
        a2.text(i, g + 0.3, f"{g:+.1f}%", ha="center", fontsize=9.5, color=INK)
    a2.set_ylabel("fixed executor vs champion assignment only", fontsize=9, color=INK2)
    a2.set_title(f"Formal evaluation: fixing only the executor,\nmean {st.mean(gains):+.1f}% (20 paired runs per size)", fontsize=10, color=INK)
    a2.set_ylim(0, 15)
    style(a2)
    save(fig, "p3_fig07_executor_data.png")


def fig_deadlock_diagram():
    for after in (False, True):
        fig, ax = plt.subplots(figsize=(6.4, 5.6))
        ax.set_xlim(-0.2, 6.2)
        ax.set_ylim(-0.8, 5.2)
        ax.set_aspect("equal")
        ax.axis("off")
        for x in range(6):
            for y in range(5):
                wall = (y == 3 and x != 2) or (x == 3 and y != 2 and y < 3)
                ax.add_patch(Rectangle((x, y), 1, 1, fc="#3b4049" if wall else "#ffffff", ec=GRID))
        ax.add_patch(Rectangle((2, 3), 1, 1, fc="#fff3c4", ec=INK))   # north door
        ax.add_patch(Rectangle((3, 2), 1, 1, fc="#fff3c4", ec=INK))   # east door
        ax.text(2.5, 4.5, "north door (below)", ha="center", fontsize=8, color=INK2)
        ax.text(4.55, 2.5, "<- east door", ha="left", va="center", fontsize=8, color=INK2)
        ax.text(1.95, 2.5, "junction ->", ha="right", va="center", fontsize=8, color=INK2)

        def robot(x, y, n, c):
            ax.add_patch(Circle((x + 0.5, y + 0.5), 0.33, fc=c, ec="none"))
            ax.text(x + 0.5, y + 0.5, n, ha="center", va="center", fontsize=9, color="white", fontweight="bold")
        if not after:
            robot(2, 2, "A", ORANGE); robot(3, 2, "B", BLUE); robot(2, 3, "C", "#7a5cc7")
            _arrow(ax, (2.85, 2.6), (3.15, 2.6), color=RED)
            _arrow(ax, (3.15, 2.4), (2.85, 2.4), color=RED)
            _arrow(ax, (2.5, 3.15), (2.5, 2.85), color=RED)
            ax.text(2.5, -0.15, "the cell below A is free, but the door rule says A must not leave the approach zone", ha="center",
                    va="top", fontsize=8, color=RED)
            ax.set_title("Deadlock: A waits for B, B waits for A, C waits for the junction.\n"
                         "Seen once from tick 330 to tick 2192:\nthe door passed 5 robots instead of 199", fontsize=9.5, color=RED)
        else:
            robot(2, 1, "A", ORANGE); robot(2, 2, "B", BLUE); robot(2, 3, "C", "#7a5cc7")
            _arrow(ax, (2.5, 1.95), (2.5, 1.55), color=OK)
            _arrow(ax, (3.2, 2.5), (2.85, 2.5), color=OK)
            ax.set_title("Watchdog: a robot that has a task, has stood still 300 ticks,\nat a door nobody entered for 300 ticks,"
                         " ignores the door rule\nfor this tick (the collision check is kept)", fontsize=9.5, color=OK)
            ax.text(2.5, -0.15, "A steps aside, B comes out, traffic flows again", ha="center", va="top", fontsize=8.5, color=OK)
        save(fig, "p3_fig09b_watchdog_fix.png" if after else "p3_fig09a_deadlock.png")


def _read_map(path):
    lines = open(path).read().splitlines()
    i = lines.index("map") + 1
    return [[1 if ch in "@T" else 0 for ch in row] for row in lines[i:]]


def fig_generated_maps():
    inst = json.load(open(os.path.join(RERUN, "maps_gen4x4", "instances.json")))
    names = sorted({k.rsplit("_", 1)[0] for k in inst})
    off = os.path.join(EM, "网络协议方向", "harness", "data", "pkg", "maps", "room", "room-64-64-16.map")
    fig, axes = plt.subplots(1, 1 + len(names), figsize=(2.0 * (1 + len(names)), 2.6))
    for ax, (title, path) in zip(axes, [("official map", off)] +
                                 [(n.replace("room", ""), os.path.join(RERUN, "maps_gen4x4", n + ".map")) for n in names]):
        ax.imshow(_read_map(path), cmap="Greys", interpolation="nearest", vmin=0, vmax=1.6)
        ax.set_title(title, fontsize=9, color=ORANGE if title == "official map" else INK)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Random-door generator: same 4x4 room frame (64x64, 16 rooms), doors placed at random\n"
                 "(random spanning tree + extra links with prob. 0.25; each joined wall gets 1 or 2 door cells). Every seed kept.",
                 fontsize=10, color=INK, y=1.12)
    save(fig, "p3_fig08_generated_maps.png")


def fig_generalization():
    rows = rows_of(GEN)
    by = by_key(rows)
    insts = sorted({r["map"] for r in rows}, key=lambda k: (k.rsplit("_", 1)[0], int(k.rsplit("_", 1)[1])))
    comps = [("full method vs base\n(champion + fixed executor)", "FULL", "NONE", BLUE),
             ("remove the global cap", "noGlobal", "FULL", ORANGE),
             ("remove the watchdog", "noWD", "FULL", "#7a5cc7")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharey=True)
    for ax, (title, a, b, c) in zip(axes, comps):
        G = paired(by, a, b, insts)
        vals = [100 * st.mean(g) for g in G]
        m, lo, hi = (100 * x for x in boot(G))
        ys = list(range(len(insts)))[::-1]
        ax.barh(ys, vals, color=c, height=0.65)
        lo_x, hi_x = min(0, min(vals)), max(0, max(vals))
        pad = 0.18 * (hi_x - lo_x)
        ax.set_xlim(lo_x - pad, hi_x + pad)
        off = 0.02 * (hi_x - lo_x + 2 * pad)
        for y, v in zip(ys, vals):
            ax.text(v + (off if v >= 0 else -off), y, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=7.5, color=INK)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(f"{title}\nmean {m:+.1f}%  [95%: {lo:+.1f}, {hi:+.1f}]", fontsize=9.5, color=INK)
        style(ax, ygrid=False, xgrid=True)
    axes[0].set_yticks(list(range(len(insts)))[::-1])
    axes[0].set_yticklabels([k.replace("room", "").replace("_", ", ") + " robots" for k in insts], fontsize=8)
    fig.suptitle("Generalization test on 8 random-door 4x4 room maps x 2 robot counts (10 paired runs each, new seeds)",
                 fontsize=10.5, color=INK, y=1.09)
    fig.text(0.5, -0.03, "change in tasks completed (%) per instance", ha="center", fontsize=9, color=INK2)
    save(fig, "p3_fig10_generalization.png")


# ---------------------------------------------------------------------------------------------------------------------
# Research history figures
# ---------------------------------------------------------------------------------------------------------------------
def fig_roadmap():
    ev = [  # project round N; protocol round P_N = project round 75+N (read-through notes)
        ("rounds 1-10", "(1) evaluation bugs:\nfixed seed, uninitialised var", INFO),
        ("rounds 11-16", "TCP-style window\nroom maps +16% (1200 ticks)", OK),
        ("round 25", "champion assignment\nabsorbs earlier gains", INFO),
        ("rounds 27-29", "(2) full 5000-tick runs show\ncollapse; quota + door +55%", OK),
        ("rounds 36-37", "(3) door stuck at 22:\nexecutor fix -> 26 / 45", OK),
        ("rounds 41-47", "three laws replace\nhand tuning (no worse)", OK),
        ("round 52", "formal evaluation (room)\n+140.5% vs starter", OK),
        ("rounds 53-62", "(4) door pricing -5.2%\nsegment routing -39..-55%", FAIL),
        ("P35-36", "(5) PFC watchdog: only\nconfirmed protocol", OK),
        ("P53-55", "(4) HN-SPF -25.9%\nCSPF -21.0%", FAIL),
        ("P60-69", "(6) three quota tweaks:\ndev pass, confirm ~0", PEND),
        ("P74-75", "(6) 4-mechanism combo\ndev +3.15%, not confirmed", PEND),
        ("P78", "VOQ at doors\ndev +1.07%, pending", PEND),
        ("later 41 rounds", "offline models,\nnumber checks", INFO),
        ("2026-11-18", "re-test + random-door\nmaps (this part)", OK),
    ]
    fig, ax = plt.subplots(figsize=(15, 5.8))
    n = len(ev)
    for a, b, lab, c in [(0, 7, "Phase 1: control doors with network laws (project rounds 1-75)", "#eef4fc"),
                         (8, 12, "Protocol phase: port one protocol per round (P01-P78)", "#fdf1ea"),
                         (13, 14, "Checks & re-test", "#f3f3f1")]:
        ax.axvspan(a - 0.5, b + 0.5, color=c, zorder=0)
        ax.text((a + b) / 2, 3.05, lab, ha="center", va="center", fontsize=10, color=INK2)
    ax.axhline(0, color=MUTED, lw=1.5, zorder=1)
    for i, (rnd, lab, col) in enumerate(ev):
        side = 1 if i % 2 == 0 else -1
        y = side * (1.0 if (i // 2) % 2 == 0 else 2.05)
        ax.plot([i, i], [0, y - side * 0.35], color=col, lw=1, zorder=2)
        ax.scatter([i], [0], s=80, color=col, edgecolor=SURF, lw=1.5, zorder=3)
        ax.text(i, y, lab, ha="center", va="center", fontsize=8.3, color=INK,
                bbox=dict(boxstyle="round,pad=0.35", fc=SURF, ec=col, lw=1.3))
        ax.text(i + 0.08, -0.2 * side, rnd, ha="left", va="center", fontsize=7.3, color=INK2)
    for lab, col in [("kept in the final method / confirmed", OK), ("failed / negative result", FAIL),
                     ("passed development, not confirmed or pending", PEND), ("found a problem / fixed evaluation / diagnosis", INFO)]:
        ax.scatter([], [], s=60, color=col, label=lab)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False, fontsize=9)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-2.7, 3.35)
    ax.axis("off")
    save(fig, "p3_fig11_roadmap.png")


def fig_ruler():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.5), gridspec_kw={"width_ratios": [1.2, 1]})
    seeds = ["seed 0\n(hard-coded)", "seed 1", "seed 2", "seed 3", "seed 4"]
    vals = [195.8, 187.1, 189.4, 182.9, 180.8]          # read-through notes, wait-v9
    a1.bar(seeds, vals, color=[ORANGE] + [GRAY] * 4, width=0.6)
    for i, v in enumerate(vals):
        a1.text(i, v + 0.4, f"{v}", ha="center", fontsize=9, color=INK)
    a1.set_ylim(175, 199)
    a1.set_ylabel("tasks completed (room map, 200 robots)", fontsize=9, color=INK2)
    a1.set_title("The evaluator hard-coded the planner seed to 0:\nchanging only the seed moves the score by up to 8% (axis starts at 175)",
                 fontsize=9.5, color=INK)
    style(a1)
    v2 = [16.2, 16.0]                                   # read-through notes, wait-v10; number check, round 109
    a2.bar(["room map\n200 robots", "room map\n300 robots"], v2, color=BLUE, width=0.5)
    for i, v in enumerate(v2):
        a2.text(i, v + 0.4, f"{v:+.1f}%", ha="center", fontsize=9.5, color=INK)
    a2.set_ylim(0, 20)
    a2.set_ylabel("TCP-style window W=2 vs then baseline", fontsize=9, color=INK2)
    a2.set_title("After fixing the evaluator (1200 ticks, round 16):\nthe window gives about +16% on the room map", fontsize=9.5, color=INK)
    style(a2)
    save(fig, "p3_fig12_fix_the_ruler.png")


def fig_routing():
    items = [  # (name, change %, phase); sources in comments
        ("Segment routing v1 (best of 6 maps)", -39.2, 1),      # protocol notes, rounds 103-105: -39.2% to -55.4%
        ("HN-SPF capped link cost A", -25.88, 2),               # p53/p54
        ("HN-SPF capped link cost B", -24.71, 2),
        ("CSPF detour limit <=10%", -20.98, 2),                 # p55
        ("FRER backup door B=10", -9.88, 2),                    # p14
        ("CSPF detour limit <=25%", -8.70, 2),
        ("HN-SPF capped link cost C", -7.93, 2),                # number check line 547
        ("HN-SPF capped link cost D", -6.80, 2),
        ("FRER backup door B=3", -6.04, 2),
        ("Door-cell pricing (5 maps, quick run)", -5.2, 1),     # round 53, wait-v43
        ("Shared-cell cost doubled", -3.76, 1),                 # round 110 note
        ("BFD+LFA reroute around failures", -2.07, 2),          # p04
        ("Fortz-Thorup cell weights", -0.29, 2),                # number check line 533
        ("System-optimal door toll", -0.06, 1),                 # round 109
        ("Route-flap damping (confirmation)", 0.20, 2),         # p57, number check line 535
    ]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    names = [i[0] for i in items][::-1]
    vals = [i[1] for i in items][::-1]
    cols = [((FAIL if ph == 2 else ORANGE) if v < -1 else GRAY) for (_, v, ph) in items][::-1]
    ax.barh(names, vals, color=cols, height=0.62)
    for i, v in enumerate(vals):
        ax.text(v - 0.6 if v < 0 else v + 0.6, i, f"{v:+.2f}%" if abs(v) < 10 else f"{v:+.1f}%",
                va="center", ha="right" if v < 0 else "left", fontsize=8.5, color=INK)
    ax.axvline(0, color=MUTED, lw=1)
    ax.axvline(-1, color=INK2, lw=1, ls="--")
    ax.text(-1.3, len(items) - 0.4, "cut-off -1%", fontsize=8.5, color=INK2, ha="right")
    ax.set_xlim(-46, 6)
    ax.set_xlabel("change in tasks completed vs the then baseline (room maps)", fontsize=9, color=INK2)
    ax.legend(handles=[Patch(color=ORANGE, label="phase 1 (traffic engineering, pricing, fixed routes)"),
                       Patch(color=FAIL, label="protocol phase (backbone routing protocols)"),
                       Patch(color=GRAY, label="within +-1% (no measurable effect)")], fontsize=8.5, frameon=False, loc="lower left")
    ax.set_title("Every 'take another route' idea failed: the door is the only way between rooms", fontsize=11, color=INK)
    style(ax, ygrid=False, xgrid=True)
    save(fig, "p3_fig13_routing.png")


def fig_funnel():
    inv = load("p72/inventory_p72.json")
    cnt, total = inv["按结局"], inv["总机制数"]
    widths = [total, total - cnt["先量跳过"], cnt["过开发没确认"] + cnt["确认通过"], cnt["确认通过"]]
    stages = [f"proposed with a written protocol: {widths[0]}", f"passed 'measure first', went to development: {widths[1]}",
              f"passed development: {widths[2]}", f"confirmed on new maps: {widths[3]}"]
    cols = [GRAY, LBLUE, PEND, OK]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for i, (w, s, c) in enumerate(zip(widths, stages, cols)):
        ax.barh(i, w, left=(total - w) / 2, color=c, height=0.7)
        if w > 30:
            ax.text(total / 2, i, s, ha="center", va="center", fontsize=9.5, color=INK)
        else:
            ax.text(total / 2 + w / 2 + 1, i, s, ha="left", va="center", fontsize=9.5, color=INK)
    drop = [f"-> stopped at 'measure first': {cnt['先量跳过']}", f"-> failed development: {cnt['开发没过']}",
            f"-> not confirmed on new maps: {cnt['过开发没确认']}"]
    for i, d in enumerate(drop):
        ax.text(total + 3, i + 0.5, d, fontsize=9, color=INK2, va="center")
    ax.set_ylim(3.6, -0.6)
    ax.set_xlim(-2, total + 2)
    ax.axis("off")
    ax.set_title("Protocol phase, rounds 1-71: 69 network mechanisms, only the watchdog passed all four gates", fontsize=11, color=INK)
    save(fig, "p3_fig14_funnel.png")


def room_mean(rel):
    xs = [r["mean"] for r in load(rel)["per_inst"] if r["inst"].startswith("room")]
    return 100 * st.mean(xs)


def fig_dev_vs_confirm():
    items = [("PFC deadlock watchdog (P35-36)", "p36/dev_compare_d300.json", "p36/confirm_compare.json"),
             ("4-mechanism combo (P74-75)", "p74/dev_compare_c4.json", "p75/confirm_compare.json"),
             ("Split 2-cell doors (P74 alone -> P76 real doors)", "p74/dev_compare_pick.json", "p76/confirm_compare.json"),
             ("3-mechanism combo (P74-75)", "p74/dev_compare_c3.json", "p75/confirm_compare_c3.json"),
             ("Auto-bandwidth cut quotas (P68-69)", "p68/dev_compare_B2.json", "p69/confirm_compare.json")]
    items = sorted([(n, room_mean(d), room_mean(c)) for n, d, c in items], key=lambda t: -t[1])
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for i, (n, d, c) in enumerate(items):
        up = c > d
        ax.plot([d, c], [i, i], color=OK if up else GRAY, lw=2, zorder=1)
        ax.scatter([d], [i], s=60, color=BLUE, zorder=2)
        ax.scatter([c], [i], s=70, color=OK if up else ORANGE, zorder=3, marker="D")
        ax.text(max(d, c) + 0.12, i, f"{d:+.2f}% -> {c:+.2f}%" + ("  confirmed" if up else ""), va="center", fontsize=8.8, color=INK)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t[0] for t in items], fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlim(-0.6, 4.8)
    ax.scatter([], [], s=60, color=BLUE, label="development (17 room instances)")
    ax.scatter([], [], s=70, color=ORANGE, marker="D", label="confirmation (15 room instances, new seeds, 20 runs each)")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    ax.set_xlabel("change in tasks completed (%) vs the then baseline", fontsize=9, color=INK2)
    ax.set_title("Development gains shrink on unseen room maps; only the watchdog grew", fontsize=11, color=INK)
    style(ax, ygrid=False, xgrid=True)
    save(fig, "p3_fig15_dev_vs_confirm.png")


def fig_combo():
    dev = load("p74/dev_compare_c4.json")["per_inst"]
    con = [r for r in load("p75/confirm_compare.json")["per_inst"] if r["inst"].startswith("room")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.9), sharey=True, gridspec_kw={"width_ratios": [17, 15]})
    for ax, data, title in [(a1, dev, f"development (17 room maps, mean {room_mean('p74/dev_compare_c4.json'):+.2f}%)"),
                            (a2, con, f"confirmation (15 room maps, mean {room_mean('p75/confirm_compare.json'):+.2f}%)")]:
        data = sorted(data, key=lambda r: -r["mean"])
        vals = [100 * r["mean"] for r in data]
        ax.bar(range(len(vals)), vals, color=[(ORANGE if r["inst"] in OFFICIAL else BLUE) for r in data], width=0.7)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([r["inst"] for r in data], rotation=70, fontsize=7)
        ax.axhline(0, color=MUTED, lw=1)
        ax.text(0, vals[0] + 0.5, f"{vals[0]:+.1f}%", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_title(title, fontsize=10, color=INK)
        style(ax)
    a1.set_ylabel("change in tasks completed (%)", fontsize=9, color=INK2)
    a1.set_ylim(-3, 19)
    a1.legend(handles=[Patch(color=ORANGE, label="official 4x4 room map (200/250/300)"), Patch(color=BLUE, label="other room maps")],
              fontsize=8.5, frameon=False, loc="upper right")
    fig.suptitle("Four mechanisms together: the gain comes from a few congested maps; the official map barely moves",
                 fontsize=11, color=INK, y=1.02)
    save(fig, "p3_fig16_combo.png")


def fig_watchdog_confirm():
    data = sorted([r for r in load("p36/confirm_compare.json")["per_inst"] if r["inst"].startswith("room")], key=lambda r: -r["mean"])
    vals = [100 * r["mean"] for r in data]
    fig, ax = plt.subplots(figsize=(10, 3.3))
    ax.bar(range(len(vals)), vals, color=[(ORANGE if r["inst"] in OFFICIAL else BLUE) for r in data], width=0.7)
    for i, v in enumerate(vals):
        ax.text(i, v + (0.25 if v >= 0 else -0.25), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([r["inst"] for r in data], rotation=60, fontsize=7.5)
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_ylabel("change in tasks completed (%)", fontsize=9, color=INK2)
    ax.set_ylim(-1.5, 12.5)
    ax.legend(handles=[Patch(color=ORANGE, label="official 4x4 room map"),
                       Patch(color=BLUE, label="generated room maps (held out, never used in development)")], fontsize=8.5, frameon=False)
    ax.set_title("Watchdog confirmation (P36, 20 runs per map): gains on a few deadlock-prone generated maps", fontsize=10.5, color=INK)
    style(ax)
    save(fig, "p3_fig17_watchdog_confirm.png")


def copy_english_figures():
    for dst, src in {"p3_en_problem.png": "en_01_problem.png", "p3_en_map_to_network.png": "en_03_map_to_network.png",
                     "p3_en_ring_vs_door.png": "en_05_pibt_ring_vs_door.png", "p3_en_door_rule.png": "en_06_door_rule.png",
                     "p3_en_door6_filmstrip.png": "en_07_door6_filmstrip.png", "p3_en_formulas.png": "en_08_four_numbers.png",
                     "p3_en_knee.png": "en_09_knee.png", "p3_en_tick3000.png": "en_10_tick3000.png"}.items():
        shutil.copyfile(os.path.join(ENFIG, src), os.path.join(OUT, dst))
        print("copied", dst)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    copy_english_figures()
    fig_collapse(with_ours=False)
    for f in [fig_ablation, fig_synergy, fig_ladder, fig_collapse, fig_quota_diagram, fig_executor_diagram, fig_executor_data,
              fig_deadlock_diagram, fig_generated_maps, fig_roadmap, fig_ruler, fig_routing, fig_funnel, fig_dev_vs_confirm,
              fig_combo, fig_watchdog_confirm]:
        f()
    if os.path.exists(GEN):
        fig_generalization()
