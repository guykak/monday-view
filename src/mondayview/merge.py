"""Merge stories from many issues into events, and count source families (pitfalls 1-3, 14-19).

A dot is one family carrying an event. Families come only from extracted entities: nothing here
searches issue text, so "Mountain View" can never match MountAIn, nor "pluralisme" Plural.
"""
import re
import unicodedata
from collections import Counter
from datetime import date

from . import config
from .money import to_usd
from .validate import COUNTED_ROUND_STATUS, TALKS_STATUS
from .week import story_date as fallback_story_date

LEGAL = {"inc", "ltd", "limited", "llc", "sas", "sa", "gmbh", "ag", "bv", "nv", "plc", "corp",
         "corporation", "co", "company", "oy", "ab", "as", "srl", "spa", "the"}
# Words a newsletter may add or drop after a company's name. Dropped only when a name remains.
GENERIC_TAIL = {"ai", "labs", "lab", "technologies", "technology", "tech", "aerospace", "systems",
                "robotics", "health", "group", "holdings", "software", "therapeutics", "bio",
                "aircraft", "space", "energy", "capital", "ventures", "partners", "vc"}

# Order in which a status is "further along". Used to pick the latest status of an event.
STATUS_RANK = {
    "rumour": 0, "planned": 1, "in_talks": 2, "bid": 3, "filed": 3, "launched": 3, "reported": 3,
    "first_close": 4, "announced": 5, "signed": 5, "priced": 5, "closed": 6, "final_close": 6,
    "completed": 7, "listed": 7, "refused": 8, "abandoned": 8,
}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_tokens(name):
    """Normalise case, accents and punctuation. 'Stryx AI' and 'STRYX.ai' give the same tokens."""
    s = strip_accents(name or "").lower().replace("&", " and ")
    s = re.sub(r"['’`]s\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [t for t in s.split() if t not in LEGAL]
    return toks


def name_keys(name):
    """Keys under which a name may match: full, squashed ('model ml' = 'modelml'),
    and with generic tail words removed ('tiberius aerospace' = 'tiberius')."""
    toks = norm_tokens(name)
    if not toks:
        return set()
    keys = {" ".join(toks), "".join(toks)}
    core = list(toks)
    while len(core) > 1 and core[-1] in GENERIC_TAIL:
        core = core[:-1]
    if core != toks and len("".join(core)) >= 4:
        keys.add(" ".join(core))
        keys.add("".join(core))
    return keys


def story_keys(story):
    keys = set()
    for n in [story.get("company")] + list(story.get("aliases") or []):
        if n:
            keys |= name_keys(n)
    return keys


def names_match(a, b):
    return bool(story_keys(a) & story_keys(b))


def _status_class(story):
    t, s = story["event_type"], story["status"]
    if t == "round":
        if s in COUNTED_ROUND_STATUS:
            return "closed"
        return "talks"
    return "any"


def _usd(story, field="equity"):
    if field == "equity":
        amt, cur = story.get("equity_amount"), story.get("currency")
        if amt is None and story.get("mixed_total"):
            amt, cur = story["mixed_total"]["amount"], story["mixed_total"]["currency"]
    elif field == "fund":
        f = story.get("fund_size") or {}
        amt, cur = f.get("amount"), f.get("currency")
    else:
        return None
    return to_usd(amt, cur)


def _amounts_compatible(a, b, field, tol):
    x, y = _usd(a, field), _usd(b, field)
    if x is None or y is None:
        return True
    if abs(x - y) <= tol * max(x, y):
        return True
    # one source giving the equity part and another the equity + other-finance total (Hone, Elysian)
    extras = []
    for s in (a, b):
        tot = to_usd(s.get("equity_amount"), s.get("currency")) or 0
        for o in s.get("other_finance") or []:
            tot += to_usd(o.get("amount"), o.get("currency")) or 0
        extras.append(tot)
        if s.get("mixed_total"):
            extras.append(to_usd(s["mixed_total"]["amount"], s["mixed_total"]["currency"]))
    return any(e and abs(e - v) <= tol * max(e, v) for e in extras for v in (x, y) if e != v)


def same_event(a, b, tol=None, window=None):
    """Two stories are one event when type, entity, status class, amount and date all agree."""
    th = config.settings()["thresholds"]
    tol = th["merge_amount_tolerance"] if tol is None else tol
    window = th["merge_window_days"] if window is None else window
    if a["event_type"] != b["event_type"]:
        return False
    if abs((a["_date"] - b["_date"]).days) > window:
        return False
    t = a["event_type"]
    if t == "acquisition":
        ka, kb = story_keys(a), story_keys(b)
        qa, qb = name_keys(a.get("acquirer") or ""), name_keys(b.get("acquirer") or "")
        if ka & kb:
            return not (qa and qb) or bool(qa & qb)
        return bool(ka & qb) and bool(kb & qa)      # target and acquirer swapped
    if not a.get("company") or not b.get("company"):
        return False
    if not names_match(a, b):
        # "Tendrils" and "Tendrils Compute": accept a leading-words match only for rounds whose
        # amounts are both stated and equal. Never on the name alone.
        ta, tb = norm_tokens(a["company"]), norm_tokens(b["company"])
        short, long_ = sorted((ta, tb), key=len)
        if not (t == "round" and short and long_[:len(short)] == short and len("".join(short)) >= 5
                and _status_class(a) == _status_class(b)
                and _usd(a) is not None and _usd(b) is not None and abs(_usd(a) - _usd(b)) <= 0.02 * max(_usd(a), _usd(b))):
            return False
    if t == "round":
        if _status_class(a) != _status_class(b):
            return False                              # talks never merge into a closed round
        return _amounts_compatible(a, b, "equity", tol)
    if t == "fund":
        return _amounts_compatible(a, b, "fund", tol)
    if t == "other":
        return (a.get("subtype") or "other") == (b.get("subtype") or "other")
    return True                                       # ipo, pricing: one event per company


def _most_common(values, prefer=None):
    vals = [v for v in values if v not in (None, "", "unstated")]
    if not vals:
        return None
    c = Counter(vals)
    top = max(c.values())
    best = [v for v in c if c[v] == top]
    if prefer:
        for v in prefer:
            if v in best:
                return v
    return sorted(best, key=lambda v: vals.index(v))[0]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", strip_accents(s or "x").lower()).strip("-") or "x"


def flatten(issues, cadence_of=None):
    """Issue files -> one flat list of mentions with their own date (pitfalls 1, 4)."""
    fams = config.families()["families"]
    out = []
    for iss in issues:
        spec = fams.get(iss["family"], {})
        cad = (cadence_of or {}).get(iss["family"]) or spec.get("cadence", "daily")
        if iss.get("letter") in (spec.get("weekly_letters") or []):
            cad = "weekly"
        for st in iss["stories"]:
            if st.get("timing") == "background":
                continue                              # an older event cited as context: never this week's
            d, basis = fallback_story_date(st, iss["issue_date"], iss["family"], cad)
            m = dict(st)
            m.update(_date=d, _date_basis=basis, _family=iss["family"], _letter=iss.get("letter"),
                     _file=iss.get("_file"), _message_id=iss["message_id"], _sent_at=iss.get("sent_at") or "",
                     _issue_date=iss["issue_date"])
            out.append(m)
    return out


def cluster(mentions):
    parent = list(range(len(mentions)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_type = {}
    for i, m in enumerate(mentions):
        by_type.setdefault(m["event_type"], []).append(i)
    for idxs in by_type.values():
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                i, j = idxs[x], idxs[y]
                if find(i) != find(j) and same_event(mentions[i], mentions[j]):
                    parent[find(j)] = find(i)
    groups = {}
    for i in range(len(mentions)):
        groups.setdefault(find(i), []).append(mentions[i])
    return list(groups.values())


def _pick_amount(ms):
    """Equity amount with the most family support, in its original currency."""
    votes = {}
    for m in ms:
        if m.get("equity_amount") is not None and m.get("currency"):
            votes.setdefault((m["equity_amount"], m["currency"], m.get("amount_qualifier") or "exact"), set()).add(m["_family"])
    if not votes:
        return None, None, None
    best = sorted(votes.items(), key=lambda kv: (-len(kv[1]), kv[0][1] == "USD", -kv[0][0]))[0][0]
    return best


def _pick_money(ms, field):
    votes = {}
    for m in ms:
        v = m.get(field)
        if v and v.get("amount"):
            votes.setdefault((v["amount"], v["currency"], v.get("qualifier") or "exact"), set()).add(m["_family"])
    if not votes:
        return None
    (amt, cur, q) = sorted(votes.items(), key=lambda kv: (-len(kv[1]), -kv[0][0]))[0][0]
    return {"amount": amt, "currency": cur, "qualifier": q}


def build_event(ms):
    """One event from its mentions. Dates and first-seen come from each story, never the cluster."""
    ms = sorted(ms, key=lambda m: (m["_sent_at"], m["_file"] or "", m.get("_idx", 0)))
    t = ms[0]["event_type"]
    families = sorted({m["_family"] for m in ms})
    names = [m["company"] for m in ms if m.get("company")]
    company = _most_common([m["company"] for m in ms if m.get("company") and m["mention_type"] != "passing"] or names)
    def reached(group):
        """When something happened, from its own stories: the earliest stated date; if no story
        states one, the date implied by the first issue to carry it (by send time)."""
        stated = [m["_date"] for m in group if m["_date_basis"] == "stated"]
        return min(stated) if stated else group[0]["_date"]

    event_date = reached(ms)
    # status history: each status at the date its own stories give it (pitfall 2)
    hist = {}
    for s in dict.fromkeys(m["status"] for m in ms):
        group = [m for m in ms if m["status"] == s]
        hist[s] = {"status": s, "date": reached(group), "family": group[0]["_family"]}
    status_history = sorted(hist.values(), key=lambda h: (h["date"], STATUS_RANK.get(h["status"], 3)))
    if t in ("acquisition", "fund"):
        # the status most families report; on a tie, the less advanced one (an agreed sale is not a completed one)
        fam = {s: len({m["_family"] for m in ms if m["status"] == s}) for s in hist}
        status = min(hist, key=lambda s: (-fam[s], STATUS_RANK.get(s, 3)))
    else:
        status = max(hist, key=lambda s: (STATUS_RANK.get(s, 3), hist[s]["date"]))
    hq = []
    hq_votes = Counter()
    for m in ms:
        for h in m.get("hq") or []:
            hq_votes[(h.get("city"), h["country"])] += 1
    cities_by_country = {}
    for (city, country), n in hq_votes.items():
        if city:
            cities_by_country.setdefault(country, []).append(city)
    any_city = bool(cities_by_country)
    for (city, country), n in sorted(hq_votes.items(), key=lambda kv: -kv[1]):
        if city is None and any_city:
            continue                                  # a bare country adds nothing once a source names the city
        if not any(h["country"] == country and strip_accents(h["city"] or "").lower() == strip_accents(city or "").lower() for h in hq):
            hq.append({"city": city, "country": country, "mentions": n})
    amt, cur, qual = _pick_amount(ms) if t == "round" else (None, None, None)
    other_finance, seen = [], set()
    for m in ms:
        for o in m.get("other_finance") or []:
            k = (o["type"], o.get("amount"), o.get("currency"))
            if k not in seen:
                seen.add(k)
                other_finance.append({"type": o["type"], "amount": o.get("amount"), "currency": o.get("currency"), "note": o.get("note")})
    mixed = _most_common([tuple(sorted(m["mixed_total"]["includes"])) for m in ms if m.get("mixed_total")])
    mixed_total = next((m["mixed_total"] for m in ms if m.get("mixed_total")), None)
    leads = [l for l, _ in Counter(l for m in ms for l in (m.get("leads") or [])).most_common()]
    best = max(ms, key=lambda m: ({"story": 2, "deal_list": 1, "passing": 0}[m["mention_type"]], len(m.get("description") or "")))
    facts = []
    for m in ms:
        for f in m.get("facts") or []:
            facts.append({"date": f.get("date"), "text": f["text"], "quote": f["quote"], "family": m["_family"],
                          "file": m["_file"], "message_id": m["_message_id"]})
    ev = {
        "id": f"{t}:{_slug(company or ms[0]['headline'][:40])}:{event_date.isoformat()}" + (":talks" if t == "round" and _status_class(ms[0]) == "talks" else ""),
        "event_type": t, "subtype": _most_common([m.get("subtype") for m in ms]),
        "company": company, "aliases": sorted(set(names) - {company}),
        "description": best.get("description"), "headline": best["headline"],
        "event_date": event_date, "first_seen": ms[0]["_sent_at"], "first_family": ms[0]["_family"],
        "status": status, "status_history": status_history,
        "families": families, "n_families": len(families),
        "hq": hq,
        "stage": _most_common([m.get("stage") for m in ms]) or ("unstated" if t == "round" else None),
        "stage_as_written": _most_common([m.get("stage_as_written") for m in ms]),
        "is_combined_round": any(m.get("is_combined_round") for m in ms),
        "equity_amount": amt, "currency": cur, "amount_qualifier": qual,
        "other_finance": other_finance, "mixed_total": mixed_total if mixed else None,
        "valuation": _pick_money(ms, "valuation"),
        "valuation_basis": _most_common([m.get("valuation_basis") for m in ms if m.get("valuation")]),
        "leads": leads,
        "acquirer": _most_common([m.get("acquirer") for m in ms]),
        "acquirer_type": _most_common([m.get("acquirer_type") for m in ms]),
        "stake": _most_common([m.get("stake") for m in ms]),
        # the softer wording is kept only if every story that words it agrees the event is not past it
        "status_note": _most_common([m.get("status_note") for m in ms if m["status"] == status
                                     and (m.get("status_note") or "").strip().lower() in config.settings()["thresholds"]["status_notes"]]),
        # a lead is a founder if a story marks it so, or if another story of the same round names that
        # person in its founder background (Sifted lists the lead, Maddyness says who he is)
        "founder_leads": sorted({l for m in ms for l in (m.get("founder_leads") or [])}
                                | {l for l in leads if any(l.lower() in (m.get("founder_background") or "").lower() for m in ms)}),
        "price": _pick_money(ms, "price"),
        "consideration": _most_common([m.get("consideration") for m in ms]),
        "confirmed_by_company": any(m.get("confirmed_by_company") for m in ms),
        "is_pe_buy_and_build": any(m.get("is_pe_buy_and_build") for m in ms),
        "fund_name": _most_common([m.get("fund_name") for m in ms]),
        "fund_size": _pick_money(ms, "fund_size"),
        "fund_strategy": _most_common([m.get("fund_strategy") for m in ms if m.get("fund_strategy") != "other"]) or _most_common([m.get("fund_strategy") for m in ms]),
        "fund_geography": _most_common([m.get("fund_geography") for m in ms]),
        "fund_focus": _most_common([m.get("fund_focus") for m in ms]),
        "tech_area": _most_common([m.get("tech_area") for m in ms]),
        "tech_area_votes": dict(Counter(m.get("tech_area") for m in ms if m.get("tech_area"))),
        "founder_background": _most_common([m.get("founder_background") for m in ms]),
        "non_raise_figures": [f for m in ms for f in (m.get("non_raise_figures") or [])],
        "n_reprints": sum(1 for m in ms if m.get("is_press_release_reprint")),
        "facts": facts,
        "mentions": [{"family": m["_family"], "letter": m["_letter"], "file": m["_file"], "message_id": m["_message_id"],
                      "sent_at": m["_sent_at"], "issue_date": m["_issue_date"], "story_date": m["_date"],
                      "date_basis": m["_date_basis"], "status": m["status"], "mention_type": m["mention_type"],
                      "headline": m["headline"], "quote": m["quote"],
                      "equity_amount": m.get("equity_amount"), "currency": m.get("currency"),
                      "is_press_release_reprint": bool(m.get("is_press_release_reprint"))} for m in ms],
    }
    return ev


def attach_deal_mentions(mentions):
    """A bare 'deal_mention' (a company named in a deals headline, no detail) takes the type of the
    one deal that company has in the same window. With no such deal, or more than one, it is left out:
    it never creates an event and never picks between two (pitfall 17)."""
    window = config.settings()["thresholds"]["merge_window_days"]
    real = [m for m in mentions if m["event_type"] in ("round", "acquisition", "ipo")]
    out, unattached = [], []
    for m in mentions:
        if m["event_type"] != "deal_mention":
            out.append(m)
            continue
        keys = story_keys(m)
        cands = [r for r in real if keys & (story_keys(r) | name_keys(r.get("acquirer") or "")) and abs((r["_date"] - m["_date"]).days) <= window
                 and not (r["event_type"] == "round" and _status_class(r) == "talks")]
        groups = []
        for r in cands:
            if not any(same_event(r, g) for g in groups):
                groups.append(r)
        if len(groups) != 1:
            unattached.append(m)
            continue
        ref = groups[0]
        a = dict(m)
        a.update(event_type=ref["event_type"], status=ref["status"], company=ref["company"], mention_type="deal_list",
                 _date=ref["_date"], _date_basis="attached")
        for k in ("equity_amount", "currency", "amount_qualifier", "mixed_total", "valuation", "price", "fund_size", "acquirer"):
            a[k] = ref.get(k) if k in ("acquirer",) else None
        a.update(hq=[], leads=[], other_finance=[], facts=[], stage=None, tech_area=None, description=None, founder_background=None)
        out.append(a)
    return out, unattached


def merge(issues):
    mentions, _ = attach_deal_mentions(flatten(issues))
    events = [build_event(g) for g in cluster(mentions)]
    # ids must be unique
    seen = Counter()
    for e in sorted(events, key=lambda e: (e["id"], e["first_seen"])):
        seen[e["id"]] += 1
        if seen[e["id"]] > 1:
            e["id"] += f":{seen[e['id']]}"
    events.sort(key=lambda e: (e["event_type"], -e["n_families"], e["company"] or "", e["id"]))
    return events


def first_family(event):
    """Pitfall 7: 'who was first' is decided by send timestamp, never by date alone."""
    m = min(event["mentions"], key=lambda m: m["sent_at"])
    return m["family"], m["sent_at"]


def is_europe(event):
    eu = set(config.settings()["europe_countries"])
    return any(h["country"] in eu for h in event["hq"])


def jsonable(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(obj)
    return obj
