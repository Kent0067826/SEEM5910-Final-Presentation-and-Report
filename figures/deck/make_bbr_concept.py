"""Concept sketch (not measured data): in-flight over time for loss-based TCP, the same idea on robots, and BBR.
Run from the repo root: python3 figures/deck/make_bbr_concept.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
INK, BLUE, RED, GREY, ORG = "#1B2631", "#0F6E7E", "#C0392B", "#5D6D7E", "#E39B2D"
t = np.linspace(0, 10, 1000); bdp = 1.0
saw = 0.9 + 0.45 * ((t * 0.55) % 1.0)          # grow until loss, then back off
saw = np.where(((t * 0.55) % 1.0) < 1, 0.75 + 0.6 * ((t * 0.55) % 1.0), saw)
robots = 0.4 + 0.32 * t                           # no loss signal: keeps growing
bbr = np.where(t < 1.2, 0.4 + 0.55 * t, bdp + 0.06 * np.sin(t * 2.5))
fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=200)
ax.axhline(bdp, color=ORG, ls="--", lw=1.4)
ax.text(9.9, 0.5, "dashed: bandwidth x delay", color=ORG, ha="right", fontsize=10, fontweight="bold")
ax.plot(t, saw, color=GREY, lw=2.2, label="loss-based TCP (Reno, CUBIC): grow until a packet is lost")
ax.plot(t, robots, color=RED, lw=2.4, label="same idea on robots: nothing is lost, so it never stops")
ax.plot(t, bbr, color=BLUE, lw=2.8, label="BBR: max delivery rate x min round-trip time")
ax.set_ylim(0, 3.6); ax.set_xlim(0, 10)
ax.set_xticks([]); ax.set_yticks([])
ax.set_xlabel("time", color=INK); ax.set_ylabel("data (or robots) in flight", color=INK)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="upper left", fontsize=9, frameon=False)
fig.suptitle("Concept: why BBR, not loss-based TCP", fontsize=12, color=INK, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.005, "Concept sketch, not measured data", fontsize=8.5, color=GREY, style="italic")
fig.tight_layout(rect=(0, 0.02, 1, 0.95))
fig.savefig("figures/deck/bbr_concept.png", facecolor="white")
