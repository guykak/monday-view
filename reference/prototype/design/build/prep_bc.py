# exec'd from prep.py (shares its namespace: A, E, S, EV, ST, out, collections, statistics, json, dt)
import re, sys, subprocess
# ---------- A: reproduce the under-merge candidate count (reviewer's rule: other-family event within +/-4 days sharing a rare entity or >=3 headline tokens)
_ef=collections.Counter(en for x in E for en in set(x['key_entities']))
_STOP=set('the and for with from that this into its new raises raised says said will after over more than about their are has have been ai startup startups funding round series seed million billion based company tech data platform build model models agents launch launches europe european'.split())
_tok={x['event_id']:set(t for sid in x['story_ids'] for t in re.findall(r'[a-z][a-z0-9]{3,}',ST[sid]['headline'].lower()))-_STOP for x in E}
_D=dt.date.fromisoformat; _cands=0; _cand_single=0
for x in E:
    if x['n_source_families']!=1: continue
    best=None
    for y in E:
        if y is x or set(y['source_families'])==set(x['source_families']) or abs((_D(x['first_seen'])-_D(y['first_seen'])).days)>4: continue
        rare=[en for en in set(x['key_entities'])&set(y['key_entities']) if _ef[en]<=6]; ov=len(_tok[x['event_id']]&_tok[y['event_id']])
        if rare or ov>=3:
            sc=len(rare)*3+ov
            if not best or sc>best[0]: best=(sc,y)
    if best: _cands+=1; _cand_single+= best[1]['n_source_families']==1
assert _cands==213, _cands
def _adj(rate):
    m=_cands*rate; fs=_cand_single/_cands; mm=m*(1-fs); ms=m*fs/2
    return 100*(2121-mm-2*ms)/(2210-mm-ms)
out['A']['undermerge']=dict(cands=_cands,checked=40,true_lo=13,true_hi=14,adj_lo=round(_adj(14/40),1),adj_hi=round(_adj(13/40),1),
    naive_lo=round(100*(2121-2*_cands*14/40)/(2210-_cands*14/40),1),naive_hi=round(100*(2121-_cands*13/40)/(2210-_cands*13/40),1))

# ---------- B
subprocess.run([sys.executable,'/home/claude/newsviz/design/build/funding_clean.py'],check=True,capture_output=True)
FC=json.load(open('/home/claude/newsviz/design/build/funding_clean.json'))
CL=[r for r in FC if r['status']=='closed']
reg=lambda L,g:[r for r in L if r['reg']==g]
sa=lambda L: sum(r['amount_usd'] or 0 for r in L)
am=lambda L:[r['amount_usd'] for r in L if r['amount_usd']]
def bk(a): return '<$5M' if a<5e6 else '$5-20M' if a<20e6 else '$20-100M' if a<100e6 else '$100M-1B' if a<1e9 else '>=$1B'
stage={}
for stg in ('Seed','Series A'):
    e=[r['amount_usd'] for r in reg(CL,'EU') if r['stage']==stg and r['amount_usd']]; u=[r['amount_usd'] for r in reg(CL,'US') if r['stage']==stg and r['amount_usd']]
    stage[stg]=dict(EU=statistics.median(e),US=statistics.median(u),nEU=len(e),nUS=len(u))
stage['All stages']=dict(EU=statistics.median(am(reg(CL,'EU'))),US=statistics.median(am(reg(CL,'US'))),nEU=len(am(reg(CL,'EU'))),nUS=len(am(reg(CL,'US'))))
# located-only geography of stories, same rule both sides (re-run tagger without the source-name fallback)
sys.path.insert(0,'/home/claude/newsviz/scripts'); import tag
EUF=('Sifted','Maddyness','EU-Startups','Sunday CET (Dragos Novac)')
USF=('Techmeme','TLDR','Fortune Term Sheet','Newcomer','AlphaSignal','Not Boring','TechCrunch Mobility','Import AI','DeepLearning.AI The Batch')
loc={}
for side,fams in (('eu',EUF),('us',USF)):
    c=collections.Counter()
    for x in S:
        if x['source_family'] in fams:
            g=tag.geo_of(x['source_text'],x['source_text'],x['entities'],''); c['Europe' if g in ('Europe','France') else g]+=1
    known=sum(v for k,v in c.items() if k!='Unknown')
    loc[side]=dict(n=sum(c.values()),located=known,eu=c['Europe']/known,us=c['US']/known)
B=dict(rounds=[dict(g=r['reg'],a=r['amount_usd'],h=r['headline'][:80],d=r['date'],t=r['topic'],st=r['stage']) for r in CL if r['reg'] in ('EU','US') and r['amount_usd']],
  n={g:len(reg(CL,g)) for g in ('EU','US','ELSE','UNK')}|{'all':len(CL)},
  usd={g:sa(reg(CL,g)) for g in ('EU','US','ELSE','UNK')}|{'all':sa(CL)},
  med=dict(EU=stage['All stages']['EU'],US=stage['All stages']['US']),
  buckets={g:collections.Counter(bk(a) for a in am(reg(CL,g))) for g in ('EU','US')},
  nwa={g:len(am(reg(CL,g))) for g in ('EU','US')}, stage=stage, loc=loc,
  clean=dict(raw=len(json.load(open('/home/claude/newsviz/data/funding_rounds.json'))),deduped=len(FC),closed=len(CL),talks=len(FC)-len(CL),
             eu_only_from_eu_letters=None),
  big={g:sum(1 for a in am(reg(CL,g)) if a>=1e9) for g in ('EU','US')},
  gap=A['eu_vs_us_sources_topic_gap'], onlyEU=A['entities_only_in_european_sources'][:8], onlyUS=A['entities_only_in_us_sources'][:8])
B['under20']={g:round(100*(B['buckets'][g]['<$5M']+B['buckets'][g]['$5-20M'])/B['nwa'][g],1) for g in ('EU','US')}
out['B']=B

# ---------- C: subject lines on a constant panel of senders present in all 8 months
TH=json.load(open('/home/claude/newsviz/raw/threads.json'))
PROMO=re.compile(r'(confirm|welcome|subscription|discount|offer|tickets?|webinar|sign ?up|% off|black friday|special offer|access code|update your)', re.I)
TH=[t for t in TH if not PROMO.search(t['subject'])]
months=sorted({t['date'][:7] for t in TH})
pres=collections.defaultdict(set)
for t in TH: pres[t['sender']].add(t['date'][:7])
panel=sorted(x for x,m in pres.items() if len(m)==len(months))
P=[t for t in TH if t['sender'] in panel]
KW={'Anthropic/Claude': r'anthropic|claude|mythos', 'OpenAI/ChatGPT': r'openai|chatgpt|gpt', 'Nvidia': r'nvidia|jensen', 'Agents': r'agent',
    'IPO': r'\bipo\b', 'Robotics/humanoids': r'robot|humanoid', 'Data centers': r'data ?cent', 'Quantum': r'quantum|quantique', 'Defence': r'defen[cs]e|d[ée]fense', 'Space': r'space|spacex|starship|satellite'}
SAGA=re.compile(r'jensen|huang|oust|shake ?up|crises|whiplash|rene haas|next act', re.I)
ipm={m:sum(1 for t in P if t['date'][:7]==m) for m in months}
kw={k:[round(100*sum(1 for t in P if t['date'][:7]==m and re.search(v,t['subject'],re.I))/ipm[m],1) for m in months] for k,v in KW.items()}
nv_saga=[sum(1 for t in P if t['date'][:7]==m and t['date'][:10]>='2026-10-30' and re.search(KW['Nvidia'],t['subject'],re.I) and SAGA.search(t['subject'])) for m in months]
nv_all=[sum(1 for t in P if t['date'][:7]==m and re.search(KW['Nvidia'],t['subject'],re.I)) for m in months]
nv_ex=[round(100*(a-s)/ipm[m],1) for a,s,m in zip(nv_all,nv_saga,months)]
IPOX=re.compile(r'\bipo\b|nasdaq|s-1|roadshow|anthropic debuts', re.I)
an_rx=KW['Anthropic/Claude']
an_all=[sum(1 for t in P if t['date'][:7]==m and re.search(an_rx,t['subject'],re.I)) for m in months]
an_ipo=[sum(1 for t in P if t['date'][:7]==m and t['date'][:10]>='2026-10-29' and re.search(an_rx,t['subject'],re.I) and IPOX.search(t['subject'])) for m in months]
an_ex=[round(100*(a-s)/ipm[m],1) for a,s,m in zip(an_all,an_ipo,months)]
# topic change excluding the Huang-saga stories
_saga=set(i for e in ('e0012','e0004','e0009') for i in EV[e]['story_ids'])
_ss=[x for x in S if x['id'] not in _saga]; _pr=[x for x in _ss if x['date']<='2026-11-12']; _rc=[x for x in _ss if x['date']>='2026-11-13']
_cp=collections.Counter(x['topic'] for x in _pr); _cr=collections.Counter(x['topic'] for x in _rc)
topics_ex=sorted([dict(topic=t,prior_share=_cp[t]/len(_pr),recent_share=_cr[t]/len(_rc),change_pp=round(100*(_cr[t]/len(_rc)-_cp[t]/len(_pr)),2)) for t in set(_cp)|set(_cr)],key=lambda d:-d['change_pp'])
# fortnight names: per 100 stories, >=20 mentions, people/companies/investors only; Huang/Nvidia/Anthropic are Direction A's storylines
sys.path.insert(0,'/home/claude/newsviz/scripts'); from gazetteer import E as GZ
pr=[x for x in S if x['date']<='2026-11-12']; rc=[x for x in S if x['date']>='2026-11-13']
cp=collections.Counter(e for x in pr for e in set(x['entities'])); cr=collections.Counter(e for x in rc for e in set(x['entities']))
names=[]
for e in set(cp)|set(cr):
    if cp[e]+cr[e]<20 or GZ.get(e,('?',))[0] not in ('company','person','investor') or e in ('Jensen Huang','Nvidia','Anthropic'): continue
    names.append(dict(entity=e,prior=cp[e],recent=cr[e],ps=100*cp[e]/len(pr),rs=100*cr[e]/len(rc)))
names.sort(key=lambda d:-(d['rs']-d['ps']))
# noise band: one standard error of a share difference, for a topic at the largest pooled share
t0=A['rising_fading']; n1,n2=t0['periods']['n_prior'],t0['periods']['n_recent']
pmax=max((d['prior_share']*n1+d['recent_share']*n2)/(n1+n2) for d in t0['topics'])
se=100*(pmax*(1-pmax)*(1/n1+1/n2))**0.5
C=dict(months=months,kw=kw,ipm=ipm,panel=len(panel),nv_ex=nv_ex,nv_saga=nv_saga,nv_all=nv_all,an_ex=an_ex,an_ipo=an_ipo,an_all=an_all,topics_ex=topics_ex,saga_n=len(_saga),chips_all=next(d['change_pp'] for d in A['rising_fading']['topics'] if d['topic'].startswith('Chips')),
  rf=t0, names=names, se=round(se,2), nper=[len(pr),len(rc)],
  fp={f:dict(n=v['n_stories'],lift={t:p['lift'] for t,p in v['profile'].items()}) for f,v in A['source_fingerprint'].items()},
  topics=list(A['topic_share_overall'].keys()))
out['C']=C
json.dump(out,open('/home/claude/newsviz/design/build/data.json','w'),default=dict)
print('A undermerge',out['A']['undermerge'],'fractile',out['A']['fractile'])
print('B n',B['n'],'usd',{k:round(v/1e9,2) for k,v in B['usd'].items()},'med',B['med'],'u20',B['under20'],'big',B['big'],'stage',stage,'loc',loc,'clean',B['clean'])
print('B buckets',{g:dict(v) for g,v in B['buckets'].items()}, B['nwa'])
print('C panel',len(panel),ipm); [print(' ',k,v) for k,v in kw.items()]; print(' nv_ex',nv_ex,'saga',nv_saga,'all',nv_all,'se',se)
print(' an_ex',an_ex,an_ipo,an_all,'chips ex',topics_ex[0]); print(' names',[(d['entity'],d['prior'],d['recent'],round(d['ps'],2),round(d['rs'],2)) for d in names])
