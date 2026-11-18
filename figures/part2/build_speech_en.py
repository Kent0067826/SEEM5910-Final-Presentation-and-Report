"""Build the Part 2 English speech (with Chinese reference) as a Word file.

Run from the repo root:  python3 figures/part2/build_speech_en.py
Needs figures/part2/en/*.png (python3 figures/part2/make_figs_en.py) and python-docx.
Numbers follow the Part 2 report (第二部分_网络建模与主要优化.docx) and its source table.
"""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
FIG = Path(__file__).resolve().parent / "en"
OUT = ROOT / "第二部分_英文演讲稿_Part2_Speech.docx"

GREY = RGBColor(0x6B, 0x77, 0x85)
BLUE = RGBColor(0x1F, 0x4E, 0x9C)

# (slide title, minutes, figure file or None, [(english, chinese), ...])
SLIDES = [
    ("Part 2. Why a computer network?", "0:40", "e01_collapse.png", [
        ("In Part 1 you saw the problem: the longer the robots run, the slower they get. "
         "At the start the fleet finishes about 127 tasks every 500 ticks; later it finishes only 37. "
         "Every robot makes a sensible move, yet they all squeeze toward the same one-cell door, "
         "and the door, which used to pass about 25 robots every 500 ticks, now passes only 2 to 8. "
         "More robots, fewer crossings.",
         "第一部分讲了问题：跑得越久，车队越慢。开局每 500 拍完成约 127 单，后面只剩 37 单。"
         "每台车每一步都合理，但大家都挤向同一道一格宽的门；这道门原来每 500 拍能过约 25 台，后来只过 2 到 8 台。车越多，过得越少。"),
    ]),
    ("Earlier work already thought in networks", "1:00", "e02_prior_work_vs_ours.png", [
        ("We are not the first to see a warehouse as a network. Route guidance counts how many planned "
         "routes use each edge and adds a congestion cost. Guidance graphs tune edge weights, like "
         "tolls on roads. Flow-based assignment solves a min-cost flow. City perimeter control limits "
         "how many cars enter a region; in a San Francisco study the controlled network finished about a "
         "third more trips. Factories protect a single lane with a semaphore, one vehicle at a time.",
         "把仓库看成网络，我们不是第一个。交通流引导数每条边上有几条计划路线，再加上拥堵代价；引导图调整每条边的权重，像给道路收费；"
         "流式派单求最小费用流；城市周界控制限制进入一个区域的车数，旧金山的算例里，受控路网多完成了约三分之一的出行；"
         "工厂用信号量保护单车道，一次只放一辆车。"),
        ("But these are traffic networks and flow networks. They ask which road to take, how expensive "
         "each road is, or how many cars are in a whole region. On our map that falls short in three ways. "
         "Door 6 cannot be avoided, so spreading the flow does not help. Nobody counts the robots that have "
         "already taken a task and are still on their way to the door. And nobody decides, together with "
         "the source, which side the door should serve now. What was missing is the computer-network model.",
         "但这些是交通网和网络流，关心的是走哪条路、每条路多贵、一个区域里总共有多少车。放到我们的地图上有三处不够："
         "门 6 绕不开，分流没用；没人去数已经接了单、还在路上的车；也没人把门先放哪边和源头限量放在一起决定。缺的是计算机网络的建模。"),
    ]),
    ("Why the computer network fits", "0:40", None, [
        ("Our collapse has a name in networking: congestion collapse. In October 1986 the early Internet "
         "collapsed the same way: one link dropped from 32 kilobits per second to 40 bits per second, "
         "about one thousandth. Every router worked; everyone simply sent onto the same link. "
         "The fix was not better routing. It was the TCP window: each sender limits the data that is "
         "sent but not yet delivered, and sizes that limit by link speed times delay. "
         "That is exactly the variable earlier work did not count.",
         "这种崩溃在网络里有名字：拥塞崩溃。1986 年 10 月，早期互联网就这样塌过：一条线路从每秒 32 千比特掉到 40 比特，约千分之一。"
         "每台路由器都正常，只是大家都往同一条线上发。解决办法不是更好的路由，而是 TCP 窗口：每个发送端限制已发出、未送达的数据量，"
         "大小按线速乘时延来定。这正是前人没有数的那个量。"),
    ]),
    ("Flatten the map into a network", "0:40", "e03_map_to_network.png", [
        ("So we flatten the map. 3,646 walkable cells become 16 nodes, one per room, and 31 edges, one per "
         "door. It is a flat network: no backbone, rooms joined directly by doors. Once flattened, door 6 "
         "stands out. It is a cut: remove it and the four lower-left rooms are cut off. 37.6 percent of all "
         "tasks must pass through this one cell.",
         "于是我们把地图压扁：3646 个可走格子变成 16 个点（每个房间一个）和 31 条边（每道门一条）。这是一张扁平网络，没有骨干网，"
         "房间直接靠门相连。压扁之后，门 6 一眼可见：它是一个割，拿掉它，左下 4 个房间就断开了。37.6% 的任务必须经过这一格。"),
    ]),
    ("A dictionary: warehouse to network", "1:00", "e04_warehouse_as_network.png", [
        ("Here is our dictionary. A room is a local network, mostly free-flowing. A door is a link, and a "
         "one-cell door is half-duplex: one direction at a time. The router is the area about eight steps "
         "around the door: within three steps of it, robots spend four times as long not moving as moving. A robot is a packet, "
         "a task is a flow, and task assignment is the sender. Door 6 has a bandwidth of about 26 robots "
         "per 500 ticks and a delay of 247 ticks to reach it.",
         "这是我们的对照词典。房间是局域网，基本畅通。门是链路，一格宽的门是半双工，一次只走一个方向。路由器是门两侧约 8 步的区域："
         "离门 3 步以内，车不前进的时间是前进时间的 4 倍多。机器人是数据包，任务是一条流，派单是发送端。门 6 的带宽约为每 500 拍 26 台，"
         "走到门口的时延约 247 拍。"),
        ("Three differences matter. A robot cannot be dropped. A waiting robot blocks a real cell. And the "
         "fleet size is fixed, so more active robots can mean fewer finished tasks.",
         "有三点不同很关键：机器人不能丢；排队的机器人占着真实的格子；车队总数固定，在干活的车越多，完成的反而可能越少。"),
    ]),
    ("Step 1. Find the ceiling: max-flow, min-cut", "0:40", "e05_four_numbers.png", [
        ("The first network tool is max-flow min-cut: a network can never carry more than its narrowest "
         "cut. Door 6 passes 26 robots per 500 ticks, and 37.6 percent of tasks need it, so the whole map "
         "can finish at most about 69 tasks per 500 ticks. Rerouting cannot raise this ceiling, because "
         "there is no other road. So the question is not which road, but how many robots we send.",
         "第一个网络工具是最大流最小割：一张网络的流量不会超过它最窄的那一刀。门 6 每 500 拍过 26 台，37.6% 的任务要过它，"
         "所以整张图每 500 拍最多完成约 69 单。换路提不高这个上限，因为没有别的路。所以问题不是走哪条路，而是放多少车。"),
    ]),
    ("Step 2. Limit at the source: a window per door", "1:00", "e06_knee.png", [
        ("The second tool is the TCP window. Before assigning a task, we count the robots that already "
         "hold a task and still have to cross door 6 in that direction, including those far away. "
         "If the count is full, we assign a different task. The size comes from bandwidth times delay, "
         "plus a breakdown factor of 2.23: 15 robots into the lower-left area, 10 out.",
         "第二个工具是 TCP 窗口。派单前，我们数一数已经拿着任务、还要往这个方向过门 6 的车，包括还在远处的车。名额满了，就改派别的单。"
         "名额大小按带宽乘时延，再乘故障放慢系数 2.23：进左下 15 台，出左下 10 台。"),
        ("This chart shows why. Without control, robots heading for the door grow from 59 to 211, and the "
         "door passes only 3 to 5. With the quota, about 25 robots are in flight and the door runs full at "
         "about 26. Past the knee there is no way back.",
         "这张图说明原因。不管门时，奔向门的车从 59 台涨到 211 台，门却只过 3 到 5 台。有了名额，在途约 25 台，门基本跑满，约 26 台。"
         "过了拐点就回不来了。"),
    ]),
    ("Step 3. Serve one side at a time, in batches", "1:00", ["e08_door_rule.png", "e07_batch_utilization.png"], [
        ("The third tool is half-duplex scheduling. The door serves one direction at a time. Robots waiting "
         "on the other side back off four cells to keep the exit clear, because a waiting robot is not a "
         "packet in memory; it stands in the way. When this side is empty, the door switches.",
         "第三个工具是半双工调度。门一次只服务一个方向；对面等待的车退到 4 格以外，把出口让出来，因为排队的车不是内存里的包，而是真的挡在路上。"
         "这一边走空了，门才换方向。"),
        ("[Show the batch chart] Why batches? A switch costs 21 ticks, while robots in one direction can "
         "follow each other every 9 ticks. Switch after every robot and the door is busy only 43 percent "
         "of the time; let ten through and it is busy 88 percent.",
         "［切到成批放行图］为什么要成批？换一次方向要 21 拍，同方向的车每 9 拍就能跟进一台。每过一台就换向，门只有 43% 的时间在用；"
         "每次放十台，就到 88%。"),
    ]),
    ("Steps 4 to 6. A fleet cap, a late credit, a watchdog", "1:00", None, [
        ("Step 4 is a fleet-wide cap, from Little's law and city perimeter control: on the official room map, "
         "138 robots holding tasks are enough to keep door 6 full; the rest wait without adding congestion.",
         "第四步是全图接单上限，来自 Little 定律和城市周界控制：官方房间图上，138 台车拿着任务就足够让门 6 跑满，其余的车待命，不添堵。"),
        ("Step 5 came from looking with network eyes. The door stayed stuck at 22. A robot that had left a "
         "cell still held it in the execution queue: the slot was free, but the credit came back one tick "
         "late. A three-line fix gave the champion's own program 16.7 percent more tasks.",
         "第五步来自用网络的眼光查账。门一直卡在 22 台：车已经离开一格，执行队列里却还占着它，空位空了，信用却晚还了一拍。"
         "改三行代码，冠军自己的程序就多完成了 16.7%。"),
        ("Step 6 borrows from lossless data-center networks. Two doors one step apart can lock each other. "
         "If a robot has waited 300 ticks and its door has seen no entry for 300 ticks, it may ignore the "
         "door rule for one tick, while collision checks stay on. Confirmed on new maps: plus 1.73 percent.",
         "第六步借自数据中心的无损网络。两道只隔一步的门会互相锁死。如果一台车等了 300 拍、它的门 300 拍没有车进，"
         "这一拍就允许它不守门口规则，防撞检查照常。在新地图上确认：+1.73%。"),
    ]),
    ("Results", "0:40", "e09_results.png", [
        ("On the eight official instances, 20 runs each: the champion's assignment adds 27 percent over the "
         "official starter, fixing the executor brings it to 63 percent, and our door control brings it "
         "to 113.6 percent. Against the same champion with the same fixed executor, the fairest comparison, "
         "we finish 32.7 percent more. On the 250-robot room map, tasks per run rise from 618 to 1,106. "
         "On maps without narrow doors the control stays off and changes nothing.",
         "在官方 8 个实例上，每个 20 局：换上冠军派单比官方起始程序多 27%，修好执行器到 63%，再加门控到 113.6%。"
         "和同样修好执行器的冠军比，这是最公平的比较，我们多完成 32.7%。250 台车的房间图上，每局从 618 单涨到 1106 单。"
         "没有窄门的地图上控制不启用，结果不变。"),
    ]),
    ("Take-away", "0:20", None, [
        ("We did not make each robot smarter. We managed the warehouse like a network: how many robots head "
         "for a door, and which side the door serves. Bandwidth, delay and switching cost told us the "
         "numbers. Next, Part 3 shows the experiments, and the failures, that led us here.",
         "我们没有让每台车更聪明，而是像管网络一样管仓库：多少车奔向这道门，这道门先放哪一边。带宽、时延和换向开销直接给出了参数。"
         "接下来第三部分讲我们是怎样一轮轮实验、包括失败，走到这里的。"),
    ]),
]


def set_run_font(run, latin, east, size, color=None, bold=False, italic=False):
    run.font.name = latin
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), east)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin = sec.bottom_margin = Cm(2.0)

    p = doc.add_paragraph()
    set_run_font(p.add_run("Part 2 Speech: Managing a Warehouse as a Computer Network"),
                 "Times New Roman", "黑体", 18, bold=True)
    p = doc.add_paragraph()
    set_run_font(p.add_run("第二部分英文讲稿（逐段附中文对照）"), "Times New Roman", "黑体", 12, GREY)

    words = sum(len(en.split()) for _, _, _, paras in SLIDES for en, _ in paras)
    p = doc.add_paragraph()
    set_run_font(p.add_run(
        f"怎么用：黑字英文是要讲的话，灰字是中文对照。每页标题可直接当幻灯片标题，标题后是建议用时和配图。"
        f"英文约 {words} 词，按每分钟 125 词约 {words / 125:.0f} 分钟。图片都在仓库 figures/part2/en/。"
        f"数字与第二部分报告一致，来源见报告末尾的数字来源表。"),
        "Times New Roman", "宋体", 10, GREY)

    for i, (title, mins, fig, paras) in enumerate(SLIDES, 1):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(14)
        h.paragraph_format.keep_with_next = True
        set_run_font(h.add_run(f"Slide {i}. {title}"), "Times New Roman", "黑体", 13, BLUE, bold=True)
        figs = [fig] if isinstance(fig, str) else (fig or [])
        cue = f"  ({mins}" + (f", figure {' + '.join(figs)})" if figs else ")")
        set_run_font(h.add_run(cue), "Times New Roman", "宋体", 9.5, GREY)
        for f in figs:
            ip = doc.add_paragraph()
            ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ip.add_run().add_picture(str(FIG / f), width=Cm(12))
        for en, zh in paras:
            pe = doc.add_paragraph()
            pe.paragraph_format.line_spacing = 1.35
            pe.paragraph_format.space_after = Pt(2)
            set_run_font(pe.add_run(en), "Times New Roman", "宋体", 12)
            pz = doc.add_paragraph()
            pz.paragraph_format.space_after = Pt(8)
            pz.paragraph_format.left_indent = Cm(0.4)
            set_run_font(pz.add_run(zh), "Times New Roman", "宋体", 10, GREY)
    doc.save(OUT)
    print("wrote", OUT, words, "words")


if __name__ == "__main__":
    main()
