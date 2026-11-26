"""Cleaned, deduplicated funding table for Direction B (correction pass).
Order: fix known parser errors -> drop debt/credit facilities -> dedupe by company within +/-10 days (keep max amount)."""
import json, re, datetime as dt, statistics as st, itertools
F=json.load(open('/home/claude/newsviz/data/funding_rounds.json'))
def reg(g): return 'EU' if g in ('Europe','France') else ('US' if g=='US' else ('UNK' if g=='Unknown' else 'ELSE'))
rows=[]; log=[]
for x in F:
    x=dict(x); h=x['headline'].lower()
    x['reg']=reg(x['geography'])
    if 'hypersonica' in h or 'hiverge' in h: x['reg']='EU'; log.append(('geo->EU',x['event_id']))
    if 'corridian' in h: x['reg']='US'; log.append(('geo->US',x['event_id']))
    if 'kalshi' in h: x['amount_usd']=None; log.append(('kalshi amount is run-rate -> null',x['event_id']))
    if h.startswith('monzo in talks'): x['deal_status']='in talks/reported'; log.append(('monzo -> in talks',x['event_id']))
    if 'cohere' in h and 'expects' in h: x['deal_status']='in talks/reported'; log.append(('cohere first close of up-to round -> in talks',x['event_id']))
    if 'agile robotics' in h: x['reg']='EU'; log.append(('Agile Robots(Munich, via Sifted) -> EU',x['event_id']))
    if h.startswith('salt lake city-based'): x['reg']='US'; log.append(('Torus -> US',x['event_id']))
    if h.startswith('sentra,') or h.startswith('ramon.space'): x['reg']='UNK'; log.append(('no location in text -> unlocated',x['event_id']))
    if 'billionaires raised' in h: log.append(('drop: political fund, not a company round',x['event_id'])); continue
    if x['round']=='Debt' or re.search(r'\bdebt\b|credit facility',h): log.append(('drop debt/credit',x['event_id'],x['headline'][:50])); continue
    rows.append(x)
# company key: reviewer's curated list of repeated names (each verified below by printing groups) + generic "<Name> raises" extraction
NAMES=['upwind','foundry','braid','ravical','pixel systems','ares intelligence','hypersonica','pliant','kabilio','planky','athlete to athlete','harbinger','humble robotics','sumary','hiverge','ancep','path robotics','graphon','tendrils','numina','mirendil','mosaico','kindo','stark future','valeria','disseqt','aevius','treat','alecto','perry ai','previsia','elysian','agon','sennder','muray']
def key(x):
    h=x['headline'].lower()
    for n in NAMES:
        if re.search(r'\b'+re.escape(n)+r'\b',h) and not (n=='treat' and 'treat' not in h[:30]): return n
    m=re.match(r"^([a-z0-9][\w\.\-' ]{1,30}?) (?:raises|raised|has raised|secures|secured|closes|lands|bags)\b",h)
    return ('auto:'+m.group(1)) if m else 'row:'+x['event_id']
D=lambda d: dt.date.fromisoformat(d)
groups=[]
for x in sorted(rows,key=lambda r:r['date']):
    k=key(x)
    g=next((g for g in groups if g['k']==k and abs((D(x['date'])-D(g['rows'][0]['date'])).days)<=10),None)
    if g: g['rows'].append(x)
    else: groups.append(dict(k=k,rows=[x]))
ded=[]
for g in groups:
    rs=g['rows']; regs=[r['reg'] for r in rs if r['reg']!='UNK']
    best=max(rs,key=lambda r:r['amount_usd'] or 0); r=dict(best)
    r['reg']=next((r2['reg'] for r2 in rs if r2['reg'] in ('EU','US')), regs[0] if regs else 'UNK') if not any(l[1]==best['event_id'] and l[0].startswith('geo') for l in log) else best['reg']
    r['dups']=len(rs); r['status']='talks' if all(q['deal_status']!='closed/announced' for q in rs) else 'closed'
    # stage from round field or headline
    hh=' '.join(q['headline'].lower() for q in rs); rd=next((q['round'] for q in rs if q['round']),None)
    if not rd:
        m=re.search(r'pre-seed|seed|series ([a-h])\b',hh)
        rd=None if not m else ('Pre-Seed' if m.group(0)=='pre-seed' else 'Seed' if m.group(0)=='seed' else 'Series '+m.group(1).upper())
    r['stage']=rd
    ded.append(r)
multi=[g for g in groups if len(g['rows'])>1]
if __name__=='__main__':
    print('input',len(F),'after drop',len(rows),'deduped',len(ded),'dup groups',len(multi),'surplus',sum(len(g['rows'])-1 for g in multi))
    for g in multi: print(' ',g['k'],[(q['reg'],q['amount_usd'],q['headline'][:38]) for q in g['rows']])
    for l in log: print(l)
json.dump(ded,open('/home/claude/newsviz/design/build/funding_clean.json','w'))
