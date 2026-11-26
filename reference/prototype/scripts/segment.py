"""Segment newsletter issues (raw/msgs/*.txt) into candidate news items.
Output: data/items_raw.json  (one record per candidate item, before tagging)
"""
import re, json, glob, os, unicodedata
RAW = '/home/claude/newsviz/raw/msgs/'
OUT = '/home/claude/newsviz/data/items_raw.json'

SOURCE_MAP = [
    ('TLDR Hardware', 'TLDR Hardware'), ('TLDR IT', 'TLDR IT'), ('TLDR Data', 'TLDR Data'),
    ('TLDR Fintech', 'TLDR Fintech'), ('TLDR', 'TLDR'),
    ('Techmeme', 'Techmeme'), ('Sifted Daily', 'Sifted Daily'), ('Startup Life by Sifted', 'Sifted Startup Life'),
    ('Fintech by Sifted', 'Sifted Fintech'), ('AI & Deeptech by Sifted', 'Sifted AI & Deeptech'),
    ('Up Round by Sifted', 'Sifted Up Round'), ('Maddyness IA', 'Maddyness IA'), ('Maddyness', 'Maddyness'),
    ('Term Sheet', 'Fortune Term Sheet'), ('Newcomer', 'Newcomer'), ('AlphaSignal', 'AlphaSignal'),
    ('Benedict Evans', 'Benedict Evans'), ('The Batch', 'DeepLearning.AI The Batch'), ('DeepLearning.AI', 'DeepLearning.AI'),
    ('Import AI', 'Import AI'), ('Not Boring', 'Not Boring'), ('EU-Startups', 'EU-Startups'),
    ('TechCrunch Mobility', 'TechCrunch Mobility'), ('Dragos Novac', 'Sunday CET (Dragos Novac)'),
]
def source_name(frm):
    for k, v in SOURCE_MAP:
        if k.lower() in frm.lower():
            return v
    return frm.split('<')[0].strip()

BOILER = re.compile(r'(unsubscribe|view in browser|view online|sign up|advertis|sponsor|copyright|all rights reserved|'
                    r'privacy policy|manage (my )?(subscription|preferences|newsletters)|forwarded|submit a deal|'
                    r'subscribe|webinar|register now|tickets?\b|discount|promo code|work with us|follow on x|'
                    r'paid for and produced|partenariat|désabonner|abonnement|s\'inscrire|read online|'
                    r'download the guide|learn more$|in partnership with|premium subscribers|upgrade here|black friday)', re.I)

def norm_ws(s):
    return re.sub(r'\s+', ' ', s).strip()

def capsfix(s):
    """TLDR/Techmeme headlines are ALL CAPS -> sentence case-ish (keep tokens with digits/known acronyms)."""
    if sum(c.isupper() for c in s) < 0.6 * max(1, sum(c.isalpha() for c in s)):
        return s
    words = s.split(' ')
    out = []
    for i, w in enumerate(words):
        core = re.sub(r'[^A-Za-z]', '', w)
        if len(core) <= 4 and core.isupper() and core in ACRO:
            out.append(w)
        elif i == 0:
            out.append(w[:1] + w[1:].lower())
        else:
            out.append(w.lower())
    return ' '.join(out)
ACRO = set('AI US UK EU CEO CFO CTO IPO GPU CPU TPU HBM AMD AWS IBM SEC FTC FCC DOJ NHS VC LLM API SDK RTL ASML TSMC SMIC NASA FBI CIA MSS NBA GTA PC OLED Q1 Q2 Q3 Q4 YOY AR VR XR NPU OS SAP BYD ARM EV EVS UAE NYT WSJ FT AMZN NVDA GOOG GAA CXMT SK RAG ML'.split())

def items_tldr(txt):
    out = []
    txt = re.sub(r'(?m)^\s*TLDR[A-Z ]*\d{4}-\d\d-\d\d\s*$', '', txt)
    txt = re.sub(r'(?m)^[^A-Za-z0-9\n]{1,6}\s*$', '', txt)
    # headline: caps text possibly multi-line followed by (N MINUTE READ) or (GITHUB REPO) etc. and [n]
    for m in re.finditer(r'\n\s*([A-Z0-9][^a-z\[\]]{12,400}?)\s*\(((?:\d+ MINUTE READ)|GITHUB REPO|WEBSITE|PODCAST|SPONSOR|VIDEO|[A-Z ]{3,20})\)\s*(?:\[\d+\])?\s*\n(.*?)(?=\n\s*\n\s*[A-Z0-9][^a-z\[\]]{12,}?\(|\Z)', txt, re.S):
        head, tag, body = m.group(1), m.group(2), m.group(3)
        if 'SPONSOR' in tag:
            continue
        head = re.sub(r'^(TLDR\b[A-Z ]*?(\d{4}-\d\d-\d\d)?\s*)', '', norm_ws(head))
        if len(head) < 15:
            continue
        head = re.sub(r'^((HEADLINES|NEWS|ANALYSIS|OPINIONS?|ENGINEERING|RESEARCH|SCIENCE|FUTURISTIC|TECHNOLOGY|PROGRAMMING|DESIGN|DATA SCIENCE|DEEP DIVES?|QUICK LINKS|MISCELLANEOUS|LAUNCHES|TRENDS|ADVICE|TUTORIALS|TOOLS|RESOURCES|BIG TECH|STARTUPS|CRYPTO|FINTECH|AI|SECURITY|ATTACKS|VULNERABILITIES|STRATEGIES|TACTICS|INNOVATIONS|HARDWARE|INFRASTRUCTURE|CLOUD|DEVOPS|ARTICLES|OPINION|AND|&|,)\s*)+(?=[A-Z0-9])', lambda m: '' if len(m.group(0).split())>=2 else m.group(0), head)
        out.append(dict(title=capsfix(head), text=norm_ws(body)[:700], kind='headline'))
    return out

def items_techmeme(txt):
    out = []
    for line in txt.split('\n'):
        if line.startswith('='):
            m = re.match(r'=(.*?)\s*=\s*\((.*?)\)\s*$', line)
            if m:
                out.append(dict(title=capsfix(norm_ws(m.group(1))), text='', kind='headline', via=m.group(2)))
    return out

def items_termsheet(txt, subject):
    out = [dict(title=subject, text='', kind='lead')]
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    joined = []
    i = 0
    while i < len(lines):
        l = lines[i]
        if l == '-' and i + 1 < len(lines):
            joined.append(lines[i + 1]); i += 2; continue
        if l.startswith('- ') and i + 1 < len(lines) and re.search(r'(acquired|acquire|stake in|merge with|invested in)\s*$', l):
            joined.append(l[2:] + ' ' + lines[i + 1]); i += 2; continue
        if l.startswith('- '):
            joined.append(l[2:])
        i += 1
    for j in joined:
        if re.search(r'(raised|acquired|acquire|promoted|hired|appointed|named|filed|priced|closed|launched|stake)', j) and len(j) > 40:
            out.append(dict(title=norm_ws(j)[:300], text=norm_ws(j), kind='deal_list'))
    return out

def items_sifted(txt, subject):
    out = [dict(title=subject.strip(), text='', kind='lead')]
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    # preview first line "+ a; b"
    if lines and lines[0].startswith('+'):
        for part in re.split(r';', lines[0][1:]):
            if len(part.strip()) > 8:
                out.append(dict(title=part.strip(), text='', kind='teaser'))
    for l in lines:
        if BOILER.search(l):
            continue
        first = l[:1]
        is_emoji = unicodedata.category(first) == 'So' or ord(first) > 0x2500 and not first.isalpha()
        if is_emoji and len(l) > 30:
            out.append(dict(title=norm_ws(re.sub(r'^[^\w]+', '', l))[:300], text='', kind='headline'))
        elif l.startswith('- ') and len(l) > 30:
            out.append(dict(title=l[2:], text='', kind='headline'))
        elif re.match(r'^[A-ZÀ-Ý][\w .,\'’()-]{1,60}-based ', l) and re.search(r'(raised|secured|closed|landed|bagged)', l):
            out.append(dict(title=norm_ws(l)[:300], text=norm_ws(l), kind='deal_list'))
    return out

def items_maddyness(txt, subject):
    subj = re.sub(r'^\d\d\.\d\d\s*-\s*', '', subject)
    out = [dict(title=subj, text='', kind='lead')]
    lines = [l.strip() for l in txt.split('\n')]
    nonempty = [l for l in lines if l]
    for i, l in enumerate(nonempty):
        if re.match(r"lire l[’']article", l, re.I) and i >= 2:
            t, d = nonempty[i - 2], nonempty[i - 1]
            t = t.lstrip('*').strip()
            if BOILER.search(t) or len(t) < 15:
                continue
            out.append(dict(title=t, text=d[:600], kind='headline'))
        m = re.match(r'^0\d\s+(.{15,})$', l)
        if m:
            out.append(dict(title=m.group(1).strip(), text='', kind='headline'))
    return out

def items_alphasignal(txt, subject):
    subj = re.sub(r'^[^\w]+', '', subject).strip()
    out = [dict(title=subj, text='', kind='lead')]
    lines = txt.split('\n')
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('▸'):
            buf = [lines[i].strip()[1:].strip()]
            j = i + 1
            single = 0
            while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('▸') and j - i < 12:
                s = lines[j].strip()
                if len(s) <= 2: single += 1
                if s in ('Top News', 'Top Papers', 'Top Repos', 'Top Tools', 'Trending Signals'): break
                buf.append(s); j += 1
            t = norm_ws(' '.join(buf))
            if single < 3 and len(t) > 20 and not BOILER.search(t):
                out.append(dict(title=t[:300], text='', kind='headline'))
            i = j
        else:
            i += 1
    return out

def items_benedict(txt):
    out = []
    blocks = re.split(r'\n\*\* ', '\n' + txt)
    skip = ('Preview from', 'News', 'About', 'Ideas', 'Column', 'Outside interests', 'Data')
    for b in blocks[1:]:
        head, _, body = b.partition('\n')
        head = head.strip()
        body = re.sub(r'^-+\s*', '', body.strip())
        paras = [p.strip() for p in re.split(r'\n\s*\n|\n', body) if len(p.strip()) > 60]
        if head.startswith(skip) or head == '':
            continue
        if head.startswith('The week in'):
            for p in paras[:8]:
                out.append(dict(title=norm_ws(p)[:200], text=norm_ws(p)[:600], kind='headline'))
            continue
        if paras and not BOILER.search(head):
            out.append(dict(title=head, text=norm_ws(paras[0])[:600], kind='analysis'))
    return out

def items_importai(txt):
    out = []
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    for i, l in enumerate(lines[:-1]):
        if l.endswith(':') and lines[i + 1].startswith('…') and 15 < len(l) < 160:
            out.append(dict(title=l[:-1], text=lines[i + 1].strip('…. '), kind='analysis'))
    return out

def items_flag_lines(txt, subject):
    out = [dict(title=subject, text='', kind='lead')]
    for l in txt.split('\n'):
        l = l.strip()
        if re.match(r'^[\U0001F1E6-\U0001F1FF]{2}\s*\S', l) and len(l) > 15:
            out.append(dict(title=norm_ws(l)[:250], text='', kind='deal_list' if re.search(r'raised|seed|series', l, re.I) else 'headline'))
    return out

def items_generic(txt, subject, cap=12):
    out = [dict(title=subject, text='', kind='lead')]
    nb = [l.strip() for l in txt.split('\n') if l.strip()]
    for i, l in enumerate(nb):
        m = re.match(r'^\(\d+[a-z]?\)\s+(.{10,200})$', l)
        if m:
            out.append(dict(title=m.group(1).strip(), text=' '.join(nb[i+1:i+3])[:600], kind='headline'))
    if len(out) > 3:
        return out
    paras = [norm_ws(p) for p in re.split(r'\n\s*\n', txt)]
    n = 0
    for p in paras:
        if n >= cap: break
        if 60 < len(p) < 900 and not BOILER.search(p[:200]) and re.search(
                r'(raised|raises|secured|launch|announc|acquir|valuation|\$\d|€\d|£\d|\d+ ?(m|bn|million|billion)\b|IPO|filed|unveil|partners? with|deal)', p, re.I):
            out.append(dict(title=p[:220], text=p[:600], kind='headline' if re.search(r'raised|secured', p) is None else 'deal_list'))
            n += 1
    return out

def items_eustartups(txt, subject):
    out = [dict(title=subject, text='', kind='lead')]
    paras = [norm_ws(p) for p in re.split(r'\n\s*\n', txt)]
    for p in paras:
        if re.search(r'(raised|secured|closed|landed|bagged|acquired)', p) and 40 < len(p) < 600 and not BOILER.search(p):
            out.append(dict(title=p[:250], text=p, kind='deal_list'))
    return out

PROMO_SUBJ = re.compile(r'(firehose problem|never be the same|£250 off|fundamentals behind every LLM|Vos Newsletters|places pour assister|50\+ Angels|Top Tech Journalists|Sifted 250 data|offre exceptionnellement)', re.I)

def main():
    recs = []
    issues = []
    for f in sorted(glob.glob(RAW + '*.txt')):
        s = open(f).read()
        hdr, _, body = s.partition('\n\n')
        h = dict(l.split(': ', 1) for l in hdr.split('\n') if ': ' in l)
        src = source_name(h['FROM'])
        subj = h.get('SUBJECT', '').strip()
        date = h['DATE'][:10]
        tid = h['THREAD'][:8]
        promo = bool(PROMO_SUBJ.search(subj)) or src == 'DeepLearning.AI'
        issue = dict(file=os.path.basename(f), source=src, date=date, subject=subj, thread=tid, promo=promo)
        issues.append(issue)
        if promo:
            continue
        sl = src.lower()
        if sl.startswith('tldr'): its = items_tldr('\n' + body)
        elif src == 'Techmeme': its = items_techmeme(body)
        elif 'term sheet' in sl: its = items_termsheet(body, subj)
        elif 'sifted' in sl: its = items_sifted(body, subj)
        elif 'maddyness' in sl: its = items_maddyness(body, subj)
        elif src == 'AlphaSignal': its = items_alphasignal(body, subj)
        elif src == 'Benedict Evans': its = items_benedict(body)
        elif src == 'Import AI': its = items_importai(body)
        elif 'dragos' in sl: its = items_flag_lines(body, subj)
        elif src == 'EU-Startups': its = items_eustartups(body, subj)
        elif src == 'Newcomer':
            first = norm_ws(body.split('\n\n')[1] if '\n\n' in body else body)[:600]
            first = re.sub(r'View this post on the web at \S+', '', first)
            its = [dict(title=subj, text=first, kind='lead')]
        else: its = items_generic(body, subj)
        # dedupe within issue
        seen = set()
        for it in its:
            key = re.sub(r'\W+', '', it['title'].lower())[:60]
            if key in seen or len(it['title']) < 12:
                continue
            seen.add(key)
            it.update(source=src, date=date, issue_file=issue['file'], issue_subject=subj)
            recs.append(it)
        issue['n_items'] = sum(1 for r in recs if r['issue_file'] == issue['file'])
    json.dump(recs, open(OUT, 'w'), indent=1, ensure_ascii=False)
    json.dump(issues, open('/home/claude/newsviz/data/issues.json', 'w'), indent=1, ensure_ascii=False)
    from collections import Counter
    c = Counter(r['source'] for r in recs)
    print(len(recs), 'items from', sum(1 for i in issues if not i['promo']), 'issues; promo', sum(i['promo'] for i in issues))
    for k, v in c.most_common(): print(v, k)
    for i in issues:
        if not i['promo'] and i.get('n_items', 0) <= 1: print('LOW', i['source'], i['subject'][:60], i.get('n_items'))

if __name__ == '__main__':
    main()
