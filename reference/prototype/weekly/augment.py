"""Adds robustness-by-family, classifier spot-check and final verdicts to stat_tests.json."""
import json
B='/home/claude/newsviz/'
exec(open(B+'weekly/stat_tests.py').read().split('# ---------- helpers')[0])
J=json.load(open(B+'weekly/stat_tests.json')); T={t['id']:t for t in J['tests']}
def drop(fam,pred):
    return {w:sum(1 for r in R if r['week']==w and pred(r) and set(r['families'])-{fam}) for w in W}
for sid,pred in [('S2',lambda r:True),('S3',lambda r:r['early'])]:
    T[sid]['robustness_drop_one_family']={f:drop(f,pred) for f in ['Techmeme','Fortune Term Sheet','Sifted','EU-Startups']}
T['S3']['eu_early_rounds']={w:sum(1 for r in R if r['week']==w and r['early'] and r['reg']=='EU') for w in W}
T['S3']['classifier_spot_check_W47']={'flagged_deep_early':29,'correct_on_reading_text':16,'precision_pct':55,
  'errors':['Fermat (fashion AI) tagged Space','Fairly (rental marketplace) tagged Chips','Arva AI, Corma (software) tagged Defence','Hone/Knit Health (care services/software) tagged Bio','Stryx AI counted twice (Sifted + Maddyness French line)'],
  'implication':'Technical-area tags must come from an LLM reading the deal paragraph against a fixed taxonomy, with a weekly spot-check; keyword/topic tags are not good enough.'}
T['S7']['classifier_spot_check_W47']='same classifier as S3, ~55% precision on deep-tech early rounds; share not publishable until re-tagged'
T['S8']['curated_W47_startup_exits']=[
 'Palo Alto Networks buys Applied Compute (customises open-weight models) for $4.5B in stock; valued at $3.25B earlier this month (Techmeme 19 Nov, Newcomer 20 Nov)',
 'MongoDB acquires Firebolt (analytics engine) (TLDR Data 19 Nov)',
 'Nvidia in advanced talks to buy Inception (diffusion LLMs) for $500M+ plus earnouts (Techmeme 20 Nov)',
 'Bending Spoons buys Mailchimp from Intuit for $3.68B; Intuit paid ~$12B in 2021 (Techmeme 20 Nov, Sunday CET 22 Nov)',
 'Iceye launches EUR2.05B cash bid for Avio (Sunday CET 22 Nov)',
 'CrowdStrike in talks to acquire Zscaler (Techmeme/TLDR 21 Nov)']
T['S9']['curated_fund_closes']={'W45':['Creandum new fund (4 families)','Yvonne Bajela new fund (~$17M)','Robin Capital EUR15m fund II'],
 'W46':['Redalpine ~EUR222m fund VIII','Course Corrected fund II (~$86M)','Zacua Ventures $135M'],
 'W47':['Plural EUR1bn (3 families)','Sofinnova Crossover II EUR725m','Norwest fund 18 $4B (US, venture+growth)'],
 'W48p':['a16z in talks to raise ~$20B (not closed)']}
T['S9']['note']='Fund closes come from Term Sheet "Funds" section, Sifted, Maddyness. Regex detection misses most; needs an LLM pass and a VC-vs-PE filter (Gemspring, Argonaut are PE). 3 VC closes a week in each full week.'
V={ # verdict, ready_from_week1, baseline needed
 'S1':('not supportable as a headline number','no','12+ weeks, and even then only as a 4-week rolling sum'),
 'S2':('stands above noise only as context','yes (as a count)','8+ weeks before week-on-week means anything'),
 'S3':('stands above noise as a ranked count, once tagging is fixed','yes (ranking by area)','8-12 weeks for per-area trends'),
 'S4':('noisy count, strong as a list','yes (list)','n/a'),
 'S5':('not supportable','no','never: measures subscriptions'),
 'S6':('noisy weekly; usable as 4-week rolling median with n','no','4-week rolling from week 4; trend after 12 weeks'),
 'S7':('not supportable until re-tagged','no','12 weeks'),
 'S8':('noisy count, strong as a curated list','yes (list)','n/a'),
 'S9':('strong as a list','yes (list)','running total from week 1; compare after a quarter'),
 'S10':('list only when an event is new; mostly one storyline','partial','n/a'),
 'S11':('stands above noise as an importance filter','yes (list)','n/a'),
 'S12':('editorial list, not a stat','yes (list, max 3 items)','n/a'),
 'S13':('not supportable','no','insufficient items'),
 'S14':('editorial list; Techmeme supplies ~70%','partial','n/a'),
 'S15':('not supportable','no','insufficient items'),
 'S16':('useful as list of new marks/markups','yes (list)','n/a'),
 'S17':('not supportable','no','media metric'),
 'S18':('not supportable for this brief','no','media metric (rejected direction)'),
 'S19':('noisy','no','12 weeks'),
 'S20':('useful as list (deal sourcing)','yes (list)','n/a'),
 'S21':('not supportable from current parsing','no','needs full-text deal parsing'),
}
for k,(v,r,b) in V.items(): T[k]['verdict']=v; T[k]['works_from_week1']=r; T[k]['baseline_needed']=b
json.dump(J,open(B+'weekly/stat_tests.json','w'),indent=1,default=str)
print('ok')
