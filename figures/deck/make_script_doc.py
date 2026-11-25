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
         3: "技术部分：模型和天花板（为什么改路线没用）、我们的车和计算机网络、道路交通哪里不同（所以要自己想出新算法 DoorFlow）、每道门的窗口（门 6 的每个数逐个推算）和名额、门口规则（一次一个方向、实测门要多少拍、走空再换、缓冲区多大）",
         4: "伪代码、最难的部分和拥堵回放演示、随机门新图测试、两个兜底（窄门口的全图上限、看门狗）、结果、哪些起作用、五条经验、结论"}
L = ["# SEEM5910 演讲稿与幻灯片（四人，15 分钟）", "",
     f"这份 Word 是幻灯片 `SEEM5910_演讲PPT_{ver}.pptx` 的讲稿版。每页依次是：幻灯片图片；讲者、时长和配图；**提示卡**（几个要点，看一眼就能接着讲）；讲稿（**每一段英文下面紧跟它的中文**）。",
     "**怎么用：** 讲稿里[加下划线]{.underline}的英文是连接词（开场、过渡、交接），幻灯片上没有，需要自己记住说出来；其余英文都印在幻灯片上，可以照着读。*【……】* 是动作提示，告诉你这时指图上哪里；**加粗**的是要讲准的关键句和数字。幻灯片备注栏里还有提示卡和中英文讲稿。", "",
     "## 分工和时间", "", "| 讲者 | 负责的页 | 内容 | 时长 |", "|------|-------|----------------------------|----|"]
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
D_ = json.load(open("figures/deck/demo/door6_numbers.json", encoding="utf-8"))
LC = json.load(open("figures/deck/demo/live_control.json", encoding="utf-8"))
def lc(v):
    r = LC["variants"][v]
    return f"{r['change_vs_DF_pct']:+.2f}%（95% 区间 {r['ci95_pct'][0]:+.2f}% 到 {r['ci95_pct'][1]:+.2f}%，60 局里 {r['worse_runs']} 局比 DoorFlow 少）"
pg = lambda key: next(s["n"] for s in S if key in s["title"])
L += ["## 说明", "", "- 图号指《全文简明版（中文）v11》里的图号；幻灯片里的图和报告共用，图中文字都是英文。",
      "- 幻灯片上的英文和这份 Word 里的英文都由 `figures/deck/script.json` 生成：幻灯片上印的是讲稿去掉连接词和动作提示后的部分，字号按每页字数自动定在 14–20 号。",
      f"- 演讲专用图：第 {pg('Where jams happen')} 页拥塞监测程序截图；第 {pg('why a fixed window')} 页三种边看边调做法的重跑对比（`demo/live_control.py`）；第 {pg('a window for each door')} 页窗口大小原理图、第 {pg('serve one side')} 页门速度曲线（`make_principle_figs.py`）；第 {pg('one direction at a time')}、{pg('how big should the buffer')} 页是门口规则详图的两半（A；B 和 C，`make_crops.py` 从 `fig_door_rule_deck.png` 切出）；第 {pg('how long does the door take')} 页过门间隔实测（`demo/door_timing.py`）；第 {pg('The hardest part')} 页回放动图；第 {pg('Two safety nets')} 页窄门口拥堵图（`demo/narrow_spots.py`）；第 {pg('Results')} 页结果图和第 {pg('Which parts matter')} 页逐项拿掉与加上（`make_deck_ablation.py`）。第 6 页的全部尝试总表、第 {pg('What makes our robots different')} 页的对比表、第 {pg('number by number')} 页的推算表和第 {pg('Lessons')} 页的五条经验直接做在幻灯片上。",
      f"- 第 {pg('What makes our robots different')} 页的对比表（我们的车 / 计算机网络 / 道路交通）：阴影格表示和我们的车不一样；计算机网络这一列六行都不一样，道路交通这一列前两行（车不能丢、等着的车占地方）一样、后四行不一样，所以两边的算法都不能直接照搬。",
      f"- 第 {pg('Why did changing routes')} 页的 37.6% 是概率估算：取货点和送货点随机落在地图上，两头在门 6 两侧的概率 = 2 × 0.2507 × 0.7493 ≈ 0.3757（0.2507 = 906 ÷ 3614，数格子得到；讲稿里不用 0.25 × 0.75，那样算出来是 37.5%）；任务文件实际是 38.5%。天花板 26 ÷ 0.3757 = 69.2 单 / 500 拍（程序里的线性规划结果 λ = 0.13841 每拍，`experiment-materials/archive/workspace/netmodel_r43/data/little_r47.json`），第 20 页用的就是 69.2；这一页的公式图先把 f 四舍五入成 0.376，所以写的是 69.1。门 6 每 500 拍 26 台是实测（第 40 轮测出 26；第 52 轮给 669 次过门计时，平均每台 18.7 拍，500 ÷ 18.7 ≈ 26.7；这次 5 局新仿真 {D_['door_rate']['crossings']} 次过门 / {D_['door_rate']['ticks']} 拍 = 每 500 拍 {D_['door_rate']['per_500']:g} 台）。",
      f"- 第 {pg('a window for each door')} 页的“窗口 = 过门速率 × 路程时间”：门每 r 拍放进一台、一趟路 T 拍，过去 T 拍里派出的车都还在路上，共 T ÷ r 台。这条计数规律在排队论里叫 Little 定律（1961 年），不是我们发现的；讲稿里不提名字，第 {pg('a window for each door')} 页的图注里写了，老师问起可以直接说。",
      f"- 第 {pg('number by number')} 页每个数的来历：① 过门速率：实测每 500 拍 26 台，两个方向各一半（5 局新仿真里进左下 {D_['door_rate']['into_lower_left']} 台、出 {D_['door_rate']['out_of_lower_left']} 台），每个方向 13 台，500 ÷ 13 ≈ 38.5 拍一台。② 空路路程：任务是随机出现的，所以不算某一单，而是取平均。程序从地图算（`window_control.cpp` 的 `cut_tfree`）：25 拍（接单后走到取货点，第 41 轮实测中位数 21、平均 28，见 `experiment-materials/archive/workspace/netmodel_r41/model_data/legs.json`）+ 门另一侧每一格到门口的最短时间的平均（走一步或转 90° 都是 3 拍）。程序打印的值是进 247、出 158（`ROBOT_BRIDGE_TRACE=1`），我们用 `demo/door6_numbers.py` 独立重算得 {D_['free_trip']['T_inward']:g}、{D_['free_trip']['T_outward']:g}，差 1–3%（两侧格子的划分略有不同）。③ 放慢倍数 2.23：第 40 轮实测。对每道割门、每个方向，记下车从接到要过这道门的单、到走到门口的实际平均时间，除以空地图上的最短时间；224 组（门 × 方向 × 地图，冠军派单程序，有故障）的中位数是 2.23。门 6 往左下：空地图 250 拍，实际 557–586 拍（200 / 250 / 300 台）。同样的测量把故障关掉，54 组的中位数是 1.33（门 6 往左下 1.38–1.41 倍），所以多出来的时间大部分是故障造成的：(2.23 − 1.33) ÷ (2.23 − 1) ≈ 73%。车自己停下的时间可以按概率估算：比赛设定每拍平均有 250 × 0.01 = 2.5 台车出故障（泊松），每次停 10–30 拍、平均 20 拍，任何时候约 2.5 × 20 = 50 台（20%）停着，这只让路程变成 1 ÷ (1 − 0.2) = 1.25 倍；1.33 × 1.25 ≈ 1.66，比 2.23 小，差的部分应当是排在坏车后面等的时间（推断，没有单独测）。数据在 `experiment-materials/archive/workspace/netmodel_r41/model_data/latency_pairs.json`，`demo/door6_numbers.py` 复算 2.23 和 1.33。报告全文把 2.23 叫“故障放慢倍数”，严格说它是有故障时的总放慢倍数。v30 讲稿说“故障只解释 1.25 倍，其余是等别的车”，不完整，v31 已改。 ④ 窗口：2.23 × 247 ≈ 551 拍，551 ÷ 38.5 ≈ 14.3 → 15；2.23 × 158 ≈ 352 拍，352 ÷ 38.5 ≈ 9.2 → 10。提前算好的只有 15 / 10 这两个上限；“路上有几台”是每一轮派单时实时数的（程序知道每台车接的单要不要过门 6、过没过门）。为什么不把上限也做成实时调：第 34 轮“测到拥堵才限流”房间图少 7–15 个百分点（测到时车已经堵在门口）；第 38 轮按延迟自动加减名额（AIMD）不如固定值（每局只有约 10 个 500 拍的窗口，波动 ±10%，边跑边调调不准）；第 42 轮按门的物理容量（每 500 拍 49 台）设名额 −1.45%，room300 −17.2%（远高于门实际能过的 26 台）；第 50–51 轮 BBR 式自适应上限 +0.08%（见报告全文第 1 阶段没留下的尝试表）。",
      f"- 第 {pg('why a fixed window')} 页的三种“边看边调”是这次重跑的（`demo/live_control.py`；规划器补丁 `demo/live_window.patch`；不打开开关时程序行为不变：抽查 2 对种子，打补丁前后完成数完全相同，1113 单和 1042 单）。官方房间图 200 / 250 / 300 台，用第 52 轮正式评测的同一组种子（任务种子 11700–11709 × 规划种子 145、146），每种做法 60 局，共 {LC['runs']} 局、{LC['errors']} 个错误；每局都和同种子的 DoorFlow 比。重跑的 DoorFlow 平均完成数和正式评测相差不到 0.6%（{'、'.join(f'{k[4:]} 台 {v[0]:g} 对 {v[1]:g}' for k, v in LC['df_mean_vs_formal_evaluation'].items())}；正式评测用的是第 51 轮的程序）。"
      f"① 只在看到堵时才限（第 34 轮的想法）：按拥塞监测程序的规则判断门口堵了（门 5 步以内有 8 台以上卡住的车：接着单、12 拍以上没动），堵了才打开门 6 的名额，卡住的车降到 2 台以下就关掉：{lc('JAM')}；从第一次堵起一直开着：{lc('LATCH')}。"
      f"② 按实测延迟自动加减名额（第 38 轮的规则，当时用在成对的门上）：从公式值 15 / 10 开始，每 250 拍算一次门口 3 格以内每过一台的等待时间，超过 250 拍就减半（不低于 8），否则在拒过单的方向加 2（不超过 48）：{lc('AIMD')}；名额在 {LC['variants']['AIMD']['window_in_range'][0]}–{LC['variants']['AIMD']['window_in_range'][1]} 之间来回变。"
      f"③ 按物理容量（第 42 轮）：公式里的门速度用 49 台 / 500 拍（一格门换着方向最多能过的台数）代替实测的 26 台，名额变成 {LC['variants']['PHYS']['window_in']} 台进：{lc('PHYS')}。"
      f"原来那三轮加在当时较早的版本上（第 34 轮管的是全图上限，第 38 轮管的是成对的门），所以数字和报告里的“房间图少 7–15 个百分点”“不如固定 24 台”“−1.45%”不同；这次都加在最终的 DoorFlow 上，只改门 6 这类单门割的名额。",
      f"- 第 {pg('the quota for each door')}、{pg('one direction at a time')} 页的 +29.1%（只开名额）和 +27.6%（只开门口规则）是第 28–29 轮的消融：17 个有一格宽割门的房间实例，和冠军派单比，当时名额还是手调的 8 台（报告全文第 28–29 轮）。第 {pg('Which parts matter')} 页的 +29.3%、+29.7%、+76.4% 是最后在官方房间图上重跑的 600 局（和底座比，名额用公式；第三部分源稿 R1）。两次测试的地图、底座和名额都不同，所以数字不一样，讲稿里分别注明了范围。第 {pg('Which parts matter')} 页的 +76.4%（600 局重跑，全部打开）和报告里的 +76.5%（第 52 轮正式评测，和同一底座比）也是两次不同的测试。",
      f"- 第 {pg('how long does the door take')}、{pg('serve one side')} 页的拍数是这次重新跑仿真测的（`demo/door_timing.py`，结果在 `demo/door_timing.json`）：官方房间图 250 台、DoorFlow 正式配置、种子 9700–9704（规划种子 101），每局 5000 拍，共 {T_['door6_crossings']} 次过门。同方向下一台：中位数 {sg['median']:g} 拍，最常见 6 拍和 9 拍（2 步、3 步；比赛设定走一步 3 拍，agentCounter = 3，{T_['move_time']['share_most_common']:.0%} 的移动正好 3 拍），最快 {sg['min']} 拍；换方向后第一台：中位数 {sw['median']:g} 拍（四分位 {sw['p25']:g}–{sw['p75']:g}）；平均每轮放 {T_['robots_per_turn']:g} 台。报告第 40 轮测的是 9 拍和 21 拍，那是更早的版本；现在要等 4 格缓冲区清空才换向，所以换向变慢，讲稿和图都用这次新测的数。",
      f"- 第 {pg('serve one side')} 页的换向实验：按固定时间表换向 −4.98%、−6.43%（第 6 页表里的 802.1Qbv）；把“每轮最多放 80 步”换成“走空再换”，总体 +1.11%，其中官方房间图 −0.4%、新生成的房间图 +1.9%（第 46 轮）。",
      f"- 第 {pg('how big should the buffer')} 页的缓冲区：下限按“下一台出来前，前一台走出几格”估：9–10 拍 ÷ 每步 3 拍 ≈ 3 格（代码里的同一公式见 `netmac.cpp` 第 59–62 行注释，第 57 轮）；再在 12 个开发实例上实测 1、2、3、4、6 格（v58 附录 H）；3 格的确认测试 −2.64%、堵死局 11 → 29（第 54–57 轮），所以用 4 格。18.7 拍和 4.8 拍来自第 52 轮给 669 次过门的逐拍计时；4.8 ÷ 18.7 ≈ 26%，和“任何时候 20% 的车停着”量级一致（还要加上被前面坏车挡住的时间）。",
      f"- 第 {pg('Two safety nets')} 页的窄门口：随机门图 GenH、249 台、种子 11901 / 172，有无全图上限各重跑一局，完成数 {N_['orders']['FULL']} / {N_['orders']['noGlobal']}，和存档 `figures/part3/rerun/general_gen4x4.jsonl` 完全一致。上限由程序按地图自动算（ROBOT_ADMIT_AUTO，和离线公式只差 1–2 台，第 59 轮），这一局里同时接单的车从没超过 {N_['runs']['FULL']['max_holding_orders']} 台；没有上限时 249 台全都接着单。虚线圈是整局卡住时间最多的两处，都在窄门口。这张图 10 对局平均 −16.9%（同一份存档）。官方图的上限：1.76 × 69.2 ÷ 500 × 2.23 × 255 ≈ 138.5，向下取整得 138 台。69.2 是天花板（第 {pg('Why did changing routes')} 页）；255 拍 = 25（接单后走到取货点）+ 230.4（取货到送货的空路平均，程序从地图算）；2.23 同第 {pg('number by number')} 页；69.2 ÷ 500 × 2.23 × 255 ≈ 79 是“同时在忙的车数”的预测；1.76 是第 46 轮扫描上限时，“结果不再上涨的上限 ÷ 这个预测”在各张图上的中位数（`experiment-materials/archive/workspace/scripts/r47_common.py`，输入值见 `experiment-materials/archive/workspace/netmodel_r43/data/little_r47.json`）。程序里比例写成 1.76 × 0.31538 = 0.555（`lcap_env17_wd.json` 的 ROBOT_ACTIVE_CAP），名额 = ⌊0.555 × 250⌋ = ⌊138.75⌋ = 138（`nms_scheduler.cpp` 里是向下取整）。",
      f"- 第 {pg('Results')} 页的 +140.5%：第 52 轮正式评测（r52b）里官方房间图 200 / 250 / 300 台各 20 局、60 对同种子局，每对“DoorFlow ÷ 官方起始程序”的比值取平均。柱子上的 +145% / +124% / +152% 是每种车数 20 对比值的平均（三个数的平均就是 +140.5%）；直接拿柱高相除（例如 1169 ÷ 473 ≈ 2.47）是“平均数之比”，所以和标签略有不同（`make_deck_ablation.py` 的 results）。和报告里“比同一底座（冠军派单 + 修好的执行器）+76.5%”不是一个口径；执行器修复这次按要求不在演讲里讲，第 {pg('Which parts matter')} 页右边的“base program”就是这个底座。",
      f"- 第 {pg('Where jams happen')} 页的截图是拥塞监测程序 `figures/deck/demo/congestion_monitor.html`（第 3000 拍）：同一张官方房间图、250 台车、同一组种子（9700 / 101），都不控制门，只换选路（冠军的选路、HN-SPF 链路代价、Fortz–Thorup 权重），各跑一局；右边“Where jams happen”是每道门在整局里堵着的时间比例，门 6 在三种选路下都是 91%–94%。完成数 609 / 435 / 612 是这一局的结果；HN-SPF 和 Fortz–Thorup 在报告里的 −25.88% 和 −0.29% 是多张图、加在当时完整方法上的测试，和这一局口径不同。数字见 `figures/deck/demo/monitor_stats.json`。",
      f"- 第 {pg('The hardest part')} 页的回放动图来自 `figures/deck/demo/`：`doorflow_demo.html` 用浏览器打开就能看（两边同步播放，拥堵的车和门自动变红，可拖动时间轴、跳到第 3000 拍）；609 和 1130 是这一局（官方房间图 250 台，种子 9700 / 101）的完成数，不是平均值。复现步骤写在 `run_demo.py` 和 `build_demo.py` 开头。",
      "- 其余数字都取自全文简明版，出处见那份文档末尾的数字来源表。",
      "- 幻灯片由 `figures/deck/build_deck.js` 生成，讲稿来自 `figures/deck/script.json`，这份 Word 由 `figures/deck/make_script_doc.py` 生成；改讲稿时改 script.json，再重新生成两份。", ""]
open("figures/deck/演讲稿_源稿.md", "w", encoding="utf-8").write("\n".join(L))
print(words, tot)
