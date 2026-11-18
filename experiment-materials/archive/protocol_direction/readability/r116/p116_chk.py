import json,statistics as st
d=json.load(open('p116_rho.json',encoding='utf-8'))
du={o['k']:o for o in json.load(open('p116_dual73.json',encoding='utf-8'))}
print(len(du),[k for k,o in du.items() if 'cut' not in o])
bad=[(k,o['ncomp'],o['prices'],o['lam'],o['Cf']) for k,o in du.items() if 'cut' in o and (len(o['prices'])!=1 or abs(o['Cf']-o['lam'])>1e-6)]
print('not single',bad)
print('cert',max(abs(o['cert']-1) for o in du.values() if 'cert' in o))
far=[o['dist'] for o in d if o['cls']=='一格门对太远']; print(min(far),max(far),sorted(far)[:5])
print('none',[o['k'] for o in d if o['prog_best'] is None])
print('widths3',[(o['k'],len(o['cut'])) for o in d if o['cls']=='三道以上'])
import collections
print(collections.Counter(len(o['cut']) for o in d))
