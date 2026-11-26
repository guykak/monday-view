"""Test candidate weekly VC stats against W45-W47 (full weeks), with partial weeks shown.
Writes weekly/stat_tests.json and weekly/w47_detail.json."""
import json, re, statistics as st, collections as C, datetime as dt

B = '/home/claude/newsviz/'
S = json.load(open(B + 'data/stories.json'))
E = {e['event_id']: e for e in json.load(open(B + 'data/events.json'))}
F = json.load(open(B + 'design/build/funding_clean.json'))
W = ['W44p', 'W45', 'W46', 'W47', 'W48p']
FULL = ['W45', 'W46', 'W47']


def wk(d):
    d = dt.date.fromisoformat(d)
    if d < dt.date(2026, 11, 2): return 'W44p'
    if d <= dt.date(2026, 11, 8): return 'W45'
    if d <= dt.date(2026, 11, 15): return 'W46'
    if d <= dt.date(2026, 11, 22): return 'W47'
    return 'W48p'


def fams_of(eids):
    out = set()
    for e in eids:
        if e in E: out |= set(E[e]['source_families'])
    return out


# ---------- funding table enrichment ----------
DEEP = [  # (area, regex on headline, topics)
    ('Defence & security hardware', r'defen[cs]e|drone|military|missile|uav|counter-drone|munition', ['Defence tech']),
    ('Space', r'space|satellite|orbit|rocket|launch vehicle', ['Space']),
    ('Chips & photonics', r'chip|semiconductor|photonic|silicon|wafer|asic|fpga|lidar', ['Chips & semiconductors']),
    ('Quantum', r'quantum', []),
    ('Robotics & autonomy', r'robot|autonom|humanoid|self-driving|warehouse automation', ['Robotics & autonomy']),
    ('Energy, compute & climate hardware', r'energy|battery|fusion|nuclear|grid|data cent|hydrogen|solar|electric aircraft|carbon', ['Data centers, compute & energy']),
    ('Bio & health', r'bio|therap|drug|clinical|medic|health|diagnos|microfluid|cell', ['Health & biotech', 'Science & research']),
]
SOFT = [
    ('AI agents, models & dev tools', r'\bai\b|agent|llm|model|copilot|inference', ['AI agents & enterprise AI', 'Foundation models & AI labs', 'Dev tools & data infra']),
    ('Fintech & crypto', r'fintech|payment|bank|crypto|stablecoin|insur|lending|wealth', ['Fintech & crypto']),
    ('Cybersecurity', r'security|cyber', ['Security, breaches & outages']),
]


def area(x):
    h = x['headline'].lower()
    for a, rx, tps in DEEP:
        if x['topic'] in tps or re.search(rx, h): return a, True
    for a, rx, tps in SOFT:
        if x['topic'] in tps or re.search(rx, h): return a, False
    return 'Other software & services', False


def stage(x):
    s = x['stage']
    if s in ('Pre-Seed', 'Seed'): return 'Pre-seed/Seed'
    if s == 'Series A': return 'Series A'
    if s in ('Series B',): return 'Series B'
    if s: return 'Series C+'
    a = x['amount_usd'] or 0
    if not a: return 'unknown'
    return 'unstaged <=$20M' if a <= 20e6 else 'unstaged >$20M'


R = []
for x in F:
    if x['status'] != 'closed': continue
    r = dict(x)
    r['week'] = wk(x['date'])
    r['families'] = sorted(fams_of([x['event_id']] + x.get('merged_event_ids', [])))
    r['area'], r['deep'] = area(x)
    r['stg'] = stage(x)
    r['early'] = r['stg'] in ('Pre-seed/Seed', 'Series A', 'unstaged <=$20M')
    R.append(r)

# ---------- helpers ----------
results = []


def series(fn, rows):
    return {w: fn([r for r in rows if r['week'] == w]) for w in W}


def summarize(vals):
    v = [vals[w] for w in FULL if vals[w] is not None]
    if len(v) < 2: return {}
    m = st.mean(v)
    return {'full_week_range': [min(v), max(v)], 'mean': round(m, 3),
            'cv_pct': round(100 * st.pstdev(v) / m, 1) if m else None,
            'max_wow_change_pct': round(max(abs(v[i + 1] - v[i]) / v[i] * 100 for i in range(len(v) - 1) if v[i]), 1) if all(v) else None}


def fam_profile(rows):
    c = C.Counter()
    for r in rows:
        for f in r['families']: c[f] += 1
    n = len(rows)
    top = c.most_common(1)[0] if c else ('-', 0)
    return {'n_families': len(c), 'top_family': top[0], 'top_family_share_pct': round(100 * top[1] / n, 1) if n else None,
            'only_techmeme_items': sum(1 for r in rows if r['families'] == ['Techmeme'])}


def add(id_, name, kind, vals, w47rows=None, extra=None, rating=None, note=''):
    d = {'id': id_, 'name': name, 'kind': kind, 'weekly': vals}
    d.update(summarize(vals))
    if w47rows is not None: d['W47_sources'] = fam_profile(w47rows)
    if extra: d.update(extra)
    d['rating'] = rating; d['note'] = note
    results.append(d)


usd = lambda rows: round(sum(r['amount_usd'] or 0 for r in rows) / 1e6, 1)
noTM = lambda rows: [r for r in rows if r['families'] != ['Techmeme']]
drop_top = lambda rows: sorted(rows, key=lambda r: -(r['amount_usd'] or 0))[1:]
med = lambda rows: round(st.median([r['amount_usd'] for r in rows if r['amount_usd']]) / 1e6, 1) if [r for r in rows if r['amount_usd']] else None
w47 = [r for r in R if r['week'] == 'W47']

# S1 capital deployed
add('S1', 'Capital deployed in closed rounds ($M)', 'sum', series(usd, R), w47,
    {'without_techmeme_only': series(lambda rs: usd(noTM(rs)), R),
     'without_largest_round': series(lambda rs: usd(drop_top(rs)), R),
     'largest_round_share_pct': series(lambda rs: round(100 * max([r['amount_usd'] or 0 for r in rs]) / max(1, sum(r['amount_usd'] or 0 for r in rs)), 1), R)},
    'not supportable as a headline number',
    'Sum is driven by 1-3 rounds a week and by which mega-rounds the newsletters chose to carry. Use only as context under the mega-round list.')
# S2 round count
add('S2', 'Closed company rounds (count, deduplicated)', 'count', series(len, R), w47,
    {'without_techmeme_only': series(lambda rs: len(noTM(rs)), R)}, 'stands above noise (as a count, with caveat)',
    'Stable W45-W47 because issue supply per family is stable. Measures newsletter coverage of deals, not the market; compare only after 8+ weeks.')
# S3 early-stage by technical area
early = [r for r in R if r['early']]
areas = sorted({r['area'] for r in R})
add('S3', 'Early-stage rounds (pre-seed to A, or <=$20M) by technical area', 'count table',
    series(len, early), [r for r in w47 if r['early']],
    {'by_area': {a: series(lambda rs, a=a: sum(1 for r in rs if r['area'] == a), early) for a in areas},
     'deep_tech_early': series(lambda rs: sum(1 for r in rs if r['deep']), early),
     'deep_tech_early_without_techmeme': series(lambda rs: sum(1 for r in noTM(rs) if r['deep']), early)},
    'stands above noise as a count/ranking; per-area week-on-week needs 8-12 weeks',
    'Fed mainly by Sifted, Term Sheet, EU-Startups; Techmeme contributes few early rounds so dropping it barely moves it.')
# S4 mega rounds
mega = lambda rs: [r for r in rs if (r['amount_usd'] or 0) >= 100e6]
add('S4', 'Mega-rounds >= $100M (count)', 'list', series(lambda rs: len(mega(rs)), R), mega(w47),
    {'without_techmeme_only': series(lambda rs: len(mega(noTM(rs))), R),
     'W47_list': [(r['date'], r['reg'], round(r['amount_usd'] / 1e6), r['headline'][:80], r['families']) for r in sorted(mega(w47), key=lambda r: -r['amount_usd'])]},
    'noisy but useful as a list', 'Techmeme carries a large share of US mega-rounds; the list is the product, not the count.')
# S5 European share
loc = lambda rs: [r for r in rs if r['reg'] in ('EU', 'US')]
eu_cnt = lambda rs: round(100 * sum(1 for r in loc(rs) if r['reg'] == 'EU') / max(1, len(loc(rs))), 1)
eu_usd = lambda rs: round(100 * sum(r['amount_usd'] or 0 for r in loc(rs) if r['reg'] == 'EU') / max(1, sum(r['amount_usd'] or 0 for r in loc(rs))), 1)
add('S5', 'European share of EU+US closed rounds (% count)', 'share', series(eu_cnt, R), loc(w47),
    {'pct_dollars': series(eu_usd, R), 'early_only_pct_count': series(lambda rs: eu_cnt([r for r in rs if r['early']]), R),
     'without_techmeme_pct_count': series(lambda rs: eu_cnt(noTM(rs)), R)},
    'not supportable', 'Share is set by the subscription mix (Sifted, EU-Startups, Maddyness are European; Term Sheet/Techmeme US) and by whether EU-Startups/Sunday CET arrived that week. Says nothing about the market.')
# S6 median by stage
add('S6', 'Median round size, Seed/pre-seed ($M)', 'median', series(lambda rs: med([r for r in rs if r['stg'] == 'Pre-seed/Seed']), R), [r for r in w47 if r['stg'] == 'Pre-seed/Seed'],
    {'n_seed': series(lambda rs: sum(1 for r in rs if r['stg'] == 'Pre-seed/Seed'), R),
     'median_series_A': series(lambda rs: med([r for r in rs if r['stg'] == 'Series A']), R),
     'n_series_A': series(lambda rs: sum(1 for r in rs if r['stg'] == 'Series A'), R),
     'median_seed_EU': series(lambda rs: med([r for r in rs if r['stg'] == 'Pre-seed/Seed' and r['reg'] == 'EU']), R),
     'median_A_EU': series(lambda rs: med([r for r in rs if r['stg'] == 'Series A' and r['reg'] == 'EU']), R)},
    'noisy weekly; useful as a rolling 4-week figure', 'n per week is 15-25 seeds and 10-20 As; weekly medians swing. Publish 4-week rolling median with n; week-on-week means nothing.')
# S7 deep-tech share
add('S7', 'Deep-tech share of closed rounds (% count)', 'share', series(lambda rs: round(100 * sum(r['deep'] for r in rs) / max(1, len(rs)), 1), R), [r for r in w47 if r['deep']],
    {'deep_usd_M': series(lambda rs: usd([r for r in rs if r['deep']]), R),
     'without_techmeme': series(lambda rs: round(100 * sum(r['deep'] for r in noTM(rs)) / max(1, len(noTM(rs))), 1), R)},
    'stands above noise as a count; share needs a longer baseline', 'Keyword+topic classifier; robust to Techmeme removal.')

# ---------- story-level stats ----------
SW = C.defaultdict(list)
for x in S: SW[wk(x['date'])].append(x)


def ev_rows(pred):
    """events (deduped) whose first appearance falls in the week, filtered by pred on stories"""
    out = {w: {} for w in W}
    for x in S:
        if pred(x):
            out[wk(x['date'])].setdefault(x['event_id'], x)
    return out


def ev_fams(eid): return E[eid]['source_families'] if eid in E else []


PE = re.compile(r'(capital|equity|partners|holdings|infrastructure|backed by)\b.*acquired|acquired .{0,40}-based (provider|manufacturer|distributor|developer of|operator)', re.I)
TECH_TOPICS = {'AI agents & enterprise AI', 'Foundation models & AI labs', 'Chips & semiconductors', 'Dev tools & data infra', 'Security, breaches & outages',
               'Robotics & autonomy', 'Space', 'Defence tech', 'Fintech & crypto', 'Data centers, compute & energy', 'Health & biotech', 'Big Tech platforms & products', 'M&A, IPOs & markets'}
ma = ev_rows(lambda x: x['type'] == 'M&A' and not PE.search(x['source_text'] or x['headline']) and x['topic'] in TECH_TOPICS and len(x['headline']) > 12)
add('S8', 'Tech M&A events (PE roll-ups excluded)', 'list', {w: len(ma[w]) for w in W}, [{'families': ev_fams(e)} for e in ma['W47']],
    {'all_MA_events_incl_PE': {w: len(ev_rows(lambda x: x['type'] == 'M&A')[w]) for w in W},
     'W47_list': [(v['date'], v['source_family'], v['amount_usd'], v['headline'][:90], ev_fams(e)) for e, v in ma['W47'].items()]},
    'noisy but useful as a list', 'Term Sheet adds ~10 PE roll-ups a week; filtering them leaves a 15-25 item list of tech acquisitions. Count is classifier-dependent.')

fund = ev_rows(lambda x: re.search(r'\b(new|debut|second|third|fourth|fifth|sixth|seventh|eighth|ninth|flagship|growth|crossover|early-stage|seed)?\s*fund\b', x['headline'], re.I)
               and re.search(r'rais|clos|launch|clos', x['headline'], re.I) and x['type'] in ('funding round', 'news', 'VC') or (x['topic'] == 'VC & startup ecosystem' and re.search(r'fund (i|ii|iii|iv|v|vi)\b|\bfund\b.*(raises|closes|closed|raised)|(raises|closes|closed|raised).*\bfund\b', x['headline'], re.I)))
add('S9', 'New VC funds closed/raised (events)', 'list', {w: len(fund[w]) for w in W}, [{'families': ev_fams(e)} for e in fund['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['amount_usd'], v['geography'], v['headline'][:90]) for e, v in fund['W47'].items()]},
    'noisy but useful as a list', 'Regex-detected; list needs manual check. European fund closes are well covered (Sifted, Maddyness).')

ipo = ev_rows(lambda x: x['type'] == 'IPO/listing')
add('S10', 'IPO/listing events', 'list', {w: len(ipo[w]) for w in W}, [{'families': ev_fams(e)} for e in ipo['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:90], ev_fams(e)) for e, v in ipo['W47'].items()]},
    'noisy but useful as a list', 'One storyline (Anthropic IPO) dominates mentions; count events, not mentions.')

# S11 consensus: events with >=3 families whose first_seen in week; also >=2
def cons(k):
    return {w: sorted([e for e in E.values() if wk(e['first_seen']) == w and e['n_source_families'] >= k], key=lambda e: -e['n_source_families']) for w in W}
c3, c2 = cons(3), cons(2)
add('S11', 'Consensus events (first seen in week, >=3 source families)', 'list', {w: len(c3[w]) for w in W}, None,
    {'ge2_families': {w: len(c2[w]) for w in W},
     'ge2_without_techmeme': {w: sum(1 for e in c2[w] if len(set(e['source_families']) - {'Techmeme'}) >= 2) for w in W},
     'W47_ge2_list': [(e['first_seen'], e['n_source_families'], e['type'], e['canonical_title'][:80], e['source_families']) for e in c2['W47']],
     'by_type_ge2_all_weeks': C.Counter(e['type'] for w in W for e in c2[w]).most_common()},
    'stands above noise as an importance filter (list)', 'Only ~4% of events reach 2+ families. Using >=2 families with at least one non-Techmeme gives 15-30 items/week; >=3 gives 2-8.')

BIG = r'\b(openai|anthropic|google|alphabet|microsoft|meta|amazon|aws|apple|nvidia|deepmind|mistral|xai|salesforce|oracle|ibm|samsung|tsmc)\b'
big = ev_rows(lambda x: x['type'] == 'product launch' and re.search(BIG, ' '.join(x['entities']) + ' ' + x['headline'], re.I))
add('S12', 'Big-company product launches (labs + big tech)', 'list', {w: len(big[w]) for w in W}, [{'families': ev_fams(e)} for e in big['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:90], ev_fams(e)) for e, v in big['W47'].items()]},
    'noisy but useful as a list (needs judgement)', 'Raw count is mostly AlphaSignal/TLDR product notes. Only a handful per week move into a startup category; that filter is editorial, not statistical.')

lay = ev_rows(lambda x: re.search(r'layoff|lay off|laid off|job cuts|cuts? \d+ (jobs|staff)|shut(s|ting)? down|shutdown|insolven|bankrupt|administration|winds? down|closes its doors', x['headline'], re.I))
add('S13', 'Layoffs / shutdowns / insolvencies (events)', 'list', {w: len(lay[w]) for w in W}, [{'families': ev_fams(e)} for e in lay['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:90]) for e, v in lay['W47'].items()]},
    'not supportable as a stat', 'Too few items, keyword hits include government shutdown and outages. Mention individually if a consensus event.')

pol = ev_rows(lambda x: x['type'] == 'policy')
add('S14', 'Policy/regulation events', 'list', {w: len(pol[w]) for w in W}, [{'families': ev_fams(e)} for e in pol['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:90], ev_fams(e)) for e, v in pol['W47'].items()]},
    'noisy but useful as a list', 'Techmeme supplies ~75% of policy items. Keep only items that change a market a startup can sell into (EU AI Act, export controls, defence procurement).')

ppl = ev_rows(lambda x: x['type'] == 'people move')
add('S15', 'People moves (events)', 'list', {w: len(ppl[w]) for w in W}, [{'families': ev_fams(e)} for e in ppl['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:90]) for e, v in ppl['W47'].items()],
     'founders_leaving_labs_all_weeks': [(v['date'], v['headline'][:90]) for w in W for e, v in ppl[w].items() if re.search(r'leav|depart|exit|quit|launch|start', v['headline'], re.I)]},
    'not supportable as a stat', '32 items in 4 weeks, half the Huang saga. Lab departures to found startups are rare and better caught by the spinout list.')

val = ev_rows(lambda x: re.search(r'valu(ation|ed at)|\bunicorn\b|decacorn', x['headline'] + ' ' + (x['source_text'] or ''), re.I) and x['type'] in ('funding round', 'news', 'IPO/listing', 'M&A'))
add('S16', 'Valuation marks mentioned (events)', 'list', {w: len(val[w]) for w in W}, [{'families': ev_fams(e)} for e in val['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['headline'][:100]) for e, v in val['W47'].items()]},
    'noisy but useful as a list', 'Mostly late-stage US AI marks (Techmeme). Useful as a list of new unicorns; no robust aggregate.')

neg = lambda xs: round(100 * sum(1 for x in xs if x['sentiment'] in ('negative', 'alarm')) / max(1, len(xs)), 1)
add('S17', 'Negative/alarm sentiment share of stories (%)', 'share', {w: neg(SW[w]) for w in W}, None,
    {'without_techmeme': {w: neg([x for x in SW[w] if x['source_family'] != 'Techmeme']) for w in W},
     'without_huang_and_anthropic_ipo': {w: neg([x for x in SW[w] if E.get(x['event_id'], {}).get('curated_key') not in ('anthropic_ipo', 'nvidia_crisis', 'huang')]) for w in W},
     'curated_keys': sorted({e.get('curated_key') for e in E.values() if e.get('curated_key')})},
    'not supportable', 'LLM-tagged tone of headlines; moves with one scandal. Says nothing about market conditions a VC acts on.')

# S18 topic attention share (source-normalised)
def topic_share(xs, t):
    fams = C.Counter(x['source_family'] for x in xs)
    # equal weight per family
    tot = 0
    for f, n in fams.items():
        tot += sum(1 for x in xs if x['source_family'] == f and x['topic'] == t) / n
    return round(100 * tot / len(fams), 1)
add('S18', 'Chips & semiconductors share of coverage (family-normalised %)', 'share', {w: topic_share(SW[w], 'Chips & semiconductors') for w in W}, None,
    {'raw_share': {w: round(100 * sum(1 for x in SW[w] if x['topic'] == 'Chips & semiconductors') / len(SW[w]), 1) for w in W}},
    'not supportable for this brief', 'Attention, not money; a media metric (rejected direction). Driven by the Nvidia storyline.')

# S19 AI-native share of rounds
add('S19', 'AI share of closed rounds (% count, headline mentions AI/agent/model)', 'share',
    series(lambda rs: round(100 * sum(1 for r in rs if re.search(r'\bai\b|agent|llm|model', r['headline'], re.I) or r['topic'] in ('AI agents & enterprise AI', 'Foundation models & AI labs')) / max(1, len(rs)), 1), R), None,
    {}, 'noisy; needs longer baseline', 'Depends on how newsletters write headlines ("AI-powered"); not a clean measure.')

# S20 spinouts / new companies
spin = ev_rows(lambda x: re.search(r'spin.?out|spun out|spin-off|stealth|emerg\w* from stealth|founded by (former|ex-)|ex-(openai|deepmind|google|meta|anthropic|nvidia)|former (openai|deepmind|google|meta|anthropic) ', x['headline'] + ' ' + (x['source_text'] or ''), re.I))
add('S20', 'Spinouts / out-of-stealth / ex-big-lab founders (events)', 'list', {w: len(spin[w]) for w in W}, [{'families': ev_fams(e)} for e in spin['W47']],
    {'W47_list': [(v['date'], v['source_family'], v['amount_usd'], v['headline'][:100]) for e, v in spin['W47'].items()]},
    'noisy but useful as a list', 'Keyword-based; small weekly n. Good deal-sourcing list; not a stat.')

# S21 investor-led-by frequency
led = C.Counter()
for x in S:
    if wk(x['date']) in FULL:
        for m in re.finditer(r'led by ([A-Z][\w&\. ]{2,30}?)(?:[,\.]| and | with |$)', x['source_text'] or ''):
            led[m.group(1).strip()] += 1
add('S21', 'Most active lead investors (from "led by" text)', 'ranking', {w: None for w in W}, None,
    {'top_leads_W45_W47': led.most_common(15), 'n_led_by_mentions': sum(led.values())},
    'not supportable', 'Lead investor is named in a minority of items (deal lists strip it). Would need full-text parsing of every issue.')

json.dump({'weeks': W, 'full_weeks': FULL, 'n_closed_rounds': len(R), 'tests': results}, open(B + 'weekly/stat_tests.json', 'w'), indent=1, default=str)
json.dump([r for r in R if r['week'] == 'W47'], open(B + 'weekly/w47_rounds.json', 'w'), indent=1, default=str)
for d in results:
    print(d['id'], d['name'][:55].ljust(56), {w: d['weekly'][w] for w in W}, 'cv', d.get('cv_pct'), '|', d.get('W47_sources', ''))
