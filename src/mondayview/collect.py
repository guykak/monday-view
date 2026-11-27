"""Sender filter, family mapping and issue counts (pitfalls 22, 27, 34). Metadata only: no bodies."""
import hashlib
import json
import re
import sys
from pathlib import Path
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
        if any(str(l).lower().startswith(processed_label_prefix.lower()) for l in t.get("labels", [])):  # AgentMail stores labels in lower case
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
        issues.append({"message_id": mid, "thread_id": t.get("threadId"), "family": fam, "letter": letter, "sent_at": t["date"],
                       "issue_date": t["date"][:10], "subject": t.get("subject"),
                       "file": out_name(t["date"][:10], fam, mid), "received": t["date"], "set": "counting"})
    issues.sort(key=lambda i: (i["sent_at"], i["message_id"]))
    return issues, skipped


def find_threads(obj):
    """Thread lists inside a saved list_threads result, however the harness wrapped it."""
    out = []
    if isinstance(obj, dict):
        if isinstance(obj.get("threads"), list):
            out += [t for t in obj["threads"] if isinstance(t, dict) and "threadId" in t]
        for v in obj.values():
            out += find_threads(v) if not (isinstance(v, list) and v is obj.get("threads")) else []
    elif isinstance(obj, list):
        if obj and all(isinstance(v, dict) and "threadId" in v for v in obj):
            return list(obj)                          # a bare list of threads, as the runbook has the session write
        for v in obj:
            out += find_threads(v)
    elif isinstance(obj, str) and obj.lstrip().startswith("{"):
        try:
            out += find_threads(json.loads(obj))
        except ValueError:
            pass
    return out


def from_agentmail(thread):
    """An AgentMail thread summary -> the metadata this module uses. The preview is dropped:
    no body text is kept, in memory or on disk."""
    sender = (thread.get("senders") or [""])[0]
    m = re.match(r"\s*(.*?)\s*<([^>]+)>\s*$", sender)
    name, addr = (m.group(1).strip('"'), m.group(2)) if m else ("", sender)
    return {"threadId": thread.get("threadId"), "sender": name, "sender_email": addr, "subject": thread.get("subject"),
            "date": thread.get("receivedTimestamp") or thread.get("timestamp"), "lastMessageId": thread.get("lastMessageId"),
            "labels": thread.get("labels") or [], "messageCount": thread.get("messageCount", 1)}


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


def main(argv):
    """python -m mondayview.collect <saved list_threads result>...
    Reads run/plan.json for the window; writes run/issues.json and run/skipped.json; prints the volume check."""
    plan = json.loads((config.ROOT / "run" / "plan.json").read_text())
    threads, seen = [], set()
    for p in argv[1:]:
        for t in find_threads(json.loads(Path(p).read_text(encoding="utf-8"))):
            if t["threadId"] not in seen:
                seen.add(t["threadId"])
                threads.append(from_agentmail(t))
    window = [parse_ts(x) for x in plan["window_utc"]] if plan.get("window_utc") else None
    issues, skipped = build_issue_list(threads, window)
    (config.ROOT / "run" / "issues.json").write_text(json.dumps(issues, indent=1, ensure_ascii=False), encoding="utf-8")
    (config.ROOT / "run" / "skipped.json").write_text(json.dumps(skipped, indent=1, ensure_ascii=False), encoding="utf-8")
    recent = plan.get("recent_issue_counts")
    action, why = volume_check(len(issues), recent)
    foot = footer_counts(issues)
    print(json.dumps({"threads_seen": len(threads), "issues": len(issues), "skipped": len(skipped), "action": action, "why": why,
                      "per_family": foot["per_family"], "silent_deal_carrying": foot["silent_deal_carrying"]}, indent=1))
    return 0 if action == "ok" else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
