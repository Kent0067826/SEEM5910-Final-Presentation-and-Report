"""Deck copy of figures/part3/p3_fig01_ablation.png (run from the repo root: python3 figures/deck/make_deck_ablation.py).
Same data (figures/part3/rerun/ablation_room_4x4.jsonl, 600 runs) and the same paired bootstrap as figures/part3/make_figs.py
fig_ablation(); only the bar labels are reworded without network terms (half-duplex, cell credit, PFC, admission, bandwidth)."""
import json, os, random, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ABL = os.path.join(ROOT, "figures", "part3", "rerun", "ablation_room_4x4.jsonl")
OUT = os.path.join(ROOT, "figures", "deck", "fig_ablation_deck.png")
R52B = os.path.join(ROOT, "experiment-materials", "archive", "workspace", "batches", "r52b-baseline", "rows.jsonl")
OUT_EXEC = os.path.join(ROOT, "figures", "deck", "fig_executor_deck.png")
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["savefig.dpi"] = 200
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#ffffff"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#b9b8b2"
OFFICIAL = ("room200", "room250", "room300")


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def paired(by, a, b, maps):
    return [[by[(m, a, s, p)] / by[(m, b, s, p)] - 1 for (mm, k, s, p) in by if mm == m and k == b and (m, a, s, p) in by]
            for m in maps]


def boot(G, n=4000, seed=0):
    rnd = random.Random(seed)
    ms = sorted(st.mean(st.mean(rnd.choice(g) for _ in g) for g in G) for _ in range(n))
    return st.mean(st.mean(g) for g in G), ms[int(.025 * n)], ms[int(.975 * n)]


def main():
    rows = [json.loads(l) for l in open(ABL, encoding="utf-8") if l.strip()]
    by = {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in rows if "completed" in r}
    left = [("Door rule: one direction at a\ntime, serve a side until empty", "noDoor"), ("Per-door quota\n(door rate x trip time)", "noQuota"),
            ("Executor fix: free a cell\nas soon as the robot leaves", "noSync"), ("Deadlock watchdog", "noWD"),
            ("Global cap\n(Little's law)", "noGlobal")]
    right = [("Door rule only", "onlyDoor"), ("Per-door quota only", "onlyQuota"), ("Global cap only", "onlyGlobal"),
             ("Everything on\n(full DoorFlow)", "FULL")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.3))
    out = {}
    for ax, items, title, base, col in [
            (a1, left, "Remove one part from the full method", "FULL", ORANGE),
            (a2, right, "Add only this part to the base\n(champion assignment + fixed executor)", "NONE", BLUE)]:
        ys = list(range(len(items)))[::-1]
        for y, (name, k) in zip(ys, items):
            m, lo, hi = (100 * x for x in boot(paired(by, k, base, OFFICIAL)))
            out[k] = round(m, 1)
            c = col if (lo > 0 or hi < 0) else GRAY
            ax.barh(y, m, color=c, height=0.6)
            ax.plot([lo, hi], [y, y], color=INK, lw=1)
            x = min(m, lo) if m < 0 else max(m, hi)
            ax.text(x + (-1 if m < 0 else 1), y, f"{m:+.1f}%", va="center", ha="right" if m < 0 else "left", fontsize=9, color=INK)
        ax.set_yticks(ys)
        ax.set_yticklabels([n for n, _ in items], fontsize=9)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(title, fontsize=10, color=INK)
        style(ax)
    fig.subplots_adjust(wspace=0.62)
    a1.set_xlim(-38, 6)
    a2.set_xlim(0, 92)
    a1.set_xlabel("change in tasks completed (%); black line = 95% interval;\ngrey = interval crosses 0 (no measurable effect)", fontsize=8.5, color=INK2)
    a2.set_xlabel("change in tasks completed (%)", fontsize=8.5, color=INK2)
    fig.suptitle("Re-test on the official 4x4 room map: 200/250/300 robots, 20 runs per version and size (600 runs, 0 errors)",
                 fontsize=10.5, color=INK, y=1.03)
    fig.savefig(OUT, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print(out)


def executor():
    """Deck copy of figures/part3/p3_fig07_executor_data.png with larger text, stacked for a narrow column. Same numbers:
    22 / 26 / 45 robots through door 6 per 500 ticks (read-through notes, wait-v27, rounds 36-37) and the paired gain of the
    fixed executor over the champion assignment in the formal evaluation (r52b-baseline rows, N2F vs N2, 20 runs per size)."""
    rows = [json.loads(l) for l in open(R52B, encoding="utf-8") if l.strip()]
    by = {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in rows if "completed" in r}
    gains = [100 * st.mean(g) for g in paired(by, "N2F", "N2", OFFICIAL)]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(4.9, 5.0), dpi=220)
    fig.subplots_adjust(left=0.13, right=0.98, top=0.90, bottom=0.08, hspace=0.75)
    v = [22, 26, 45]
    a1.bar(["before\nthe fix", "after the fix", "after the fix,\nbreakdowns off"], v, color=[GRAY, BLUE, "#1baf7a"], width=0.55)
    for i, x in enumerate(v): a1.text(i, x + 1.2, f"{x}", ha="center", fontsize=11, color=INK, fontweight="bold")
    a1.set_ylim(0, 54); a1.set_title("Robots through door 6 per 500 ticks (rounds 36-37)", fontsize=10.5, color=INK, loc="left")
    a2.bar(["200 robots", "250 robots", "300 robots"], gains, color=BLUE, width=0.5)
    for i, g in enumerate(gains): a2.text(i, g + 0.4, f"{g:+.1f}%", ha="center", fontsize=11, color=INK, fontweight="bold")
    a2.set_ylim(0, 15); a2.set_title(f"Fixing only the executor: orders, mean {st.mean(gains):+.1f}%\n(official room map, 20 paired runs per size)", fontsize=10.5, color=INK, loc="left")
    for ax in (a1, a2):
        style(ax); ax.tick_params(labelsize=9.5)
    fig.savefig(OUT_EXEC, facecolor=SURF)
    plt.close(fig)
    print("executor gains", [round(g, 1) for g in gains], round(st.mean(gains), 1))


if __name__ == "__main__":
    main()
    executor()
