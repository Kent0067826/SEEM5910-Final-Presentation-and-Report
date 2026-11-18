import sys; sys.path.insert(0, '/home/user/simbuild/run')
from run import batch
Q = {'ROBOT_BRIDGE_CREDIT': None, 'ROBOT_CUT2_CREDIT': None}                       # 每门名额（带宽×时延）
D = {'ROBOT_BMAC': None, 'ROBOT_LMAC': None}                                        # 门口半双工成批放行
G = {'ROBOT_ACTIVE_CAP': None}                                                     # 全图接单上限（最大流）
W = {'ROBOT_PFC_WD': None, 'ROBOT_PFC_WD_DRAIN': None}                             # PFC 看门狗
X = {'ROBOT_EXEC_SYNCFIX': None}                                                    # 执行器修复
NONE = {**Q, **D, **G, **W, 'ROBOT_NET': None}                                      # = 冠军派单 + 修好执行器
V = {'FULL': {}, 'noQuota': Q, 'noDoor': {**D, 'ROBOT_ACTIVE_CAP_GATE': '0'}, 'noGlobal': G, 'noWD': W, 'noSync': X, 'NONE': NONE,
     'onlyQuota': {**D, **G, **W}, 'onlyDoor': {**Q, **G, **W, 'ROBOT_NET': None}, 'onlyGlobal': {**Q, **D, **W, 'ROBOT_NET': None, 'ROBOT_ACTIVE_CAP_GATE': '0'}}
jobs = [dict(map=m, method=k, seed=s, pseed=p, env=e) for k, e in V.items() for m in ['room300', 'room250', 'room200']
        for s in range(11900, 11910) for p in (171, 172)]
batch(jobs, '/home/user/simbuild/run/ablation.jsonl', workers=4)
print('DONE')
