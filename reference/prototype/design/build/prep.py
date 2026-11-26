import json, collections, statistics, math, datetime as dt
D='/home/claude/newsviz/data/'
A=json.load(open(D+'aggregates.json')); E=json.load(open(D+'events.json')); S=json.load(open(D+'stories.json')); F=json.load(open(D+'funding_rounds.json'))
EV={e['event_id']:e for e in E}; ST={s['id']:s for s in S}
d0=dt.date(2026,10,29); DAYS=[(d0+dt.timedelta(i)).isoformat() for i in range(29)]
di=lambda d: (dt.date.fromisoformat(d)-d0).days
out={}
# ---------- A
dust=collections.Counter(di(e['first_seen']) for e in E if e['n_source_families']==1)
two=[dict(d=di(e['first_seen']),t=e['canonical_title'][:70],s=e['source_families']) for e in E if e['n_source_families']==2]
SHORT={'e0000':'Anthropic IPO, S-1 to Nasdaq debut','e0001':'Isomorphic Labs raises $5B','e0002':'Payhawk raises $280M','e0003':'AI bubble and correction debate',
'e0004':'Jensen Huang resigns as Nvidia CEO','e0005':'Fractile raises £540M','e0006':'SE3 raises $30M (defence)','e0007':'Model ML raises $250M',
'e0008':'US midterms and tech','e0009':'Nvidia board reinstates Huang','e0010':'Sequoia shuts London office','e0011':'Plural raises €1bn fund',
'e0012':'Nvidia probes spy plot on Huang','e0013':'Binance $6.3B hack','e0014':'OpenAI raises ~$11B','e0015':'Zipline raises $1.5B',
'e0016':'DoorDash to buy Instacart','e0017':'Daisytuner $6M seed','e0018':'Genesis AI $500M Series A'}
_TH={t['threadId'][:8]:t['date'] for t in json.load(open('/home/claude/newsviz/raw/threads.json'))}
_IS={i['file']:i['thread'] for i in json.load(open(D+'issues.json'))}
sendts=lambda x: _TH[_IS[x['issue_file']]]   # issue send time; breaks same-day ties
hero=[]
for e in E:
    if e['n_source_families']<3: continue
    ss=sorted((ST[i] for i in e['story_ids']),key=sendts)
    days=collections.Counter(di(x['date']) for x in ss)
    deal = e['type'] in ('funding round','IPO/listing','M&A') or e['topic']=='VC & startup ecosystem'
    ff=ss[0]['source_family']; lead=min(di(x['date']) for x in ss if x['source_family']!=ff)-di(ss[0]['date'])
    # European = a European company or fund. e0003 is an opinion theme (geography defaulted from Maddyness), not a company.
    eu = e['geography'] in ('Europe','France') and e['event_id']!='e0003'
    hero.append(dict(id=e['event_id'],t=SHORT[e['event_id']],f=e['n_source_families'],a=di(e['first_seen']),b=di(e['last_seen']),m=e['n_mentions'],
        eu=eu,deal=deal,theme=e['event_id']=='e0003',days=sorted([[k,v] for k,v in days.items()]),fams=e['source_families'],first=ff,lead=lead,spread=e['spread_days']))
assert len(hero)==19 and sum(h['deal'] for h in hero)==13 and sum(h['eu'] for h in hero)==8
def lane(eids):
    c=collections.defaultdict(collections.Counter)
    for i in eids:
        for sid in EV[i]['story_ids']: c[ST[sid]['source_family']][di(ST[sid]['date'])]+=1
    return {f:sorted(v.items()) for f,v in c.items()}
SL=A['storylines_daily']
anth=lane(['e0000']); nv=lane(['e0012','e0004','e0009'])
assert sum(c for v in anth.values() for _,c in v)==EV['e0000']['n_mentions']==40
assert sum(c for v in nv.values() for _,c in v)==SL['Nvidia leadership crisis (spy probe -> resignation -> reinstatement)']['total']
isdeal=lambda e: e['type'] in ('funding round','IPO/listing','M&A') or e['topic']=='VC & startup ecosystem'
base=dict(deal_events=sum(map(isdeal,E)),events=len(E),deal_2fam=sum(isdeal(e) for e in E if e['n_source_families']==2),
  fund_share={f:round(100*sum(1 for x in S if x['source_family']==f and x['type']=='funding round')/sum(1 for x in S if x['source_family']==f)) for f in ('EU-Startups','Fortune Term Sheet','Sifted','TechCrunch Mobility')})
fr=EV['e0005']; frs=sorted((ST[i] for i in fr['story_ids']),key=sendts)
fr_other=min(x['date'] for x in frs if x['source_family']!='Sifted')
out['A']=dict(days=DAYS,dust=[dust.get(i,0) for i in range(29)],two=two,hero=hero,anth=anth,nv=nv,base=base,
    reach=A['events_by_reach'],kn=A['key_numbers'],nvmarks=dict(spy=di(EV['e0012']['first_seen']),resign=di(EV['e0004']['first_seen']),back=di(EV['e0009']['first_seen'])),
    fractile=dict(first=frs[0]['date'],other=fr_other,lead=di(fr_other)-di(frs[0]['date']),others=sorted({x['source_family'] for x in frs if x['date']==fr_other})),
    undermerge=dict(cands=213,low=93,high=95))
exec(open('/home/claude/newsviz/design/build/prep_bc.py').read())
