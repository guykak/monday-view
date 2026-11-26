import json,sys
data=json.load(open('/home/claude/newsviz/design/build/data.json'))
for k in sys.argv[1:]:
    src=open(f'/home/claude/newsviz/design/build/{k}.tpl.html').read()
    blob=json.dumps(data[k.upper()[-1]],separators=(',',':')).replace('</','<\\/')
    open(f'/home/claude/newsviz/design/direction-{k[-1]}.html','w').write(src.replace('/*__DATA__*/{}',blob))
    print('wrote',k)
