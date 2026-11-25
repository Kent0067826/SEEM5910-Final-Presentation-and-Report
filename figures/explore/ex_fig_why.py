"""Figure for the report (section 9, four extra admission ideas at door 6): why none of them helped.
  (a) paired change in completed orders vs DoorFlow, 60 runs per idea (dots = runs, bar = mean with bootstrap 95% interval)
  (b) change in door-6 crossings vs change in completed orders, all 420 pairs (least-squares line)
  (c) actual minus estimated arrival time at door 6 (the estimate ideas A and B used), 752 crossings in 3 DoorFlow runs
Inputs: summary_main.json, runs_main.jsonl, why_no_gain.json, arrival_spread.json (all in figures/explore).
Output: figures/explore/ex_fig1_why.png"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
TXT, SUB, GRID, BLUE, DARK = '#191919', '#666666', '#e6e6e6', '#257de0', '#3a3a3a'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9.5, 'text.color': TXT, 'axes.labelcolor': TXT,
                     'xtick.color': SUB, 'ytick.color': SUB, 'axes.edgecolor': '#bdbdbd', 'axes.linewidth': 0.8})
S = json.loads((HERE / 'summary_main.json').read_text())['variants']
R = [json.loads(l) for l in open(HERE / 'runs_main.jsonl')]
W = json.loads((HERE / 'why_no_gain.json').read_text())
A = json.loads((HERE / 'arrival_spread.json').read_text())
df = {(r['map'], r['seed'], r['pseed']): r for r in R if r['variant'] == 'DF'}
NAMES = [('A100', 'A  book a 100-tick slot'), ('A200', 'A  book a 200-tick slot'), ('B150', 'B  direction phases, 150'),
         ('B300', 'B  direction phases, 300'), ('CNEAR', 'C  cap robots crossing now'), ('CFAR', 'C  cap robots crossing later'),
         ('DALPHA', 'D  own slow-down per door')]
fig = plt.figure(figsize=(8.8, 8.4)); gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1], hspace=0.52, wspace=0.3,
                                                              left=0.25, right=0.975, top=0.925, bottom=0.075)
ax = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]
ax[1].set_position([0.085, 0.075, 0.39, 0.33]); ax[2].set_position([0.585, 0.075, 0.39, 0.33])

# (a)
a = ax[0]; LO, HI = -15, 10; rng = np.random.default_rng(1)
for i, (v, name) in enumerate(NAMES):
    y = len(NAMES) - 1 - i
    rat = np.array([100 * (r['completed'] / df[(r['map'], r['seed'], r['pseed'])]['completed'] - 1) for r in R if r['variant'] == v])
    a.scatter(np.clip(rat, LO, HI), y + rng.uniform(-0.18, 0.18, len(rat)), s=9, color=BLUE, alpha=0.28, linewidths=0)
    m, (lo, hi) = S[v]['change_pct'], S[v]['ci95_pct']
    a.plot([lo, hi], [y, y], color=DARK, lw=2, solid_capstyle='round'); a.scatter([m], [y], s=46, color=DARK, zorder=3, edgecolors='white', linewidths=1.2)
    a.text(HI + 1.2, y, f"{m:+.2f}%", va='center', fontsize=9, color=TXT, fontweight='bold')
    a.text(HI + 5.6, y, f"{S[v]['better']}/60 better", va='center', fontsize=9, color=TXT)
    n_out = int(np.sum(rat < LO))
    if n_out: a.text(LO + 0.2, y + 0.32, f'{n_out} below {LO}%', fontsize=7, color=SUB)
a.axvline(0, color='#9e9e9e', lw=1)
a.set_yticks(range(len(NAMES))); a.set_yticklabels([n for _, n in NAMES][::-1], fontsize=8.8, color=TXT)
a.set_xlim(LO, HI + 12); a.set_xticks(range(LO, HI + 1, 5)); a.set_xlabel('change in completed orders vs DoorFlow, same seeds (%)', x=0.405)
a.axvline(HI + 0.6, color=GRID, lw=1); a.text(HI + 1.2, len(NAMES) - 0.35, 'mean', fontsize=8, color=SUB); a.text(HI + 5.6, len(NAMES) - 0.35, 'runs better', fontsize=8, color=SUB)
a.set_title('(a) None of the four ideas beats DoorFlow', loc='left', fontsize=10.5, fontweight='bold', pad=17)
a.text(0, 1.02, 'dots: 60 runs each   bar: mean and 95% interval', transform=a.transAxes, fontsize=8.5, color=SUB)
[a.axvline(x, color=GRID, lw=0.6, zorder=0) for x in range(LO, HI + 1, 5) if x != 0]; a.set_axisbelow(True)
for sp in ('top', 'right'): a.spines[sp].set_visible(False)
a.set_ylim(-0.6, len(NAMES) - 0.1)

# (b)
b = ax[1]
dx = np.array([r['door6_crossings'] - df[(r['map'], r['seed'], r['pseed'])]['door6_crossings'] for r in R if r['variant'] != 'DF'])
dy = np.array([r['completed'] - df[(r['map'], r['seed'], r['pseed'])]['completed'] for r in R if r['variant'] != 'DF'])
b.scatter(dx, dy, s=11, color=BLUE, alpha=0.45, linewidths=0)
k, c0 = np.polyfit(dx, dy, 1); xs = np.array([dx.min(), dx.max()]); b.plot(xs, k * xs + c0, color=DARK, lw=1.6)
b.axhline(0, color='#9e9e9e', lw=0.8); b.axvline(0, color='#9e9e9e', lw=0.8)
b.text(0.03, 0.95, f"r = {W['corr_crossings_vs_orders']:.2f}\n+1 crossing ≈ +{W['orders_per_extra_crossing']:.1f} orders", transform=b.transAxes, va='top', fontsize=8.5)
b.set_xlabel('change in robots through door 6'); b.set_ylabel('change in completed orders')
b.set_title('(b) Orders follow door-6 crossings', loc='left', fontsize=10.5, fontweight='bold', pad=17)
b.text(0, 1.02, f"{W['pairs']} pairs: each idea vs DoorFlow, same seeds", transform=b.transAxes, fontsize=8.5, color=SUB)
b.grid(color=GRID, lw=0.6); b.set_axisbelow(True)
for sp in ('top', 'right'): b.spines[sp].set_visible(False)

# (c)
c = ax[2]
err = np.array([t - q for v in A['per_side'].values() for t, q in v['pairs'] if q >= 0])
c.hist(err, bins=np.arange(-250, 701, 25), color=BLUE, alpha=0.85, edgecolor='white', linewidth=0.6)
ymax = c.get_ylim()[1]
c.axvspan(-50, 50, color='#9e9e9e', alpha=0.18, lw=0); c.axvline(0, color='#9e9e9e', lw=1)
c.text(-245, ymax * 0.9, 'grey band:\nA100 slot\n(±50 ticks)', fontsize=8, color=SUB, va='top')
al = A['all']
c.text(0.98, 0.97, f"late by {al['error_mean']:.0f} on average\nspread (SD) {al['error_sd']:.0f}\nshared lateness removed:\n"
                   f"{100 * al['share_within_50_after_removing_median']:.0f}% within ±50\n{100 * al['share_within_100_after_removing_median']:.0f}% within ±100",
       transform=c.transAxes, ha='right', va='top', fontsize=8.5)
c.set_xlabel('actual minus estimated arrival (ticks)'); c.set_ylabel('robots')
c.set_title('(c) Arrival times are too uncertain', loc='left', fontsize=10.5, fontweight='bold', pad=17)
c.text(0, 1.02, f"{al['n']} crossings, 3 DoorFlow runs", transform=c.transAxes, fontsize=8.5, color=SUB)
c.grid(axis='y', color=GRID, lw=0.6); c.set_axisbelow(True)
for sp in ('top', 'right'): c.spines[sp].set_visible(False)
fig.savefig(HERE / 'ex_fig1_why.png', dpi=200, facecolor='white'); print('saved')
