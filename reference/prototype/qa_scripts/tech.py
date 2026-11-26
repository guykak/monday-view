from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    for k in 'abc':
        for w in (1440,1280):
            pg=b.new_page(viewport={'width':w,'height':900})
            errs=[];reqs=[]
            pg.on('console',lambda m: errs.append(m.type+':'+m.text) if m.type in('error','warning') else None); pg.on('pageerror',lambda e: errs.append(str(e)))
            pg.on('request',lambda r: reqs.append(r.url) if not r.url.startswith(('file:','data:')) else None)
            pg.goto(f'file:///home/claude/newsviz/design/direction-{k}.html'); pg.wait_for_timeout(500)
            sw=pg.evaluate('document.documentElement.scrollWidth')
            # text overlap detection in svg
            ov=pg.evaluate('''()=>{const ts=[...document.querySelectorAll('svg text')].filter(t=>t.textContent.trim()).map(t=>{const r=t.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom,t.textContent.trim()]}).filter(r=>r[2]-r[0]>0);
            const out=[];for(let i=0;i<ts.length;i++)for(let j=i+1;j<ts.length;j++){const a=ts[i],b=ts[j];const ix=Math.min(a[2],b[2])-Math.max(a[0],b[0]), iy=Math.min(a[3],b[3])-Math.max(a[1],b[1]); if(ix>2&&iy>3) out.push(a[4]+' <> '+b[4]);} 
            const clip=[...document.querySelectorAll('svg')].flatMap(s=>{const R=s.getBoundingClientRect();return [...s.querySelectorAll('text')].filter(t=>{const r=t.getBoundingClientRect();return r.width>0&&(r.left<R.left-1||r.right>R.right+1)}).map(t=>t.textContent)});
            return {ov:out.slice(0,30),n:out.length,clip:clip.slice(0,20)}}''')
            fonts=pg.evaluate("[...new Set([...document.querySelectorAll('*')].map(e=>getComputedStyle(e).fontFamily))].slice(0,8)")
            print(k,w,'scrollW',sw,'errs',errs,'ext reqs',reqs[:5]); print('  overlaps',ov['n'],ov['ov'][:15]); print('  clipped',ov['clip']); print('  fonts',fonts)
    b.close()
