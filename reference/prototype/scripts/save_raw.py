import json,glob,re,os,html
D='/tmp/claude-tool-results/4915f557-152f-59a4-b010-f1597c0b7c44/'
OUT='/home/claude/newsviz/raw/'
def slug(s):
    s=re.sub(r'<.*?>','',s).strip().strip('"')
    return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:30]
def clean(t):
    t=html.unescape(t)
    t=re.sub(r'(?m)^[\s\u2007\u034f]+$','',t)
    t=re.sub(r'\(\s*https?://[^\s)]+\s*\)','',t)       # (url)
    t=re.sub(r'\[\s*https?://[^\]]+\]','',t)
    t=re.sub(r'https?://\S+','',t)
    t=re.sub(r'[​-‏͏­ ﻿]|‌','',t)
    t=re.sub(r'[ \t]+',' ',t)
    t=re.sub(r'\n\s*\n+','\n\n',t)
    return t.strip()
def h2t(h):
    h=re.sub(r'(?is)<(script|style).*?</\1>','',h)
    h=re.sub(r'(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>','\n',h)
    h=re.sub(r'<[^>]+>','',h)
    return html.unescape(h)
done=0;meta={}
for f in glob.glob(D+'*'):
    if 'list_threads' in f: continue
    try:
        s=open(f).read(); d=json.loads(s)
    except Exception: continue
    if isinstance(d,list):
        try: d=json.loads(d[0]['text'])
        except Exception: continue
    if not isinstance(d,dict) or 'messageId' not in d: continue
    txt=d.get('text') or ''
    if len(txt)<500 and d.get('html'): txt=h2t(d['html'])
    date=d['timestamp'][:10]
    fn=f"{date}_{slug(d['from'])}_{d['threadId'][:8]}.txt"
    body=clean(txt)
    open(OUT+'msgs/'+fn,'w').write(f"FROM: {d['from']}\nDATE: {d['timestamp']}\nSUBJECT: {d['subject']}\nTHREAD: {d['threadId']}\n\n{body}\n")
    meta[d['messageId']]=fn; done+=1
json.dump(meta,open(OUT+'fetched_index.json','w'),indent=0)
print(done)
