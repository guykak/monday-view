"""Validate extracted issue files and apply the field rules that guard the money pitfalls (3, 8-10)."""
import json
import re
from functools import lru_cache
from pathlib import Path

import jsonschema

from . import config

COUNTED_ROUND_STATUS = {"closed", "announced"}
TALKS_STATUS = {"in_talks", "rumour", "planned"}
NON_RAISE_WORDS = r"(run[- ]?rate|annuali[sz]ed|\bARR\b|revenue|sales|bookings|trading volume)"
RAISE_WORDS = r"(rais|secur|clos|funding|round|invest|financing|lev[ée]|backing|inject|pocket|land|bag|nab|scor|collect|get|got)"


@lru_cache(maxsize=1)
def schema():
    return json.loads((config.ROOT / "schemas" / "story.schema.json").read_text())


def schema_errors(issue):
    v = jsonschema.Draft202012Validator(schema())
    return [f"{'/'.join(map(str, e.path))}: {e.message[:160]}" for e in v.iter_errors(issue)]


def _amount_tokens(amount):
    """Ways a figure may be written in a quote: 5000000000 -> '5', 7300000 -> '7.3' / '7,3'."""
    out = set()
    for div in (1e9, 1e6, 1e3, 1):
        v = amount / div
        if v >= 1:
            s = f"{v:.3f}".rstrip("0").rstrip(".")
            out.add(s)
            out.add(s.replace(".", ","))
            break
    return out


def looks_like_non_raise(quote, amount):
    """Pitfall 10: is `amount` in this quote a revenue / ARR / run-rate figure rather than a raise?
    True when the number sits next to a non-raise word and no raise word is nearer."""
    if not quote or not amount:
        return False
    for tok in _amount_tokens(amount):
        for m in re.finditer(r"(?<![\d.,])" + re.escape(tok) + r"(?![\d])", quote):
            window = quote[max(0, m.start() - 60): m.end() + 60]
            if re.search(NON_RAISE_WORDS, window, re.I):
                before = quote[max(0, m.start() - 60): m.start()]
                after = quote[m.end(): m.end() + 60]
                nr = min([len(before) - x.end() for x in re.finditer(NON_RAISE_WORDS, before, re.I)] +
                         [x.start() for x in re.finditer(NON_RAISE_WORDS, after, re.I)] or [999])
                rz = min([len(before) - x.end() for x in re.finditer(RAISE_WORDS, before, re.I)] +
                         [x.start() for x in re.finditer(RAISE_WORDS, after, re.I)] or [999])
                if nr < rz:
                    return True
    return False


def clean_story(story):
    """Return (story, flags). Never raises a figure's standing: it only demotes doubtful ones."""
    s = dict(story)
    flags = []
    s.setdefault("aliases", [])
    s.setdefault("hq", [])
    s.setdefault("leads", [])
    s.setdefault("other_finance", [])
    s.setdefault("facts", [])
    s.setdefault("non_raise_figures", [])
    if s["event_type"] == "round":
        s.setdefault("stage", "unstated")
        if s.get("stage") is None:
            s["stage"] = "unstated"
        amt = s.get("equity_amount")
        if amt and looks_like_non_raise(s.get("quote"), amt):
            s["non_raise_figures"] = s["non_raise_figures"] + [{"kind": "other", "text": f"{amt:g} {s.get('currency')} (was read as a raise)"}]
            s["equity_amount"] = None
            flags.append("amount_was_non_raise")
        val = s.get("valuation")
        if val and amt and val.get("amount") == amt and not re.search(r"valu", s.get("quote", ""), re.I):
            s["valuation"] = None
            flags.append("valuation_equal_to_raise_dropped")
        if s.get("amount_qualifier") == "up_to" and s["status"] in COUNTED_ROUND_STATUS:
            # "up to $5B" is a ceiling under negotiation, not a closed amount (B1: Cohere)
            s["status"] = "in_talks"
            flags.append("up_to_amount_treated_as_talks")
        if s.get("tech_area") not in config.taxonomy():
            if s.get("tech_area") is not None:
                flags.append("unknown_tech_area")
            s["tech_area"] = "other"
        if s.get("equity_amount") is not None and not s.get("currency"):
            s["equity_amount"] = None
            flags.append("amount_without_currency")
    if len(s.get("quote", "")) > config.settings()["thresholds"]["quote_max_chars"]:
        s["quote"] = s["quote"][:300]
        flags.append("quote_truncated")
    return s, flags


INCLUDE_WORDS = [("equity", "equity"), ("grant", "grant"), ("public funding", "grant"), ("subsid", "grant"), ("debt", "debt"),
                 ("loan", "debt"), ("customer", "customer_value_fund"), ("secondar", "secondary")]


def repair(issue):
    """Mechanical repairs of small format slips, each one flagged. Nothing here changes a figure.
    - a quote over 300 characters is cut to its first 300 (still verbatim);
    - mixed_total.includes given as words ("grants and equity") becomes a list."""
    flags = []
    for n, st in enumerate(issue.get("stories") or []):
        if not isinstance(st, dict):
            continue
        if isinstance(st.get("quote"), str) and len(st["quote"]) > 300:
            st["quote"] = st["quote"][:300]
            flags.append(f"{n}:quote_cut")
        for f in st.get("facts") or []:
            if isinstance(f, dict) and isinstance(f.get("quote"), str) and len(f["quote"]) > 300:
                f["quote"] = f["quote"][:300]
                flags.append(f"{n}:fact_quote_cut")
            if isinstance(f, dict) and isinstance(f.get("text"), str) and len(f["text"]) > 240:
                f["text"] = f["text"][:240]
                flags.append(f"{n}:fact_text_cut")
        mt = st.get("mixed_total")
        if isinstance(mt, dict) and isinstance(mt.get("includes"), str):
            words = mt["includes"].lower()
            inc = []
            for needle, kind in INCLUDE_WORDS:
                if needle in words and kind not in inc:
                    inc.append(kind)
            if "private" in words and "equity" not in inc:
                inc.append("equity")
            mt["includes"] = inc or ["other"]
            flags.append(f"{n}:mixed_includes_parsed")
        if isinstance(st.get("description"), str) and len(st["description"]) > 120:
            st["description"] = st["description"][:120]
        if isinstance(st.get("headline"), str) and len(st["headline"]) > 200:
            st["headline"] = st["headline"][:200]
    return flags


def load_issue(path):
    """-> (issue or None, errors, flags). An issue that fails the schema is not used."""
    path = Path(path)
    try:
        issue = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, [f"not JSON: {e}"], []
    flags = repair(issue) if isinstance(issue, dict) else []
    errs = schema_errors(issue)
    if errs:
        return None, errs, []
    stories = []
    for n, st in enumerate(issue["stories"]):
        st, fl = clean_story(st)
        st["_idx"] = n
        stories.append(st)
        flags += [f"{n}:{f}" for f in fl]
    issue = dict(issue, stories=stories, _file=path.name)
    return issue, [], flags


def load_dir(folder, expected=None):
    """Load every issue file in a folder. `expected` (list of {file, family, issue_date, message_id})
    pins the metadata to the collected list, so a wrong family or date in a file cannot leak in."""
    issues, failed, flags = [], {}, {}
    by_file = {e["file"]: e for e in (expected or [])}
    names = sorted(by_file) if expected else sorted(p.name for p in Path(folder).glob("*.json"))
    for name in names:
        p = Path(folder) / name
        if not p.exists():
            failed[name] = ["missing"]
            continue
        issue, errs, fl = load_issue(p)
        if errs:
            failed[name] = errs
            continue
        e = by_file.get(name)
        if e:
            for k in ("family", "issue_date", "message_id", "letter"):
                if e.get(k):
                    issue[k] = e[k]
            if e.get("received") and not issue.get("sent_at"):
                issue["sent_at"] = e["received"]
        issues.append(issue)
        if fl:
            flags[name] = fl
    return issues, failed, flags
