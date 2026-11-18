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
    ("Part 2. Why a computer network?", "0:50", "e01_jam_tick3000.png", [
        ("In Part 1 you saw the problem: the longer the robots run, the slower they get, from about 127 tasks "
         "every 500 ticks at the start to 37 later. This frame from a real run shows why. At tick 3000, orange "
         "robots must cross door 6 into the lower-left rooms and blue robots must come out. They meet face to "
         "face at a one-cell door. 97 robots wait to go in, 38 wait to come out, and 130 robots hold a task but "
         "cannot move. Every robot followed its plan, and the plans all ended at the same door.",
         "第一部分讲了问题：跑得越久越慢，从开局每 500 拍约 127 单掉到后来的 37 单。这张真实运行的画面说明了原因。"
         "第 3000 拍，橙色的车要穿过门 6 进左下的房间，蓝色的车要出来，两边在一格宽的门口面对面顶住。97 台等着进，38 台等着出，"
         "全图 130 台车拿着任务却动不了。每台车都按计划走，而所有计划都走到了同一道门。"),
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
        ("But these are traffic networks and flow networks. They ask which road to take, how expensive each "
         "road is, or how many cars are in a whole region. On our map that falls short in three ways, "
         "and we have evidence for each.",
         "但这些是交通网和网络流，关心的是走哪条路、每条路多贵、一个区域里总共有多少车。放到我们的地图上有三处不够，每一处我们都有证据。"),
    ]),
    ("Three gaps, with evidence", "1:30", ["e02a_no_bypass.png", "e02b_far_from_door.png", "e02c_both_needed.png"], [
        ("First, door 6 cannot be avoided. A linear program over the room network shows that only door 6 limits "
         "the whole map: one more robot per 500 ticks through door 6 gives 2.66 more tasks, while widening any of "
         "the other 30 doors gives nothing. And every rerouting method we tried made things worse, by up to "
         "26 percent.",
         "第一，门 6 绕不开。对房间网络求线性规划可以看到，只有门 6 卡住整张图：门 6 每 500 拍多过 1 台车，就能多完成 2.66 单；"
         "其余 30 道门加宽一点都没用。我们试过的每一种换路办法都让结果变差，最多差了约 26%。"),
        ("Second, the wrong robots are counted. In the same frame, many orange robots are still rooms away, "
         "but their tasks already commit them to door 6. A rule at the door cannot see them until it is too late.",
         "第二，数的车不对。在同一个画面里，很多橙色的车还在别的房间，但它们的任务已经决定要过门 6。门口的规则要等它们到了才看得见，那时已经晚了。"),
        ("Third, the door and the source must be decided together. We only saw this later, in an ablation: the quota alone gave "
         "29.1 percent more tasks than the champion assignment, the door rule alone 27.6 percent, and both "
         "together 51.2 percent.",
         "第三，门口放行和源头限量要一起决定。这是我们后来在消融实验里才看清的：只开名额比冠军派单多 29.1%，只开门口规则多 27.6%，两个一起开多 51.2%。"),
    ]),
    ("Why we tried a computer network", "0:50", None, [
        ("Our collapse shows two features: past some point, more load means less throughput, and many "
         "independent deciders share one bottleneck. The 1986 Internet congestion collapse shows the same two "
         "features: one link fell from 32 kilobits per second to 40 bits per second. But the cause was "
         "different. There, acknowledgements were delayed or lost in long queues, senders kept retransmitting, "
         "and the link filled with duplicates. Robots are never retransmitted or dropped; they jam face to "
         "face at a one-cell door and block the cells others need.",
         "我们看到的崩溃有两个特征：负载超过某一点后吞吐下降；许多各自做决定的个体共享一个瓶颈。1986 年互联网的拥塞崩溃也有这两个特征，"
         "一条线路从每秒 32 千比特掉到 40 比特。但原因不同：那里是确认包在长队列里延误或丢失，发送端不停重传，线路被重复数据占满。"
         "机器人不会被重传，也不会被丢掉；它们是在一格宽的门口面对面顶住，并占着别人要用的格子。"),
        ("So we did not borrow the fixes for retransmission. We borrowed one idea that does not depend on the "
         "cause: limit, at the source, how much is sent but not yet delivered, so the system stays before the "
         "drop. And because robots cannot be dropped and block cells while they wait, we also looked at "
         "lossless data-center networks, which face pauses, spreading jams and deadlock.",
         "所以我们不借专门对付重传的办法，只借一个不依赖原因的思路：在源头限制已发出、未送达的量，让系统停在下降点之前。"
         "又因为机器人不能丢、等的时候还占着格子，我们也去看了数据中心的无损网络，那里同样有暂停、堵塞蔓延和死锁。"),
        ("So we asked a question that only experiments could answer: if we model the warehouse as a computer "
         "network and borrow its congestion control for the door, will the fleet finish more tasks? "
         "What follows was not planned from the start. We tried ideas one by one, kept what the experiments "
         "supported, and dropped the rest; Part 3 tells that story.",
         "于是我们提出一个只能靠实验回答的问题：如果把仓库按计算机网络建模，借用它管拥塞的办法来管门，车队能不能完成更多的单？"
         "后面的内容不是一开始就定好的，而是一项项试出来的：实验支持的留下，不支持的放弃，这个过程在第三部分讲。"),
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
         "plus a breakdown factor of 2.23: 15 robots into the lower-left area, 10 out. Unlike TCP, the quota is "
         "fixed and is released when a robot crosses the door, not by an acknowledgement, so only an experiment "
         "could tell us whether it works.",
         "第二个工具是 TCP 窗口。派单前，我们数一数已经拿着任务、还要往这个方向过门 6 的车，包括还在远处的车。名额满了，就改派别的单。"
         "名额大小按带宽乘时延，再乘故障放慢系数 2.23：进左下 15 台，出左下 10 台。和 TCP 不同，名额是固定的，靠车过门释放，"
         "不靠确认报文，所以它有没有用只能靠实验回答。"),
        ("This chart shows why. Without control, robots heading for the door grow from 59 to 211, and the "
         "door passes only 3 to 5. With the quota, about 25 robots are in flight and the door runs full at "
         "about 26. Past the knee there is no way back.",
         "这张图说明原因。不管门时，奔向门的车从 59 台涨到 211 台，门却只过 3 到 5 台。有了名额，在途约 25 台，门基本跑满，约 26 台。"
         "过了拐点就回不来了。"),
    ]),
    ("Step 3. Serve one side at a time, in batches", "1:00", ["e08_door_rule.png", "e07_batch_utilization.png"], [
        ("The third tool is half-duplex scheduling. The door serves one direction at a time. Robots waiting "
         "on the other side back off four cells to keep the exit clear. This rule is not in any network "
         "protocol: a waiting packet sits in memory, but a waiting robot stands in the way. When this side is "
         "empty, the door switches.",
         "第三个工具是半双工调度。门一次只服务一个方向；对面等待的车退到 4 格以外，把出口让出来。这一条任何网络协议里都没有：排队的包待在内存里，排队的机器人却挡在路上。"
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
         "A switch's watchdog would drop the stuck packets; robots cannot be dropped. So if a robot has waited "
         "300 ticks and its door has seen no entry for 300 ticks, it may ignore the door rule for one tick, "
         "while collision checks stay on. Confirmed on new maps: plus 1.73 percent.",
         "第六步借自数据中心的无损网络。两道只隔一步的门会互相锁死。如果一台车等了 300 拍、它的门 300 拍没有车进，"
         "这一拍就允许它不守门口规则，防撞检查照常。交换机的看门狗会丢掉卡住的包，机器人不能丢，所以改成暂时放宽规则。在新地图上确认：+1.73%。"),
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
