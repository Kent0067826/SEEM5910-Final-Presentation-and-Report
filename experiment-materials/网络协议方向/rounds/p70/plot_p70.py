# 第 70 轮图：p70_mech.png（第 50–69 轮骨干网线一览）、p70_result.png（G-1 三步先量）
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']; plt.rcParams['axes.unicode_minus'] = False
OUT = '../../报告源/图/'
# 图 1：第 50–69 轮做过的骨干网机制，按层和结局
rows = [('拓扑层·按负载选路', 'ARPANET SPF / HN-SPF / CSPF', '开发掉分', '53–55'),
        ('路由层·振荡阻尼', 'BGP RFD（RFC 2439）', '过开发·没确认', '56–57'),
        ('路由器层·门口端口', 'FRR/LFA、BFD、MBB、抢占、软抢占、PCE 下发', '先量跳过', '58–59、64–66'),
        ('拓扑层·准入余量', 'SWAN 余量、自动带宽（开局收）', '过开发·没确认', '60–63'),
        ('拓扑层·割名额', 'MPLS-TE 自动带宽（RFC 3209 / 8231）', '过开发·没确认', '67–69'),
        ('物理层·转身/偏转', '少拐弯、BLESS、oFIB', '先量跳过 / 掉分', '50–52'),
        ('路由器层·所有门（新）', 'RSVP-TE 逐跳接纳 / 软抢占', '先量过线·待写协议', '70')]
col = {'开发掉分': '#d1495b', '过开发·没确认': '#edae49', '先量跳过': '#9aa5b1', '先量跳过 / 掉分': '#9aa5b1', '先量过线·待写协议': '#2e86ab'}
fig, ax = plt.subplots(figsize=(10, 4.6)); ax.axis('off')
for k, (lay, src, res, rd) in enumerate(rows):
    y = len(rows) - k
    ax.text(0.0, y, lay, fontsize=11, va='center', fontweight='bold')
    ax.text(0.27, y, src, fontsize=10, va='center')
    ax.add_patch(plt.Rectangle((0.66, y - 0.35), 0.22, 0.7, color=col[res], transform=ax.transData))
    ax.text(0.77, y, res, fontsize=10, va='center', ha='center', color='white', fontweight='bold')
    ax.text(0.90, y, '第 ' + rd + ' 轮', fontsize=10, va='center')
ax.set_xlim(0, 1.02); ax.set_ylim(0.3, len(rows) + 1)
for x, t in ((0.0, '层·损失块'), (0.27, '骨干网出处'), (0.71, '结局'), (0.90, '轮次')):
    ax.text(x, len(rows) + 0.75, t, fontsize=11, color='#555')
ax.set_title('第 50–69 轮骨干网机制一览：门口端口只量过“最忙那扇门”', fontsize=13)
plt.tight_layout(); plt.savefig(OUT + 'p70_mech.png', dpi=150); plt.close()
# 图 2：G-1 三步
d = json.load(open('g1b_measure.json', encoding='utf8'))
m = d['mean_17']
labs = ['门口区等\n（账本）', '第一步\n别的门', '第二步\n门格空着', '第三步\n要过这扇门', '其中被\n前车挡着', '没被挡']
vals = [7.32, 100 * m['other'], 100 * m['other_empty'], 100 * m['other_intend'], 100 * m['other_intend_blocked'], 100 * (m['other_intend'] - m['other_intend_blocked'])]
ref = [None, 100 * m['busiest'], 100 * m['busiest_empty'], 100 * m['busiest_intend'], 100 * m['busiest_intend_blocked'], 100 * (m['busiest_intend'] - m['busiest_intend_blocked'])]
fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1.1, 1.3]))
ax = axs[0]; x = range(len(labs))
ax.bar([i - 0.2 for i in x], vals, 0.4, color=['#bbb', '#2e86ab', '#2e86ab', '#2e86ab', '#edae49', '#3c9d5d'], label='最忙门以外的门')
ax.bar([i + 0.2 for i in x[1:]], ref[1:], 0.4, color='#d1495b', alpha=0.7, label='最忙那扇门（参照）')
for i, v in enumerate(vals): ax.text(i - 0.2, v + 0.12, f'{v:.2f}', ha='center', fontsize=9)
ax.axhline(2.0, ls='--', color='k'); ax.text(5.4, 2.1, '跳过线 2%', ha='right', fontsize=9)
ax.set_xticks(list(x)); ax.set_xticklabels(labs, fontsize=9); ax.set_ylabel('占全部车·拍（17 图平均，%）')
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color='#2e86ab', label='最忙门以外的门'), Patch(color='#d1495b', alpha=0.7, label='最忙那扇门（参照）')], fontsize=9, loc='upper right')
ax.set_title('一层层拆：别的门门口等 6.19% → 要过且门空 2.40%', fontsize=11)
ax = axs[1]; per = sorted(d['per_inst'], key=lambda r: -r['other_intend'])
names = [r['inst'] for r in per]
a = [100 * (r['other_intend'] - r['other_intend_blocked']) for r in per]; b = [100 * r['other_intend_blocked'] for r in per]
ax.barh(names, a, color='#3c9d5d', label='没被挡（门口规则能管的上限）'); ax.barh(names, b, left=a, color='#edae49', label='被前车挡着（排队）')
ax.axvline(2.0, ls='--', color='k'); ax.invert_yaxis(); ax.tick_params(axis='y', labelsize=8); ax.legend(fontsize=8, loc='lower right')
ax.set_xlabel('第三步：门格空着、车要过这扇门却在门口等（% 车·拍）'); ax.set_title('每张图（多门图最高）', fontsize=11)
plt.tight_layout(); plt.savefig(OUT + 'p70_result.png', dpi=150); plt.close()
