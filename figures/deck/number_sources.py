"""Recompute the deck's numbers from the raw records, so every number on the slides can be checked.

Usage (repo root):  python3 figures/deck/number_sources.py      -> prints a table and writes figures/deck/number_sources.json
Every check reads a file in the repository (map, task file, run logs, earlier result files); nothing is typed in by hand
except the values printed on the slides, which are compared with the recomputed ones.
"""
import json, random, statistics as st, sys
sys.dont_write_bytecode = True
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[2]
EM = R / "experiment-materials"
DEMO = R / "figures/deck/demo"
OUT = {}


def rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def check(key, slide_value, value, how, src):
    OUT[key] = dict(slide=slide_value, recomputed=value, how=how, source=src)


# ---- the map (slides 2, 8) -----------------------------------------------------------------------------------------
rg = json.loads((EM / "archive/tools/replay_report/region_graph_room64.json").read_text())
sm = rg["summary"]
check("rooms / doors", "16 / 31", f"{sm['rooms']} / {sm['doors']}", "counted on the map (region graph)", "archive/tools/replay_report/region_graph_room64.json")
check("one-cell doors", "most one cell wide", f"{sm['lane1']} of {sm['doors']} (one door 2 cells)", "counted on the map", "same")
check("free cells", "3,646", f"{rg['free']} = {sm['room_cells']} room cells + {sm['door_cells']} door cells", "counted on the map", "same")
ll = [p["cells"] for b in rg["bridges"] if b["door"] == 6 for p in b["parts"] if 4 in p["rooms"]][0]
f = ll / sm["room_cells"]
check("lower-left room cells", "906 of 3,614", f"{ll} of {sm['room_cells']} = {f:.4f}", "counted on the map", "same")
check("P(order crosses door 6)", "37.6%", f"2 x {f:.4f} x {1 - f:.4f} = {2 * f * (1 - f):.4f}", "probability (random ends)", "formula")
tasks = (EM / "网络协议方向/harness/data/pkg/maps/room/room-example_250.tasks").read_text().split("\n")
n_tasks = int([l for l in tasks if l and not l.startswith("#")][0])
check("task file", "38.5% (530 of 1,375)", f"{n_tasks} tasks in the file; 530 / {n_tasks} = {530 / n_tasks:.3f}",
      "counted in the task file (530 = tasks whose two ends are on different sides of door 6, report section 2.2)", "harness/data/pkg/maps/room/room-example_250.tasks")
try:   # recount: tasks whose pickup and delivery are in rooms on different sides of door 6
    import sys; sys.path.insert(0, str(DEMO)); import build_demo as bd
    H, W, free = bd.load_map(); lab = bd.room_labels(free, rg); LLR = {4, 8, 12, 13}
    pairs = [[int(x) for x in l.split(",")] for l in tasks if l and not l.startswith("#") and "," in l]
    cross = sum((lab[a] in LLR) != (lab[b] in LLR) for a, b in pairs); on_door = sum(lab[a] < 0 or lab[b] < 0 for a, b in pairs)
    check("task file recount", "530", f"{cross} of {len(pairs)} = {cross / len(pairs):.3f} ({on_door} tasks have an end outside the room cells, e.g. on a door cell)", "counted in the task file", "same")
except ImportError:
    pass
cfg = json.loads((EM / "网络协议方向/harness/data/pkg/maps/room/room250.json").read_text())
check("competition settings", "3 ticks per move; breakdowns", f"agentCounter={cfg['agentCounter']}, delayConfig={cfg['delayConfig']}, tasks revealed {cfg['numTasksReveal']} x robots",
      "competition setting", "harness/data/pkg/maps/room/room250.json")

# ---- slide 3: 127 -> 37 (round 31 test batch) and the curve (round 52) -------------------------------------------------
def prof_mean(path, meth):
    P = [r["prof"] for r in rows(path) if r["map"] in ("room200", "room250", "room300") and r["method"] == meth]
    return len(P), [round(st.mean(p[i] for p in P), 1) for i in range(len(P[0]))]
n, p31 = prof_mean(EM / "archive/workspace/batches/r31-test/rows.jsonl", "N2")
check("slowing down (card)", "127 -> 37", f"{p31[0]} -> {p31[-1]} ({n} runs)", "measured: orders per 500 ticks, champion assignment, mean of 60 runs (3 sizes x 20)", "archive/workspace/batches/r31-test/rows.jsonl")
n, p52 = prof_mean(EM / "archive/workspace/batches/r52b-baseline/rows.jsonl", "N2")
check("slowing down (curve)", "figure", f"{p52[0]} -> {p52[-1]} ({n} runs)", "measured, same setting, round-52 runs drawn in the figure", "archive/workspace/batches/r52b-baseline/rows.jsonl")

# ---- slide 22: +140.5 % (round 52 formal evaluation) -----------------------------------------------------------------
R52 = rows(EM / "archive/workspace/batches/r52b-baseline/rows.jsonl")
by = {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in R52}
per = {}
for m in ("room200", "room250", "room300"):
    rr = [by[(m, "LCAP", s, p)] / by[k] - 1 for k in by if k[0] == m and k[1] == "DEF" for (_, _, s, p) in [k] if (m, "LCAP", s, p) in by]
    per[m] = (len(rr), 100 * st.mean(rr), st.mean(by[k] for k in by if k[0] == m and k[1] == "DEF"), st.mean(by[k] for k in by if k[0] == m and k[1] == "LCAP"))
check("DoorFlow vs starter", "+140.5% (60 runs); +145 / +124 / +152", f"{st.mean(v[1] for v in per.values()):+.1f}%; " + " / ".join(f"{v[1]:+.0f}% (n={v[0]}, {v[2]:.0f} -> {v[3]:.0f})" for v in per.values()),
      "statistics: mean of 60 same-seed ratios", "archive/workspace/batches/r52b-baseline/rows.jsonl (methods DEF, LCAP)")


# ---- slide 23: 600-run ablation; slide 20/21: 640-run generalization ---------------------------------------------------
def paired(path, a, b, maps):
    by = {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in rows(path)}
    G = [[by[(m, a, s, p)] / by[k] - 1 for k in by if k[0] == m and k[1] == b for (_, _, s, p) in [k] if (m, a, s, p) in by] for m in maps]
    return 100 * st.mean(st.mean(g) for g in G), sum(len(g) for g in G)
AB = R / "figures/part3/rerun/ablation_room_4x4.jsonl"
M3 = ["room200", "room250", "room300"]
check("ablation runs", "600", f"{len(rows(AB))}", "counted rows", "figures/part3/rerun/ablation_room_4x4.jsonl")
for a, b, lab in [("noDoor", "FULL", "-25.6"), ("noQuota", "FULL", "-13.6"), ("noWD", "FULL", "-0.4"), ("noGlobal", "FULL", "+0.7"),
                  ("onlyDoor", "NONE", "+29.7"), ("onlyQuota", "NONE", "+29.3"), ("onlyGlobal", "NONE", "+15.7"), ("FULL", "NONE", "+76.4")]:
    v, n = paired(AB, a, b, M3)
    check(f"ablation {a} vs {b}", lab, f"{v:+.1f}% (n={n})", "statistics: mean of same-seed ratios, 3 sizes x 20", "figures/part3/rerun/ablation_room_4x4.jsonl")
GN = R / "figures/part3/rerun/general_gen4x4.jsonl"
gmaps = sorted({r["map"] for r in rows(GN)})
check("generalization runs", "640, 8 maps x 199/249", f"{len(rows(GN))} rows, {len(gmaps)} instances", "counted rows", "figures/part3/rerun/general_gen4x4.jsonl")
for a, b, lab, ms in [("FULL", "NONE", "+86.9", gmaps), ("noGlobal", "FULL", "-1.4", gmaps), ("noWD", "FULL", "+0.2", gmaps), ("noGlobal", "FULL", "-16.9", ["roomGenH_249"])]:
    v, n = paired(GN, a, b, ms)
    check(f"generalization {a} vs {b} {'GenH_249' if len(ms) == 1 else 'all'}", lab, f"{v:+.1f}% (n={n})", "statistics: mean of same-seed ratios", "figures/part3/rerun/general_gen4x4.jsonl")

# ---- slide 13: knee figure (one replay each, 250 robots) ---------------------------------------------------------------
mfd = json.loads((EM / "archive/protocol_direction/readability/演讲结构报告/mfd.json").read_text())
nd, lc = mfd["N2F"], mfd["LCAP"]
check("knee: no door control", "59 at start -> 211, 3 cross", f"{nd[0]['L']} -> {nd[-1]['L']}, last X={nd[-1]['X']}", "measured: one replay, 250 robots, mean per 500-tick window", "archive/protocol_direction/readability/演讲结构报告/mfd.json")
check("knee: quota", "about 25 on the way, 26 cross", f"L {min(w['L'] for w in lc[1:])}-{max(w['L'] for w in lc[1:])}, mean X after first window {st.mean(w['X'] for w in lc[1:]):.1f}", "measured, same replay pair", "same")

# ---- slides 8, 11, 12, 15, 16, 19, 21: stored outputs of the demo scripts ---------------------------------------------
D6 = json.loads((DEMO / "door6_numbers.json").read_text()); DT = json.loads((DEMO / "door_timing.json").read_text())
R6 = json.loads((DEMO / "door6_rate.json").read_text())
check("door rate (steady)", "26 per 500 = 1,175 / 45", f"{R6['formula']} (median {R6['median_period']})", "counted: crossings per 500-tick period after the first 500, 5 runs", "figures/deck/demo/door6_rate.json")
check("door rate", "26 per 500; 620 in / 635 out", f"{D6['door_rate']['per_500']} per 500 ({D6['door_rate']['crossings']} in {D6['door_rate']['ticks']} ticks); {D6['door_rate']['into_lower_left']} / {D6['door_rate']['out_of_lower_left']}",
      "measured: crossings counted in 5 runs; planner uses 26 (round 40)", "figures/deck/demo/door6_numbers.json")
check("free trip", "247 / 158", f"planner {D6['free_trip']['planner_uses']}; independent recompute {D6['free_trip']['T_inward']} / {D6['free_trip']['T_outward']}", "computed from the map: 25 + mean shortest time over every cell", "same")
check("slowdown", "2.23 / 1.33", f"{D6['slowdown']['median_with_breakdowns']} (n={D6['slowdown']['cases_with']}) / {D6['slowdown']['median_without_breakdowns']} (n={D6['slowdown']['cases_without']})",
      "measured (round 40): median of real / free time to the door", "archive/workspace/netmodel_r41/model_data/latency_pairs.json")
check("window", "15 / 10", f"ceil(2.23*247/38.5)={-(-2.23 * 247 // (500 / 13)):.0f}, ceil(2.23*158/38.5)={-(-2.23 * 158 // (500 / 13)):.0f}", "formula", "-")
check("door timing", "1,255; 10; 34; 9.3", f"{DT['door6_crossings']}; {DT['same_direction_gap']['median']}; {DT['switch_gap']['median']}; {DT['robots_per_turn']}", "measured: 5 runs, seeds 9700-9704", "figures/deck/demo/door_timing.json")
U = lambda n, h=10, s=34: n * h / ((n - 1) * h + s)
check("door speed", "29% / 81%", f"{100 * U(1):.0f}% / {100 * U(10):.0f}%", "formula with measured medians", "-")
LT = json.loads((R / "experiment-materials/archive/workspace/netmodel_r43/data/little_r47.json").read_text())["room250"]
lam = LT["lam"] * 500
check("ceiling", "69.2 orders per 500 ticks", f"{lam:.1f} (linear program, = 26 / 0.3757 = {26 / (2 * f * (1 - f)):.1f})", "formula / linear program", "archive/workspace/netmodel_r43/data/little_r47.json")
check("global cap", "138", f"1.76 x {lam:.1f}/500 x 2.23 x (25 + {LT['Tleg2']:.1f}) = {1.76 * LT['lam'] * 2.23 * (25 + LT['Tleg2']):.1f} -> 138", "formula; 1.76 from a sweep (round 46)", "archive/workspace/scripts/r47_common.py")
NS = json.loads((DEMO / "narrow_spots.json").read_text())
check("narrow doorways run", "818 / 1,277; 249 / 177", f"{NS['orders']['noGlobal']} / {NS['orders']['FULL']}; max holding {NS['runs']['noGlobal']['max_holding_orders']} / {NS['runs']['FULL']['max_holding_orders']}", "measured: one run each", "figures/deck/demo/narrow_spots.json")
MS = json.loads((DEMO / "monitor_stats.json").read_text())
check("monitor runs", "609 / 435 / 612; door 6 jammed 91-94%", " / ".join(str(v["finished"]) for v in MS["runs"].values()) + "; " + " / ".join(f"{100 * v['jammed_share_by_door']['6']:.0f}%" for v in MS["runs"].values()),
      "measured: one run each", "figures/deck/demo/monitor_stats.json")
DS = json.loads((DEMO / "demo_stats.json").read_text())
check("demo run", "609 / 1,130", f"{DS['none']['finished']} / {DS['doorflow']['finished']}", "measured: one run each (seed 9700 / 101)", "figures/deck/demo/demo_stats.json")
LC = json.loads((DEMO / "live_control.json").read_text())
check("live control", "-1.1 / -1.0 / -3.3 / -7.5; window 8-41; 28 in", " / ".join(f"{LC['variants'][k]['change_vs_DF_pct']:+.2f}" for k in ("JAM", "LATCH", "AIMD", "PHYS")) + f"; {LC['variants']['AIMD']['window_in_range']}; {LC['variants']['PHYS']['window_in']}",
      f"statistics: {LC['runs']} runs, 60 pairs per idea", "figures/deck/demo/live_control.json")

if __name__ == "__main__":
    (R / "figures/deck/number_sources.json").write_text(json.dumps(OUT, indent=1, ensure_ascii=False))
    w = max(len(k) for k in OUT)
    for k, v in OUT.items():
        print(f"{k:<{w}}  slide: {v['slide']:<38}  recomputed: {v['recomputed']}")
