import json,re,itertools,datetime,statistics as st
f=json.load(open('/home/claude/newsviz/data/funding_rounds.json'))
STOP={'raises','raised','series','round','startup','million','funding','based','led','seed','with','software','data','group','agents','powered','infrastructure','deeptech','analytics','tools','security','cloud','management','agent','accounting','payments','berlin','british','german','toulouse','insurtech','dutch','aerospace','aircraft','robotics','blue'}
def words(h): return set(re.findall(r'[a-z]{4,}',h.lower()))-STOP
par=list(range(len(f)))
def find(i):
  while par[i]!=i: par[i]=par[par[i]]; i=par[i]
  return i
pairs=[]
for i,j in itertools.combinations(range(len(f)),2):
  a,b=f[i],f[j]
  if not a['amount_usd'] or not b['amount_usd']: continue
  if abs(a['amount_usd']-b['amount_usd'])>0.1*max(a['amount_usd'],b['amount_usd']): continue
  if abs((datetime.date.fromisoformat(a['date'])-datetime.date.fromisoformat(b['date'])).days)>10: continue
  w=words(a['headline'])&words(b['headline'])
  if w: pairs.append((i,j,w)); par[find(i)]=find(j)
groups={}
for i in range(len(f)): groups.setdefault(find(i),[]).append(i)
multi=[g for g in groups.values() if len(g)>1]
print('pairs',len(pairs),'groups with dups',len(multi),'extra rows',sum(len(g)-1 for g in multi))
for g in multi: print([ (f[i]['geography'],f[i]['headline'][:45]) for i in g])
def reg(x):
  g=x['geography']; return 'EU' if g in('Europe','France') else g
# dedup: keep one per group, geography: prefer Europe/US known over Unknown
ded=[]
for g in groups.values():
  rows=[f[i] for i in g]
  geos=[reg(r) for r in rows if reg(r) not in('Unknown',)]
  geo=geos[0] if geos else 'Unknown'
  r=dict(rows[0]); r['reg']=geo; r['amount_usd']=max((x['amount_usd'] or 0) for x in rows) or None
  ded.append(r)
json.dump(ded,open('/tmp/qa/ded.json','w'))
for name,data in [('orig',[dict(x,reg=reg(x)) for x in f]),('dedup',ded)]:
  n=len(data); eu=[x for x in data if x['reg']=='EU']; us=[x for x in data if x['reg']=='US']
  tot=sum(x['amount_usd'] or 0 for x in data)
  sa=lambda L: sum(x['amount_usd'] or 0 for x in L)
  med=lambda L: st.median([x['amount_usd'] for x in L if x['amount_usd']])/1e6
  u20=lambda L: sum(1 for x in L if x['amount_usd'] and x['amount_usd']<20e6)/len([x for x in L if x['amount_usd']])
  print(name,n,len(eu),len(us),round(len(eu)/n*100,1),round(sa(eu)/1e9,2),round(sa(us)/1e9,2),round(tot/1e9,2),round(sa(eu)/tot*100,1),'med',med(eu),med(us),'u20',round(u20(eu)*100,1),round(u20(us)*100,1), 'eu>1B',sum(1 for x in eu if (x['amount_usd'] or 0)>1e9),'us>1B',sum(1 for x in us if (x['amount_usd'] or 0)>1e9))
