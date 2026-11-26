# Verifies numbers shown in each direction against data files. Funding and subject-line numbers recomputed here independently of prep.
import json, statistics, re, collections, sys
from playwright.sync_api import sync_playwright
D='/home/claude/newsviz/data/'
A=json.load(open(D+'aggregates.json')); E=json.load(open(D+'events.json')); S=json.load(open(D+'stories.json'))
ST={s['id']:s for s in S}
kn=A['key_numbers']; R=A['events_by_reach']
ev3=[e for e in E if e['n_source_families']>=3]
isdeal=lambda e: e['type'] in ('funding round','IPO/listing','M&A') or e['topic']=='VC & startup ecosystem'
eu8=[e for e in ev3 if e['geography'] in ('Europe','France') and e['event_id']!='e0003']
fr=[ST[i] for i in next(e for e in E if e['curated_key']=='fractile')['story_ids']]
fr_first=min(s['date'] for s in fr); fr_other=min(s['date'] for s in fr if s['source_family']!='Sifted')
import datetime as dt
lead=(dt.date.fromisoformat(fr_other)-dt.date.fromisoformat(fr_first)).days
_TH={t['threadId'][:8]:t['date'] for t in json.load(open('/home/claude/newsviz/raw/threads.json'))}; _IS={i['file']:i['thread'] for i in json.load(open(D+'issues.json'))}
firsts=collections.Counter(sorted((ST[i] for i in e['story_ids']),key=lambda s:_TH[_IS[s['issue_file']]])[0]['source_family'] for e in ev3)
assert firsts['Techmeme']==11 and firsts['Sifted']==3
tm=lambda ids: sum(1 for i in ids for sid in [x for e in E if e['event_id']==i for x in e['story_ids']] if ST[sid]['source_family']=='Techmeme')
# funding (independent recompute from cleaned table rows)
FC=json.load(open('/home/claude/newsviz/design/build/funding_clean.json')); CL=[r for r in FC if r['status']=='closed']
g=lambda r: [x for x in CL if x['reg']==r]; am=lambda L:[x['amount_usd'] for x in L if x['amount_usd']]; tot=sum(am(CL))
medE,medU=statistics.median(am(g('EU'))),statistics.median(am(g('US')))
sd=lambda stg,r: statistics.median([x['amount_usd'] for x in g(r) if x['stage']==stg and x['amount_usd']])
assert len(CL)==289 and len(g('EU'))==132
m1=lambda v:'$'+(f"{v/1e6:.1f}" if v%1e6 else f"{v/1e6:.0f}")+'M'
B=json.load(open('/home/claude/newsviz/design/build/data.json'))['B']; C=json.load(open('/home/claude/newsviz/design/build/data.json'))['C']
gap={x['topic']:x for x in A['eu_vs_us_sources_topic_gap']}; fp=A['source_fingerprint']
# constant panel recompute
TH=json.load(open('/home/claude/newsviz/raw/threads.json'))
PROMO=re.compile(r'(confirm|welcome|subscription|discount|offer|tickets?|webinar|sign ?up|% off|black friday|special offer|access code|update your)', re.I)
TH=[t for t in TH if not PROMO.search(t['subject'])]; months=sorted({t['date'][:7] for t in TH})
pres=collections.defaultdict(set)
for t in TH: pres[t['sender']].add(t['date'][:7])
P=[t for t in TH if len(pres[t['sender']])==8]
pct=lambda rx,m: round(100*sum(1 for t in P if t['date'][:7]==m and re.search(rx,t['subject'],re.I))/sum(1 for t in P if t['date'][:7]==m),1)
an=[pct(r'anthropic|claude|mythos',m) for m in months]; ag=[pct('agent',m) for m in months]; nvt=pct('nvidia|jensen','2026-11')
exp={
 'a':["About 19 in 20 news events", f"{kn['events']:,}", f"{kn['events_single_family']:,} ({kn['events_single_family_pct']}%)", f"{len(ev3)} / 2,210",
      f"{sum(map(isdeal,ev3))} of {len(ev3)}", f"{round(100*sum(map(isdeal,E))/len(E))}% of all events", f"{len(eu8)} of {len(ev3)}", f"{lead} days", "Sifted’s lead on Fractile",
      f"Techmeme {firsts['Techmeme']}, Sifted {firsts['Sifted']}, 5 others 1 each", 'Isomorphic Labs raises $5B 9 stories · 5d · first Techmeme', 'Genesis AI $500M Series A 3 stories · same day · first Sifted', 'Daisytuner $6M seed 3 stories · 2d · first Sifted', 'Zipline raises $1.5B 4 stories · same day · first Techmeme', 'Fractile raises £540M 13 stories · 17d · first Sifted (+13d)', f"Anthropic IPO · 40 stories", "Nvidia leadership crisis · 32 stories",
      f"Techmeme carried {tm(['e0000'])} of the 40", f"Techmeme carried {tm(['e0012','e0004','e0009'])} of the 32", "~93–95%", "213 candidate twins", "a theme, not one event", "37.5%"],
 'b':[f"{round(100*len(g('EU'))/len(CL))}%", f"{round(100*sum(am(g('EU')))/tot)}%", f"{len(CL)} closed company rounds", f"{len(g('EU'))} were European ({100*len(g('EU'))/len(CL):.1f}%)",
      f"${sum(am(g('EU')))/1e9:.1f}B of ${tot/1e9:.1f}B ({100*sum(am(g('EU')))/tot:.1f}%)", f"{m1(medE)} vs {m1(medU)}", f"{m1(sd('Seed','EU'))} vs {m1(sd('Seed','US'))}", f"{m1(sd('Series A','EU'))} vs {m1(sd('Series A','US'))}",
      f"US {sd('Seed','US')/sd('Seed','EU'):.1f}× Europe", f"US {sd('Series A','US')/sd('Series A','EU'):.1f}× Europe",
      f"Europe has {sum(a>=1e9 for a in am(g('EU')))} round of $1B or more; the US has {sum(a>=1e9 for a in am(g('US')))}",
      f"{B['loc']['eu']['eu']*100:.1f}%", f"{B['loc']['us']['eu']*100:.1f}%", "84.7%", "8.4%", "354 extracted rounds → 300", "11 “in talks” rounds excluded, leaving 289",
      f"VC is {gap['VC & startup ecosystem']['eu_sources_share']*100:.1f}% of their stories vs {gap['VC & startup ecosystem']['us_sources_share']*100:.1f}%", "Starling Bank18","Amazon56","More European deals, smaller cheques"],
 'c':["Nvidia’s November spike is one story", 'ex-scandal -0.7 pts vs avg', f"with Huang scandal {nvt}%", f"with IPO {an[-1]}%", '11 of 36 Anthropic subjects', '13.1%', f"{ag[-1]}% (May: {max(ag)}%)", '+1.58', 'Chips is +2.00', f"peak May {max(ag)}%",
      f"constant panel of {sum(1 for x in pres.values() if len(x)==8)} senders", "4.4→5.6", f"±{C['se']:.1f} pts", "Chips, foundation models, VC, M&A/IPOs",
      f"{fp['TLDR']['profile']['Dev tools & data infra']['lift']:.1f}×", f"{fp['Sifted']['profile']['VC & startup ecosystem']['lift']:.1f}×", f"{fp['AlphaSignal']['profile']['Foundation models & AI labs']['lift']:.1f}×", "(small n)", "37.5%"]}
assert C['kw']['Anthropic/Claude']==an and C['kw']['Agents']==ag
banned={'a':['96% of stories','9 of 19','travel slowly','41 items','Term Sheet 5'],'b':['Same deal flow','Names only one side mentions','deduplicated across newsletters','48.6%','23.9%'],'c':['Anthropic fell','0.2% to 15%','UK','up every month']}
ok=True
with sync_playwright() as p:
    b=p.chromium.launch()
    for k,lst in exp.items():
        pg=b.new_page(viewport={'width':1440,'height':900}); pg.goto(f'file:///home/claude/newsviz/design/direction-{k}.html'); pg.wait_for_timeout(300)
        txt=pg.evaluate("document.body.innerText + ' ' + [...document.querySelectorAll('svg text')].map(t=>t.textContent).join(' ')")
        flat=re.sub(r'\s+','',txt)
        for e in lst:
            hit = e in txt or re.sub(r'\s+','',e) in flat
            ok&=hit; print(k,'OK ' if hit else 'MISSING',e)
        for e in banned[k]:
            bad=re.search(r'(?<![A-Za-z])'+re.escape(e)+r'(?![A-Za-z])',txt) is not None
            ok&=not bad; print(k,'BANNED PRESENT' if bad else 'gone',e)
    b.close()
print('ALL OK' if ok else 'PROBLEMS')
