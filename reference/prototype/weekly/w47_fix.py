"""Revision: story-dated, company-merged family counts for W47 items via raw text; Hone fix; recomputed lists/medians."""
import json, re, glob, os, statistics as st, collections as C
B='/home/claude/newsviz/'
S=json.load(open(B+'data/stories.json'))
fam={x['issue_file']:x['source_family'] for x in S}
for i in json.load(open(B+'data/issues.json')):
    fam.setdefault(i['file'], i['source'])
def family(f):
    if f in fam: return fam[f]
    n=f.lower()
    for k,v in [('sifted','Sifted'),('tldr','TLDR'),('techmeme','Techmeme'),('term-sheet','Fortune Term Sheet'),('maddyness','Maddyness'),('eu-startups','EU-Startups'),('dragos','Sunday CET (Dragos Novac)'),('newcomer','Newcomer'),('not-boring','Not Boring'),('benedict','Benedict Evans'),('alphasignal','AlphaSignal'),('batch','DeepLearning.AI The Batch'),('import-ai','Import AI'),('mobility','TechCrunch Mobility')]:
        if k in n: return v
    return '?'
W47=[f for f in sorted(glob.glob(B+'raw/msgs/*.txt')) if '2026-11-16'<=os.path.basename(f)[:10]<='2026-11-22']
TXT={os.path.basename(f):re.sub(r'\s+',' ',open(f,errors='ignore').read()) for f in W47}
def fams(pattern, extra=None):
    out=C.defaultdict(list)
    for f,t in TXT.items():
        # company names match case-sensitively, or in an ALL-CAPS headline (Techmeme); stops 'Mountain View' matching MountAIn
        hit=any(m.group()==m.group().upper() or re.fullmatch(pattern,m.group()) for m in re.finditer(pattern,t,re.I))
        if hit and (extra is None or re.search(extra,t,re.I)):
            out[family(f)].append(f[:10])
    return dict(out)
ITEMS={
 'Anthropic IPO priced/listed':(r'Anthropic',r'IPO|Nasdaq|debut|listing|priced|oversubscribed'),
 'Nvidia board rules out Huang return':(r'(rule[sd]? out|no plans to reinstate)',r'Huang'),
 'Isomorphic Labs $5B':(r'Isomorphic',None),'Genesis AI $500M A':(r'Genesis AI',None),'Payhawk $280M':(r'Payhawk',None),
 'Model ML $250M':(r'Model ML',None),'Boltz $110M A':(r'\bBoltz\b',None),'Tiberius $85M A':(r'Tiberius',None),
 'Hone Health':(r'Hone Health',None),'Ramon.Space $124M B':(r'Ramon\.?Space',None),'Megarobo $200M':(r'Megarobo',None),
 'Stark Future':(r'Stark Future',None),'Remanence $30M seed':(r'Remanence',None),'Daisytuner':(r'Daisytuner',None),
 'MountAIn':(r'MountAIn',None),'Vetaion':(r'Vetaion',None),'Mosaico':(r'Mosaico',None),'Stryx AI':(r'Stryx',None),
 'Elysian Aircraft':(r'Elysian',None),'Commit Biologics':(r'Commit Biologics',None),'Dcubed':(r'Dcubed',None),
 'Seawolf':(r'Seawolf',None),'Plural EUR1bn':(r'Plural',r'fund'),'Sofinnova Crossover II':(r'Sofinnova',r'725|crossover'),
 'Norwest fund 18':(r'Norwest',r'\$4 ?b'),'Applied Compute (PANW)':(r'Applied Compute',r'Palo Alto'),
 'Mailchimp (Bending Spoons)':(r'Mailchimp',r'Bending Spoons'),'Inception (Nvidia)':(r'Inception',r'diffusion'),
 'Firebolt (MongoDB)':(r'Firebolt',None),'Avio (Iceye)':(r'Avio\b',r'Iceye'),'Zscaler (CrowdStrike)':(r'Zscaler',r'CrowdStrike'),
 'Sell-off Friday':(r'sell-?off',r'tech|Nasdaq'),
 'Redalpine':(r'Redalpine',None),'Creandum':(r'Creandum',r'fund'),
}
res={k:fams(p,e) for k,(p,e) in ITEMS.items()}
# Newcomer 20 Nov names Mailchimp in 'Six Notable Deals' without the buyer; same line credits Applied Compute, so count it for both (review visual_check V3)
res['Mailchimp (Bending Spoons)'].update(fams(r'Mailchimp',r'Notable Deals'))
for k,v in res.items(): print(k.ljust(32),len(v),{a:sorted(set(b)) for a,b in v.items()})
json.dump(res,open(B+'weekly/w47_family_counts.json','w'),indent=1)
