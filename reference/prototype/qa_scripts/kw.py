import sys,glob,re,os
pat=sys.argv[1]; filt=sys.argv[2] if len(sys.argv)>2 else None; n=int(sys.argv[3]) if len(sys.argv)>3 else 10
seen=set();out=[]
for fn in sorted(glob.glob('/home/claude/newsviz/raw/msgs/*.txt')):
  t=open(fn,errors='ignore').read()
  for m in re.finditer(pat,t,re.I):
    s=t[max(0,m.start()-150):m.end()+220].replace('\n',' ')
    if filt and not re.search(filt,s,re.I): continue
    k=s[100:260]
    if k in seen: continue
    seen.add(k); out.append(os.path.basename(fn)[:30]+' :: '+s)
for o in out[:n]: print(o); print()
print('total',len(out))
