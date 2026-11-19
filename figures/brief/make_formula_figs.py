"""Draw the four formula figures used in the Chinese full-text summary (one per optimization)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["mathtext.fontset"] = "dejavuserif"

FIGS = [
    ("b_f1_bound.png", "Bound (max-flow / min-cut)",
     r"$X^{*} = \dfrac{C}{f} = \dfrac{26}{0.376} = 69.1$  tasks per 500 ticks",
     ["C = door 6 bandwidth, 26 robots per 500 ticks (measured)",
      "f = share of tasks that must cross door 6: 2 x 0.2507 x 0.7493 = 0.376"]),
    ("b_f2_quota.png", "Per-door quota (bandwidth x delay)",
     r"$K = \lceil\, \alpha \, T \, \dfrac{C}{2} \,\rceil = \lceil\, 2.23 \times \dfrac{247}{500} \times 13 \,\rceil = \lceil 14.3 \rceil = 15$",
     ["inbound T = 247 ticks -> 15 robots;  outbound T = 158 ticks -> 10 robots",
      "T = travel time to the door;  C/2 = 13 robots per 500 ticks per direction;  alpha = 2.23 slowdown from breakdowns"]),
    ("b_f3_door_rule.png", "Door rule (half-duplex link, polling)",
     r"$U(n) = \dfrac{n\,h}{(n-1)\,h + s} = \dfrac{9n}{9(n-1) + 21}$      $U(1) = 43\%$,   $U(10) = 88\%$",
     ["n = robots let through per batch;  h = 9 ticks between two robots in the same direction",
      "s = 21 ticks to switch direction (h and s measured)"]),
    ("b_f4_admission.png", "Global admission cap (Little's law)",
     r"$A = \lfloor\, \beta \, X^{*} \alpha \, (T_1 + T_2) \,\rfloor = \lfloor\, 1.76 \times \dfrac{69.2}{500} \times 2.23 \times 255 \,\rfloor = \lfloor 138.5 \rfloor = 138$",
     ["X* = 69.2 tasks per 500 ticks (linear program);  T1 + T2 = 255 ticks for one task without congestion",
      "alpha = 2.23 slowdown from breakdowns;  beta = 1.76 safety margin"]),
]

for name, title, formula, notes in FIGS:
    fig = plt.figure(figsize=(8, 2.3), dpi=200)
    fig.text(0.03, 0.86, title, fontsize=14, weight="bold", color="#1f2937")
    fig.text(0.05, 0.52, formula, fontsize=15, color="#111827", va="center")
    for i, line in enumerate(notes):
        fig.text(0.05, 0.20 - i * 0.12, line, fontsize=9.5, color="#4b5563")
    fig.savefig(f"figures/brief/{name}", facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("wrote", name)
