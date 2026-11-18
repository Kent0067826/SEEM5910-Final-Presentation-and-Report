# 第 73 轮：抽看 room250 几段“别处、四邻空、有任务、站满 300 拍”的站立段（诊断用）
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'rounds' / 'p27')); sys.path.insert(0, str(R / 'rounds' / 'p35')); sys.path.insert(0, str(R / 'rounds' / 'p39'))
import ipfix_account as A
from diag_collapse import sim
from measure_idle_block import task_series
inst = sys.argv[2]; f = Path(sys.argv[1]) / f'{inst}_LCAPWD_9700_103.json'
h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
o = json.loads(f.read_text()); N = len(o['start']); T = o['makespan']
tasks = {t[0]: t for t in o['tasks']}
PP = [sim(o, i)[0] for i in range(N)]
shown = 0
for i in range(N):
    P = PP[i]; S = task_series(o['actualSchedule'][i], T); s = 0
    for t in range(1, T):
        if P[t] != P[t-1]:
            if t - s >= 300 and S[s] >= 0 and P[s] not in dlab and P[s] not in apron:
                v = P[s]; occ = {PP[j][s + 150] for j in range(N) if j != i}
                a, b = v; nb = [u for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if F(*u)]
                if not any(u in occ for u in nb):
                    tk = tasks[S[s]]; locs = tk[2]
                    print('robot', i, 'cell', v, 'ticks', s, t, 'task', S[s], 'locs', locs, 'w', w, 'cells', [(x // w, x % w) for x in locs] if all(isinstance(x, int) for x in locs) else '',
                          'plannerAct', o['actualPaths'][i][s // 3:s // 3 + 12] if isinstance(o['actualPaths'][i], str) else '')
                    shown += 1
            s = t
        if shown >= 6: break
    if shown >= 6: break
