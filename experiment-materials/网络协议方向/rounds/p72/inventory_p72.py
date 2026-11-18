# 第 72 轮：协议方向第 1–71 轮全线盘点（按三层模型 × 结局归类），画两张图
# 数据来自报告源第三、四节和各轮实验结果与分析（手工整理，一项机制一行）
import json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

HERE = Path(__file__).resolve().parent
FIG = HERE.parent.parent / '报告源' / '图'

# (轮次, 机制, 出处, 层, 结局)
# 层：拓扑层 / 路由器层 / 物理层；结局：确认通过 / 过开发没确认 / 开发没过 / 先量跳过
ITEMS = [
    ('1–2', 'RTS/CTS + NAV 预约换向', 'IEEE 802.11', '路由器层', '过开发没确认'),
    ('3', 'EF 门前过门车优先', 'RFC 3246', '路由器层', '开发没过'),
    ('4', 'BFD + LFA 绕开故障车', 'RFC 5880 / 5286', '物理层', '开发没过'),
    ('5', '令牌桶按门速放任务', 'RFC 2697 / TCP pacing', '拓扑层', '开发没过'),
    ('6', 'CoDel + ECN 管派车', 'RFC 8289 / 3168', '拓扑层', '先量跳过'),
    ('7', 'DCTCP 自适应名额', 'RFC 8257', '拓扑层', '先量跳过'),
    ('8', '全双工分车道', 'IEEE 802.3', '路由器层', '先量跳过'),
    ('9', 'VOQ 按方向排队', 'McKeown iSLIP', '路由器层', '先量跳过'),
    ('10', 'PFC 逐跳暂停派车', 'IEEE 802.1Qbb', '拓扑层', '开发没过'),
    ('11', 'TCP 滑动窗口跟车', 'RFC 793', '物理层', '先量跳过'),
    ('11', '二进制指数退避', 'IEEE 802.3', '物理层', '先量跳过'),
    ('12', '令牌环提前释放', 'IEEE 802.5', '路由器层', '开发没过'),
    ('13', 'TXOP 限时放行', 'IEEE 802.11e', '路由器层', '先量跳过'),
    ('13', 'Qbv 固定时间表', 'IEEE 802.1Qbv', '路由器层', '开发没过'),
    ('14', 'FRER 故障换门', 'IEEE 802.1CB', '拓扑层', '开发没过'),
    ('15', 'RACK 按时间判故障', 'RFC 8985', '物理层', '先量跳过'),
    ('15', 'PSFP 门口禁停', 'IEEE 802.1Qci', '路由器层', '先量跳过'),
    ('16', '虚拟直通（转向）', 'Kermani–Kleinrock 1979', '物理层', '先量跳过'),
    ('16–18', 'HTTP/1.1 流水线多派', 'RFC 2616', '拓扑层', '过开发没确认'),
    ('19', '任播 / CDN 就近', 'RFC 4786', '拓扑层', '先量跳过'),
    ('20–21', 'TCP SACK 故障让序', 'RFC 2018', '物理层', '开发没过'),
    ('22', '逐跳信用流控', 'Kung 信用流控 / InfiniBand', '路由器层', '开发没过'),
    ('23', 'Flowlet 切换', 'Kandula 2007', '拓扑层', '先量跳过'),
    ('23', 'RED 随机早期检测', 'Floyd–Jacobson 1993', '路由器层', '开发没过'),
    ('24', '偏转路由', 'Baran 1964 / BLESS', '路由器层', '先量跳过'),
    ('24', 'QUIC 无队头阻塞', 'RFC 9000', '路由器层', '先量跳过'),
    ('25', '虫孔同拍跟进', 'Dally–Seitz 1986', '物理层', '先量跳过'),
    ('26', 'SWAN/B4 严格优先级', 'SIGCOMM 2013', '拓扑层', '开发没过'),
    ('28', 'Fortz–Thorup 格子加权', 'INFOCOM 2000', '拓扑层', '开发没过'),
    ('30', '门口优先（横穿车）', 'iSLIP 优先级', '路由器层', '先量跳过'),
    ('31', '转身藏进排队', '路由器流水线', '物理层', '先量跳过'),
    ('31', '预判路由跟进', 'TCP 窗口', '路由器层', '开发没过'),
    ('32', '多装门口调度器（部分 SDN）', 'Panopticon 2014', '路由器层', '开发没过'),
    ('33', '门簇统一调度', 'PIM / iSLIP', '路由器层', '先量跳过'),
    ('33–34', '2 格门分道 / 自动协商', 'IEEE 802.3u', '路由器层', '开发没过'),
    ('35', 'PFC 死锁看门狗（早版）', 'Guo 2016', '物理层', '开发没过'),
    ('36', 'ECN / DCQCN 降速', 'SIGCOMM 2015', '拓扑层', '先量跳过'),
    ('36', 'K=300 看门狗 + 排水', 'PFC watchdog', '物理层', '确认通过'),
    ('37', 'Duato 逃生通道', 'Duato 1993', '物理层', '过开发没确认'),
    ('38', '拆圈防死锁', 'Dally–Seitz 1987', '物理层', '先量跳过'),
    ('39', '空闲车挡门', '链路层空闲帧', '路由器层', '先量跳过'),
    ('40', 'ARPANET 按时延换门', 'McQuillan 1980', '拓扑层', '先量跳过'),
    ('41', '虚拟直通（门口让位）', 'Kermani–Kleinrock 1979', '物理层', '先量跳过'),
    ('42', '放宽全局名额', 'TCP 窗口', '拓扑层', '开发没过'),
    ('47', 'TCP 窗口扩大（执行窗口）', 'RFC 7323', '物理层', '开发没过'),
    ('48', '到点立刻换目标', 'TCP 快速重传思路', '物理层', '开发没过'),
    ('49', '到点换目标 + 避流路线', 'ECMP / 流量感知', '拓扑层', '开发没过'),
    ('50', '少拐弯路由', 'NoC 转弯模型', '物理层', '先量跳过'),
    ('50', '朝向抖动抑制', 'RFC 2439', '物理层', '先量跳过'),
    ('51', '偏转路由代价', 'BLESS / MinBD', '路由器层', '先量跳过'),
    ('52', 'oFIB 不退回刚离开的格', 'RFC 6976', '物理层', '开发没过'),
    ('53–54', 'HN-SPF 链路代价限变', 'Khanna–Zinky 1989', '拓扑层', '开发没过'),
    ('55', 'CSPF 限绕路', 'RFC 3209', '拓扑层', '开发没过'),
    ('56–57', 'BGP 路由阻尼', 'RFC 2439', '拓扑层', '过开发没确认'),
    ('58', 'IP 快速重路由', 'RFC 5286', '路由器层', '先量跳过'),
    ('58', 'MPLS-TE 自动带宽（门口）', 'RFC 3209', '路由器层', '先量跳过'),
    ('59', 'BFD / make-before-break 等三项', 'RFC 5880 等', '路由器层', '先量跳过'),
    ('60', '少过几扇门', 'IS-IS 权重', '拓扑层', '先量跳过'),
    ('60', 'SWAN 清道夫流', 'SIGCOMM 2013', '拓扑层', '先量跳过'),
    ('60–61', 'SWAN 留余量（名额 ×0.9）', 'SIGCOMM 2013', '拓扑层', '过开发没确认'),
    ('62–63', '按实测收名额', 'MPLS-TE auto-bw + SWAN', '拓扑层', '过开发没确认'),
    ('64', '虚拟直通（门格）', 'Kermani–Kleinrock 1979', '物理层', '先量跳过'),
    ('64', 'BGP 抖动抑制认图', 'RFC 2439', '拓扑层', '先量跳过'),
    ('65', 'MPLS-TE 优先级抢占', 'RFC 3209', '路由器层', '先量跳过'),
    ('65', 'IS-IS 过载位', 'RFC 6987', '拓扑层', '先量跳过'),
    ('66', 'RSVP-TE 软抢占', 'RFC 5712', '路由器层', '先量跳过'),
    ('66', 'PCE 主动下发', 'RFC 8231 / 8281', '路由器层', '先量跳过'),
    ('67–69', '自动带宽调割名额', 'RFC 3209 / 8231', '拓扑层', '过开发没确认'),
    ('70–71', 'RSVP-TE 逐跳接纳（所有门）', 'RFC 3209 / 5712', '路由器层', '先量跳过'),
]

LAYERS = ['拓扑层', '路由器层', '物理层']
OUTS = ['确认通过', '过开发没确认', '开发没过', '先量跳过']
COL = {'确认通过': '#2e7d32', '过开发没确认': '#f9a825', '开发没过': '#c62828', '先量跳过': '#90a4ae'}

cnt = {L: Counter(i[4] for i in ITEMS if i[3] == L) for L in LAYERS}
tot = Counter(i[4] for i in ITEMS)
out = {'总机制数': len(ITEMS), '按结局': dict(tot),
       '按层': {L: dict(cnt[L]) for L in LAYERS},
       '机制': [dict(zip(['轮次', '机制', '出处', '层', '结局'], i)) for i in ITEMS]}
(HERE / 'inventory_p72.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(len(ITEMS), dict(tot))
for L in LAYERS:
    print(L, dict(cnt[L]))

# 图 1（讲机制）：三层模型 × 每层试过的机制数，以及账本里对应的损失块
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.set_xlim(0, 10); ax.set_ylim(0, 6.2); ax.axis('off')
rows = [
    ('拓扑层', '门簇=路由器，房间里的路段=线，任务=多跳流', '没任务 30.9%（全局名额 19.5% + 割名额 11.5%）\n载货前进 20.7%（有用功）', '选路、名额、派车\nSPF / HN-SPF / CSPF / SWAN / auto-bw'),
    ('路由器层', '一扇门或门簇 + 两侧 2–3 步=交换机', '门口区等 7.3%、门格里等 0.7%\n别处等 9.5%', '换向、优先、接纳\nNAV / EF / VOQ / RSVP-TE / 软抢占'),
    ('物理层', '格子、前进、转身、故障', '故障 21.1%（题目给定）\n转身 7.1%、空车前进 2.6%', '流控、直通、防死锁\nPFC 看门狗 / 虫孔 / Duato'),
]
for k, (L, d, loss, mech) in enumerate(rows):
    y = 4.4 - k * 1.95
    ax.add_patch(plt.Rectangle((0.1, y), 2.1, 1.5, color=['#bbdefb', '#c8e6c9', '#ffe0b2'][k]))
    ax.text(1.15, y + 1.0, L, ha='center', va='center', fontsize=14, weight='bold')
    ax.text(1.15, y + 0.45, f'试过 {sum(cnt[L].values())} 项', ha='center', va='center', fontsize=10)
    ax.text(2.4, y + 1.2, d, fontsize=9.5, va='center', color='#333')
    ax.text(2.4, y + 0.5, loss, fontsize=9.5, va='center')
    ax.text(6.6, y + 0.75, mech, fontsize=9.5, va='center', color='#1a237e')
ax.text(2.4, 6.05, '这一层是什么 / 账本里归它的损失（车·拍，17 图平均）', fontsize=10, weight='bold')
ax.text(6.6, 6.05, '对应的网络机制（试过的）', fontsize=10, weight='bold')
fig.tight_layout()
fig.savefig(FIG / 'p72_mech.png', dpi=150)

# 图 2（讲结果）：每层各种结局的机制数
fig, ax = plt.subplots(figsize=(8.5, 4.2))
left = [0] * len(LAYERS)
for o in OUTS:
    v = [cnt[L].get(o, 0) for L in LAYERS]
    ax.barh(LAYERS, v, left=left, color=COL[o], label=f'{o}（{tot.get(o, 0)}）')
    for i, x in enumerate(v):
        if x:
            ax.text(left[i] + x / 2, i, str(x), ha='center', va='center', color='white' if o != '先量跳过' else 'black', fontsize=10)
    left = [a + b for a, b in zip(left, v)]
ax.invert_yaxis()
ax.set_xlabel('机制个数')
ax.set_title(f'协议方向第 1–71 轮：{len(ITEMS)} 项机制的结局')
ax.legend(loc='lower right', fontsize=9)
fig.tight_layout()
fig.savefig(FIG / 'p72_result.png', dpi=150)
