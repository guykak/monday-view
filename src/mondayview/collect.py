"""Sender filter, family mapping and issue counts (pitfalls 22, 27, 34). Metadata only: no bodies."""
import hashlib
import re
from statistics import median

from . import config
from .week import parse_ts


def _addr(s):
    m = re.search(r"<([^>]+)>", s or "")
    return (m.group(1) if m else (s or "")).strip().lower()


def classify(sender_email, sender_name="", subject="", fams=None):
    """-> (family, letter) for a newsletter issue, or (None, reason) for anything else.
    Only senders listed under `families` are ever collected."""
    fams = fams or config.families()
    addr = _addr(sender_email)
    for pat in fams.get("ignore_subject_patterns", []):
        if re.search(pat, subject or ""):
            return None, "ignored subject"
    for ig in fams.get("ignore_senders", []):
        ig = ig.lower()
        if addr == ig or (ig.startswith("@") and addr.endswith(ig)):
            return None, "ignored sender"
    for fam, spec in fams["families"].items():
        if addr in [s.lower() for s in spec["senders"]]:
            letters = spec.get("letters_by_sender_name") or []
            name = (sender_name or "").strip().lower()
            letter = fam
            # longest letter name first, so "Maddyness IA" is not read as "Maddyness"
            for cand in sorted(letters, key=len, reverse=True):
                if cand.lower() in name:
                    letter = cand
                    break
            return fam, letter
    return None, "unknown sender"


def out_name(issue_date, family, message_id):
    """<date>_<family>_<hash8>.json; never the raw message ID (it contains <, > and @)."""
    h = hashlib.sha256(message_id.encode()).hexdigest()[:8]
    slug = re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")
    return f"{issue_date}_{slug}_{h}.json"


def build_issue_list(threads, window=None, processed_label_prefix="mv-processed-", fams=None):
    """threads: list of dicts with sender, sender_email, subject, date (ISO), lastMessageId, labels.
    Returns (issues, skipped). Skips anything outside the window, already processed, or not a
    listed newsletter sender. Skipped mail is logged by sender and subject only."""
    issues, skipped, seen = [], [], set()
    for t in threads:
        ts = parse_ts(t["date"])
        mid = t.get("lastMessageId") or t.get("messageId")
        meta = {"sender": t.get("sender"), "sender_email": t.get("sender_email"), "subject": t.get("subject")}
        if window and not (window[0] <= ts < window[1]):
            skipped.append({**meta, "reason": "outside window"})
            continue
        if any(l.startswith(processed_label_prefix) for l in t.get("labels", [])):
            skipped.append({**meta, "reason": "already processed"})
            continue
        if mid in seen:
            skipped.append({**meta, "reason": "duplicate thread"})
            continue
        fam, letter = classify(t.get("sender_email"), t.get("sender"), t.get("subject"), fams)
        if fam is None:
            skipped.append({**meta, "reason": letter})
            continue
        seen.add(mid)
        issues.append({"message_id": mid, "family": fam, "letter": letter, "sent_at": t["date"],
                       "issue_date": t["date"][:10], "subject": t.get("subject")})
    issues.sort(key=lambda i: (i["sent_at"], i["message_id"]))
    return issues, skipped


def footer_counts(issues, fams=None):
    """Pitfall 22: counts come from the collected list. Names families and letters that sent none."""
    fams = fams or config.families()
    per_family, per_letter = {}, {}
    for i in issues:
        per_family[i["family"]] = per_family.get(i["family"], 0) + 1
        per_letter[i.get("letter") or i["family"]] = per_letter.get(i.get("letter") or i["family"], 0) + 1
    silent_families = [f for f in fams["families"] if f not in per_family]
    silent_letters = []
    for f, spec in fams["families"].items():
        if f in silent_families:
            continue
        for l in spec.get("report_silent_letters", []):
            if l not in per_letter:
                silent_letters.append(l)
    ordered = sorted(per_family.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"total": len(issues), "per_family": dict(ordered), "per_letter": per_letter,
            "silent_families": silent_families, "silent_letters": silent_letters,
            "silent_deal_carrying": [f for f in silent_families if fams["families"][f].get("deal_carrying")]}


def usual_issues(recent_counts=None):
    """Pitfall 34: usual = median of recent weeks, seeded from W45-W47."""
    counts = list(recent_counts or []) or config.settings()["budgets"]["usual_issues_seed"]
    return median(counts)


def volume_check(n_issues, recent_counts=None):
    b = config.settings()["budgets"]
    usual = usual_issues(recent_counts)
    if n_issues < b["min_issue_share"] * usual:
        return "hold", f"{n_issues} issues is under half the usual {usual:g}"
    if n_issues > b["max_issues"]:
        return "hold", f"{n_issues} issues is over the limit of {b['max_issues']}"
    return "ok", f"{n_issues} issues (usual {usual:g})"
