"""Compute aggregates.json from stories/events/issues/threads."""
import json, re, statistics, datetime as dt, sys
from collections import Counter, defaultdict
sys.path.insert(0, '/home/claude/newsviz/scripts')
from gazetteer import E
from tag import TOPIC_RX, topic_scores

P = '/home/claude/newsviz/data/'
S = json.load(open(P + 'stories.json'))
EV = json.load(open(P + 'events.json'))
ISS = json.load(open(P + 'issues.json'))
TH = json.load(open('/home/claude/newsviz/raw/threads.json'))
EVI = {e['event_id']: e for e in EV}

def d(s): return dt.date.fromisoformat(s)
def wk(s):
    y, w, _ = d(s).isocalendar(); return f'{y}-W{w:02d}'
WEEKS = sorted(set(wk(s['date']) for s in S))
def week_range(w):
    days = sorted(set(s['date'] for s in S if wk(s['date']) == w)); return days[0], days[-1], len(days)
TOPICS = sorted(set(s['topic'] for s in S), key=lambda t: -sum(1 for s in S if s['topic'] == t))
FAMS = sorted(set(s['source_family'] for s in S), key=lambda f: -sum(1 for s in S if s['source_family'] == f))
REGION_TYPES = {'region'}
def etype(e): return E[e][0] if e in E else 'company'
A = {}

# ---- corpus
A['corpus'] = dict(
    window=[min(s['date'] for s in S), max(s['date'] for s in S)],
    issues_read=sum(1 for i in ISS if not i['promo']), promo_issues_excluded=sum(1 for i in ISS if i['promo']),
    stories=len(S), events=len(EV), multi_source_events=sum(1 for e in EV if e['n_sources'] >= 2),
    events_3plus_families=sum(1 for e in EV if e['n_source_families'] >= 3),
    stories_by_source=Counter(s['source'] for s in S).most_common(),
    stories_by_family=Counter(s['source_family'] for s in S).most_common(),
    issues_by_source=Counter(i['source'] for i in ISS if not i['promo']).most_common(),
    item_kinds=Counter(s['item_kind'] for s in S).most_common(),
    weeks={w: dict(zip(['first_day', 'last_day', 'n_days'], week_range(w))) for w in WEEKS},
    inbox_total_threads=len(TH), inbox_range=[TH[0]['date'][:10], TH[-1]['date'][:10]])

# ---- topic volume by week (raw + share) and source-normalised share
tw = defaultdict(Counter)
for s in S: tw[wk(s['date'])][s['topic']] += 1
A['topic_by_week'] = {w: {t: dict(count=tw[w][t], share=round(tw[w][t] / sum(tw[w].values()), 4)) for t in TOPICS} for w in WEEKS}
def fam_norm_share(stories):
    by = defaultdict(Counter)
    for s in stories: by[s['source_family']][s['topic']] += 1
    fams = [f for f in by if sum(by[f].values()) >= 5]
    return {t: round(sum(by[f][t] / sum(by[f].values()) for f in fams) / len(fams), 4) for t in TOPICS} if fams else {}
A['topic_share_overall'] = {t: dict(count=sum(1 for s in S if s['topic'] == t), share_raw=round(sum(1 for s in S if s['topic'] == t) / len(S), 4)) for t in TOPICS}
fn = fam_norm_share(S)
for t in TOPICS: A['topic_share_overall'][t]['share_source_normalised'] = fn[t]
last = max(d(s['date']) for s in S)
d3 = [str(last - dt.timedelta(days=i)) for i in range(20, -1, -1)]
td = defaultdict(Counter)
for s in S:
    if s['date'] in d3: td[s['date']][s['topic']] += 1
A['topic_by_day_last3w'] = {day: dict(td[day]) for day in d3}
A['issues_by_day_last3w'] = {day: sum(1 for i in ISS if i['date'] == day and not i['promo']) for day in d3}

# ---- entities
ent_c = Counter(e for s in S for e in s['entities'])
ent_src = defaultdict(set)
for s in S:
    for e in s['entities']: ent_src[e].add(s['source_family'])
non_region = [e for e, _ in ent_c.most_common() if etype(e) not in REGION_TYPES]
top30 = non_region[:30]
ew = defaultdict(Counter)
for s in S:
    for e in s['entities']: ew[e][wk(s['date'])] += 1
A['top_entities'] = [dict(entity=e, type=etype(e), home=E[e][1] if e in E else None, mentions=ent_c[e], n_source_families=len(ent_src[e]),
                          weekly={w: ew[e][w] for w in WEEKS}) for e in top30]
A['top_regions_mentioned'] = [dict(entity=e, mentions=c) for e, c in ent_c.most_common() if etype(e) in REGION_TYPES][:12]
pairs = Counter()
for s in S:
    es = sorted(set(e for e in s['entities'] if etype(e) not in REGION_TYPES))
    for i in range(len(es)):
        for j in range(i + 1, len(es)): pairs[(es[i], es[j])] += 1
A['entity_cooccurrence_top50'] = [dict(source=a, target=b, weight=w) for (a, b), w in pairs.most_common(50)]

# ---- consensus events
A['consensus_events_top25'] = [dict(event_id=e['event_id'], title=e['canonical_title'], topic=e['topic'], type=e['type'],
                                    n_source_families=e['n_source_families'], n_sources=e['n_sources'], n_mentions=e['n_mentions'],
                                    first_seen=e['first_seen'], last_seen=e['last_seen'], spread_days=e['spread_days'],
                                    first_source=e['first_source'], source_families=e['source_families'], amount_usd=e['amount_usd'])
                               for e in EV[:25]]
A['events_by_reach'] = Counter(f"{min(e['n_source_families'],5)}{'+' if e['n_source_families']>=5 else ''} families" for e in EV)

# ---- storylines (curated keys rolled up)
STORY = {
 'Nvidia leadership crisis (spy probe -> resignation -> reinstatement)': ['nvidia_spy_probe', 'jensen_resigns', 'jensen_return'],
 'Anthropic IPO': ['anthropic_ipo', 'anthropic_q3_rev'],
 'Binance $6.3B hack': ['binance_hack'],
 'Microsoft 365 outage': ['m365_outage'],
 'AI does maths (ETH disproof, Riemann proof)': ['eth_disproof', 'riemann_proof'],
 'AI bubble / market jitters': ['ai_bubble'],
 'US midterms & tech': ['us_midterms'],
 'European mega-rounds (Isomorphic, Fractile, Payhawk, Model ML)': ['isomorphic_5b', 'fractile', 'payhawk_280m', 'model_ml'],
 'European VC fund/firm shake-up (Sequoia London, Plural, Creandum)': ['sequoia_london', 'plural_fund', 'creandum_fund'],
}
key_of = {}
for e in EV:
    if e.get('curated_key'):
        for sid in e['story_ids']: key_of[sid] = e['curated_key']
A['storylines_daily'] = {}
alldays = sorted(set(s['date'] for s in S))
for name, keys in STORY.items():
    c = Counter(s['date'] for s in S if key_of.get(s['id']) in keys)
    fams = set(s['source_family'] for s in S if key_of.get(s['id']) in keys)
    A['storylines_daily'][name] = dict(total=sum(c.values()), n_source_families=len(fams), daily={day: c[day] for day in alldays})

# ---- per-source topic fingerprint (lift vs source-normalised average)
A['source_fingerprint'] = {}
for f in FAMS:
    ss = [s for s in S if s['source_family'] == f]
    if len(ss) < 15: continue
    c = Counter(s['topic'] for s in ss)
    prof = {}
    for t in TOPICS:
        sh = c[t] / len(ss)
        prof[t] = dict(share=round(sh, 4), lift=round(sh / fn[t], 2) if fn[t] else None, diff_pp=round(100 * (sh - fn[t]), 1))
    top = sorted(TOPICS, key=lambda t: -(prof[t]['diff_pp']))[:3]
    A['source_fingerprint'][f] = dict(n_stories=len(ss), profile=prof, over_indexes_on=top,
                                      europe_share=round(sum(1 for s in ss if s['region_group'] == 'Europe (incl. France)') / len(ss), 3),
                                      us_share=round(sum(1 for s in ss if s['geography'] == 'US') / len(ss), 3))

# ---- funding (deduplicated by event: one amount per event)
fund_ev = defaultdict(list)
for s in S:
    if s['type'] == 'funding round': fund_ev[s['event_id']].append(s)
vc_eids = {s['event_id'] for s in S if s['type'] == 'funding round' and s['topic'] == 'VC & startup ecosystem'}
fund_ev = {k: v for k, v in fund_ev.items() if k not in vc_eids}
vc_funds = defaultdict(list)
for s in S:
    if s['type'] == 'funding round' and s['topic'] == 'VC & startup ecosystem': vc_funds[s['event_id']].append(s)
A['vc_fund_raises'] = [dict(event_id=k, title=EVI[k]['canonical_title'], date=min(x['date'] for x in v), amount_usd=max((x['amount_usd'] or 0) for x in v) or None,
                            geography=v[0]['geography'], n_sources=len(set(x['source'] for x in v))) for k, v in vc_funds.items()]
A['vc_fund_raises'].sort(key=lambda r: -(r['amount_usd'] or 0))
rounds = []
for eid, ss in fund_ev.items():
    amts = [s['amount_usd'] for s in ss if s['amount_usd']]
    if amts:
        mc = Counter(round(x, -5) for x in amts).most_common()
        amts = [mc[0][0]] if mc[0][1] > 1 else [amts[0]]
    s0 = ss[0]
    comp = next((e for s in ss for e in s['entities'] if etype(e) not in ('investor', 'region', 'person', 'event', 'org', 'product')), None)
    best = next((s for s in ss if s['amount_usd'] and s['item_kind'] != 'lead'), next((s for s in ss if s['item_kind'] != 'lead'), s0))
    hw = re.sub(r'^(Defence startup|AI startup|Startup)\s+', '', best['headline']).split()
    if hw and (not comp or comp.lower() not in best['headline'].lower()):
        w0 = hw[0].strip(',')
        comp = w0 if (w0[:1].isupper() and '-' not in w0 and w0.lower() not in ('ai', 'the', 'a', 'an', 'sources', 'source', 'exclusive', 'how', 'why', 'cloud', 'self-driving', 'canada-based', 'french', 'uk', 'us', 'german', 'european', 'swiss', 'dutch', 'spanish', 'italian', 'swedish', 'danish', 'finnish', 'norwegian', 'israeli', 'indian', 'chinese', 'japanese', 'nvidia', 'google', 'openai', 'anthropic')) else None
    rounds.append(dict(event_id=eid, date=min(s['date'] for s in ss), company=comp, headline=EVI[eid]['canonical_title'] if EVI[eid].get('curated_key') else best['headline'],
                       topic=Counter(s['topic'] for s in ss).most_common(1)[0][0], geography=Counter(s['geography'] for s in ss).most_common(1)[0][0],
                       round=next((s['round'] for s in ss if s['round']), None), amount_usd=max(amts) if amts else None,
                       n_sources=len(set(s['source'] for s in ss)), deal_status='closed/announced' if any(s['deal_status'] == 'closed/announced' for s in ss) else 'in talks/reported'))
# merge duplicate events of the same company within 10 days (auto-clustering misses some)
def ckey(r): return re.sub(r'[^a-z0-9]', '', r['company'].lower())[:10] if r['company'] else r['event_id']
rounds.sort(key=lambda r: r['date'])
merged = []
for r in rounds:
    m = next((x for x in merged if ckey(x) == ckey(r) and abs((d(x['date']) - d(r['date'])).days) <= 10), None)
    if m:
        m['n_sources'] += r['n_sources']; m['amount_usd'] = m['amount_usd'] or r['amount_usd']; m['merged_event_ids'] = m.get('merged_event_ids', []) + [r['event_id']]
    else: merged.append(r)
rounds = merged
rounds_amt = [r for r in rounds if r['amount_usd']]
def summ(rs):
    a = [r['amount_usd'] for r in rs if r['amount_usd']]
    return dict(count=len(rs), count_with_amount=len(a), sum_usd=round(sum(a)), median_usd=round(statistics.median(a)) if a else None, max_usd=max(a) if a else None)
A['funding'] = dict(
    note='Company funding rounds only (VC fund raises reported separately under vc_fund_raises). Deduplicated by event (same round reported by several newsletters counted once; max stated amount kept). Amounts converted EUR*1.08, GBP*1.27.',
    overall=summ(rounds), closed_only=summ([r for r in rounds if r['deal_status'] == 'closed/announced']), in_talks_only=summ([r for r in rounds if r['deal_status'] != 'closed/announced']),
    by_topic={t: summ([r for r in rounds if r['topic'] == t]) for t in TOPICS if any(r['topic'] == t for r in rounds)},
    by_geography={g: summ([r for r in rounds if r['geography'] == g]) for g in sorted(set(r['geography'] for r in rounds))},
    by_week={w: summ([r for r in rounds if wk(r['date']) == w]) for w in WEEKS},
    by_round={k: summ([r for r in rounds if (r['round'] or 'Undisclosed') == k]) for k in sorted(set(r['round'] or 'Undisclosed' for r in rounds))},
    top25_rounds=sorted(rounds_amt, key=lambda r: -r['amount_usd'])[:25],
    size_buckets=Counter(('<$5M' if r['amount_usd'] < 5e6 else '$5-20M' if r['amount_usd'] < 2e7 else '$20-100M' if r['amount_usd'] < 1e8 else '$100M-1B' if r['amount_usd'] < 1e9 else '>$1B') for r in rounds_amt))
A['funding']['by_geography_x_bucket'] = {g: Counter(('<$5M' if r['amount_usd'] < 5e6 else '$5-20M' if r['amount_usd'] < 2e7 else '$20-100M' if r['amount_usd'] < 1e8 else '$100M-1B' if r['amount_usd'] < 1e9 else '>$1B') for r in rounds_amt if r['geography'] == g) for g in sorted(set(r['geography'] for r in rounds_amt))}
json.dump(rounds, open(P + 'funding_rounds.json', 'w'), indent=1, ensure_ascii=False)

# ---- rising vs fading: last 2 weeks vs prior 2 weeks (by share of stories)
cut = str(last - dt.timedelta(days=13))
H1 = [s for s in S if s['date'] < cut]; H2 = [s for s in S if s['date'] >= cut]
def shares(ss, key):
    c = Counter(); [c.update([s[key]]) if key != 'entities' else c.update(set(s['entities'])) for s in ss]; return c
t1, t2 = shares(H1, 'topic'), shares(H2, 'topic')
A['rising_fading'] = dict(periods=dict(prior=[min(s['date'] for s in H1), max(s['date'] for s in H1)], recent=[cut, str(last)], n_prior=len(H1), n_recent=len(H2)))
A['rising_fading']['topics'] = sorted([dict(topic=t, prior_share=round(t1[t] / len(H1), 4), recent_share=round(t2[t] / len(H2), 4),
                                            change_pp=round(100 * (t2[t] / len(H2) - t1[t] / len(H1)), 2)) for t in TOPICS], key=lambda x: -x['change_pp'])
e1, e2 = shares(H1, 'entities'), shares(H2, 'entities')
ents = [e for e in set(e1) | set(e2) if e1[e] + e2[e] >= 8]
er = [dict(entity=e, prior=e1[e], recent=e2[e], prior_share=round(e1[e] / len(H1), 4), recent_share=round(e2[e] / len(H2), 4),
           change_pp=round(100 * (e2[e] / len(H2) - e1[e] / len(H1)), 2)) for e in ents]
A['rising_fading']['entities_rising'] = sorted(er, key=lambda x: -x['change_pp'])[:12]
A['rising_fading']['entities_fading'] = sorted(er, key=lambda x: x['change_pp'])[:12]

# ---- geography share
def geo_mix(ss):
    c = Counter(s['region_group'] for s in ss); n = len(ss)
    return {k: round(c[k] / n, 4) for k in ['US', 'Europe (incl. France)', 'China', 'Other', 'Unknown']} | {'France_only': round(sum(1 for s in ss if s['geography'] == 'France') / n, 4), 'n': n}
A['geography'] = dict(overall=geo_mix(S), by_week={w: geo_mix([s for s in S if wk(s['date']) == w]) for w in WEEKS},
                      by_source_family={f: geo_mix([s for s in S if s['source_family'] == f]) for f in FAMS if sum(1 for s in S if s['source_family'] == f) >= 15},
                      known_only=geo_mix([s for s in S if s['geography'] != 'Unknown']),
                      europe_sources_vs_us_sources=dict(
                          european_sources=geo_mix([s for s in S if s['source_family'] in ('Sifted', 'Maddyness', 'EU-Startups', 'Sunday CET (Dragos Novac)')]),
                          us_sources=geo_mix([s for s in S if s['source_family'] in ('Techmeme', 'TLDR', 'Fortune Term Sheet', 'Newcomer', 'AlphaSignal', 'Not Boring', 'TechCrunch Mobility', 'Import AI', 'DeepLearning.AI The Batch')])))
# what European sources cover that US sources don't (topic shares)
EUF = ('Sifted', 'Maddyness', 'EU-Startups', 'Sunday CET (Dragos Novac)')
eu = [s for s in S if s['source_family'] in EUF]; us = [s for s in S if s['source_family'] not in EUF + ('Benedict Evans',)]
ce, cu = Counter(s['topic'] for s in eu), Counter(s['topic'] for s in us)
A['eu_vs_us_sources_topic_gap'] = sorted([dict(topic=t, eu_sources_share=round(ce[t] / len(eu), 4), us_sources_share=round(cu[t] / len(us), 4),
                                               gap_pp=round(100 * (ce[t] / len(eu) - cu[t] / len(us)), 1)) for t in TOPICS], key=lambda x: -x['gap_pp'])
# entities only European sources see (>=3 mentions in EU sources, 0 in US sources)
eu_e = Counter(e for s in eu for e in s['entities'] if etype(e) not in REGION_TYPES)
us_e = Counter(e for s in us for e in s['entities'])
A['entities_only_in_european_sources'] = [dict(entity=e, eu_mentions=c) for e, c in eu_e.most_common() if us_e[e] == 0 and c >= 3][:20]
A['entities_only_in_us_sources'] = [dict(entity=e, us_mentions=c) for e, c in Counter(e for s in us for e in s['entities'] if etype(e) not in REGION_TYPES).most_common() if eu_e[e] == 0 and c >= 8][:20]

# ---- sentiment by topic
A['sentiment_by_topic'] = {t: dict(Counter(s['sentiment'] for s in S if s['topic'] == t)) for t in TOPICS}
A['type_by_topic'] = {t: dict(Counter(s['type'] for s in S if s['topic'] == t)) for t in TOPICS}

# ---- long-run context: subject lines of every inbox thread Apr-Nov (keyword topic match), per month, per 100 issues
PROMO = re.compile(r'(confirm|welcome|subscription|discount|offer|tickets?|webinar|sign ?up|% off|black friday|special offer|access code|update your)', re.I)
mon = defaultdict(Counter); mon_n = Counter()
for t in TH:
    if PROMO.search(t['subject']): continue
    m = t['date'][:7]; mon_n[m] += 1
    sc = topic_scores(t['subject'], '')
    for k, v in sc.items():
        if v > 0: mon[m][k] += 1
A['subject_line_topic_trend_monthly'] = dict(note='All 3,254 inbox threads (Apr 10-Nov 26), subject lines only, keyword match (multi-label). Value = % of that month\'s issues whose subject mentions the topic. Sources subscribed changed over time (inbox pruned after Aug), so read as directional.',
                                              issues_per_month=dict(sorted(mon_n.items())),
                                              pct={m: {k: round(100 * mon[m][k] / mon_n[m], 1) for k in TOPICS if k in mon[m]} for m in sorted(mon_n)})
kw = {'Anthropic/Claude': r'anthropic|claude|mythos', 'OpenAI/ChatGPT': r'openai|chatgpt|gpt', 'Nvidia': r'nvidia|jensen', 'Agents': r'agent',
      'IPO': r'\bipo\b', 'Robotics/humanoids': r'robot|humanoid', 'Data centers': r'data ?cent', 'Quantum': r'quantum|quantique', 'Defence': r'defen[cs]e|d[ée]fense', 'Space': r'space|spacex|starship|satellite'}
A['subject_line_keyword_trend_monthly'] = {m: {k: round(100 * sum(1 for t in TH if t['date'][:7] == m and not PROMO.search(t['subject']) and re.search(v, t['subject'], re.I)) / mon_n[m], 1) for k, v in kw.items()} for m in sorted(mon_n)}

json.dump(A, open(P + 'aggregates.json', 'w'), indent=1, ensure_ascii=False, default=lambda o: dict(o) if isinstance(o, Counter) else str(o))
print('ok')

# ---- key numbers cited in findings.md (computed, so the brief can be checked against this block)
eu_r = [r for r in rounds if r['geography'] in ('Europe', 'France')]; us_r = [r for r in rounds if r['geography'] == 'US']
tot_amt = sum(r['amount_usd'] or 0 for r in rounds)
c3 = [e for e in EV if e['n_source_families'] >= 3]
dealish = [e for e in c3 if e['type'] in ('funding round', 'M&A', 'IPO/listing') or e['topic'] == 'VC & startup ecosystem']
A['funding']['by_region_group'] = {'Europe (incl. France)': summ(eu_r), 'US': summ(us_r)}
K = dict(
 stories=len(S), issues=A['corpus']['issues_read'], events=len(EV), techmeme_share_of_items=round(sum(1 for s in S if s['source'] == 'Techmeme') / len(S), 3),
 events_single_family=sum(1 for e in EV if e['n_source_families'] == 1), events_single_family_pct=round(100 * sum(1 for e in EV if e['n_source_families'] == 1) / len(EV), 1),
 events_3plus_families=len(c3), events_3plus_families_pct=round(100 * len(c3) / len(EV), 1), events_3plus_that_are_deals_or_vc=len(dealish),
 events_3plus_european=sum(1 for e in c3 if e['geography'] in ('Europe', 'France')),
 eu_rounds=len(eu_r), us_rounds=len(us_r), all_rounds=len(rounds), eu_rounds_pct=round(100 * len(eu_r) / len(rounds), 1),
 eu_amount_usd_bn=round(sum(r['amount_usd'] or 0 for r in eu_r) / 1e9, 2), us_amount_usd_bn=round(sum(r['amount_usd'] or 0 for r in us_r) / 1e9, 2), all_amount_usd_bn=round(tot_amt / 1e9, 2),
 eu_amount_pct=round(100 * sum(r['amount_usd'] or 0 for r in eu_r) / tot_amt, 1),
 eu_median_usd_m=round(statistics.median([r['amount_usd'] for r in eu_r if r['amount_usd']]) / 1e6, 1), us_median_usd_m=round(statistics.median([r['amount_usd'] for r in us_r if r['amount_usd']]) / 1e6, 1),
 eu_rounds_under_20m_pct=round(100 * sum(1 for r in eu_r if r['amount_usd'] and r['amount_usd'] < 2e7) / sum(1 for r in eu_r if r['amount_usd']), 1),
 us_rounds_under_20m_pct=round(100 * sum(1 for r in us_r if r['amount_usd'] and r['amount_usd'] < 2e7) / sum(1 for r in us_r if r['amount_usd']), 1),
 top_entity_by_mentions=A['top_entities'][0]['entity'], top_entity_mentions=A['top_entities'][0]['mentions'],
 widest_entity=max(A['top_entities'], key=lambda e: e['n_source_families'])['entity'], widest_entity_families=max(e['n_source_families'] for e in A['top_entities']),
 n_source_families=len(set(s['source_family'] for s in S)),
)
A['key_numbers'] = K
json.dump(A, open(P + 'aggregates.json', 'w'), indent=1, ensure_ascii=False, default=lambda o: dict(o) if isinstance(o, Counter) else str(o))
print(json.dumps(K, indent=0))
