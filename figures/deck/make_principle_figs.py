"""Two figures for the deck's principle slides (run from the repo root):
  figures/deck/fig_bdp_principle.png  -- Little's law and the bandwidth-delay product (theory sketch + where each method sits)
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
    C, T0, B = 1.0, 1.0, 1.15            # capacity, free trip time, buffer (in units of BDP)
    bdp = C * T0
    N = np.linspace(0, 3.0, 600)
    X = np.minimum(N / T0, C)                       # Little: X = N / T as long as T = T0
    T = np.maximum(T0, N / C)                       # Little: T = N / X once X is capped at C
    Xr = np.where(N <= bdp, N / T0, C * np.exp(-0.95 * (N - bdp)))   # robots: blocking pulls the rate down (sketch)
    fig = plt.figure(figsize=(7.4, 5.9), dpi=220)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.08, left=0.1, right=0.97, top=0.88, bottom=0.15)
    a1, a2 = fig.add_subplot(gs[0]), fig.add_subplot(gs[1], sharex=None)
    for ax in (a1, a2):
        ax.axvspan(0, bdp, color=LIGHT, zorder=0)
        ax.axvspan(bdp, bdp + B, color=PALE, zorder=0)
        ax.axvspan(bdp + B, 3.0, color="#F6DDD9", zorder=0)
        ax.axvline(bdp, color=ORG, ls="--", lw=1.6, zorder=2)
        ax.axvline(bdp + B, color=GREY, ls=":", lw=1.4, zorder=2)
        ax.set_xlim(0, 3.0)
        ax.spines[["top", "right"]].set_visible(False)
    a1.plot(N[N <= bdp + B], X[N <= bdp + B], color=TEAL, lw=2.8)
    a1.plot(N, Xr, color=RED, lw=2.4, ls=(0, (5, 2)))
    a1.text(1.62, C + 0.05, "network link: $X=\\min(N/T_0,\\,C)$", color=TEAL, fontsize=9, ha="center")
    a1.set_ylim(0, 1.42); a1.set_yticks([0, C]); a1.set_yticklabels(["0", "$C$"])
    a1.set_ylabel("delivery rate $X$")
    a1.text(0.5 * bdp, 1.27, "door / link\nsometimes idle", ha="center", va="center", color=GREY, fontsize=9)
    a1.text(bdp + B / 2, 1.27, "full: extra only\nwaits in a queue", ha="center", va="center", color=GREY, fontsize=9)
    a1.text(bdp + B + (3 - bdp - B) / 2, 1.27, "buffer overflow:\nTCP loses packets", ha="center", va="center", color=GREY, fontsize=9)
    a1.annotate("robots at a one-cell door (sketch):\nwaiting robots block the other side,\nso the rate falls", xy=(1.4, C * np.exp(-0.95 * 0.4)), xytext=(1.04, 0.2),
                color=RED, fontsize=8.8, ha="left", va="center", arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.0))
    a1.scatter([bdp], [C], s=70, color=ORG, zorder=5, edgecolor="white", lw=1.2)
    a1.annotate("optimal point (BBR)\n$N^{*}=C\\cdot T_0$", xy=(bdp, C), xytext=(0.03, 0.9), color=ORG, fontsize=9.5,
                fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=ORG, lw=1.0))
    a1.tick_params(labelbottom=False)
    a2.plot(N[N <= bdp + B], T[N <= bdp + B], color=TEAL, lw=2.8)
    a2.scatter([bdp + B], [(bdp + B) / C], s=60, color=GREY, zorder=5, edgecolor="white", lw=1.2)
    a2.annotate("loss-based TCP (Reno, CUBIC)\nsettles here: $N=C\\cdot T_0+B$", xy=(bdp + B, (bdp + B) / C), xytext=(0.98, 2.55),
                color=GREY, fontsize=9, ha="left", arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.0))
    a2.set_ylim(0, 3.1); a2.set_yticks([0, T0]); a2.set_yticklabels(["0", "$T_0$"])
    a2.set_ylabel("trip time $T$")
    a2.set_xticks([0, bdp, bdp + B]); a2.set_xticklabels(["0", "$C\\cdot T_0$\n(BDP)", "$C\\cdot T_0+B$"])
    a2.set_xlabel("robots (or data) on the way, $N$")
    fig.text(0.1, 0.955, "Little's law and the bandwidth-delay product", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(0.1, 0.918, "$N = X\\cdot T$,   $X=\\min(N/T_0,\\ C)$,   $T=\\max(T_0,\\ N/C)$   $\\Rightarrow$   best $N^{*}=C\\cdot T_0$",
             fontsize=10.5, color=INK)
    fig.text(0.1, 0.012, "$C$: bottleneck rate (door 6: 26 per 500 ticks)   $T_0$: trip time with no queue   $B$: buffer   (theory sketch)",
             fontsize=7.8, color=GREY, style="italic")
    fig.savefig(path, facecolor="white")
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
            ("RTT / RTprop", "real time (Little's law) / no-queue time: bars, right"),
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
    bx.set_title("measured real / model delay (round 50)\n> 1 = robots waiting in a hidden queue", fontsize=7.9, color=INK, loc="left")
    fig.savefig(path, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    bdp_principle("figures/deck/fig_bdp_principle.png")
    bbr_loop("figures/deck/fig_bbr_loop.png")
    door_util("figures/deck/fig_door_util.png")
