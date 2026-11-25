"""Write the Markdown source of the Word speech script from script.json (run from the repo root, then pandoc)."""
import json, re, sys
ver = sys.argv[1] if len(sys.argv) > 1 else "v2"
S = json.load(open("figures/deck/script.json", encoding="utf-8"))
T_ = json.load(open("figures/deck/demo/door_timing.json", encoding="utf-8"))
N_ = json.load(open("figures/deck/demo/narrow_spots.json", encoding="utf-8"))
tot = {}
for s in S:
    m, sec = map(int, s["time"].split(":")); tot[s["speaker"]] = tot.get(s["speaker"], 0) + m * 60 + sec
plain = lambda t: re.sub(r"【[^】]*】", "", t).replace("{", "").replace("}", "")
words = sum(len(plain(s["en"]).split()) for s in S)
# 【…】 = pointing cue (italic); {…} = linking words, said from memory, not on the slide (underlined)
cue = lambda t: re.sub(r"\{([^}]*)\}", r"[\1]{.underline}", re.sub(r"【([^】]*)】", r"*【\1】*", t))
parts = {1: "开场、比赛背景、越跑越慢", 2: "堵在门口（花一周写监测程序看回放）、前人工作、我们试过的全部办法（提升都不大）、拥塞监测程序（不管怎么改选路，拥塞总在同几处）",
         3: "技术部分：模型和天花板（为什么改路线没用）、我们的车和计算机网络、道路交通哪里不同（所以要自己想出新算法 DoorFlow）、每道门的窗口（名额）、门口规则（一次一个方向、实测门要多少拍、走空再换、缓冲区多大）",
         4: "伪代码、最难的部分和拥堵回放演示、随机门新图测试、两个兜底（窄门口的全图上限、看门狗）、结果、哪些起作用、五条经验、结论"}
L = ["# SEEM5910 演讲稿与幻灯片（四人，15 分钟）", "",
     f"这份 Word 是幻灯片 `SEEM5910_演讲PPT_{ver}.pptx` 的讲稿版。每页依次是：幻灯片图片；讲者、时长和配图；**提示卡**（几个要点，看一眼就能接着讲）；讲稿（**每一段英文下面紧跟它的中文**）。",
     "**怎么用：** 讲稿里[加下划线]{.underline}的英文是连接词（开场、过渡、交接），幻灯片上没有，需要自己记住说出来；其余英文都印在幻灯片上，可以照着读。*【……】* 是动作提示，告诉你这时指图上哪里；**加粗**的是要讲准的关键句和数字。幻灯片备注栏里还有提示卡和中英文讲稿。", "",
     "## 分工和时间", "", "| 讲者 | 负责的页 | 内容 | 时长 |", "|---|---|---|---|"]
for k in sorted(tot):
    pages = [str(s["n"]) for s in S if s["speaker"] == k]
    L.append(f"| 讲者 {k} | 第 {pages[0]}–{pages[-1]} 页 | {parts[k]} | {tot[k] // 60}:{tot[k] % 60:02d} |")
T = sum(tot.values())
L += [f"| 合计 | {len(S)} 页 | | {T // 60}:{T % 60:02d} |", "",
      "讲者 3 负责模型、名额和门口规则这些主要的技术内容，所以时间最长；讲者 1、2 讲问题和想法；讲者 4 讲伪代码、最难的部分和演示、随机门测试和两个兜底、结果和结论。交接处的讲稿里都写好了交接语。", "",
      f"英文讲稿共 {words} 词（不算动作提示）。按各页时长合计 {T // 60}:{T % 60:02d}，平均每分钟约 {words / (T / 60):.0f} 词，离 15 分钟还留了约 {900 - T} 秒给停顿和指图。", ""]
for s in S:
    figs = "；".join(s["figs"]) if s["figs"] else "无（文字和数字卡片）"
    L += [f"## 第 {s['n']} 页　{s['title']}", "", f"![第 {s['n']} 页](figures/deck/slides/slide-{s['n']:02d}.png)", "",
          f"**讲者 {s['speaker']}　·　{s['time']}　·　配图：{figs}**", "", "**提示卡**", ""]
    L += [f"- {h}" for h in s["hints"]]
    L += ["", "**讲稿**", ""]
    for g in s["segs"]:
        L += [cue(g["en"]), "", "> " + cue(g["zh"]), ""]
sg, sw = T_["same_direction_gap"], T_["switch_gap"]
L += ["## 说明", "", "- 图号指《全文简明版（中文）v11》里的图号；幻灯片里的图和报告共用，图中文字都是英文。",
      "- 幻灯片上的英文和这份 Word 里的英文都由 `figures/deck/script.json` 生成：幻灯片上印的是讲稿去掉连接词和动作提示后的部分，字号按每页字数自动定在 14–20 号。",
      "- 演讲专用图：第 7 页拥塞监测程序截图；第 10 页窗口大小原理图、第 14 页门速度曲线（`make_principle_figs.py`）；第 12、15 页是门口规则详图的两半（A；B 和 C，`make_crops.py` 从 `fig_door_rule_deck.png` 切出）；第 13 页过门间隔实测（`demo/door_timing.py`）；第 17 页回放动图；第 19 页窄门口拥堵图（`demo/narrow_spots.py`）；第 20 页结果图和第 21 页逐项拿掉与加上（`make_deck_ablation.py`）。第 6 页的全部尝试总表、第 9 页的对比表和第 22 页的五条经验直接做在幻灯片上。",
      "- 第 9 页的对比表（我们的车 / 计算机网络 / 道路交通）：阴影格表示和我们的车不一样；计算机网络这一列六行都不一样，道路交通这一列前两行（车不能丢、等着的车占地方）一样、后四行不一样，所以两边的算法都不能直接照搬。",
      "- 第 10 页的窗口：门 6 每个方向每 500 拍 13 台（门每 500 拍 26 台的一半），即每 38.5 拍一台；空路走到门口 247 拍（实测）；随机故障让路程变成 2.23 倍（实测），约 550 拍；路上约 550 ÷ 38.5 ≈ 14.3 台，窗口取 15（出左下方向 158 拍，得 10）。“路上的车数 = 速率 × 时间”在排队论里叫 Little 定律（1961 年），不是我们发现的；讲稿里不提名字，第 10 页的图注里写了，老师问起可以直接说。",
      f"- 第 13、14 页的拍数是这次重新跑仿真测的（`demo/door_timing.py`，结果在 `demo/door_timing.json`）：官方房间图 250 台、DoorFlow 正式配置、种子 9700–9704（规划种子 101），每局 5000 拍，共 {T_['door6_crossings']} 次过门。同方向下一台：中位数 {sg['median']:g} 拍，最常见 6 拍和 9 拍（2 步、3 步；比赛设定走一步 3 拍，agentCounter = 3，{T_['move_time']['share_most_common']:.0%} 的移动正好 3 拍），最快 {sg['min']} 拍；换方向后第一台：中位数 {sw['median']:g} 拍（四分位 {sw['p25']:g}–{sw['p75']:g}）；平均每轮放 {T_['robots_per_turn']:g} 台。报告第 40 轮测的是 9 拍和 21 拍，那是更早的版本；现在要等 4 格缓冲区清空才换向，所以换向变慢，讲稿和图都用这次新测的数。",
      "- 第 14 页的换向实验：按固定时间表换向 −4.98%、−6.43%（第 6 页表里的 802.1Qbv）；把“每轮最多放 80 步”换成“走空再换”，总体 +1.11%，其中官方房间图 −0.4%、新生成的房间图 +1.9%（第 46 轮）。",
      "- 第 15 页的缓冲区：下限按“下一台出来前，前一台走出几格”估：9–10 拍 ÷ 每步 3 拍 ≈ 3 格（代码里的同一公式见 `netmac.cpp` 第 59–62 行注释，第 57 轮）；再在 12 个开发实例上实测 1、2、3、4、6 格（v58 附录 H）；3 格的确认测试 −2.64%、堵死局 11 → 29（第 54–57 轮），所以用 4 格。",
      f"- 第 19 页的窄门口：随机门图 GenH、249 台、种子 11901 / 172，有无全图上限各重跑一局，完成数 {N_['orders']['FULL']} / {N_['orders']['noGlobal']}，和存档 `figures/part3/rerun/general_gen4x4.jsonl` 完全一致。上限由程序按地图自动算（ROBOT_ADMIT_AUTO），这一局里同时接单的车从没超过 {N_['runs']['FULL']['max_holding_orders']} 台；没有上限时 249 台全都接着单。虚线圈是整局卡住时间最多的两处，都在窄门口。这张图 10 对局平均 −16.9%（同一份存档）；官方图的上限是 1.76 × 69.2 ÷ 500 × 2.23 × 255 ≈ 138 台。",
      "- 第 20 页的 +140.5%：第 52 轮正式评测（r52b）里官方房间图 200 / 250 / 300 台各 20 局、60 对同种子局，每对“DoorFlow ÷ 官方起始程序”的比值取平均。和报告里“比同一底座（冠军派单 + 修好的执行器）+76.5%”不是一个口径；执行器修复这次按要求不在演讲里讲，第 21 页右边的“base program”就是这个底座。",
      "- 第 7 页的截图是拥塞监测程序 `figures/deck/demo/congestion_monitor.html`（第 3000 拍）：同一张官方房间图、250 台车、同一组种子（9700 / 101），都不控制门，只换选路（冠军的选路、HN-SPF 链路代价、Fortz–Thorup 权重），各跑一局；右边“Where jams happen”是每道门在整局里堵着的时间比例，门 6 在三种选路下都是 91%–94%。完成数 609 / 435 / 612 是这一局的结果；HN-SPF 和 Fortz–Thorup 在报告里的 −25.88% 和 −0.29% 是多张图、加在当时完整方法上的测试，和这一局口径不同。数字见 `figures/deck/demo/monitor_stats.json`。",
      "- 第 17 页的回放动图来自 `figures/deck/demo/`：`doorflow_demo.html` 用浏览器打开就能看（两边同步播放，拥堵的车和门自动变红，可拖动时间轴、跳到第 3000 拍）；609 和 1130 是这一局（官方房间图 250 台，种子 9700 / 101）的完成数，不是平均值。复现步骤写在 `run_demo.py` 和 `build_demo.py` 开头。",
      "- 其余数字都取自全文简明版，出处见那份文档末尾的数字来源表。",
      "- 幻灯片由 `figures/deck/build_deck.js` 生成，讲稿来自 `figures/deck/script.json`，这份 Word 由 `figures/deck/make_script_doc.py` 生成；改讲稿时改 script.json，再重新生成两份。", ""]
open("figures/deck/演讲稿_源稿.md", "w", encoding="utf-8").write("\n".join(L))
print(words, tot)
