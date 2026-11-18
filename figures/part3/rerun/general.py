"""Generalization test on random-door 4x4 room maps: does the max-flow global cap and the PFC watchdog help there?"""
import sys, json; sys.path.insert(0, '/home/user/simbuild/run')
import run as R
inst = json.load(open('/home/user/SEEM5910-Final-Presentation-and-Report/figures/part3/rerun/maps_gen4x4/instances.json'))
base_env = dict(R.CFG['room250']['env']); base_env.pop('ROBOT_ACTIVE_CAP')      # official-room settings of the full method
base_env['ROBOT_ADMIT_AUTO'] = '1'                                              # global cap computed by the program from each map
for k, v in inst.items(): R.CFG[k] = dict(env=base_env, mapfile=v['mapfile'], team=v['team'])
Q = {'ROBOT_BRIDGE_CREDIT': None, 'ROBOT_CUT2_CREDIT': None}
D = {'ROBOT_BMAC': None, 'ROBOT_LMAC': None}
G = {'ROBOT_ADMIT_AUTO': None, 'ROBOT_ACTIVE_CAP': None}
W = {'ROBOT_PFC_WD': None, 'ROBOT_PFC_WD_DRAIN': None}
V = {'FULL': {}, 'noGlobal': G, 'noWD': W, 'NONE': {**Q, **D, **G, **W, 'ROBOT_NET': None}}
jobs = [dict(map=m, method=k, seed=s, pseed=p, env=e) for k, e in V.items() for m in sorted(inst, key=lambda x: -inst[x]['team'])
        for s in range(11900, 11905) for p in (171, 172)]
R.batch(jobs, '/home/user/simbuild/run/general.jsonl', workers=4)
print('DONE')
