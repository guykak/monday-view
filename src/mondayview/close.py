"""Closing steps of a run (spec §3 step 8) and hold notices (spec §5).

python -m mondayview.close log <history dir> [--usage run/usage.json] [--note "..."]
    writes logs/<week>_<UTC stamp>.json from the plan, summary and skipped senders; prints the labelling plan.
python -m mondayview.close staged
    checks the staged git paths for this mode; exit code 1 if anything outside history/ and logs/ is staged.
python -m mondayview.close hold <week label> "<reason>"
    writes run/hold_plan.json: the short notice to send, or send=false in dry-run or with no recipient.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config, guards

RUN = config.ROOT / "run"


def _load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def log(history_dir, usage=None, note=None, now=None):
    plan = _load(RUN / "plan.json", {})
    summary = _load(Path(history_dir) / "summary.json", {})
    issues = _load(RUN / "issues.json", [])
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    entry = {"stamp_utc": stamp, "plan": plan, "issues": len(issues), "skipped": _load(RUN / "skipped.json", []),
             "summary": {k: summary.get(k) for k in ("week", "mode", "words", "compact_level", "html_bytes", "checks", "extraction_failed", "repairs")},
             "usage": _load(usage) if usage else None, "note": note}
    logs = config.ROOT / "logs"
    logs.mkdir(exist_ok=True)
    out = logs / f"{plan.get('week', 'W00')}_{plan.get('mode', 'dry-run')}_{stamp}.json"
    out.write_text(json.dumps(entry, indent=1, ensure_ascii=False), encoding="utf-8")
    labelling = {"apply": bool(plan.get("labels_issues")), "label": f"mv-processed-{plan.get('week')}",
                 "thread_ids": [i["thread_id"] for i in issues if i.get("thread_id")] if plan.get("labels_issues") else []}
    return out, labelling


def staged(mode=None):
    mode = mode or _load(RUN / "plan.json", {}).get("mode", "scheduled")
    paths = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=config.ROOT, capture_output=True, text=True, check=True).stdout.split()
    guards.check_staged_paths(paths, "scheduled" if mode in ("scheduled", "test", "dry-run") else mode)
    return paths


def hold_plan(week_label, reason, mode=None, settings=None):
    s = settings or config.settings()
    mode = mode or _load(RUN / "plan.json", {}).get("mode", s["mode"])
    send = mode in ("test", "scheduled") and bool(s.get("recipient"))
    text = (f"Monday view {week_label} is on hold.\n\nReason: {reason}\n\nNothing was sent. "
            "The run's files and log are in the repo under history/ and logs/.")
    return {"send": send, "mode": mode, "recipient": s.get("recipient") or "", "subject": f"{s['subject_prefix']}Monday view {week_label} on hold",
            "labels": ["monday-view-hold", f"mv-hold-{week_label}"] if mode == "scheduled" else ["monday-view-test", f"mv-test-hold-{week_label}"],
            "text": text, "cc": [], "bcc": []}


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "log":
        usage = argv[argv.index("--usage") + 1] if "--usage" in argv else None
        note = argv[argv.index("--note") + 1] if "--note" in argv else None
        out, labelling = log(argv[2], usage, note)
        print(json.dumps({"log": str(out.relative_to(config.ROOT)), "labelling": labelling}, indent=1))
    elif cmd == "staged":
        try:
            print(json.dumps({"ok": True, "staged": staged()}, indent=1))
        except guards.GuardError as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1
    elif cmd == "hold":
        plan = hold_plan(argv[2], argv[3])
        RUN.mkdir(exist_ok=True)
        (RUN / "hold_plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
        print(json.dumps(plan, indent=1))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
