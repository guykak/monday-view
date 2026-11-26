"""Data for the W47 visual. Facts are transcribed from weekly/w47_sample.md (each checked to appear verbatim there);
counts are recomputed from weekly/w47_rounds.json and weekly/w47_family_counts.json."""
import json, re
W='/home/claude/newsviz/weekly/'
MD=open(W+'w47_sample.md').read()
def need(*snips):
    for s in snips: assert s in MD, s
# ---- block 2 counts, recomputed
R=json.load(open(W+'w47_rounds.json'))
early=[r for r in R if r['week']=='W47' and r['early']]
# remove Stryx double count (Maddyness French line e1783 = Stryx AI e0136; stat_tests revision: stryx_duplicate_removed)
early=[r for r in early if r['event_id']!='e1783']
for r in early:
    if r['event_id']=='e1638': r['amount_usd']=28e6   # Hone Health: $28M Series A equity (+$200M growth financing, not equity)
TS='Fortune Term Sheet'
n=len(early); eu=[r for r in early if r['reg']=='EU']; row=[r for r in early if r['reg']!='EU']
ts_any=sum(TS in r['families'] for r in early); ts_only=sum(r['families']==[TS] for r in early)
big_eu=[r for r in eu if (r['amount_usd'] or 0)>=50e6]; big_row=[r for r in row if (r['amount_usd'] or 0)>=50e6]
assert (n,len(eu),ts_any,n-ts_only)==(55,28,30,35), (n,len(eu),ts_any,n-ts_only)
need('55 rounds reported, 28 in Europe','Term Sheet carried 30 of the 55; the total is 35 without it')
AREAS=[('AI applications and agents',10),('AI infrastructure (compilers, edge, model training)',3),('Other software and consumer',3),('Robotics and manufacturing',2),('Defence and aerospace',2),('Health',2),('Space',1),('Fintech',1)]
for a,c in AREAS: need(f'| {a} | {c} |')
assert sum(c for _,c in AREAS)==len(eu)-len(big_eu)==24
early_out=dict(n=n,eu=len(eu),row=len(row),ts_any=ts_any,ts_only=ts_only,ts_plus=ts_any-ts_only,no_ts=n-ts_any,without_ts=n-ts_only,
  big_eu=sorted([r['headline'].split(' raises')[0] for r in big_eu]),big_row=len(big_row),areas=AREAS)
# ---- family counts (dots) from w47_family_counts.json
FC=json.load(open(W+'w47_family_counts.json')); fam=lambda k: len(FC[k])
DEEP=[ # name, city, amount, stage, lead, line, family key   (all strings verbatim in sample)
 ('Daisytuner','Darmstadt','€6m','seed','Elaia and LEA Ventures','Open-source compiler that runs AI code natively on Nvidia, AMD and newer accelerators.','Daisytuner'),
 ('MountAIn','Grenoble','€7.3m','seed','360 Capital','Runs AI applications on low-cost, low-power chips.','MountAIn'),
 ('Vetaion','Munich','€5.7m','pre-seed','Visionaries Tomorrow and UVC','Robotic manufacturing of electrical control cabinets.','Vetaion'),
 ('Mosaico','','€7.5m','','','Data for robotics AI.','Mosaico'),
 ('Stryx AI','Paris','€7.7m','seed','Armand Thiberge (Brevo founder) and Impala','Radar and interceptors against drones.','Stryx AI'),
 ('Elysian Aircraft','NL','€12m+','in grants and equity','','Battery-electric aircraft.','Elysian Aircraft'),
 ('Dcubed','Munich','€27.2m','Series A','Warsaw Equity Group','Satellite deployment and power systems.','Dcubed')]
for d in DEEP:
    need(d[0],d[2],d[5]); [need(x) for x in d[1:5] if x]
deep=[dict(name=a,city=b,amt=c,stage=d,lead=e,line=f,dots=fam(k)) for a,b,c,d,e,f,k in DEEP]
md_dots={'Daisytuner':3,'MountAIn':3,'Vetaion':2,'Mosaico':2,'Stryx AI':2,'Elysian Aircraft':3,'Dcubed':1}
assert all(d['dots']==md_dots[d['name']] for d in deep)
need('**Remanence** (Paris), $30m seed, EQT Ventures and FirstMark. Founded by H Company alumni, including its ex-CTO. ●●●●●')
reman=dict(name='Remanence',city='Paris',amt='$30m',stage='seed',lead='EQT Ventures and FirstMark',line='Founded by H Company alumni, including its ex-CTO.',dots=fam('Remanence $30M seed'))
# ---- block 3 (USD for positioning; EUR converted at the pipeline's EUR×1.08)
BIG=[('Isomorphic Labs','London, Alphabet','$5B Series C',5e9,None,'','Isomorphic Labs $5B'),
 ('Genesis AI','Paris / San Carlos','$500M Series A',5e8,3.5e9,'$3.5B','Genesis AI $500M A'),
 ('Payhawk','London','$280M Series C',2.8e8,None,'','Payhawk $280M'),
 ('Model ML','London','$250M Series B',2.5e8,1.5e9,'$1.5B','Model ML $250M'),
 ('Boltz','London','$110M Series A',1.1e8,None,'','Boltz $110M A'),
 ('Tiberius Aerospace','London / Newport Beach','$85M Series A',8.5e7,1e9,'$1B+','Tiberius $85M A'),
 ('Commit Biologics','Copenhagen','€54m seed',54e6*1.08,None,'','Commit Biologics')]
for a,b,c,*_ in BIG: need(a,b,c.replace('€54m seed','€54m seed'))
need('14 rounds of $100M or more were reported, equity only','Sierra ~$1.5B at ~$30B','Cognition $2B+ at $75B')
big=[dict(name=a,where=b,label=c,usd=d,val=e,vlab=f,dots=fam(g)) for a,b,c,d,e,f,g in BIG]
talks=[dict(name='Sierra',label='~$1.5B',usd=1.5e9,val=30e9,vlab='~$30B'),dict(name='Cognition',label='$2B+',usd=2e9,val=75e9,vlab='$75B')]
# ---- block 1
need('priced at $83 a share','$81.3bn','opened at $111.50 (+34%), closed at $97.17 (+17%)','$1.3T','$93.5bn','SoftBank about −15%, TSMC −5%+, Samsung and SK Hynix −6%+','(10 families)')
ipo=dict(price=83,open=111.50,close=97.17,raised='$81.3bn',cap='$1.3T',total='$93.5bn',fams=fam('Anthropic IPO priced/listed'),
  open_pct=round(100*(111.50/83-1)),close_pct=round(100*(97.17/83-1)),
  selloff=[('SoftBank',15,'about −15%'),('Samsung',6,'−6%+'),('SK Hynix',6,'−6%+'),('TSMC',5,'−5%+')])
assert ipo['fams']==10 and ipo['open_pct']==34 and ipo['close_pct']==17
# ---- block 4
need('Applied Compute','$4.5B in stock','valued at $3.25B earlier in November','Bending Spoons → Mailchimp:** $3.68B','Intuit paid ~$12B in 2021')
exits=[dict(acq='Palo Alto Networks',tgt='Applied Compute',what='customises open-weight models',before=3.25e9,blab='$3.25B mark, earlier in Nov',after=4.5e9,alab='$4.5B in stock',dots=fam('Applied Compute (PANW)')),
       dict(acq='Bending Spoons',tgt='Mailchimp',what='',before=12e9,blab='~$12B paid by Intuit, 2021',after=3.68e9,alab='$3.68B',dots=fam('Mailchimp (Bending Spoons)'))]
assert exits[1]['dots']==3 and fam('Plural EUR1bn')==4
for e in exits: e['chg']=round(100*(e['after']/e['before']-1))
need('Nvidia in advanced talks for Inception (diffusion LLMs), $500M+ (Techmeme)','MongoDB buys Firebolt (TLDR)','Iceye bids €2.05B cash for Avio (Sunday CET)','CrowdStrike in talks for Zscaler (Techmeme)')
single=[('Nvidia','Inception (diffusion LLMs)','advanced talks, $500M+','Techmeme','Inception (Nvidia)'),('MongoDB','Firebolt','buys','TLDR','Firebolt (MongoDB)'),
        ('Iceye','Avio','€2.05B cash bid','Sunday CET','Avio (Iceye)'),('CrowdStrike','Zscaler','in talks','Techmeme','Zscaler (CrowdStrike)')]
assert all(fam(k)==1 for *_,k in single)
need('Plural closes €1bn for European early stage, 30+ companies. ●●●●','Sofinnova Crossover II €725m (late-stage life sciences) ●●','Norwest fund 18, $4B (US venture and growth) ●')
funds=[dict(name='Plural',lab='€1bn',usd=1e9*1.08,note='European early stage, 30+ companies',dots=fam('Plural EUR1bn')),
       dict(name='Sofinnova Crossover II',lab='€725m',usd=725e6*1.08,note='late-stage life sciences',dots=2),
       dict(name='Norwest fund 18',lab='$4B',usd=4e9,note='US venture and growth',dots=1)]
# ---- block 5 & footer
need("API tokens 20% cheaper than GPT-6 Astra, at $8 / $40 per million input/output tokens","under one-third of GPT-6 Astra's cost per task on its own evals","Gemini 4 Neon: $3 / $15 per million input/output tokens",
     "TLDR 12, Sifted 9, AlphaSignal 6, Techmeme 6, Term Sheet 5, Maddyness 5, Newcomer 4; others 1 each")
sources=[('TLDR',12),('Sifted',9),('AlphaSignal',6),('Techmeme',6),('Term Sheet',5),('Maddyness',5),('Newcomer',4)]
# issue counts recomputed from raw file names dated 16-22 Nov
import glob,os,collections
_c=collections.Counter()
for f in glob.glob('/home/claude/newsviz/raw/msgs/*.txt'):
    b=os.path.basename(f)
    if '2026-11-16'<=b[:10]<='2026-11-22':
        n=b[11:].lower(); _c['TLDR' if 'tldr' in n else 'Sifted' if 'sifted' in n else 'AlphaSignal' if 'alphasignal' in n else 'Techmeme' if 'techmeme' in n else 'Term Sheet' if 'term-sheet' in n else 'Maddyness' if n.startswith('maddyness') else 'Newcomer' if 'newcomer' in n else n]+=1
assert all(_c[k]==v for k,v in sources), {k:_c[k] for k,_ in sources}
D=dict(early=early_out,deep=deep,reman=reman,big=big,talks=talks,ipo=ipo,exits=exits,single=[dict(acq=a,tgt=b,what=c,src=d) for a,b,c,d,_ in single],funds=funds,sources=sources)
json.dump(D,open(W+'build/data.json','w'),ensure_ascii=False)
print(json.dumps(early_out)); print([ (e['tgt'],e['chg']) for e in exits])
