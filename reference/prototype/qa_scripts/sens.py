import json,re,datetime,random,collections as C
e=json.load(open('/home/claude/newsviz/data/events.json')); s={x['id']:x for x in json.load(open('/home/claude/newsviz/data/stories.json'))}
D=lambda d: datetime.date.fromisoformat(d)
ent_freq=C.Counter(en for x in e for en in set(x['key_entities']))
STOP=set('the and for with from that this into its new raises raised says said will after over more than about their are has have been ai startup startups funding round series seed million billion based company tech data platform build model models agents launch launches europe european'.split())
def toks(x):
  t=set()
  for sid in x['story_ids']: t|=set(re.findall(r'[a-z][a-z0-9]{3,}',s[sid]['headline'].lower()))
  return t-STOP
single=[x for x in e if x['n_source_families']==1]
cands=[]
for x in single:
  tx=toks(x); best=None
  for y in e:
    if y is x: continue
    if set(y['source_families'])==set(x['source_families']) : continue
    if abs((D(x['first_seen'])-D(y['first_seen'])).days)>4: continue
    rare=[en for en in set(x['key_entities'])&set(y['key_entities']) if ent_freq[en]<=6]
    ov=len(tx&toks(y))
    if rare or ov>=3:
      sc=len(rare)*3+ov
      if not best or sc>best[0]: best=(sc,y,rare,tx&toks(y))
  if best: cands.append((x,best))
print('single',len(single),'with candidate match',len(cands))
random.seed(1); samp=random.sample(cands,40)
for x,(sc,y,rare,ov) in samp:
  hx=s[x['story_ids'][0]]['headline'][:90]; hy=s[y['story_ids'][0]]['headline'][:90]
  print(f"{x['event_id']}[{x['source_families'][0][:10]}] {hx}\n   ~ {y['event_id']}[{','.join(f[:8] for f in y['source_families'])}] {hy}  rare={rare} ov={sorted(ov)[:5]}")
json.dump([(x['event_id'],b[1]['event_id']) for x,b in cands],open('/tmp/qa/cands.json','w'))
