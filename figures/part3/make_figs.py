# -*- coding: utf-8 -*-
"""第三部分（关键迭代与实验图解）的作图脚本。

在仓库根目录运行：  python3 figures/part3/make_figs.py
依赖：matplotlib；中文字体 /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc

数据来源：
  * 能从仓库原始记录读的，一律直接读文件（r52b 的 rows.jsonl、协议方向各轮 *_compare.json、
    p72 的 inventory_p72.json）。
  * 原始结果文件不在本仓库的（第一阶段早期轮次、协议方向 p01–p63 的部分轮次），
    数字抄自 experiment-materials/网络协议方向/报告源/通读/数字核对表.md
    和两份通读笔记，每个常数旁边注明出处，方便核对。
"""
import json
import os
import shutil
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "figures", "part3")
EM = os.path.join(ROOT, "experiment-materials")
ROUNDS = os.path.join(EM, "网络协议方向", "rounds")

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 100
plt.rcParams["savefig.dpi"] = 200

# 调色：分类色按固定顺序；状态色只表达“确认/没确认/失败/待定”，图上同时写字，不只靠颜色
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
SURF = "#ffffff"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
RED = "#e34948"
GRAY = "#b9b8b2"
OK = "#008300"       # 确认通过 / 保留进正式方法
FAIL = RED           # 失败 / 负结果
PEND = YELLOW        # 过开发、没确认或暂缓
INFO = BLUE          # 发现、修评测、诊断


OFFICIAL = ("room200", "room250", "room300")   # 官方 4×4 房间图（64×64，16 个房间）的三种车数


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


# ---------------------------------------------------------------------------
# 图 1  迭代路线图（时间线）
# ---------------------------------------------------------------------------
def fig_roadmap():
    # (轮次标签, 文字, 状态)  协议第 N 轮 = 项目第 75+N 轮（协议方向通读笔记“编号提醒”）
    # 横轴按事件顺序等距排列（不按真实轮次比例），轮次写在每个点下面
    ev = [
        ("第1–10轮", "①评测有bug：种子写死、\n变量没初始化", INFO),
        ("第11–16轮", "TCP式窗口翻案\n房间图 +16%（1200拍）", OK),
        ("第25轮", "冠军派单一来，\n前面收益大半被覆盖", INFO),
        ("第27–29轮", "②跑满5000拍发现崩溃\n名额+门口规则 +55.2%", OK),
        ("第36–37轮", "③门卡在22台\n修执行器后 26/45台", OK),
        ("第41–47轮", "三条定律取代手调\n不比手调差", OK),
        ("第52轮", "正式评测（4×4房间图）\n比官方程序 +140.5%", OK),
        ("第53–62轮", "④门格加价 -5.2%\n分段路由 -39%~-55%", FAIL),
        ("P35–36", "⑤看门狗：唯一通过\n新图确认的协议机制", OK),
        ("P53–55", "④HN-SPF -25.9%\nCSPF -21.0%", FAIL),
        ("P60–69", "⑥名额微调三项\n开发过、确认≈0", PEND),
        ("P74–75", "⑥四项组合 开发+3.15%\n新房间图 +1.65%，没确认", PEND),
        ("P78", "门口按去向排队\n开发+1.07%，暂缓", PEND),
        ("后续41轮", "离线建模与\n数字核对", INFO),
    ]
    fig, ax = plt.subplots(figsize=(14, 5.6))
    n = len(ev)
    phases = [(0, 7, "第一阶段：用网络定律管门（项目第1–75轮）", "#eef4fc"),
              (8, 12, "协议方向：逐项搬网络协议（P01–P78）", "#fdf1ea"),
              (13, 13, "核查", "#f3f3f1")]
    for a, b, lab, c in phases:
        ax.axvspan(a - 0.5, b + 0.5, color=c, zorder=0)
        ax.text((a + b) / 2, 3.05, lab, ha="center", va="center", fontsize=10, color=INK2)
    ax.axhline(0, color=MUTED, lw=1.5, zorder=1)
    for i, (rnd, lab, col) in enumerate(ev):
        side = 1 if i % 2 == 0 else -1
        y = side * (1.0 if (i // 2) % 2 == 0 else 2.05)
        ax.plot([i, i], [0, y - side * 0.35], color=col, lw=1, zorder=2)
        ax.scatter([i], [0], s=80, color=col, edgecolor=SURF, lw=1.5, zorder=3)
        ax.text(i, y, lab, ha="center", va="center", fontsize=8.6, color=INK,
                bbox=dict(boxstyle="round,pad=0.35", fc=SURF, ec=col, lw=1.3))
        ax.text(i + 0.08, -0.2 * side, rnd, ha="left", va="center", fontsize=7.5, color=INK2, rotation=0)
    for lab, col in [("确认通过 / 留进正式方法", OK), ("失败 / 负结果", FAIL),
                     ("开发过了、新图没站住或暂缓", PEND), ("发现问题 / 修评测 / 诊断", INFO)]:
        ax.scatter([], [], s=60, color=col, label=lab)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=4, frameon=False, fontsize=9)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-2.7, 3.35)
    ax.axis("off")
    save(fig, "fig3_1_roadmap.png")


# ---------------------------------------------------------------------------
# 图 2  拥塞崩溃：每 500 拍完成数随时间（r52b 正式评测 640 局原始记录）
# ---------------------------------------------------------------------------
def fig_collapse():
    rows = [json.loads(l) for l in open(os.path.join(EM, "archive", "workspace", "batches",
                                                     "r52b-baseline", "rows.jsonl"), encoding="utf-8")]
    acc = defaultdict(list)
    for r in rows:
        acc[(r["map"], r["method"])].append(r["prof"])
    names = {"DEF": "官方入门程序", "N2": "+冠军派单", "N2F": "+修好执行器", "LCAP": "+本文的名额与门口规则"}
    cols = {"DEF": GRAY, "N2": "#8fb6e8", "N2F": BLUE, "LCAP": ORANGE}
    maps = ["room200", "room250", "room300"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, m in zip(axes, maps):
        for meth in ["DEF", "N2", "N2F", "LCAP"]:
            P = acc[(m, meth)]
            n = len(P[0])
            mean = [sum(p[i] for p in P) / len(P) for i in range(n)]
            xs = [500 * (i + 1) for i in range(n)]
            ax.plot(xs, mean, color=cols[meth], lw=2, marker="o", ms=4, label=f"{names[meth]}")
        ax.set_title(f"官方房间图 {m[4:]} 台车（各 {len(P)} 局平均）", fontsize=10, color=INK)
        ax.set_xlabel("拍（一局 5000 拍）", fontsize=9, color=INK2)
        style(ax)
    axes[0].set_ylabel("每 500 拍完成的单数", fontsize=9, color=INK2)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=4, frameon=False, fontsize=9)
    fig.suptitle("不管门时完成速度越跑越慢（拥塞崩溃）；管住门后掉得少得多，后半程仍是对照的 2–3 倍", fontsize=11, color=INK, y=1.02)
    save(fig, "fig3_2_collapse_over_time.png")


# ---------------------------------------------------------------------------
# 图 3  第①步：先校准尺子（数字抄自通读笔记 / 数字核对表）
# ---------------------------------------------------------------------------
def fig_ruler():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw={"width_ratios": [1.2, 1]})
    # 左：规划器种子写死时，同一配置只因种子不同就差这么多（第1–75轮通读笔记 wait-v9 条，官方房间图 200 台）
    seeds = ["种子0\n（写死的）", "种子1", "种子2", "种子3", "种子4"]
    vals = [195.8, 187.1, 189.4, 182.9, 180.8]
    a1.bar(seeds, vals, color=[ORANGE] + [GRAY] * 4, width=0.6)
    for i, v in enumerate(vals):
        a1.text(i, v + 0.4, f"{v}", ha="center", fontsize=9, color=INK)
    a1.set_ylim(175, 199)
    a1.set_ylabel("完成数（房间图 200 台，同一程序）", fontsize=9, color=INK2)
    a1.set_title("评测把规划器种子写死成 0：\n换个种子成绩最多差 8%（纵轴从 175 起）", fontsize=10, color=INK)
    style(a1)
    # 右：修好评测后窗口重测，官方 4×4 房间图（通读笔记 wait-v10 条；数字核对表第 109 轮节）
    labs = ["房间图 200 台", "房间图 300 台"]
    v2 = [16.2, 16.0]
    a2.bar(labs, v2, color=BLUE, width=0.5)
    for i, v in enumerate(v2):
        a2.text(i, v + 0.4, f"{v:+.1f}%", ha="center", fontsize=9.5, color=INK)
    a2.set_ylim(0, 20)
    a2.set_ylabel("TCP 式窗口 W=2 比当时基线", fontsize=9, color=INK2)
    a2.set_title("修好评测再测（1200 拍，第16轮）：\n窗口在 4×4 房间图上 +16% 左右", fontsize=10, color=INK)
    style(a2)
    save(fig, "fig3_3_fix_the_ruler.png")

# ---------------------------------------------------------------------------
# 图 4  第③步：执行器修复（左：门通过量，通读笔记 wait-v27；右：r52b 原始记录逐实例）
# ---------------------------------------------------------------------------
def fig_executor():
    rows = [json.loads(l) for l in open(os.path.join(EM, "archive", "workspace", "batches",
                                                     "r52b-baseline", "rows.jsonl"), encoding="utf-8")]
    by = {}
    for r in rows:
        by[(r["map"], r["method"], r["seed"], r["pseed"])] = r["completed"]
    gains = []
    for m in OFFICIAL:
        ds = [by[(mm, "N2F", s, p)] / by[(mm, "N2", s, p)] - 1
              for (mm, meth, s, p) in by if mm == m and meth == "N2"]
        gains.append(100 * sum(ds) / len(ds))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.6))
    labs = ["修之前", "修之后\n（有故障）", "修之后\n（关掉故障）"]
    v = [22, 26, 45]
    a1.bar(labs, v, color=[GRAY, BLUE, AQUA], width=0.55)
    for i, x in enumerate(v):
        a1.text(i, x + 0.8, f"{x} 台", ha="center", fontsize=9.5, color=INK)
    a1.set_ylabel("关键门每 500 拍过车数", fontsize=9, color=INK2)
    a1.set_title("门的过车数一直卡在 22 台\n修执行器后才松动（第36–37轮）", fontsize=10, color=INK)
    a1.set_ylim(0, 52)
    style(a1)
    short = ["房间图 200 台", "房间图 250 台", "房间图 300 台"]
    a2.bar(short, gains, color=BLUE, width=0.5)
    for i, g in enumerate(gains):
        a2.text(i, g + 0.3, f"{g:+.1f}%", ha="center", fontsize=9.5, color=INK)
    a2.set_ylabel("修好执行器 比 只换冠军派单", fontsize=9, color=INK2)
    a2.set_title(f"正式评测：只修执行器，三种车数平均 +{sum(gains)/len(gains):.1f}%\n（rows.jsonl 原始记录，每种 20 局同种子配对）",
                 fontsize=10, color=INK)
    a2.set_ylim(0, 15)
    style(a2)
    save(fig, "fig3_4_executor_fix.png")

# ---------------------------------------------------------------------------
# 图 5  第④步：换路 / 流量工程全部失败（开发或探索对比；数字见通读笔记、数字核对表）
# ---------------------------------------------------------------------------
def fig_routing():
    items = [  # (名称, 变化%, 阶段)  出处见注释
        ("分段路由第一版（6实例，最好的一个）", -39.2, "第一阶段"),          # 协议方向通读笔记 第104-105轮：第一版6个全差 -39.2%到-55.4%
        ("HN-SPF 压平代价 A", -25.88, "协议方向"),                       # p53/p54
        ("HN-SPF 压平代价 B", -24.71, "协议方向"),
        ("CSPF 限绕路 ≤10%", -20.98, "协议方向"),                        # p55
        ("备用门 FRER B=10", -9.88, "协议方向"),                         # p14
        ("CSPF 限绕路 ≤25%", -8.70, "协议方向"),
        ("HN-SPF 压平代价 C", -7.93, "协议方向"),                        # 数字核对表 547 行
        ("HN-SPF 压平代价 D", -6.80, "协议方向"),
        ("备用门 FRER B=3", -6.04, "协议方向"),
        ("门格加价（5 张图试跑）", -5.2, "第一阶段"),                    # 第53轮 wait-v43
        ("全图共用格子代价加倍", -3.76, "第一阶段"),                     # 第110轮补记
        ("BFD+LFA 绕开故障车", -2.07, "协议方向"),                       # p04
        ("Fortz–Thorup 格子加权", -0.29, "协议方向"),                    # 数字核对表 533 行
        ("系统最优过门费", -0.06, "第一阶段"),                            # 第109轮
        ("路由抖动时才开阻尼（新图确认）", 0.20, "协议方向"),              # p57 数字核对表 535 行
    ]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    names = [i[0] for i in items][::-1]
    vals = [i[1] for i in items][::-1]
    cols = [(FAIL if v < -1 else GRAY) if ph == "协议方向" else (ORANGE if v < -1 else GRAY)
            for (_, v, ph) in items][::-1]
    ax.barh(names, vals, color=cols, height=0.62)
    for i, v in enumerate(vals):
        ax.text(v - 0.6 if v < 0 else v + 0.6, i, f"{v:+.2f}%" if abs(v) < 10 else f"{v:+.1f}%",
                va="center", ha="right" if v < 0 else "left", fontsize=8.5, color=INK)
    ax.axvline(0, color=MUTED, lw=1)
    ax.axvline(-1, color=INK2, lw=1, ls="--")
    ax.text(-1.3, len(items) - 0.4, "淘汰线 -1%", fontsize=8.5, color=INK2, ha="right")
    ax.set_xlim(-46, 6)
    ax.set_xlabel("完成数变化（和当时的基线比）", fontsize=9, color=INK2)
    ax.scatter([], [], marker="s", s=60, color=ORANGE, label="第一阶段（流量工程、加价、指定路线）")
    ax.scatter([], [], marker="s", s=60, color=FAIL, label="协议方向（骨干网路由协议）")
    ax.scatter([], [], marker="s", s=60, color=GRAY, label="没超过 ±1%（看不出作用）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")
    ax.set_title("所有“换一条路走”的做法：没有一个带来可靠提升（多数是开发对比，最后一项是新图确认）", fontsize=11, color=INK)
    style(ax, ygrid=False, xgrid=True)
    save(fig, "fig3_5_routing_failures.png")


# ---------------------------------------------------------------------------
# 图 6  先量后做的漏斗（p72 inventory_p72.json）
# ---------------------------------------------------------------------------
def fig_funnel():
    inv = load("p72/inventory_p72.json")
    order = ["先量跳过", "开发没过", "过开发没确认", "确认通过"]
    cnt = inv["按结局"]
    total = inv["总机制数"]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    left = total
    widths = [total, total - cnt["先量跳过"], cnt["过开发没确认"] + cnt["确认通过"], cnt["确认通过"]]
    stages = [f"提出并写了协议\n{total} 项", f"先量过线、进开发对比\n{widths[1]} 项",
              f"开发对比过关\n{widths[2]} 项", f"新地图确认通过\n{widths[3]} 项"]
    cols = [GRAY, "#8fb6e8", PEND, OK]
    for i, (w, s, c) in enumerate(zip(widths, stages, cols)):
        ax.barh(i, w, left=(total - w) / 2, color=c, height=0.7)
        if w > 12:
            ax.text(total / 2, i, s, ha="center", va="center", fontsize=9.5, color=INK)
        else:
            ax.text(total / 2 + w / 2 + 1, i, s.replace("\n", "："), ha="left", va="center", fontsize=9.5, color=INK)
    ax.set_ylim(3.6, -0.6)
    ax.set_xlim(-2, total + 2)
    ax.axis("off")
    drop = [f"先量就停：{cnt['先量跳过']} 项", f"开发没过：{cnt['开发没过']} 项", f"新图没站住：{cnt['过开发没确认']} 项"]
    for i, d in enumerate(drop):
        ax.text(total + 3, i + 0.5, "→ " + d, fontsize=9, color=INK2, va="center")
    ax.set_title("协议方向第 1–71 轮盘点：69 项网络机制，四道关走到底的只有看门狗", fontsize=11, color=INK)
    save(fig, "fig3_6_funnel.png")


# ---------------------------------------------------------------------------
# 图 7  开发成绩 vs 新地图确认（哑铃图）
# ---------------------------------------------------------------------------
def room_mean(rel):
    """只取房间图实例（名字以 room 开头），按实例等权平均，单位 %。"""
    xs = [r["mean"] for r in load(rel)["per_inst"] if r["inst"].startswith("room")]
    return 100 * sum(xs) / len(xs)


def fig_dev_vs_confirm():
    # 开发：17 个开发实例本来全是房间图；确认：只取 15 个房间图实例（去掉迷宫、随机、仓库），事后重算
    items = [
        ("防死锁看门狗（P35–36）", "p36/dev_compare_d300.json", "p36/confirm_compare.json"),
        ("四项组合（P74–75）", "p74/dev_compare_c4.json", "p75/confirm_compare.json"),
        ("2格门分两道（P74 单开 → P76 只用真门）", "p74/dev_compare_pick.json", "p76/confirm_compare.json"),
        ("三项组合（P74–75）", "p74/dev_compare_c3.json", "p75/confirm_compare_c3.json"),
        ("按实测自动调割名额（P68–69）", "p68/dev_compare_B2.json", "p69/confirm_compare.json"),
    ]
    items = [(n, room_mean(d), room_mean(c)) for n, d, c in items]
    items.sort(key=lambda t: -t[1])
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for i, (n, d, c) in enumerate(items):
        up = c > d
        ax.plot([d, c], [i, i], color=OK if up else GRAY, lw=2, zorder=1)
        ax.scatter([d], [i], s=60, color=BLUE, zorder=2)
        ax.scatter([c], [i], s=70, color=OK if up else ORANGE, zorder=3, marker="D")
        ax.text(max(d, c) + 0.12, i, f"{d:+.2f}% → {c:+.2f}%" + ("  正式确认通过" if up else ""),
                va="center", fontsize=8.8, color=INK)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t[0] for t in items], fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlim(-0.6, 4.8)
    ax.scatter([], [], s=60, color=BLUE, label="开发对比（17 个房间图开发实例）")
    ax.scatter([], [], s=70, color=ORANGE, marker="D", label="新种子确认（15 个房间图实例，每实例 20 局）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    ax.set_xlabel("完成数变化（%，和当时的基线比）", fontsize=9, color=INK2)
    ax.set_title("开发成绩换一批房间图就缩水：只有看门狗反而更高", fontsize=11, color=INK)
    style(ax, ygrid=False, xgrid=True)
    save(fig, "fig3_7_dev_vs_confirm.png")

# ---------------------------------------------------------------------------
# 图 8  四项组合：开发 vs 确认 的逐实例（p74 / p75 原始比较文件）
# ---------------------------------------------------------------------------
def fig_combo():
    dev = load("p74/dev_compare_c4.json")["per_inst"]
    con = [r for r in load("p75/confirm_compare.json")["per_inst"] if r["inst"].startswith("room")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.9), sharey=True,
                                 gridspec_kw={"width_ratios": [17, 15]})
    for ax, data, title in [(a1, dev, f"开发对比（17 个房间图，平均 {room_mean('p74/dev_compare_c4.json'):+.2f}%）"),
                            (a2, con, f"新种子确认（15 个房间图，平均 {room_mean('p75/confirm_compare.json'):+.2f}%）")]:
        data = sorted(data, key=lambda r: -r["mean"])
        vals = [100 * r["mean"] for r in data]
        cols = [(ORANGE if r["inst"] in OFFICIAL else BLUE) for r in data]
        ax.bar(range(len(vals)), vals, color=cols, width=0.7)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([r["inst"] for r in data], rotation=70, fontsize=7)
        ax.axhline(0, color=MUTED, lw=1)
        for i, v in enumerate(vals):
            if i == 0:
                ax.text(i, v + 0.5, f"{v:+.1f}%", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_title(title, fontsize=10, color=INK)
        style(ax)
    a1.set_ylabel("完成数变化（%）", fontsize=9, color=INK2)
    a1.set_ylim(-3, 19)
    a1.legend(handles=[Patch(color=ORANGE, label="官方 4×4 房间图（200/250/300 台）"),
                       Patch(color=BLUE, label="其他房间图")], fontsize=8.5, frameon=False, loc="upper right")
    fig.suptitle("四项机制一起开：好处只来自少数几张特别堵的图，官方 4×4 房间图上几乎不动", fontsize=11, color=INK, y=1.02)
    save(fig, "fig3_8_combo_per_instance.png")


# ---------------------------------------------------------------------------
# 图 0  正式评测：官方 4×4 房间图的三级台阶（r52b 原始记录）
# ---------------------------------------------------------------------------
def fig_ladder():
    rows = [json.loads(l) for l in open(os.path.join(EM, "archive", "workspace", "batches",
                                                     "r52b-baseline", "rows.jsonl"), encoding="utf-8")]
    acc = defaultdict(list)
    for r in rows:
        acc[(r["map"], r["method"])].append(r["completed"])
    meths = ["DEF", "N2", "N2F", "LCAP"]
    names = ["官方入门程序", "+冠军派单", "+修好执行器", "+名额与门口规则（本文）"]
    cols = [GRAY, "#8fb6e8", BLUE, ORANGE]
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    w = 0.2
    for j, (m, nm, c) in enumerate(zip(meths, names, cols)):
        ys = [sum(acc[(mp, m)]) / len(acc[(mp, m)]) for mp in OFFICIAL]
        xs = [i + (j - 1.5) * w for i in range(3)]
        ax.bar(xs, ys, width=w * 0.92, color=c, label=nm)
        for x, y in zip(xs, ys):
            ax.text(x, y + 12, f"{y:.0f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["200 台车", "250 台车", "300 台车"], fontsize=9.5)
    ax.set_ylabel("一局（5000 拍）平均完成单数", fontsize=9, color=INK2)
    ax.set_ylim(0, 1320)
    ax.legend(fontsize=8.5, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    style(ax)
    save(fig, "fig3_0_formal_ladder.png")


# ---------------------------------------------------------------------------
# 图 6b  看门狗确认：只看房间图实例（p36 confirm_compare.json）
# ---------------------------------------------------------------------------
def fig_watchdog():
    data = [r for r in load("p36/confirm_compare.json")["per_inst"] if r["inst"].startswith("room")]
    data.sort(key=lambda r: -r["mean"])
    vals = [100 * r["mean"] for r in data]
    fig, ax = plt.subplots(figsize=(10, 3.3))
    cols = [(ORANGE if r["inst"] in OFFICIAL else BLUE) for r in data]
    ax.bar(range(len(vals)), vals, color=cols, width=0.7)
    for i, v in enumerate(vals):
        ax.text(i, v + (0.25 if v >= 0 else -0.25), f"{v:+.1f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([r["inst"] for r in data], rotation=60, fontsize=7.5)
    ax.axhline(0, color=MUTED, lw=1)
    ax.set_ylabel("完成数变化（%）", fontsize=9, color=INK2)
    ax.set_ylim(-1.5, 12.5)
    ax.legend(handles=[Patch(color=ORANGE, label="官方 4×4 房间图"),
                       Patch(color=BLUE, label="新画的房间图（留出，开发时没见过）")], fontsize=8.5, frameon=False)
    ax.set_title("看门狗确认：好处集中在几张容易锁死的新房间图，官方 4×4 房间图上几乎不动", fontsize=10.5, color=INK)
    style(ax)
    save(fig, "fig3_6b_watchdog_confirm.png")

def copy_existing():
    src = {
        "fig3_2b_replay_tick3000.png": os.path.join(EM, "网络协议方向", "报告源", "图", "演讲_回放_第3000拍.png"),
    }
    for dst, s in src.items():
        shutil.copyfile(s, os.path.join(OUT, dst))
        print("copied", dst)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    copy_existing()
    fig_ladder()
    fig_watchdog()
    fig_roadmap()
    fig_collapse()
    fig_ruler()
    fig_executor()
    fig_routing()
    fig_funnel()
    fig_dev_vs_confirm()
    fig_combo()


# ---------------------------------------------------------------------------
# 图 9  重新测试（2026-11-18）：官方 4×4 房间图上逐项去掉 / 单独加上
#   数据 figures/part3/rerun/ablation_room_4x4.jsonl（600 局，种子 11900–11909 × 规划 171、172）
# ---------------------------------------------------------------------------
def _abl_rows():
    import random as _r, statistics as _st
    rows = [json.loads(l) for l in open(os.path.join(OUT, "rerun", "ablation_room_4x4.jsonl"), encoding="utf-8")]
    by = {(r["map"], r["method"], r["seed"], r["pseed"]): r["completed"] for r in rows}
    def comp(a, b):
        G = [[by[(m, a, s, p)] / by[(m, b, s, p)] - 1 for (mm, k, s, p) in by if mm == m and k == b] for m in OFFICIAL]
        rnd = _r.Random(0)
        ms = sorted(_st.mean(_st.mean(rnd.choice(g) for _ in g) for g in G) for _ in range(4000))
        return 100 * _st.mean(_st.mean(g) for g in G), 100 * ms[100], 100 * ms[3899]
    return comp


def fig_ablation():
    comp = _abl_rows()
    left = [("门口半双工穷尽放行", "noDoor"), ("每门名额（带宽×时延）", "noQuota"), ("执行器信用及时归还", "noSync"),
            ("PFC 死锁看门狗", "noWD"), ("全图接单上限（最大流）", "noGlobal")]
    right = [("门口半双工穷尽放行", "onlyDoor"), ("每门名额（带宽×时延）", "onlyQuota"), ("全图接单上限（最大流）", "onlyGlobal"),
             ("全部打开（完整方法）", "FULL")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.0))
    for ax, items, title, base, col in [
            (a1, left, "从完整方法里去掉一项，完成数掉多少", "FULL", ORANGE),
            (a2, right, "在底座（冠军派单+修好执行器）上只加这一项", "NONE", BLUE)]:
        vals = [comp(k, base) if base == "FULL" else comp(k, base) for _, k in items]
        names = [n for n, _ in items]
        ys = list(range(len(items)))[::-1]
        for y, (m, lo, hi), n in zip(ys, vals, names):
            c = col if (lo > 0 or hi < 0) else GRAY
            ax.barh(y, m, color=c, height=0.6)
            ax.plot([lo, hi], [y, y], color=INK, lw=1)
            x = min(m, lo) if m < 0 else max(m, hi)
            ax.text(x + (-1 if m < 0 else 1), y, f"{m:+.1f}%", va="center", ha="right" if m < 0 else "left", fontsize=9, color=INK)
        ax.set_yticks(ys)
        ax.set_yticklabels(names, fontsize=9)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(title, fontsize=10, color=INK)
        style(ax, ygrid=False, xgrid=True)
    fig.subplots_adjust(wspace=0.55)
    a1.set_xlim(-32, 6)
    a2.set_xlim(0, 92)
    a1.set_xlabel("完成数变化（%，黑线为 95% 区间；灰色＝区间跨 0，看不出作用）", fontsize=8.5, color=INK2)
    a2.set_xlabel("完成数变化（%）", fontsize=8.5, color=INK2)
    fig.suptitle("重新测试：官方 4×4 房间图，200/250/300 台车，每个版本每种车数 20 局（共 600 局，0 错误）", fontsize=10.5, color=INK, y=1.02)
    save(fig, "fig3_9_ablation_rerun.png")


fig_ablation()
