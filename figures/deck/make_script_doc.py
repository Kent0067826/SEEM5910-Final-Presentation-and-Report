"""Write the Markdown source of the Word speech script from script.json (run from the repo root, then pandoc)."""
import json, re, sys
ver = sys.argv[1] if len(sys.argv) > 1 else "v2"
S = json.load(open("figures/deck/script.json", encoding="utf-8"))
tot = {}
for s in S:
    m, sec = map(int, s["time"].split(":")); tot[s["speaker"]] = tot.get(s["speaker"], 0) + m * 60 + sec
words = sum(len(re.sub(r"【[^】]*】", "", s["en"]).split()) for s in S)
cue = lambda t: re.sub(r"【([^】]*)】", r"*【\1】*", t)
parts = {1: "开场、比赛背景、越跑越慢", 2: "堵在门口（花一周写监测程序看回放）、前人工作、我们试过的全部办法（提升都不大）、拥塞监测程序（不管怎么改选路，拥塞总在同几处）",
         3: "技术部分：模型和车的特点、改路线还是改调度（在这里引出 DoorFlow）、名额（TCP 窗口的逻辑、像 BBR 一样全局调控、名额一版一版改出来）、门口规则（一次一个方向、门口的队列调度）、执行器修复",
         4: "伪代码、最难的部分和拥堵回放演示、随机门新图测试和两个兜底、结果、哪些起作用、五条经验（DoorFlow 为什么是这个样子）、结论"}
L = ["# SEEM5910 演讲稿与幻灯片（四人，15 分钟）", "",
     f"这份 Word 是幻灯片 `SEEM5910_演讲PPT_{ver}.pptx` 的讲稿版。每页依次是：幻灯片图片；讲者、时长和配图；**提示卡**（几个要点，看一眼就能接着讲）；讲稿（**每一段英文下面紧跟它的中文**，英文用简单词和短句，方便记、讲得快也好懂）。",
     "讲稿里的 *【……】* 是动作提示，告诉你这时指图上哪里；**加粗**的是这一页要讲准的关键句和数字。幻灯片备注栏里有同样的提示卡和讲稿，放映时用演讲者视图就能看到。", "",
     "## 分工和时间", "", "| 讲者 | 负责的页 | 内容 | 时长 |", "|---|---|---|---|"]
for k in sorted(tot):
    pages = [str(s["n"]) for s in S if s["speaker"] == k]
    L.append(f"| 讲者 {k} | 第 {pages[0]}–{pages[-1]} 页 | {parts[k]} | {tot[k] // 60}:{tot[k] % 60:02d} |")
T = sum(tot.values())
L += [f"| 合计 | {len(S)} 页 | | {T // 60}:{T % 60:02d} |", "",
      "讲者 3 负责模型、名额、门口规则和执行器修复这些主要的技术内容，所以时间最长；讲者 1、2 讲问题和想法；讲者 4 讲伪代码、最难的部分和演示、随机门测试和两个兜底、结果和结论。交接处的讲稿里都写好了交接语。", "",
      f"英文讲稿共 {words} 词（不算动作提示）：按每分钟 130 词约 {words / 130:.1f} 分钟，按放慢到每分钟 110 词约 {words / 110:.1f} 分钟。各页时长是 15 分钟的分配，讲稿比它短，留出了放慢语速和停顿指图的时间。", ""]
for s in S:
    figs = "；".join(s["figs"]) if s["figs"] else "无（文字和数字卡片）"
    L += [f"## 第 {s['n']} 页　{s['title']}", "", f"![第 {s['n']} 页](figures/deck/slides/slide-{s['n']:02d}.png)", "",
          f"**讲者 {s['speaker']}　·　{s['time']}　·　配图：{figs}**", "", "**提示卡**", ""]
    L += [f"- {h}" for h in s["hints"]]
    L += ["", "**讲稿**", ""]
    for g in s["segs"]:
        L += [cue(g["en"]), "", "> " + cue(g["zh"]), ""]
L += ["## 说明", "", "- 图号指《全文简明版（中文）v11》里的图号；幻灯片里的图和报告共用，图中文字都是英文。",
      "- 第 7、10、11、14、16、17、20 页用的是演讲专用图（第 6 页的全部尝试总表和第 21 页的五条经验直接做在幻灯片上），放在 `figures/deck/`：在途量与带宽时延积原理图、BBR 控制环与 DoorFlow 对照图（`make_principle_figs.py`）、门利用率公式图（同报告图 11，只改了标题）、伪代码（幻灯片上，和源码 `nms_scheduler.cpp`、`netmac.cpp` 逐条对过）、拥堵回放动图、逐项拿掉与加上图（`make_deck_ablation.py`，数据和报告图 16 相同，只把标签改成不带网络术语的说法）。",
      "- TCP 窗口和 BBR 只在第 10、11 页出现，是 DoorFlow 借用的原理，讲的时候说清楚出处；其余页不用网络术语。",
      "- 第 7 页的截图是拥塞监测程序 `figures/deck/demo/congestion_monitor.html`（第 3000 拍）：同一张官方房间图、250 台车、同一组种子（9700 / 101），都不控制门，只换选路（冠军的选路、HN-SPF 链路代价、Fortz–Thorup 权重），各跑一局；右边“Where jams happen”是每道门在整局里堵着的时间比例，门 6 在三种选路下都是 91%–94%。完成数 609 / 435 / 612 是这一局的结果；HN-SPF 和 Fortz–Thorup 在报告里的 −25.88% 和 −0.29% 是多张图、加在当时完整方法上的测试，和这一局口径不同。数字见 `figures/deck/demo/monitor_stats.json`。",
      "- 第 17 页的回放动图来自 `figures/deck/demo/`：`doorflow_demo.html` 用浏览器打开就能看（两边同步播放，拥堵的车和门自动变红，可拖动时间轴、跳到第 3000 拍）；609 和 1130 是这一局（官方房间图 250 台，种子 9700 / 101）的完成数，不是平均值。复现步骤写在 `run_demo.py` 和 `build_demo.py` 开头。",
      "- 讲稿里的数字都取自全文简明版，出处见那份文档末尾的数字来源表。",
      "- 幻灯片由 `figures/deck/build_deck.js` 生成，讲稿来自 `figures/deck/script.json`，这份 Word 由 `figures/deck/make_script_doc.py` 生成；改讲稿时改 script.json，再重新生成两份。", ""]
open("figures/deck/演讲稿_源稿.md", "w", encoding="utf-8").write("\n".join(L))
print(words, tot)
