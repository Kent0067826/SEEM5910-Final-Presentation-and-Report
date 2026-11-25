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
            ("Deadlock watchdog", "noWD"),
            ("Global cap\n(whole-map quota)", "noGlobal")]
    right = [("Door rule only", "onlyDoor"), ("Per-door quota only", "onlyQuota"), ("Global cap only", "onlyGlobal"),
             ("Everything on\n(full DoorFlow)", "FULL")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.3))
    out = {}
    for ax, items, title, base, col in [
            (a1, left, "Remove one part from the full method", "FULL", ORANGE),
            (a2, right, "Add only this part to the base program", "NONE", BLUE)]:
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


def results():
    """Results slide: official starter program vs DoorFlow on the official room map, from the formal evaluation
    (r52b-baseline rows: DEF = official starter, LCAP = DoorFlow; 20 runs per robot count, paired by seed).
    The average gain is the mean of the 60 paired run ratios (the report's +140.5%); the label over each pair of bars is the mean
    of that robot count's 20 paired ratios, so the three labels average to the title's number."""
    rows = [json.loads(l) for l in open(R52B, encoding="utf-8") if l.strip()]
    acc, pair = {}, {}
    for r in rows:
        if r["map"] in OFFICIAL and r["method"] in ("DEF", "LCAP"):
            acc.setdefault((r["map"], r["method"]), []).append(r["completed"])
            pair.setdefault((r["map"], r["seed"], r["pseed"]), {})[r["method"]] = r["completed"]
    ratios = [v["LCAP"] / v["DEF"] for v in pair.values() if len(v) == 2]
    avg = (st.mean(ratios) - 1) * 100
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    w = 0.36
    for i, mp in enumerate(OFFICIAL):
        a, b = st.mean(acc[(mp, "DEF")]), st.mean(acc[(mp, "LCAP")])
        ax.bar(i - w / 2, a, width=w * 0.95, color=GRAY, label="official starter program" if i == 0 else None)
        ax.bar(i + w / 2, b, width=w * 0.95, color=ORANGE, label="DoorFlow (ours)" if i == 0 else None)
        ax.text(i - w / 2, a + 15, f"{a:.0f}", ha="center", fontsize=10, color=INK)
        ax.text(i + w / 2, b + 15, f"{b:.0f}", ha="center", fontsize=10, color=INK, fontweight="bold")
        g = (st.mean(v["LCAP"] / v["DEF"] for k, v in pair.items() if k[0] == mp and len(v) == 2) - 1) * 100   # mean of this size's 20 paired ratios
        ax.text(i, b + 105, f"+{g:.0f}%", ha="center", fontsize=11.5, color=ORANGE, fontweight="bold")
    ax.set_xticks(range(3)); ax.set_xticklabels([f"{m[4:]} robots" for m in OFFICIAL], fontsize=10.5)
    ax.set_ylabel("orders finished per run (5,000 ticks)", fontsize=9.5, color=INK2)
    ax.set_ylim(0, 1420)
    ax.legend(fontsize=9.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2)
    fig.text(0.5, -0.06, "Each % label: mean of that size's 20 same-seed ratios (DoorFlow ÷ starter); the three labels average to +140.5% (60 pairs).",
             ha="center", fontsize=8.6, color=INK2, style="italic")
    ax.set_title("Official room map, 20 runs per bar, same seeds for both programs", fontsize=11, color=INK)   # the headline number is on the slide
    style(ax)
    fig.savefig(os.path.join(ROOT, "figures", "deck", "fig_results_deck.png"), dpi=220, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    print("results", {m: (round(st.mean(acc[(m, 'DEF')]), 1), round(st.mean(acc[(m, 'LCAP')]), 1)) for m in OFFICIAL}, "avg", round(avg, 1), len(ratios))


if __name__ == "__main__":
    main()
    results()
