import json,re,statistics as st
f=json.load(open('/home/claude/newsviz/data/funding_rounds.json'))
names=['upwind','foundry','braid','ravical','pixel systems','ares intelligence','hypersonica','pliant','kabilio','planky','athlete to athlete','harbinger','humble robotics','sumary','hiverge','ancep','path robotics','graphon','tendrils','numina','mirendil','mosaico','kindo','stark future','valeria','disseqt','aevius','treat','alecto','perry ai','previsia','elysian','agon','sennder','muray']
fix_geo={'hypersonica':'EU','hiverge':'EU'}
def reg(x):
  g=x['geography']; return 'EU' if g in('Europe','France') else g
groups={};rest=[]
for x in f:
  h=x['headline'].lower(); k=None
  for n in names:
    if re.search(r'\b'+re.escape(n)+r'\b',h): k=n;break
  if k and not (k=='treat' and 'treat' not in h[:30]): groups.setdefault(k,[]).append(x)
  else: rest.append(dict(x,reg=reg(x)))
ded=list(rest)
for k,rows in groups.items():
  regs=[reg(r) for r in rows if reg(r)!='Unknown']
  r=dict(rows[0]); r['reg']=fix_geo.get(k, regs[0] if regs else 'Unknown')
  r['amount_usd']=max((x['amount_usd'] or 0) for x in rows) or None
  ded.append(r)
print('groups',{k:len(v) for k,v in groups.items() if len(v)>1})
# variant: also remove Kalshi $5B (run-rate), debt/credit facilities
def clean(L):
  out=[]
  for x in L:
    h=x['headline'].lower()
    if 'kalshi' in h: x=dict(x,amount_usd=None)
    if re.search(r'debt|credit facility',h): continue
    out.append(x)
  return out
def stats(name,data):
  n=len(data); eu=[x for x in data if x['reg']=='EU']; us=[x for x in data if x['reg']=='US']
  sa=lambda L: sum(x['amount_usd'] or 0 for x in L); tot=sa(data)
  am=lambda L:[x['amount_usd'] for x in L if x['amount_usd']]
  print(name,'n',n,'eu',len(eu),'us',len(us),'eu%',round(len(eu)/n*100,1),'eu$',round(sa(eu)/1e9,2),'us$',round(sa(us)/1e9,2),'tot',round(tot/1e9,2),'eu$%',round(sa(eu)/tot*100,1),'us$%',round(sa(us)/tot*100,1),'med',round(st.median(am(eu))/1e6,1),round(st.median(am(us))/1e6,1),'u20',round(100*sum(a<20e6 for a in am(eu))/len(am(eu)),1),round(100*sum(a<20e6 for a in am(us))/len(am(us)),1),'us>=1B',sum(a>=1e9 for a in am(us)))
stats('orig',[dict(x,reg=reg(x)) for x in f]); stats('dedup',ded); stats('dedup+clean',clean(ded))
stats('dedup+clean closed only',[x for x in clean(ded) if x['deal_status']=='closed/announced'])
