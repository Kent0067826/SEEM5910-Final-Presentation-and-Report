import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts'); from r39_common import *
Z = json.load(open(V + 'test_freeze_v29.json')); B = V + Z['binary']; base = Z['methods']['C24CF']
jobs = []
for k in ['room250', 'roomCD_194', 'roomBF_240', 'roomAD_189']:
    for cap in ['0.25', '0.4', '0.6', '0.8', 'off']:
        env = dict(base); 
        if cap == 'off': env.pop('ROBOT_ACTIVE_CAP', None)
        else: env['ROBOT_ACTIVE_CAP'] = cap; env['ROBOT_ACTIVE_CAP_GATE'] = '0'
        for s in range(9700, 9705):
            jobs.append(dict(map=k, method='cap' + cap, seed=s, pseed=101, env=env, mapfile=INST[k][0], team=INST[k][1], program=B, ticks=5000))
run_batch(jobs, '/home/claude/r40/dev/cap.jsonl', workers=2)
