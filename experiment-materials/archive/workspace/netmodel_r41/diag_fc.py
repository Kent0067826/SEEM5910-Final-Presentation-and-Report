import sys, json
sys.path.insert(0, '/home/claude/proj/v10/scripts'); from r41_common import *
jobs = []
for k in ['roomFC_194', 'roomFB_246']:
    for m, e in [('C24CF', C24CF), ('NETcap', NETCAP), ('C24sig', dict(C24CF, ROBOT_CUT2_SIGFIX='1'))]:
        for s in range(9700, 9705):
            jobs.append(dict(map=k, method=m, seed=s, pseed=101, env=e, mapfile=INST[k][0], team=INST[k][1], program=BIN41, ticks=5000))
run_batch(jobs, '/home/claude/r40/dev/diag_fc.jsonl', workers=2)
