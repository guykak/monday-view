"""Cluster stories into cross-source events -> data/events.json ; adds event_id to stories."""
import json, re, datetime as dt
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

P = '/home/claude/newsviz/data/'
S = json.load(open(P + 'stories.json'))
GENERIC = {'US government', 'EU', 'UK', 'France', 'Germany', 'China', 'India', 'Japan', 'Taiwan', 'Nasdaq', 'North Korea'}
FR_STOP = 'le la les de des du un une et en à au aux pour par sur dans avec son sa ses qui que est sont a ont plus ce cette'.split()

def d(s): return dt.date.fromisoformat(s)
docs = [(s['headline'] + ' ' + s['source_text']).lower() for s in S]
vec = TfidfVectorizer(stop_words=list(__import__('sklearn.feature_extraction.text', fromlist=['ENGLISH_STOP_WORDS']).ENGLISH_STOP_WORDS) + FR_STOP + ['said', 'says', 'sources', 'report', 'reportedly', 'new', 'ai'],
                      ngram_range=(1, 2), min_df=1, sublinear_tf=True)
X = vec.fit_transform(docs)
sim = cosine_similarity(X)
n = len(S)
dates = np.array([d(s['date']).toordinal() for s in S])
ents = [set(e for e in s['entities'] if e not in GENERIC) for s in S]

import sys
sys.path.insert(0, '/home/claude/newsviz/scripts')
from signatures import SIG
curated = {}
for key, title, rx, a, b, topic in SIG:
    r = re.compile(rx, re.I)
    for i, s in enumerate(S):
        if i in curated: continue
        if a <= s['date'] <= b and r.search(s['headline'] + ' ' + s['source_text']):
            curated[i] = key
parent = list(range(n))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[rb] = ra

TH = 0.42
first_of = {}
for i, k in curated.items():
    if k in first_of: parent[i] = first_of[k]
    else: first_of[k] = i
for i in range(n):
    if i in curated: continue
    for j in range(i + 1, n):
        if j in curated: continue
        if abs(dates[i] - dates[j]) > 3: continue
        s = sim[i, j]
        shared = ents[i] & ents[j]
        ok = s >= TH or (s >= 0.28 and shared)
        ai, aj = S[i]['amount_usd'], S[j]['amount_usd']
        if ai and aj and shared and abs(ai - aj) / max(ai, aj) < 0.12 and S[i]['type'] == S[j]['type']:
            ok = True
        if ok: union(i, j)

comps = defaultdict(list)
for i in range(n): comps[find(i)].append(i)

# split over-large components with a stricter threshold
final = []
for c in comps.values():
    if len(c) <= 30 or c[0] in curated:
        final.append(c); continue
    sub = {i: i for i in c}
    def f2(a):
        while sub[a] != a: a = sub[a]
        return a
    for a in c:
        for b in c:
            if a < b and abs(dates[a] - dates[b]) <= 2 and sim[a, b] >= 0.5:
                ra, rb = f2(a), f2(b)
                if ra != rb: sub[rb] = ra
    g = defaultdict(list)
    for a in c: g[f2(a)].append(a)
    final += list(g.values())

events = []
for c in final:
    c = sorted(c, key=lambda i: (S[i]['date'], S[i]['source']))
    ck = curated.get(c[0])
    if len(c) > 1:
        sub = sim[np.ix_(c, c)].sum(1)
        # prefer non-deal headline items as canonical
        pref = [k for k, i in enumerate(c) if S[i]['item_kind'] in ('headline', 'lead')]
        k = max(pref or range(len(c)), key=lambda k: sub[k])
        med = c[k]
    else:
        med = c[0]
    srcs = sorted(set(S[i]['source'] for i in c))
    fams = sorted(set(S[i]['source_family'] for i in c))
    ent = Counter(e for i in c for e in S[i]['entities'])
    sig = {k: (t, tp) for k, t, _, _, _, tp in SIG}
    events.append(dict(
        curated_key=ck,
        canonical_title=sig[ck][0] if ck else S[med]['headline'],
        first_seen=S[c[0]]['date'], last_seen=max(S[i]['date'] for i in c),
        sources=srcs, n_sources=len(srcs), n_source_families=len(fams), source_families=fams,
        n_mentions=len(c),
        topic=sig[ck][1] if ck else Counter(S[i]['topic'] for i in c).most_common(1)[0][0],
        type=Counter(S[i]['type'] for i in c).most_common(1)[0][0],
        key_entities=[e for e, _ in ent.most_common(6)],
        geography=Counter(S[i]['geography'] for i in c).most_common(1)[0][0],
        amount_usd=max((S[i]['amount_usd'] or 0) for i in c) or None,
        first_source=S[c[0]]['source'],
        spread_days=(d(max(S[i]['date'] for i in c)) - d(S[c[0]]['date'])).days,
        story_ids=[S[i]['id'] for i in c]))
events.sort(key=lambda e: (-e['n_source_families'], -e['n_sources'], -e['n_mentions'], e['first_seen']))
for k, e in enumerate(events):
    e['event_id'] = f'e{k:04d}'
    for sid in e['story_ids']:
        pass
id2ev = {sid: e['event_id'] for e in events for sid in e['story_ids']}
for s in S: s['event_id'] = id2ev[s['id']]
events = [{'event_id': e.pop('event_id'), **e} for e in events]
json.dump(events, open(P + 'events.json', 'w'), indent=1, ensure_ascii=False)
json.dump(S, open(P + 'stories.json', 'w'), indent=1, ensure_ascii=False)
print(len(events), 'events;', sum(1 for e in events if e['n_sources'] >= 2), 'multi-source;', sum(1 for e in events if e['n_source_families'] >= 3), '>=3 families')
for e in events[:40]:
    print(e['n_source_families'], e['n_sources'], e['n_mentions'], e['first_seen'], e['last_seen'], '|', e['canonical_title'][:80], '|', ','.join(e['key_entities'][:3]))
