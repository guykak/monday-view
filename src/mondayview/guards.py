"""Guards: checks that must pass before anything is sent or committed (pitfalls 12, 26, 28-32)."""
import hashlib
import json
import re
from pathlib import Path

from . import config

ALLOWED_COMMIT_PREFIXES = ("history/", "logs/")
TOTAL_PATTERNS = [r"\btotall?ing\b", r"\bin total\b", r"\bcombined (?:total|value)\b", r"\ba total of [$€£]", r"\b(?:sum|aggregate) of\b",
                  r"[$€£]\s?[\d.,]+\s?(?:[MB]|bn|m)\b[^.|]{0,30}\b(?:raised|invested) (?:in all|overall|across)\b"]
TREND_PATTERNS = [r"\btrend(?:s|ing)?\b", r"\bup from last week\b", r"\bdown from last week\b", r"\bweek[- ]on[- ]week\b",
                  r"\bmomentum\b", r"\baccelerat(?:ing|ion|ed|es)\b", r"\bcompared with (?:last|previous) week\b"]


class GuardError(Exception):
    pass


# ---------------------------------------------------------------- send guards

def subject_for(mode, week_label, settings=None):
    s = settings or config.settings()
    return f"{s['subject_prefix']}Monday view {week_label}"


def labels_for(mode, week_label, utc_stamp=None):
    """Pitfall 32: only mv-WNN counts as sent. Test sends can never block a real one."""
    if mode == "scheduled":
        return ["monday-view", f"mv-{week_label}"]
    if mode == "test":
        if not utc_stamp:
            raise GuardError("a test send needs a UTC timestamp for its label")
        return ["monday-view-test", f"mv-test-{week_label}-{utc_stamp}"]
    raise GuardError(f"mode {mode!r} sends nothing")


def already_sent(thread_labels_lists, week_label):
    """True only if a thread carries both `sent` and the real label mv-WNN."""
    real = f"mv-{week_label}".lower()   # AgentMail stores labels in lower case
    return any("sent" in low and real in low
               for low in ([str(l).lower() for l in ls] for ls in thread_labels_lists))


def make_send_plan(mode, week_label, html, text, utc_stamp=None, settings=None):
    s = settings or config.settings()
    plan = {"mode": mode, "week": week_label, "recipient": s.get("recipient") or "",
            "subject": subject_for(mode, week_label, s), "send": mode in ("test", "scheduled"),
            "labels": labels_for(mode, week_label, utc_stamp) if mode in ("test", "scheduled") else [],
            "html_bytes": len(html.encode("utf-8")), "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "text_bytes": len(text.encode("utf-8")), "cc": [], "bcc": []}
    return plan


def check_send(plan, html, text, settings=None):
    """Raise GuardError unless this exact email may be sent (spec §3 step 7)."""
    s = settings or config.settings()
    errs = []
    if plan["mode"] not in ("test", "scheduled") or not plan.get("send"):
        errs.append(f"mode {plan['mode']} must not send")
    if not s.get("recipient"):
        errs.append("recipient is not confirmed in config/settings.yaml")
    elif plan["recipient"] != s["recipient"]:
        errs.append("recipient differs from settings.recipient")
    if plan.get("cc") or plan.get("bcc"):
        errs.append("cc and bcc are never allowed")
    if isinstance(plan["recipient"], (list, tuple)) or "," in str(plan["recipient"]) or ";" in str(plan["recipient"]):
        errs.append("exactly one recipient")
    if s.get("subject_prefix") and not plan["subject"].startswith(s["subject_prefix"]):
        errs.append("subject must start with the test prefix until Phase 2")
    wk = plan["week"]
    if plan["mode"] == "scheduled" and plan["labels"] != ["monday-view", f"mv-{wk}"]:
        errs.append("scheduled labels must be monday-view, mv-WNN")
    if plan["mode"] == "test":
        if any(l == f"mv-{wk}" for l in plan["labels"]) or not any(l.startswith(f"mv-test-{wk}-") for l in plan["labels"]):
            errs.append("test sends use mv-test-… labels, never mv-WNN")
    size = len(html.encode("utf-8"))
    if size >= s["thresholds"]["html_max_bytes"]:
        errs.append(f"HTML is {size} bytes; the limit is {s['thresholds']['html_max_bytes']}")
    if size != plan["html_bytes"] or hashlib.sha256(html.encode("utf-8")).hexdigest() != plan["html_sha256"]:
        errs.append("HTML differs from the send plan")
    if not text or not text.strip():
        errs.append("the plain-text part is missing")
    if re.search(r"<img\b|<script\b|<link\b", html, re.I):
        errs.append("no images, scripts or linked files in the v1 email")
    if errs:
        raise GuardError("; ".join(errs))
    return True


def check_sent(plan, sent_message):
    """Post-send check: compare what AgentMail stored with the plan. Returns a list of mismatches."""
    out = []
    to = sent_message.get("to") or []
    if [t.lower() for t in to] != [plan["recipient"].lower()]:
        out.append("recipient")
    if sent_message.get("cc") or sent_message.get("bcc"):
        out.append("cc/bcc present")
    if sent_message.get("subject") != plan["subject"]:
        out.append("subject")
    h = sent_message.get("html") or ""
    if hashlib.sha256(h.encode("utf-8")).hexdigest() != plan["html_sha256"]:
        out.append("html hash")
    return out


# ---------------------------------------------------------------- commit guard

def check_staged_paths(paths, mode="scheduled"):
    """Scheduled and test runs commit only under history/ and logs/, and never a raw body."""
    bad = [p for p in paths if not p.startswith(ALLOWED_COMMIT_PREFIXES)]
    raw = [p for p in paths if re.search(r"(^|/)(raw|run|cache|scratch)/|\.(eml|mbox)$|(^|/)bodies/", p)]
    if mode in ("scheduled", "test") and bad:
        raise GuardError("a run may commit only under history/ and logs/: " + ", ".join(bad[:5]))
    if raw:
        raise GuardError("newsletter bodies are never committed: " + ", ".join(raw[:5]))
    return True


# ---------------------------------------------------------------- content guards

def word_count(md):
    return len(md.split())


def check_words(md, settings=None):
    th = (settings or config.settings())["thresholds"]
    n = word_count(md)
    if not th["words_min"] <= n <= th["words_max"]:
        raise GuardError(f"{n} words; the view must be {th['words_min']}-{th['words_max']}")
    return n


def find_totals(text):
    """Pitfall 12: no dollar totals anywhere."""
    return [m.group(0) for p in TOTAL_PATTERNS for m in re.finditer(p, text, re.I)]


def find_trend_claims(text, weeks_of_history=0, settings=None):
    """Pitfall 26: no trend claim before 8 weeks of history, and never from one storyline."""
    th = (settings or config.settings())["thresholds"]
    if weeks_of_history >= th["min_weeks_for_trends"]:
        return []
    return [m.group(0) for p in TREND_PATTERNS for m in re.finditer(p, text, re.I)]


NUM = r"(?<![\w.])[~$€£]?\d[\d,]*(?:\.\d+)?"


def numbers_in(text):
    """Figures in a text, normalised: '$81.3bn' -> '81.3', '+34%' -> '34', '1,000' -> '1000'."""
    out = []
    for m in re.finditer(NUM, text or ""):
        tok = re.sub(r"[~$€£,]", "", m.group(0)).rstrip(".")
        if tok:
            out.append(tok)
    return out


def unsupported_numbers(text, quotes, allowed=()):
    """Rule 4: every number in editor-written text must appear in a cited source quote
    (or be a number Python computed, passed in `allowed`). Dates like '18 Nov' are skipped."""
    src = " ".join(quotes)
    have = set(numbers_in(src)) | {str(a) for a in allowed}
    have |= {h.rstrip("0").rstrip(".") for h in have if "." in h}
    missing = []
    for m in re.finditer(NUM, text or ""):
        tok = re.sub(r"[~$€£,]", "", m.group(0)).rstrip(".")
        after = text[m.end():m.end() + 5]
        if re.match(r"\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", after):
            continue
        if tok not in have and tok.rstrip("0").rstrip(".") not in have:
            missing.append(m.group(0))
    return missing


def check_editorial(editorial, events, computed_numbers=()):
    """Every sourced line the editor wrote: its quotes must exist in the extraction (same file),
    and its numbers must appear in those quotes. Returns a list of problems (empty = pass)."""
    known = {}
    for ev in events:
        for m in ev["mentions"]:
            known.setdefault(m["file"], set()).add(m["quote"])
        for f in ev["facts"]:
            known.setdefault(f["file"], set()).add(f["quote"])
    problems = []

    def norm(s):
        return re.sub(r"\s+", " ", (s or "")).strip().lower()

    def found(s):
        """The cited words must be part of a quote the extraction holds for that same issue."""
        q = norm(s.get("quote"))
        return bool(q) and any(q in norm(k) for k in known.get(s.get("file"), set()))

    def check_item(where, text, sources):
        quotes = []
        for s in sources or []:
            if not found(s):
                problems.append(f"{where}: quote not found in extraction for {s.get('file')}: {str(s.get('quote'))[:60]}")
            quotes.append(s.get("quote") or "")
        miss = unsupported_numbers(text, quotes, computed_numbers)
        if miss:
            problems.append(f"{where}: numbers without a source quote: {miss}")

    b1 = editorial.get("block1") or {}
    for n, f in enumerate(b1.get("facts", [])):
        check_item(f"block1.facts[{n}]", f["text"], f.get("sources"))
    for key in ("for_us",):
        if b1.get(key):
            miss = unsupported_numbers(b1[key], [], computed_numbers)
            if miss:
                problems.append(f"block1.{key}: numbers not allowed here: {miss}")
    if editorial.get("headline"):
        allq = [s.get("quote") or "" for f in b1.get("facts", []) for s in f.get("sources", [])]
        miss = unsupported_numbers(editorial["headline"], allq, computed_numbers)
        if miss:
            problems.append(f"headline: numbers without a source: {miss}")
    b5 = editorial.get("block5") or {}
    if b5.get("text"):
        check_item("block5", b5["text"], b5.get("sources"))
        if not re.search(r"per (?:million )?(?:input|output|token|task)|per-token|per-task", b5["text"], re.I):
            problems.append("block5: the price measure (per token, per task) is not named")
        if not b5.get("sources"):
            problems.append("block5: no source")
    for eid, note in (editorial.get("block4_notes") or {}).items():
        check_item(f"block4_notes[{eid}]", note.get("text", ""), note.get("sources"))
    for name, note in (editorial.get("fund_notes") or {}).items():
        check_item(f"fund_notes[{name}]", note.get("text", ""), note.get("sources"))
    for name, text in (editorial.get("descriptions") or {}).items():
        if numbers_in(text):
            problems.append(f"descriptions[{name}]: a description carries no numbers")
    all_text = " ".join([editorial.get("headline") or "", b1.get("for_us") or "", b5.get("text") or ""]
                        + [f["text"] for f in b1.get("facts", [])])
    for t in find_totals(all_text):
        problems.append(f"dollar total: {t}")
    return problems


def budget_check(n_issues, n_failed, agents_used, reopens, minutes, settings=None):
    """Spec §5: returns (action, reasons). action is 'ok' or 'hold'."""
    b = (settings or config.settings())["budgets"]
    reasons = []
    if n_issues and n_failed / n_issues > b["max_extract_fail_share"]:
        reasons.append(f"extraction failed on {n_failed} of {n_issues} issues")
    if agents_used > n_issues + b["max_agents_over_issues"]:
        reasons.append(f"{agents_used} sub-agent calls is over the limit")
    if reopens > b["max_factcheck_reopens"]:
        reasons.append(f"{reopens} fact-check re-opens is over the limit")
    if minutes > b["max_wall_minutes"]:
        reasons.append(f"{minutes:.0f} minutes is over the wall-time limit")
    return ("hold" if reasons else "ok"), reasons


def factcheck_action(report, settings=None):
    """Spec §5: fail on block 1, or more than 20% of the numbers in blocks 1-4 -> hold.
    Otherwise drop the failing items and rebuild (pitfall 29), then re-check once."""
    b = (settings or config.settings())["budgets"]
    checks = report.get("checks", [])
    fails = [c for c in checks if c.get("verdict") == "fail"]
    if any(str(c.get("block")) == "1" for c in fails):
        return "hold", "the fact-check failed block 1"
    nums = [c for c in checks if str(c.get("block")) in ("1", "2", "3", "4") and c.get("kind") in ("number", "dots")]
    if nums and sum(1 for c in nums if c.get("verdict") == "fail") / len(nums) > b["max_factcheck_fail_share"]:
        return "hold", "more than 20% of the numbers failed the fact-check"
    return ("rebuild" if fails else "ok"), f"{len(fails)} items failed"
