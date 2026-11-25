"""Two figures for the deck's principle slides (run from the repo root):
  figures/deck/fig_bdp_principle.png  -- how big a door's quota should be, from Little's law (theory sketch + door-6 numbers)
  figures/deck/fig_quota_deck.png     -- per-door quota formula (same as figures/brief/b_f2_quota.png, retitled)
  figures/deck/fig_door_util_curve.png -- door utilization U(n) as a curve (slide 14)
  figures/deck/fig_door_rule_deck.png -- door rule in detail: buffer geometry and switching rule, buffer-size sweep, 18.7-tick budget
  figures/deck/fig_bbr_loop.png       -- BBR's control loop, mapped onto DoorFlow, with the measured delay ratios of round 50
  figures/deck/fig_door_util.png      -- door utilization formula (same as figures/brief/b_f3_door_rule.png, retitled)
Numbers in fig_bbr_loop: 26 crossings / 500 ticks (13 per direction), 2.23, 138 (report sec. 6); real / model delay
1.5x on the cuts in our model, 2.16-2.40x and 2.81x, 2.88x on the missed cuts (round 50, wait-v40; notes 第1-75轮_通读笔记.md
and the comment in window_control.cpp); BBR facts from Cardwell et al., ACM Queue 2016."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

INK, TEAL, ORG, RED, GREY, LIGHT, PALE = "#1B2631", "#0F6E7E", "#E39B2D", "#C0392B", "#5D6D7E", "#EDF2F4", "#FBEFD9"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GREY, "axes.labelcolor": INK,
                     "xtick.color": GREY, "ytick.color": GREY, "mathtext.fontset": "dejavusans"})


def bdp_principle(path):
    """How big should a door's quota be? Derived from the counting rule N = X * T (known as Little's law; theory sketch, no measured data)."""
    C, T0 = 1.0, 1.0                     # door rate, trip time with no queue (units: the best quota = 1)
    best = C * T0
    N = np.linspace(0, 3.0, 600)
    X = np.minimum(N / T0, C)                       # Little: X = N / T as long as T = T0
    T = np.maximum(T0, N / C)                       # Little: T = N / X once X is capped at C
    Xr = np.where(N <= best, N / T0, C * np.exp(-0.95 * (N - best)))   # robots: blocking pulls the rate down (sketch)
    fig = plt.figure(figsize=(7.4, 5.9), dpi=220)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.08, left=0.1, right=0.97, top=0.88, bottom=0.15)
    a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    for ax in (a1, a2):
        ax.axvspan(0, best, color=LIGHT, zorder=0)
        ax.axvspan(best, 3.0, color=PALE, zorder=0)
        ax.axvline(best, color=ORG, ls="--", lw=1.6, zorder=2)
        ax.set_xlim(0, 3.0)
        ax.spines[["top", "right"]].set_visible(False)
    a1.plot(N, X, color=TEAL, lw=2.8)
    a1.plot(N, Xr, color=RED, lw=2.4, ls=(0, (5, 2)))
    a1.text(2.05, C + 0.05, "ideal door: more robots, more crossings, up to $C$", color=TEAL, fontsize=9, ha="center")
    a1.set_ylim(0, 1.42); a1.set_yticks([0, C]); a1.set_yticklabels(["0", "$C$"])
    a1.set_ylabel("robots crossing per tick, $X$")
    a1.text(0.5 * best, 1.27, "too few on the way:\nthe door sometimes waits", ha="center", va="center", color=GREY, fontsize=9)
    a1.text(best + (3 - best) / 2, 1.27, "too many: the door is full,\nextra robots only queue", ha="center", va="center", color=GREY, fontsize=9)
    a1.annotate("robots at a one-cell door (sketch):\nwaiting robots block the other side,\nso the rate falls", xy=(1.4, C * np.exp(-0.95 * 0.4)), xytext=(1.04, 0.2),
                color=RED, fontsize=8.8, ha="left", va="center", arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.0))
    a1.scatter([best], [C], s=70, color=ORG, zorder=5, edgecolor="white", lw=1.2)
    a1.annotate("best quota\n$N^{*}=C\\cdot T_0$", xy=(best, C), xytext=(0.03, 0.9), color=ORG, fontsize=9.5,
                fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=ORG, lw=1.0))
    a1.tick_params(labelbottom=False)
    a2.plot(N, T, color=TEAL, lw=2.8)
    a2.annotate("past the best quota, extra robots\nonly add waiting time", xy=(2.3, 2.3), xytext=(1.15, 2.6),
                color=GREY, fontsize=9, ha="left", arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.0))
    a2.text(1.95, 0.42, "door 6, inward:  $C$ = 13 per 500 ticks,\n$T_0$ = 2.23 x 247 ticks  ->  $N^{*}$ = 14.3  ->  quota 15",
            fontsize=8.6, color=INK, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=ORG, lw=1.0))
    a2.set_ylim(0, 3.1); a2.set_yticks([0, T0]); a2.set_yticklabels(["0", "$T_0$"])
    a2.set_ylabel("trip time $T$")
    a2.set_xticks([0, best]); a2.set_xticklabels(["0", "$C\\cdot T_0$"])
    a2.set_xlabel("robots on the way: hold an order through the door, not crossed yet, $N$")
    fig.text(0.1, 0.955, "How many robots should head for a door?", fontsize=12.5, fontweight="bold", color=INK)
    # v38: the counting rule itself is printed on the slide next to the figure, so the figure no longer repeats it
    fig.text(0.1, 0.034, "$C$: door rate per direction    $T_0$: trip time while the door has no queue (door 6: 2.23 x free trip, measured)    theory sketch",
             fontsize=7.8, color=GREY, style="italic")
    fig.text(0.1, 0.008, "The counting rule $N = X\\cdot T$ is known in queueing theory as Little's law.",
             fontsize=7.8, color=GREY, style="italic")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def quota_fig(path):
    """Deck copy of figures/brief/b_f2_quota.png (same formula and notes), titled without network terms."""
    with plt.rc_context({"mathtext.fontset": "dejavuserif"}):
        fig = plt.figure(figsize=(8, 2.3), dpi=200)
        fig.text(0.03, 0.86, "Per-door quota (door rate x trip time)", fontsize=14, weight="bold", color="#1f2937")
        fig.text(0.05, 0.52, r"$K = \lceil\, \alpha \, T \, \dfrac{C}{2} \,\rceil = \lceil\, 2.23 \times \dfrac{247}{500} \times 13 \,\rceil = \lceil 14.3 \rceil = 15$",
                 fontsize=15, color="#111827", va="center")
        for i, line in enumerate(["inbound T = 247 ticks -> 15 robots;  outbound T = 158 ticks -> 10 robots",
                                  "T = free trip to the door;  C/2 = 13 robots per 500 ticks per direction;  alpha = 2.23 measured slowdown"]):
            fig.text(0.05, 0.20 - i * 0.12, line, fontsize=9.5, color="#4b5563")
        fig.savefig(path, facecolor="white", bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)


def door_util(path):
    """Deck copy of figures/brief/b_f3_door_rule.png (same formula and notes), retitled without network terms."""
    with plt.rc_context({"mathtext.fontset": "dejavuserif"}):
        fig = plt.figure(figsize=(8, 2.3), dpi=200)
        fig.text(0.03, 0.86, "Door utilization (one direction at a time, served in turns)", fontsize=14, weight="bold", color="#1f2937")
        fig.text(0.05, 0.52, r"$U(n) = \dfrac{n\,h}{(n-1)\,h + s} = \dfrac{9n}{9(n-1) + 21}$      $U(1) = 43\%$,   $U(10) = 88\%$",
                 fontsize=15, color="#111827", va="center")
        for i, line in enumerate(["n = robots let through per turn;  h = 9 ticks between two robots in the same direction",
                                  "s = 21 ticks to switch direction (h and s measured)"]):
            fig.text(0.05, 0.20 - i * 0.12, line, fontsize=9.5, color="#4b5563")
        fig.savefig(path, facecolor="white", bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)


def door_util_curve(path):
    """Door utilization U(n) = n h / ((n - 1) h + s) with h and s measured in 5 DoorFlow runs (demo/door_timing.json:
    medians of the same-direction gap and of the switch gap at door 6), as a curve; marks the measured robots per turn."""
    import json, os
    m = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo", "door_timing.json")))
    h, s, nbar = m["same_direction_gap"]["median"], m["switch_gap"]["median"], m["robots_per_turn"]
    f = lambda k: k * h / ((k - 1) * h + s) * 100
    n = np.arange(1, 31)
    fig, ax = plt.subplots(figsize=(6.6, 4.3), dpi=220)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.80, bottom=0.14)
    ax.fill_between(n, f(n), 100, color=PALE, zorder=0)
    ax.plot(n, f(n), color=TEAL, lw=2.8, marker="o", ms=3.5)
    for k, lab, dx, dy in [(1, f"1 robot per turn: {h:g} / {s:g} = {f(1):.0f}%", 2.0, -4),
                           (10, f"10 per turn: {10 * h:g} / {s + 9 * h:g} = {f(10):.0f}%", 2.5, -12)]:
        ax.scatter([k], [f(k)], s=70, color=ORG, zorder=5, edgecolor="white", lw=1.2)
        ax.annotate(lab, xy=(k, f(k)), xytext=(k + dx, f(k) + dy), fontsize=9.5, color=INK, fontweight="bold",
                    arrowprops=dict(arrowstyle="-|>", color=ORG, lw=1.0))
    ax.axvline(nbar, color=GREY, ls=":", lw=1.2)
    ax.text(nbar + 0.4, 36, f"measured: {nbar:g} robots\nper turn on average", fontsize=8.8, color=GREY, va="bottom")
    ax.text(10.6, 97.6, f"shaded: time lost to switching ({s - h:g} extra ticks per switch)", fontsize=8.6, color=ORG, ha="left", va="center")
    ax.set_xlim(0, 31); ax.set_ylim(20, 104)
    ax.set_xlabel("robots let through per turn, $n$", fontsize=10); ax.set_ylabel("door speed, share of its top speed (%)", fontsize=9.5)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=9)
    fig.text(0.02, 0.94, "Door speed: one direction at a time, served in turns", fontsize=12, fontweight="bold", color=INK)
    with plt.rc_context({"mathtext.fontset": "dejavuserif"}):
        fig.text(0.02, 0.865, r"$U(n)=\dfrac{n\,h}{(n-1)\,h+s}=\dfrac{%gn}{%g(n-1)+%g}$" % (h, h, s), fontsize=10.5, color=INK)
        fig.text(0.50, 0.875, f"$h$ = {h:g} ticks to the next robot, same direction\n$s$ = {s:g} ticks to switch direction (medians, 5 runs)", fontsize=9, color=GREY, va="center")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def door_rule_deck(path):
    """Door rule in detail (slide 13): buffer geometry + switching rule, buffer-size sweep, time budget of one crossing.
    Sweep: 12 dev instances vs 4 cells (v58 appendix H, table after 'later in 12 dev instances'); 3 cells confirmation
    -2.64% [-3.41, -1.83], deadlocked runs 11 -> 29 (rounds 54-57). Time budget: round 52 (wait-v42), official 250-robot
    map, second half of 5 runs, 669 crossings of door 6: 18.7 ticks per crossing."""
    from matplotlib.patches import Rectangle, Circle, Patch
    from matplotlib.lines import Line2D
    fig = plt.figure(figsize=(13.0, 5.2), dpi=200)
    # ---- A: buffer geometry ----
    ax = fig.add_axes([0.015, 0.25, 0.40, 0.63]); ax.set_aspect("equal"); ax.axis("off")
    R, Cn, dr, dc = 9, 13, 4, 6
    def dist(r, c): return abs(r - dr) + abs(c - dc)
    for r in range(R):
        for c in range(Cn):
            x, y = c, R - 1 - r
            if c == dc and r != dr: fc = "#3a4650"
            elif c == dc: fc = "#1B2631"
            elif dist(r, c) <= 4: fc = PALE
            else: fc = "white"
            ax.add_patch(Rectangle((x, y), 1, 1, fc=fc, ec="#d5dde2", lw=0.6))
    for r in range(R):     # exit fan on the receiving (right) side: within 3 steps, kept clear
        for c in range(dc + 1, Cn):
            if dist(r, c) <= 3: ax.add_patch(Rectangle((c, R - 1 - r), 1, 1, fc="none", ec=TEAL, lw=0, hatch="////", alpha=0.4))
    ax.add_patch(Rectangle((dc, R - 1 - dr), 1, 1, fc="none", ec="black", lw=2.2))
    BL, OR_, GR = "#2a78d6", "#eb6834", "#b9b8b2"
    def bot(r, c, col, mark=None):
        ax.add_patch(Circle((c + 0.5, R - 1 - r + 0.5), 0.36, fc=col, ec="white", lw=1.0, zorder=5))
        if mark: ax.text(c + 0.5, R - 1 - r + 0.5, mark, ha="center", va="center", fontsize=8.5, color="white", fontweight="bold", zorder=6)
    for c in (2, 3, 4, 5): bot(dr, c, BL)                       # active side, back to back
    bot(dr, dc, BL); ax.annotate("", xy=(dc + 2.3, R - 1 - dr + 0.5), xytext=(dc + 0.9, R - 1 - dr + 0.5), arrowprops=dict(arrowstyle="-|>", color=BL, lw=2))
    bot(dr - 1, dc + 2, BL)                                      # exiting robot moving away
    for (r, c) in [(dr, 11), (dr - 1, 10), (dr + 1, 10), (dr - 2, 11)]: bot(r, c, OR_)   # waiting side at the buffer edge
    bot(dr + 2, 11, OR_, "II")                                   # a waiting robot in a random pause
    for (r, c) in [(1, 1), (7, 1), (8, 12), (0, 9)]: bot(r, c, GR)
    ax.set_xlim(-0.2, Cn + 0.2); ax.set_ylim(-0.2, R + 0.2)
    fig.text(0.015, 0.925, "A  A one-cell door with a 4-cell buffer on each side", fontsize=10.5, fontweight="bold", color=INK)
    hs = [Line2D([], [], marker="o", ls="", ms=8, mfc=BL, mec="white", label="active side: crossing back to back"),
          Line2D([], [], marker="o", ls="", ms=8, mfc=OR_, mec="white", label="waiting side: queues at the buffer edge"),
          Line2D([], [], marker="o", ls="", ms=8, mfc=OR_, mec="white", label="II = random pause, but not in the exit"),
          Line2D([], [], marker="o", ls="", ms=8, mfc=GR, mec="white", label="not crossing this door"),
          Patch(fc=PALE, ec="#d5dde2", label="4-cell buffer"),
          Patch(fc="white", ec=TEAL, hatch="////", label="exit fan, kept clear (3 cells)")]
    fig.legend(handles=hs, loc="lower left", bbox_to_anchor=(0.01, 0.105), ncol=2, fontsize=8.2, frameon=False, handletextpad=0.4, columnspacing=1.2)
    fig.text(0.015, 0.06, "Rule:  serve side $s$;   wind down when $W_s(8)=0$ and $W_o(8)>0$;   switch when the door is empty and $A_s(4)=0$",
             fontsize=9.6, color=INK)
    fig.text(0.015, 0.018, "$W(8)$: crossers within 8 cells    $A(4)$: crossers inside the 4-cell buffer    robots held by the rule get the lowest priority",
             fontsize=8.4, color=GREY)
    # ---- B: buffer-size sweep ----
    b = fig.add_axes([0.52, 0.58, 0.455, 0.31])
    xs = [1, 2, 3, 4, 6]; m = [-9.0, -5.2, 0.2, 0.0, -4.2]; lo = [-10.0, -6.3, -0.6, 0.0, -5.5]; hi = [-8.0, -4.1, 1.1, 0.0, -2.8]
    for x, v, l, h in zip(xs, m, lo, hi):
        col = TEAL if x == 4 else (RED if v < -1 else GREY)
        b.plot([x, x], [l, h], color=col, lw=1.4); b.scatter([x], [v], s=46 if x != 4 else 80, color=col, zorder=5, marker="o" if x != 4 else "*")
    b.scatter([3], [-2.64], s=40, facecolor="white", edgecolor=RED, lw=1.5, zorder=6); b.plot([3, 3], [-3.41, -1.83], color=RED, lw=1.2, ls=":")
    b.axhline(0, color=GREY, lw=0.8, ls=":"); b.set_xticks(xs); b.set_xticklabels([f"{x} cell" + ("s" if x > 1 else "") for x in xs], fontsize=8.5)
    b.set_ylim(-11.5, 3.0); b.set_ylabel("change vs 4 cells (%)", fontsize=8.5); b.tick_params(labelsize=8)
    b.spines[["top", "right"]].set_visible(False)
    b.set_title("B  How big should the buffer be?  (12 dev instances, 95% intervals)", fontsize=10.5, fontweight="bold", color=INK, loc="left")
    b.text(1.15, -10.9, "too close: robots coming out\nstay 7.6 ticks in the door", fontsize=7.8, color=RED, va="bottom")
    b.text(5.95, -7.4, "too far: the queue\nblocks other doors", fontsize=7.8, color=RED, ha="right", va="top")
    b.text(3.12, -2.35, "3 cells: +0.2% on dev maps, but -2.64% in\nconfirmation; deadlocked runs 11 → 29", fontsize=7.6, color=RED, va="top")
    b.text(4.12, 0.9, "kept: 4 cells", fontsize=8.2, color=TEAL, fontweight="bold")
    # ---- C: where one crossing's 18.7 ticks go ----
    c = fig.add_axes([0.52, 0.04, 0.455, 0.36]); c.axis("off"); c.set_xlim(0, 18.7); c.set_ylim(0, 1)
    segs = [("move\nthrough", 3.0, "#7fb8c4"), ("wait for\nexit", 1.5, "#a9c7cf"), ("break-\ndown", 1.0, RED), ("next robot\narrives", 4.1, "#7fb8c4"),
            ("turn", 2.1, "#a9c7cf"), ("breakdown\nnear door", 3.8, RED), ("switch\nside", 2.2, ORG), ("other", 1.0, "#d5dde2")]
    x0 = 0
    for name, w, col in segs:
        c.add_patch(Rectangle((x0, 0.33), w, 0.28, fc=col, ec="white", lw=1.2))
        c.text(x0 + w / 2, 0.47, f"{w:g}", ha="center", va="center", fontsize=8.5, color="white" if col in (RED, ORG) else INK, fontweight="bold")
        c.text(x0 + w / 2, 0.29, name, ha="center", va="top", fontsize=7.0, color=INK)
        x0 += w
    c.text(0, 0.99, "C  Where one robot's 18.7 ticks at door 6 go  (round 52, 669 crossings)", fontsize=10.5, fontweight="bold", color=INK, va="top")
    c.text(0, 0.82, "random breakdowns: 1.0 + 3.8 = 4.8 ticks (26%)", fontsize=8.8, color=RED, va="center")
    c.text(0, 0.72, "door rate: 500 / 18.7 = 26.7 robots per 500 ticks  (measured: 26)", fontsize=8.8, color=INK, va="center")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def box(ax, x, y, w, h, title, body, fc, ec, tcol=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.025", fc=fc, ec=ec, lw=1.4))
    ax.text(x + 0.018, y + h - 0.03, title, fontsize=9.6, fontweight="bold", color=tcol, va="top")
    ax.text(x + 0.018, y + h - 0.085, body, fontsize=8.4, color=INK, va="top", linespacing=1.35)


def arrow(ax, p, q, col=TEAL, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=13, lw=1.6, color=col,
                                 connectionstyle=f"arc3,rad={rad}"))


def bbr_loop(path):
    fig = plt.figure(figsize=(7.6, 6.0), dpi=220)
    ax = fig.add_axes([0, 0.22, 1, 0.71]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.text(0.03, 0.955, "BBR's control loop, and how DoorFlow uses it", fontsize=12.5, fontweight="bold", color=INK)
    box(ax, 0.02, 0.72, 0.42, 0.25, "1  Measure every window",
        "delivery rate  $r_t$ = delivered / time\nround-trip time  $\\mathrm{RTT}_t$", LIGHT, TEAL)
    box(ax, 0.50, 0.72, 0.47, 0.25, "Why the minimum delay",
        "if the limit followed the current RTT:\njam $\\rightarrow$ longer RTT $\\rightarrow$ bigger limit $\\rightarrow$ worse jam",
        PALE, ORG, tcol=ORG)
    box(ax, 0.02, 0.22, 0.42, 0.35, "2  Filter (no loss needed)",
        "$\\mathrm{BtlBw}=\\max\\ r_t$  over ~10 RTTs\n   (delivery is never faster than the limit)\n"
        "$\\mathrm{RTprop}=\\min\\ \\mathrm{RTT}_t$  over 10 s\n   (a queue can only add delay)", LIGHT, TEAL)
    box(ax, 0.50, 0.22, 0.47, 0.35, "3  Limit and probe",
        "pacing rate $=g\\cdot\\mathrm{BtlBw}$\n   $g$ cycles 1.25, 0.75, 1, 1, ... (probe, drain)\n"
        "in flight $\\leq 2\\cdot\\mathrm{BtlBw}\\cdot\\mathrm{RTprop}$\nProbeRTT: drain briefly every 10 s", LIGHT, TEAL)
    arrow(ax, (0.23, 0.72), (0.23, 0.585))
    arrow(ax, (0.445, 0.40), (0.495, 0.40))
    arrow(ax, (0.56, 0.585), (0.40, 0.715), rad=0.25)
    ax.text(0.485, 0.625, "next\nwindow", fontsize=7.8, color=TEAL, ha="center", va="center")
    mx = fig.add_axes([0.03, 0.03, 0.58, 0.28]); mx.axis("off"); mx.set_xlim(0, 1); mx.set_ylim(0, 1)
    rows = [("BBR", "DoorFlow"),
            ("BtlBw", "door crossings: 26 / 500 ticks (13 per direction)"),
            ("RTprop", "no-queue time: shortest path x 2.23 (breakdowns)"),
            ("RTT / RTprop", "real time (on the way ÷ rate) / no-queue time: bars"),
            ("in-flight limit", "quota per door and direction (buffer size)"),
            ("one connection", "every door and direction at once; global cap 138")]
    for i, (a, b) in enumerate(rows):
        y = 0.92 - i * 0.17
        if i == 0:
            mx.text(0.0, y, a, fontsize=9.2, fontweight="bold", color=TEAL, va="center")
            mx.text(0.31, y, b, fontsize=9.2, fontweight="bold", color=ORG, va="center"); continue
        mx.add_patch(FancyBboxPatch((0.0, y - 0.07), 0.995, 0.14, boxstyle="round,pad=0.0,rounding_size=0.02",
                                    fc=LIGHT if i % 2 else "white", ec="none"))
        mx.text(0.01, y, a, fontsize=8.6, color=INK, va="center", fontweight="bold")
        mx.text(0.31, y, b, fontsize=8.3, color=INK, va="center")
    bx = fig.add_axes([0.69, 0.07, 0.29, 0.18])
    labels = ["cuts in\nour model", "missed\ncuts", "worst two\nmissed cuts"]
    lo, hi = [1.5, 2.16, 2.81], [1.5, 2.40, 2.88]
    cols = [TEAL, ORG, RED]
    for i in range(3):
        bx.bar(i, hi[i], color=cols[i], width=0.6, alpha=0.9)
        if hi[i] != lo[i]:
            bx.bar(i, hi[i] - lo[i], bottom=lo[i], color="white", width=0.6, alpha=0.45, hatch="////", edgecolor=cols[i])
        bx.text(i, hi[i] + 0.08, (f"{lo[i]:.1f}x" if lo[i] == hi[i] else f"{lo[i]:.2f}-{hi[i]:.2f}x"), ha="center",
                fontsize=7.4, color=INK)
    bx.axhline(1, color=GREY, lw=0.8, ls=":")
    bx.set_xticks(range(3)); bx.set_xticklabels(labels, fontsize=7.2)
    bx.set_ylim(0, 3.4); bx.set_yticks([0, 1, 2, 3]); bx.tick_params(labelsize=7.2)
    bx.spines[["top", "right"]].set_visible(False)
    bx.set_title("measured real / model delay (round 50)\n> 1 = the model's time is too short there", fontsize=7.9, color=INK, loc="left")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    bdp_principle("figures/deck/fig_bdp_principle.png")
    bbr_loop("figures/deck/fig_bbr_loop.png")
    door_util("figures/deck/fig_door_util.png")
    quota_fig("figures/deck/fig_quota_deck.png")
    door_rule_deck("figures/deck/fig_door_rule_deck.png")
    door_util_curve("figures/deck/fig_door_util_curve.png")
