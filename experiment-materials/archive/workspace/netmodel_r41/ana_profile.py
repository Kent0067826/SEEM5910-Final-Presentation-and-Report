"""完成速度随时间的变化（每 500 拍完成几单），和网络模型的"稳态"预测 C_c / f_c 对照。"""
import json, gzip, sys, collections, statistics
sys.path.insert(0, '/home/claude/r40')
rows = [json.loads(l) for l in open('/home/claude/r40/batch/rows.jsonl')]
def profile(gz):
    o = json.load(gzip.open(gz)); nloc = {t[0]: len(t[2]) // 2 for t in o['tasks']}
    p = [0] * 10
    for t, a, tid, seq in o['events']:
        if seq == nloc.get(tid): p[min(9, t // 500)] += 1
    return p, o['numTaskFinished']
out = {}
for inst in ['room200', 'room250', 'room300', 'roomAD_189', 'roomBF_240', 'roomS_247', 'roomCD_194', 'room250_nd']:
    for m in ('C24CF', 'N2F'):
        ps = []
        for r in rows:
            if r['inst'] == inst and r['method'] == m:
                p, n = profile(f"/home/claude/r40/batch/replays/{inst}_{m}_{r['seed']}_{r['pseed']}.json.gz")
                assert abs(sum(p) - n) <= 2, (sum(p), n)
                ps.append(p)
        avg = [round(statistics.mean(x), 1) for x in zip(*ps)]
        out[f'{inst}|{m}'] = avg
        print(f'{inst:11s} {m:6s}', avg)
json.dump(out, open('/home/claude/r40/batch/profiles.json', 'w'), indent=1)
