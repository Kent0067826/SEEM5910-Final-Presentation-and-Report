import json,sys,collections
base=sys.argv[1]; news=sys.argv[2].split(',')
B={(d['map'],d['seed'],d['pseed']):d['completed'] for d in map(json.loads,open(base,encoding='utf8'))}
N={};err=0
for f in news:
  for d in map(json.loads,open(f,encoding='utf8')): N[(d['map'],d['seed'],d['pseed'])]=d['completed']; err+=d['errors']+d['plannerErrors']
per=collections.defaultdict(lambda:[0,0])
for k,v in N.items():
  per[k[0]][0]+=B[k]; per[k[0]][1]+=v
r={m:100*(n/b-1) for m,(b,n) in per.items()}
for m in sorted(r): print(f"{m:12s} {per[m][0]:6d} {per[m][1]:6d} {r[m]:+6.2f}%")
print(f"runs {len(N)} mean {sum(r.values())/len(r):+.3f}% worst {min(r.values()):+.2f}% errors {err}")
