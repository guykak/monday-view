# Every number on the page must appear in w47_sample.md or be derived in code (listed with its derivation).
import json,re
from playwright.sync_api import sync_playwright
W='/home/claude/newsviz/weekly/'
MD=open(W+'w47_sample.md').read(); D=json.load(open(W+'build/data.json')); E=D['early']
norm=lambda t:t.replace('−','-').replace(',','')
mdn=set(re.findall(r'\d+(?:\.\d+)?',norm(MD)))
derived={  # number -> derivation (checked)
 str(E['ts_only']):'rounds carried only by Term Sheet (w47_rounds.json)', str(E['ts_plus']):'Term Sheet + other families', str(E['no_ts']):'rounds without Term Sheet',
 str(E['row']):'55-28 rest of world', str(len(E['big_eu'])):'European early rounds >= $50M', str(E['big_row']):'RoW early rounds >= $50M',
 str(len(E['big_eu'])+E['big_row']):'all early rounds >= $50M', '38':'4.5/3.25-1', '69':'3.68/12-1',
 '100':'axis tick / IPO price axis / token index base', '110':'price axis', '120':'price axis', '80':'price axis', '90':'price axis', '10':'axis $10B / count', '1.08':'EUR->USD rule', '18':'date', '19':'date','20':'date','16':'date','22':'date',
}
assert D['exits'][0]['chg']==round(100*(4.5/3.25-1)) and D['exits'][1]['chg']==round(100*(3.68/12-1))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1440,'height':900}); pg.goto('file://'+W+'w47_visual.html'); pg.wait_for_timeout(300)
    txt=pg.evaluate("document.body.innerText+' '+[...document.querySelectorAll('svg text')].map(t=>t.textContent).join(' ')"); b.close()
nums=sorted(set(re.findall(r'\d+(?:\.\d+)?',norm(txt))),key=float)
bad=[]
for n in nums:
    if n in mdn: continue
    if n in derived: print('derived',n,'=',derived[n]); continue
    bad.append(n)
print('NOT TRACED:',bad)
# key phrases present
for s in ['~$81.3bn','$93.5bn','~$1.3T','$111.50','$97.17','+34%','+17%','about −15%','−6%+','−5%+','55 rounds, 28 in Europe','Term Sheet carried 30 of the 55','count is 35','14 rounds of $100M or more','valued at ~$30B','valued at $75B','valued at $3.5B','valued at $1.5B','valued at $1B+','$3.25B mark','$4.5B in stock','~$12B paid by Intuit, 2021','$3.68B','+38%','−69%','€1bn','€725m','$4B','$8 / $40 per M','−20%','$3 / $15','under one-third of GPT-6 Astra (claim)','AlphaSignal 6','10 families','€2.05B cash bid','$500M+']:
    assert s in txt, s
print('phrases OK')
