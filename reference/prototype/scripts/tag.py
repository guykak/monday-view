"""Tag candidate items -> data/stories.json + stories.csv"""
import json, re, csv, sys
sys.path.insert(0, '/home/claude/newsviz/scripts')
from gazetteer import E

R = json.load(open('/home/claude/newsviz/data/items_raw.json'))
GZ = [(name, t, geo, re.compile('|'.join(r'(?:%s)' % a for a in al), re.I)) for name, (t, geo, al) in E.items()]

TOPICS = {
 'Foundation models & AI labs': [r'\bmodel(s)?\b', r'\bllm', r'gpt', r'claude', r'gemini', r'openai', r'anthropic', r'mistral', r'deepseek', r'frontier', r'benchmark', r'reasoning', r'open[- ]weight', r'xai', r'grok', r'kimi', r'qwen', r'superintelligence', r'\bagi\b', r'mod[eè]le', r'perplexity', r'tokens?\b', r'post-training', r'inference'],
 'AI agents & enterprise AI': [r'agent', r'agentic', r'copilot', r'assistant', r'enterprise ai', r'automation', r'workflow', r'ai-powered', r'ai-native', r'ai platform', r'chatbot', r'\bia\b', r'intelligence artificielle', r'vibe[- ]cod', r'legal ai', r'customer service'],
 'Dev tools & data infra': [r'developer', r'\bdev\b', r'database', r'postgres', r'sql', r'duckdb', r'kafka', r'data (platform|warehouse|lake|pipeline|engineering)', r'lakehouse', r'iceberg', r'open[- ]source', r'github', r'\bapi\b', r'\bsdk\b', r'coding', r'code review', r'kubernetes', r'cloud (cost|billing|native)', r'\brag\b', r'embedding', r'mcp', r'evals?\b', r'observability', r'snowflake', r'databricks', r'mongodb'],
 'Chips & semiconductors': [r'chip', r'semiconductor', r'\bgpu', r'\btpu', r'\bnpu', r'\bcpu', r'foundry', r'\bfab\b', r'tsmc', r'asml', r'\bhbm\b', r'memory (prices|chip)', r'dram', r'nand', r'\bssd\b', r'2nm', r'3nm', r'wafer', r'photonic', r'silicon', r'optical (processor|compute)', r'processor', r'rtl', r'verilog', r'nvidia', r'\bamd\b', r'intel', r'qualcomm', r'\barm\b', r'quantum', r'qubit', r'quantique', r'semi-?conducteur', r'puce'],
 'Data centers, compute & energy': [r'data ?cent(er|re)', r'compute', r'gpu (debt|cloud|cluster)', r'supercomputer', r'hyperscal', r'capex', r'power (grid|plant|demand)', r'\benergy\b', r'nuclear', r'electricity', r'megawatt', r'gigawatt', r'\bgw\b', r'coreweave', r'nscale', r'nebius', r'stargate', r'orbital (compute|data)', r'cooling', r'\bgrid\b', r'transformer', r'\bmw\b', r'battery', r'solar', r'énergie', r'centre de données'],
 'VC & startup ecosystem': [r'\bvc\b', r'\bvcs\b', r'venture (capital|firm)', r'\bfund\b', r'fundrais(e|ing) (for|of) (its|a) .*fund', r'\blps?\b', r'limited partner', r'general partner', r'unicorn', r'founders?', r'startup ecosystem', r'accelerator', r'angel', r'sequoia', r'andreessen', r'a16z', r'lakestar', r'creandum', r'northzone', r'accel\b', r'index ventures', r'portfolio', r'fonds', r'investisseur', r'secondar', r'emergent', r'ai 100', r'startup list', r'slush', r'web summit'],
 'M&A, IPOs & markets': [r'\bipo\b', r'listing', r'nasdaq', r'nyse', r'\bs-1\b', r'acqui', r'merger', r'\bbuy(s|ing)?\b .* for \$', r'take .* private', r'shares? (rose|fell|jump|drop|plunge|surge|tank)', r'stock', r'market cap', r'valuation', r'earnings', r'revenue (up|down|grew)', r'\bq[1-4]\b', r'quarter', r'analysts?', r'bubble', r'bulle', r'rachat', r'introduction en bourse', r'spac', r'tender offer', r'private equity', r'buyout'],
 'Big Tech platforms & products': [r'apple', r'iphone', r'macbook', r'google', r'microsoft', r'\bmeta\b', r'amazon', r'instagram', r'youtube', r'windows', r'android', r'\bios\b', r'\bsearch\b', r'smart glasses', r'chrome', r'\boffice\b', r'm365', r'microsoft 365', r'outlook', r'gmail', r'pixel'],
 'Policy, regulation & geopolitics': [r'regulat', r'\blaws?\b(?! firms?)', r'lawsuit', r'entity list', r'commerce department', r'lobby', r'sues?\b', r'court', r'antitrust', r'\bftc\b', r'\bfcc\b', r'\bsec\b', r'\bdoj\b', r'congress', r'senate', r'white house', r'trump', r'government', r'minister', r'policy(?! stack)', r'tariff', r'export control', r'sanction', r'national security', r'midterm', r'democrat', r'republican', r'election', r'ai act', r'\beu\b', r'brussels', r'budget', r'tax', r'sovereign', r'spy', r'espionage', r'intelligence agency', r'\bmss\b', r'gouvernement', r'pr[ée]sidentielle', r'ministre', r'r[ée]glementation', r'subpoena', r'probe'],
 'Security, breaches & outages': [r'hack', r'breach', r'ransomware', r'malware', r'vulnerab', r'exploit', r'zero[- ]day', r'\bcve', r'phishing', r'outage', r'cyber', r'attack', r'leak', r'exposed', r'security', r'compromis', r'stolen', r'theft', r'tradertraitor', r'cybers[ée]curit[ée]', r'incident'],
 'Robotics & autonomy': [r'robot', r'humanoid', r'autonomous', r'self-driving', r'robotaxi', r'waymo', r'cybercab', r'\bfsd\b', r'drone', r'lidar', r'\bav\b', r'physical ai', r'manufacturing automation', r'warehouse automation', r'robotique', r'mobility', r'\bev\b', r'electric vehicle', r'scooter'],
 'Space': [r'\bspace\b', r'spacex', r'satellite', r'rocket', r'launch vehicle', r'orbit', r'starship', r'starlink', r'nasa', r'spacex', r'lunar', r'\bmoon\b', r'spatial', r'blue origin', r'reentry'],
 'Fintech & crypto': [r'fintech', r'(?<!west )\bbank(s|ing)?\b', r'payment', r'stablecoin', r'crypto', r'bitcoin', r'ethereum', r'blockchain', r'binance', r'coinbase', r'wallet', r'lending', r'insurance', r'insurtech', r'neobank', r'revolut', r'monzo', r'starling', r'klarna', r'\bramp\b', r'kalshi', r'polymarket', r'prediction market', r'\bcards?\b', r'trading', r'\baml\b', r'compliance', r'banque', r'paiement', r'assurance', r'mutuelle'],
 'Health & biotech': [r'health', r'biotech', r'drug', r'pharma', r'clinical', r'protein', r'antibod', r'genom', r'medical', r'patient', r'hospital', r'therap', r'diagnos', r'cancer', r'\bnhs\b', r'isomorphic', r'santé', r'médic', r'allerg', r'longevity', r'neuro'],
 'Defence tech': [r'defen[cs]e', r'military', r'pentagon', r'\bdod\b', r'warfare', r'weapon', r'missile', r'anduril', r'helsing', r'nato', r'd[ée]fense', r'armée', r'dual-use', r'drone warfare', r'munition'],
 'Science & research': [r'research', r'paper', r'arxiv', r'proof', r'theorem', r'hypothesis', r'riemann', r'conjecture', r'mathemat', r'physics', r'scientist', r'discovery', r'study finds', r'researchers', r'lab result', r'world model', r'algorithm', r'attention', r'sparse', r'context window', r'clustering'],
 'Talent, leadership & work': [r'\bceo\b', r'steps? down', r'resign', r'appoint', r'hire[sd]?\b', r'hiring', r'layoff', r'job cuts', r'workforce', r'employees', r'talent', r'\bjoins\b', r'promoted', r'leaves', r'exit', r'chief .* officer', r'\bcfo\b', r'lays? off', r'staff', r'\bpdg\b', r'nouveau (pdg|patron)', r'jobseekers', r'hire', r'\bcto\b', r'culture', r'therapy', r'all-hands', r'patron', r'dirigeant', r'démission', r'recrut', r'emploi', r'licenci', r'career', r'burnout'],
 'Consumer, media & gaming': [r'consumer', r'gaming', r'\bgame\b', r'gta', r'netflix', r'spotify', r'streaming', r'social media', r'tiktok', r'creator', r'music', r'film', r'e-commerce', r'retail', r'delivery', r'doordash', r'instacart', r'travel', r'food', r'dating', r'reddit', r'advertis', r'smartphone', r'wearable', r'jeux', r'earbuds', r'app store', r'apps?\b', r'immobilier', r'real estate', r'athlet', r'sport'],
}
TOPIC_RX = {k: [re.compile(p, re.I) for p in v] for k, v in TOPICS.items()}

def topic_scores(title, text):
    sc = {}
    for k, rxs in TOPIC_RX.items():
        s = 0
        for rx in rxs:
            if rx.search(title): s += 2
            elif rx.search(text): s += 1
        sc[k] = s
    return sc

FX = {'$': 1.0, '€': 1.08, '£': 1.27}
AMT = re.compile(r'(?P<cur>[$€£])\s?(?P<num>\d+(?:[.,]\d+)?)\s?(?P<unit>bn|billion|b\b|m\b|mn|million|k\b|thousand|t\b|trillion)?', re.I)
AMT_EUR_FR = re.compile(r'(?P<num>\d+(?:[.,]\d+)?)\s?(?P<unit>millions?|milliards?|M|Md)\s?(?:d[’\']euros|€|EUR)', re.I)
AMT_WORD = re.compile(r'(?P<num>\d+(?:[.,]\d+)?)\s?(?P<unit>million|billion|M|B)\s(?:dollars|USD|euros|EUR)', re.I)
UNIT = {'bn': 1e9, 'billion': 1e9, 'b': 1e9, 'm': 1e6, 'mn': 1e6, 'million': 1e6, 'k': 1e3, 'thousand': 1e3, 't': 1e12, 'trillion': 1e12,
        'millions': 1e6, 'milliard': 1e9, 'milliards': 1e9, 'md': 1e9}

def amounts(s):
    out = [(p, a) for p, a in _amounts(s) if not re.search(r'^.{0,25}valu(ation|ed)|post-money', s[p:p+40], re.I)
           and not re.search(r'(valu(ation|ed|ing|es) (it |the company |the [\w-]+ )?(of|at)|at an? |worth |valuing it at |up from|from|target|total funding to|totall?ing|bringing (its|the) total( funding)? to|after raising( over)?|including|in total|than)\s*~?$', s[max(0, p-40):p], re.I)
           and not re.search(r'^[^,;]{0,12}\s*(in total|total)', s[p:p+25], re.I)]
    return out
def _amounts(s):
    out = []
    for m in AMT.finditer(s):
        u = (m.group('unit') or '').lower()
        if not u: continue
        n = float(m.group('num').replace(',', '.') if m.group('num').count(',') == 1 and len(m.group('num').split(',')[1]) != 3 else m.group('num').replace(',', ''))
        out.append((m.start(), n * UNIT[u] * FX[m.group('cur')]))
    for m in AMT_EUR_FR.finditer(s):
        u = m.group('unit').lower()
        mult = 1e9 if u.startswith(('milliard', 'md')) else 1e6
        out.append((m.start(), float(m.group('num').replace(',', '.')) * mult * 1.08))
    return sorted(out)

RAISE = re.compile(r'\b(raised?|raises|raising|secur(ed|es)|closed? (a|its)|lands?|bags?|funding|round|l[èe]ve|lev[ée]e|seed|series [a-h])\b', re.I)
ACQ = re.compile(r'\b(acquir\w*|to buy|buys|bought|merger|merge|rachat|rach[eè]te|takeover|take .* private|agreed to purchase)\b', re.I)
IPO = re.compile(r'\b(ipo|s-1|listing|lists on|debut(s|ed)? on|priced (its|the) (ipo|offering)|introduction en bourse|go public|spac)\b', re.I)
EARN = re.compile(r'\b(reports? q[1-4]|q[1-4] (revenue|results|earnings)|earnings|quarterly (results|revenue)|revenue (up|down|rose|fell))\b', re.I)
PEOPLE = re.compile(r'\b(ceo|cfo|cto|coo|chief \w+ officer|president|chair)\b.*\b(steps? down|resign\w*|appoint\w*|named|hire[sd]|joins|leaves|depart\w*|ousted|oust|reinstat\w*|return\w*|successor|interim|promoted)\b|\b(steps? down|resign\w*|appoint\w*|hires|promoted|reinstat\w*|ousted?)\b', re.I)
POLICY = re.compile(r'\b(law|bill|regulat\w*|ruling|court|judge|lawsuit|sues?|sued|antitrust|ftc|fcc|sec\b|doj|congress|senate|government|minister|ministre|export control\w*|tariff\w*|sanction\w*|ai act|gouvernement|subpoena\w*|authoriz\w*|ban(s|ned)?)\b', re.I)
INCIDENT = re.compile(r'\b(hack\w*|breach\w*|outage|ransomware|exploit\w*|vulnerab\w*|zero-day|leak\w*|attack\w*|malware|stolen|compromis\w*|disrupt\w*|exposed|crash\w*|spy|spied|espionage)\b', re.I)
LAUNCH = re.compile(r'\b(launch\w*|unveil\w*|releas\w*|introduc\w*|debut\w*|rolls? out|rolling out|ships?|now available|generally available|announc\w* .*(model|product|app|feature)|lance|d[ée]voile|open-sources?)\b', re.I)
OPINION = re.compile(r'\b(why|how|what|should|opinion|analysis|lessons|the case (for|against)|explained|deep dive|interview|q&a|mapped|to watch|we look|inside|guide)\b|\?', re.I)
ROUND = re.compile(r'\b(pre-seed|seed|series [a-h]\+?|growth (funding|round|equity)|debt (funding|financing)|venture debt|bridge)\b', re.I)

ALARM = re.compile(r'\b(hack\w*|breach\w*|ransomware|spy|espionage|national security|outage|crisis|crash\w*|plunge\w*|stolen|theft|scandal|abus\w*|fraud|bubble|bulle|collapse|ousted?|probe|investigation)\b', re.I)
NEG = re.compile(r'\b(drop\w*|fall\w*|fell|cut\w*|delay\w*|loss(es)?|sued|sues|lawsuit|fail\w*|layoffs?|shut\w*|exit|decline\w*|slump\w*|tank\w*|warn\w*|risk\w*|concern\w*|criticis\w*|recul\w*|baisse|pertes?|resign\w*|steps? down|struggl\w*|halt\w*|retreat\w*|tepid)\b', re.I)
POS = re.compile(r'\b(rais\w*|launch\w*|record|surg\w*|beat\w*|wins?|won|grow\w*|growth|soar\w*|jump\w*|profit\w*|rentable|lève|lev[ée]e|expand\w*|breakthrough|success\w*|oversubscribed|popped|pop|up \d+%|doubl\w*|tripl\w*|reinstat\w*|approv\w*|unicorn)\b', re.I)

GEO_PLACES = {
 'France': r'\bparis\b|lyon|marseille|toulouse|bordeaux|nantes|lille|grenoble|montpellier|nice|rennes|strasbourg|sophia|france|french|fran[cç]aise?',
 'Europe': r'london|u\.k\.|\buk\b|england|scotland|edinburgh|cambridge, (uk|england)|oxford|berlin|munich|hamburg|germany|german|amsterdam|netherlands|dutch|stockholm|sweden|swedish|copenhagen|denmark|danish|helsinki|espoo|finland|oslo|norway|madrid|barcelona|spain|spanish|lisbon|portugal|milan|turin|rome|italy|italian|zurich|zug|geneva|lausanne|basel|switzerland|swiss|vienna|graz|austria|brussels|belgium|warsaw|poland|krak[oó]w|prague|czech|tallinn|estonia|vilnius|riga|dublin|ireland|irish|athens|greece|greek|bucharest|romania|sofia|bulgaria|budapest|hungary|ljubljana|zagreb|luxembourg|europe|european',
 'US': r'san francisco|new york|nyc|palo alto|menlo park|mountain view|seattle|boston|austin|los angeles|chicago|miami|denver|calif\.|california|texas|mass\.|massachusetts|washington|d\.c\.|va\.|virginia|colo\.|fla\.|tenn\.|ga\.|n\.y\.|wash\.|utah|ohio|mich\.|emeryville|silicon valley|u\.s\.|\bus\b|american|delaware|atlanta|pittsburgh|philadelphia|san diego|san jose|oakland|brooklyn',
 'China': r'beijing|shanghai|shenzhen|hangzhou|china|chinese|hong kong',
 'Other': r'tel aviv|israel|toronto|montreal|vancouver|canada|singapore|tokyo|japan|seoul|korea|india|bangalore|bengaluru|mumbai|dubai|uae|abu dhabi|riyadh|saudi|sydney|australia|s[aã]o paulo|brazil|mexico|lagos|nairobi|taiwan|taipei',
}
GEO_RX = {k: re.compile(v, re.I) for k, v in GEO_PLACES.items()}

def geo_of(title, text, ents, source):
    s = title + ' ' + text[:300]
    m = re.search(r"([A-Z][\w .'’-]{1,40}?)(?:, [A-Z][\w .]+)?-based", s)
    if m:
        loc = m.group(0)
        for k in ['France', 'Europe', 'China', 'Other', 'US']:
            if GEO_RX[k].search(loc): return k
    for flag, g in [('🇫🇷', 'France'), ('🇺🇸', 'US'), ('🇨🇳', 'China')]:
        if flag in s: return g
    if re.search(r'[\U0001F1E6-\U0001F1FF]{2}', s): return 'Europe'
    for e in ents:
        if e in E and E[e][0] in ('company', 'person') and E[e][1]:
            return E[e][1]
    for e in ents:
        if e in E: return E[e][1]
    if re.search(r'startup fran[cç]aise|french (startup|tech)|la french tech', s, re.I): return 'France'
    if source.startswith('Maddyness'): return 'France'
    if source.startswith('Sifted') or source in ('EU-Startups', 'Sunday CET (Dragos Novac)'): return 'Europe'
    return 'Unknown'

def startup_name(title):
    for pat in [r"^(?:Exclusive:\s*)?([A-Z][\w.&'’ -]{1,40}?), (?:an? (?:[\w .,'’-]{0,60}?-based|developer|provider|maker|builder|operator|platform|company|startup)|the |which |that )",
                r"^[\w .,'’()-]{0,60}?-based ([A-Z][\w.&'’-]+(?: [A-Z][\w.&'’-]+){0,2}),? (?:which|that|a|an)\b",
                r"^([A-Z][\w.&'’-]+(?: [A-Z][\w.&'’-]+){0,2}) (?:raises|raised|secures|secured|lands|bags|closes|lève|annonce)",
                r"^[\U0001F1E6-\U0001F1FF]{2}\s*([\w.&'’ -]{2,30}?)\s+-\s"]:
        m = re.search(pat, title)
        if m:
            n = m.group(1).strip(' ,*')
            n = re.sub(r"^(?:[\w.' -]+-based|How|Why|Inside|Exclusive:?|Defence startup|AI startup|French startup|UK neobank|Startup)\s+", '', n).strip()
            if n.lower() not in ('the', 'it', 'this', 'a', 'an') and len(n) > 1:
                return n
    return None

def short_headline(it, ents, typ, amt, rnd):
    t = it['title']
    t = re.sub(r'^(exclusive|scoop|sources?|source|breaking|analysis|opinion)\s*:\s*', '', t, flags=re.I)
    t = re.sub(r'^[^\w$€£]+', '', t)
    if it['kind'] == 'deal_list' or (typ == 'funding round' and startup_name(it['title'])):
        n = startup_name(it['title'])
        if n:
            what = ''
            m = re.search(r'(?:developer|provider|maker|builder|operator) of ([^,.;]{3,60})', t)
            m2 = re.search(r'which (?:develops|offers|builds|provides|is building|makes|uses|helps) ([^,.;]{3,60})', t)
            what = (m or m2).group(1) if (m or m2) else ''
            if typ == 'M&A':
                return ' '.join(f"{n} acquisition deal{' ($' + fmt(amt) + ')' if amt else ''}".split()[:12])
            if typ == 'people move':
                return ' '.join(t.split()[:12])
            parts = [n, 'raises']
            parts.append(f'${fmt(amt)}' if amt else 'funding')
            if rnd: parts.append(rnd)
            if what: parts += ['for'] + what.split()[:5]
            return ' '.join(parts)[:120]
    t = re.split(r'(?<=[a-z0-9%)])[;:] |, (?:as|after|while|with|saying|amid|according) ', t)[0]
    w = t.split()
    if len(w) > 12:
        w = w[:12]
        while w and w[-1].lower() in ('a', 'an', 'the', 'of', 'to', 'for', 'and', 'in', 'on', 'at', 'with', 'by', 'its', 'as', 'from', 'de', 'la', 'le', 'les', 'des', 'du', 'et', 'à', 'en'):
            w = w[:-1]
    s = ' '.join(w)
    return s[:1].upper() + s[1:]

CASE = {}
def build_case():
    import glob, collections
    cnt = collections.defaultdict(collections.Counter)
    for f in glob.glob('/home/claude/newsviz/raw/msgs/*'):
        if 'techmeme' in f: continue
        for w in re.findall(r"[A-Za-z][A-Za-z0-9'’.-]*[A-Za-z0-9]", open(f).read()):
            if w.isupper() and len(w) > 4: continue
            cnt[w.lower()][w] += 1
    for k, c in cnt.items():
        w, n = c.most_common(1)[0]
        if w != k and n >= 2 and c[k] < n: CASE[k] = w
    for name in E:
        for part in name.split():
            CASE.setdefault(part.lower(), part)
            CASE[part.lower()] = part
def recase(h):
    out = []
    for i, w in enumerate(h.split(' ')):
        m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z0-9'’.-]*?)([^A-Za-z0-9]*)$", w)
        if m and m.group(2).lower() in CASE and not (m.group(2).lower() in ('it','us','a','in','on','at','by','to','up','new','may','will','top','one','all','says','meta','apple') and i>0 and m.group(2).islower()):
            w = m.group(1) + CASE[m.group(2).lower()] + m.group(3)
        out.append(w)
    s = ' '.join(out)
    return s[:1].upper() + s[1:]

def fmt(v):
    return f'{v/1e9:.1f}B' if v >= 1e9 else f'{v/1e6:.0f}M'

def classify(it):
    title, text = it['title'], it.get('text', '') or ''
    full = title + ' ' + text[:400]
    ents = []
    for name, t, geo, rx in GZ:
        if rx.search(title) or rx.search(text[:300]):
            ents.append(name)
    sn = startup_name(title)
    if sn and not any(sn.lower() == e.lower() for e in ents) and it['kind'] in ('deal_list', 'headline', 'lead', 'teaser'):
        if not re.search(r'\b(startup|company|firm|fund|startups|investors?)\b', sn, re.I):
            ents.insert(0, sn)
    # type
    if it['kind'] == 'deal_list':
        if ACQ.search(full): typ = 'M&A'
        elif re.search(r'\b(promoted|hired|appointed|named)\b', title): typ = 'people move'
        elif IPO.search(full): typ = 'IPO/listing'
        else: typ = 'funding round'
    elif IPO.search(title) or re.search(r'\b(plans? to list|to go public|going public)\b', title, re.I): typ = 'IPO/listing'
    elif EARN.search(title) or re.search(r'\b(forecast|guidance|outlook|bonds?|notes offering|debt offering|buybacks?|dividends?)\b', title, re.I): typ = 'earnings' if EARN.search(title) else 'news'
    elif re.search(r'startups (have )?raised|funding (fell|rose|reached|totall?ed|hit)|raised a combined|across (all )?(its )?funds', title, re.I): typ = 'analysis-opinion'
    elif ACQ.search(title): typ = 'M&A'
    elif RAISE.search(title) and amounts(title): typ = 'funding round'
    elif INCIDENT.search(title): typ = 'incident'
    elif PEOPLE.search(title): typ = 'people move'
    elif EARN.search(title): typ = 'earnings'
    elif POLICY.search(title): typ = 'policy'
    elif LAUNCH.search(title): typ = 'product launch'
    elif it['kind'] in ('analysis',) or OPINION.search(title): typ = 'analysis-opinion'
    else: typ = 'news'
    # amount
    amt = None
    if typ in ('funding round', 'M&A', 'IPO/listing'):
        am = amounts(title) if typ == 'M&A' else (amounts(title) or amounts(text[:300]))
        if typ == 'M&A' and am and re.search(r'(\d+x revenue|one-third|paid for in|in 20\d\d)', title):
            am = []
        if am:
            amt = am[0][1]
            if typ == 'funding round' and amt > 5e10:  # valuations sometimes listed first; take smallest plausible
                amt = min(a for _, a in am)
    rm = ROUND.search(full)
    rnd = rm.group(0).title().replace('Series', 'Series') if rm and typ == 'funding round' else None
    if rnd and rnd.lower().startswith('growth'): rnd = 'Growth'
    if rnd and 'debt' in rnd.lower(): rnd = 'Debt'
    # topic
    sc = topic_scores(title, text[:400])
    if typ in ('funding round',) and sc['VC & startup ecosystem'] > 0:
        sc['VC & startup ecosystem'] -= 1  # sector beats generic VC words for rounds
    if typ == 'funding round':
        sc['M&A, IPOs & markets'] -= 2
    if typ in ('IPO/listing', 'M&A', 'earnings'):
        sc['M&A, IPOs & markets'] += 1
    if re.search(r'\b(fund (i|ii|iii|iv|v|\d)|new fund\b|fund of|closes? (a |its )?\$?\d+.* fund|raises? .*fund\b|lps?\b)', full, re.I):
        sc['VC & startup ecosystem'] += 3
    FUNDRX = r'\b(fund (i|ii|iii|iv|v|\d)|new fund\b|vc fund|venture fund|first close|final close|fund of funds|\blps?\b|limited partners|(raises?|raised|closes?|closed|raising|close of)\b.{0,45}\bfunds?\b(?!ing)|across (its|their) (new )?funds|hedge fund|growth fund|buyout fund|investment fund)'
    is_fund = bool(re.search(FUNDRX, title, re.I))
    if typ == 'funding round' and is_fund:
        sc['VC & startup ecosystem'] += 5
    if typ == 'funding round' and not is_fund:
        sc['VC & startup ecosystem'] = min(sc['VC & startup ecosystem'], 0)
        if re.search(r'openai|anthropic|xai|mistral|deepseek|thinking machines|safe superintelligence', title, re.I):
            sc['Foundation models & AI labs'] += 3
    PRIO = ['Security, breaches & outages', 'Defence tech', 'Space', 'Health & biotech', 'Robotics & autonomy',
            'Fintech & crypto', 'Chips & semiconductors', 'Policy, regulation & geopolitics', 'Data centers, compute & energy', 'Science & research', 'Dev tools & data infra',
            'Talent, leadership & work', 'Consumer, media & gaming', 'Big Tech platforms & products', 'VC & startup ecosystem',
            'M&A, IPOs & markets', 'AI agents & enterprise AI', 'Foundation models & AI labs']
    best = max(sorted(sc.items(), key=lambda kv: PRIO.index(kv[0])), key=lambda kv: kv[1])
    topic = best[0] if best[1] > 0 else 'Other'
    if topic == 'Other' and re.search(r'\bAI\b|\bIA\b|AI-|artificial intelligence|\bai\b', full):
        topic = 'AI agents & enterprise AI'
    if topic == 'Other' and re.search(r"state of european tech|europe'?s? (tech|startup)|european (tech|startup)|french tech|ecosystem|startups?\b", full, re.I):
        topic = 'VC & startup ecosystem'
    sec = [k for k, v in sorted(sc.items(), key=lambda kv: -kv[1]) if v >= 2 and k != topic][:2]
    geo = geo_of(title, text, ents, it['source'])
    # sentiment
    if ALARM.search(title): sent = 'alarm'
    else:
        p, n = len(POS.findall(title)), len(NEG.findall(title))
        sent = 'positive' if p > n else 'negative' if n > p else 'neutral'
    head = re.sub(r'^(Miscellaneous|Partnerships|New research|Quick links)\s+', '', recase(short_headline(it, ents, typ, amt, rnd)) if False else '') or None
    head = recase(short_headline(it, ents, typ, amt, rnd)) if it['source'] in ('Techmeme',) or it['source'].startswith('TLDR') else short_headline(it, ents, typ, amt, rnd)
    head = re.sub(r'^(Miscellaneous|Partnerships|New research|Quick links)\s+', '', head)
    head = head[:1].upper() + head[1:]
    status = 'in talks/reported' if typ in ('funding round', 'M&A', 'IPO/listing') and re.search(r'\b(in talks|talks to|considering|plans? to|planning|pitching|seeks?|seeking|exploring|could|weighs?|eyes)\b', title, re.I) else ('closed/announced' if typ in ('funding round', 'M&A', 'IPO/listing') else None)
    return dict(date=it['date'], source=it['source'], headline=head, deal_status=status, entities=ents[:8], topic=topic,
                secondary_topics=sec, type=typ, amount_usd=round(amt) if amt else None, round=rnd,
                geography=geo, sentiment=sent, item_kind=it['kind'], source_text=title[:300],
                issue_file=it['issue_file'])

def main():
    build_case()
    S = []
    for i, it in enumerate(R):
        r = classify(it)
        r['id'] = f's{i:05d}'
        S.append(r)
    from overrides import OVR
    nov = 0
    for r in S:
        for rx, upd in OVR:
            if re.search(rx, r['source_text'], re.I):
                if r['type'] in ('funding round', 'M&A', 'IPO/listing') or 'topic' in upd or 'geography' in upd:
                    for k, v in upd.items():
                        if k == 'amount_usd' and r['type'] not in ('funding round', 'M&A', 'IPO/listing'): continue
                        r[k] = v
                    nov += 1
    print('overrides applied', nov)
    # source family for normalisation
    for r in S:
        s = r['source']
        r['source_family'] = 'TLDR' if s.startswith('TLDR') else 'Sifted' if s.startswith('Sifted') else 'Maddyness' if s.startswith('Maddyness') else s
        r['region_group'] = 'Europe (incl. France)' if r['geography'] in ('Europe', 'France') else r['geography']
    keys = ['id', 'date', 'source', 'source_family', 'headline', 'entities', 'topic', 'secondary_topics', 'type', 'deal_status', 'amount_usd', 'round', 'geography', 'region_group', 'sentiment', 'item_kind', 'source_text', 'issue_file']
    S = [{k: r[k] for k in keys} for r in S]
    json.dump(S, open('/home/claude/newsviz/data/stories.json', 'w'), indent=1, ensure_ascii=False)
    with open('/home/claude/newsviz/data/stories.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in S:
            rr = dict(r); rr['entities'] = '; '.join(r['entities']); rr['secondary_topics'] = '; '.join(r['secondary_topics'])
            w.writerow(rr)
    from collections import Counter
    print(len(S))
    for name, field in [('topic', 'topic'), ('type', 'type'), ('geo', 'geography'), ('sent', 'sentiment')]:
        print(name, Counter(r[field] for r in S).most_common())

if __name__ == '__main__':
    main()
