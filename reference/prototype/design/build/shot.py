import sys,asyncio
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    for k in sys.argv[1:]:
        pg=b.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        errs=[]; pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
        pg.goto(f'file:///home/claude/newsviz/design/direction-{k}.html'); pg.wait_for_timeout(400)
        pg.screenshot(path=f'/home/claude/newsviz/design/shot-{k}.png',full_page=True)
        print(k, pg.evaluate('document.documentElement.scrollHeight'), pg.evaluate('document.documentElement.scrollWidth'), errs)
    b.close()
