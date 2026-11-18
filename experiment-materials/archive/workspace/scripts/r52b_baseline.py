"""Supplementary comparison (protocol_r52b_baseline.md): official default vs champion scheduler vs fixed executor vs LCAP,
official 8 instances, fresh seeds 11700-11709 x 145, 146, 5000 ticks."""
import sys; sys.path.insert(0, '/home/claude/proj/v10/scripts'); from r51_common import *
OFF8 = ['room200', 'room250', 'room300', 'maze40', 'maze60', 'random200', 'random300', 'warehouse100']
M = {'DEF': lambda k: {}, 'N2': lambda k: {'ROBOT_SCHED': 'nms', 'ROBOT_NMS_W': '2'},
     'N2F': lambda k: {'ROBOT_SCHED': 'nms', 'ROBOT_NMS_W': '2', 'ROBOT_EXEC_SYNCFIX': '1'}, 'LCAP': lcap_env}
mk = lambda k, m, s, p: dict(map=k, method=m, seed=s, pseed=p, env=M[m](k), mapfile=INST[k][0], team=INST[k][1], program=BIN51, ticks=5000)
J = [mk(k, m, s, p) for s in range(11700, 11710) for p in (145, 146) for k in OFF8 for m in M]
if __name__ == '__main__':
    run_batch(J, V + 'batches/r52b-baseline/rows.jsonl', workers=2)
