import json, sys, collections
from pathlib import Path
R = Path(sys.argv[1]); sys.path.insert(0, str(R/'rounds/p27'))
import ipfix_account as A
for cfgname, pj in [('lcap_env17_wd.json', 'rounds/p34/pick_doors.json'), ('lcap_env_p75confirm_wd.json', 'rounds/p75/pick_doors_p75.json')]:
    A.CFG = json.loads((A.H / cfgname).read_text(encoding='utf8')); A.CFG.pop('_COMMON_ENV', None)
    P = json.loads((R/pj).read_text(encoding='utf8'))['maps']
    for inst, r in P.items():
        h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
        size = collections.Counter(rlab.values())
        out = []
        for d in r['doors']:
            if not d['picked']: continue
            adj = set()
            for (a, b) in map(tuple, d['cells']):
                for u in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                    if u in rlab: adj.add(rlab[u])
            out.append(sorted(size[x] for x in adj))
        big = sorted(size.values(), reverse=True)
        print(inst, 'rooms', len(size), 'top sizes', big[:6], 'picked adj sizes', out[:8], '...' if len(out)>8 else '')
