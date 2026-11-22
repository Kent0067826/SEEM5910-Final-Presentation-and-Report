"""Concept sketch (not measured data): TCP in-flight data vs delivery rate and delay, BBR operating point.
Run from the repo root: python3 figures/deck/make_tcp_concept.py"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
INK, BLUE, ORG, GREY = "#1B2631", "#0F6E7E", "#E39B2D", "#5D6D7E"
x = np.linspace(0, 3, 300); bdp = 1.0
rate = np.minimum(x, bdp); delay = np.maximum(1.0, x)
fig, axs = plt.subplots(2, 1, figsize=(6.4, 4.6), dpi=200, sharex=True)
for ax in axs:
    ax.axvline(bdp, color=ORG, ls="--", lw=1.6)
    ax.spines[["top", "right"]].set_visible(False); ax.set_yticks([])
    ax.axvspan(0, bdp, color="#EDF2F4", zorder=0)
axs[0].plot(x, rate, color=BLUE, lw=2.6)
axs[0].set_ylabel("delivery rate", color=INK); axs[0].set_ylim(0, 1.35)
axs[0].text(0.5, 1.12, "link sometimes idle", ha="center", color=GREY, fontsize=10)
axs[0].text(2.0, 1.12, "no faster: extra data only queues", ha="center", color=GREY, fontsize=10)
axs[0].text(bdp + 0.04, 0.25, "best point:\nin flight = bandwidth x delay\n(BBR aims here)", color=ORG, fontsize=10, fontweight="bold")
axs[1].plot(x, delay, color=BLUE, lw=2.6)
axs[1].set_ylabel("round-trip delay", color=INK); axs[1].set_ylim(0, 3.3)
axs[1].text(2.05, 2.75, "queue grows, delay grows", ha="center", color=GREY, fontsize=10)
axs[1].set_xlabel("data in flight (sent, not yet confirmed)", color=INK); axs[1].set_xticks([])
fig.suptitle("Concept (TCP / BBR): how much data to keep in flight", fontsize=12, color=INK, fontweight="bold", x=0.02, ha="left")
fig.text(0.02, 0.005, "Concept sketch, not measured data", fontsize=8.5, color=GREY, style="italic")
fig.tight_layout(rect=(0, 0.02, 1, 0.96))
fig.savefig("figures/deck/tcp_bdp_concept.png", facecolor="white")
