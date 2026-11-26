import json,sys
from playwright.sync_api import sync_playwright
W='/home/claude/newsviz/weekly/'
d=json.dumps(json.load(open(W+'build/data.json')),ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
open(W+'w47_visual.html','w').write(open(W+'build/tpl.html').read().replace('/*__DATA__*/{}',d))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1440,'height':900}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
    pg.goto('file://'+W+'w47_visual.html'); pg.wait_for_timeout(300)
    pg.screenshot(path=W+'w47_visual.png',full_page=True)
    print(pg.evaluate('document.documentElement.scrollHeight'),errs)
    if 'blocks' in sys.argv:
        import os; os.makedirs(W+'email',exist_ok=True)
        for i,sel in enumerate(['#b1','#b2','#b3','#b4','#b5'],1): pg.locator(sel).screenshot(path=W+f'email/w47_block{i}.png')
    b.close()
