import json,glob,re,collections
threads={}
for f in glob.glob('/tmp/claude-tool-results/4915f557-152f-59a4-b010-f1597c0b7c44/*.json'):
    d=json.load(open(f))
    try: obj=json.loads(d[0]['text'])
    except Exception as e: print('skip',f,e); continue
    if 'threads' not in obj: continue
    for t in obj['threads']:
        threads[t['threadId']]=t
rows=[]
for t in threads.values():
    s=t['senders'][0]
    m=re.match(r'\s*"?(.*?)"?\s*<(.+)>',s)
    name,addr=(m.group(1),m.group(2)) if m else (s,s)
    rows.append(dict(threadId=t['threadId'],sender=name,sender_email=addr,subject=t.get('subject',''),date=t['timestamp'],messageCount=t['messageCount'],lastMessageId=t['lastMessageId'],size=t.get('size'),preview=t.get('preview','')[:300]))
rows.sort(key=lambda r:r['date'])
json.dump(rows,open('/home/claude/newsviz/raw/threads.json','w'),indent=1,ensure_ascii=False)
print(len(rows),rows[0]['date'],rows[-1]['date'])
c=collections.Counter(r['sender'] for r in rows)
for k,v in c.most_common(): print(v,k)
