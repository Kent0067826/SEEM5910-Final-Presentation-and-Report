import sys, json, os; sys.path.insert(0, '.')
import run as R
from concurrent.futures import ThreadPoolExecutor
def go(a):
    m, s, p = a; log = f'/home/user/simbuild/run/wd_{m}_{s}_{p}.json'
    r = R.run(dict(map=m, method='FULL', seed=s, pseed=p, env={'ROBOT_PFC_WD_LOG': log}))
    return m, s, p, r.get('completed'), open(log).read().strip()
jobs = [(m, s, 171) for m in ['room200', 'room250', 'room300'] for s in (11900, 11901)]
with ThreadPoolExecutor(4) as ex:
    for x in ex.map(go, jobs): print(x)
