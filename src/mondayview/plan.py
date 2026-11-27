"""Run plan: week, window and mode -> run/plan.json. Usage: python -m mondayview.plan [mode=test week=W47]"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config, week


def make_plan(now=None, override="", prev_summary=None):
    s = config.settings()
    now = now or datetime.now(timezone.utc)
    opts = dict(kv.split("=", 1) for kv in override.split() if "=" in kv)
    mode = opts.get("mode", s["mode"])
    if mode not in ("dry-run", "test", "scheduled"):
        raise ValueError(f"unknown mode {mode}")
    y, w, monday, sunday = week.report_week(now)
    if opts.get("week"):
        w = int(opts["week"].lstrip("Ww"))
        monday, sunday = week.week_bounds(y, w)
    elif mode == "test":
        y, w = 2026, 47
        monday, sunday = week.week_bounds(y, w)
    label = f"W{w:02d}"
    plan = {"mode": mode, "iso_year": y, "week": label, "monday": monday.isoformat(), "sunday": sunday.isoformat(),
            "run_started_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "history_dir": {"dry-run": f"history/dryrun/{label}", "test": f"history/test/{label}", "scheduled": f"history/{label}"}[mode],
            "sends": mode in ("test", "scheduled"), "labels_issues": mode == "scheduled", "advances_cutoff": mode == "scheduled"}
    if mode != "scheduled":
        # a named week is collected whole: its Monday 00:00 UTC to the next Monday 00:00 UTC
        from datetime import datetime as _dt, timedelta as _td
        start = _dt(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
        plan["window_utc"] = [start.isoformat(timespec="seconds"), (start + _td(days=7)).isoformat(timespec="seconds")]
    if mode == "scheduled":
        start, end = week.collection_window(now, (prev_summary or {}).get("cutoff_utc"), s["first_cutoff_time"])
        plan["window_utc"] = [start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")]
        plan["new_cutoff_utc"] = end.isoformat(timespec="seconds")
    return plan


def main(argv):
    plan = make_plan(override=" ".join(argv[1:]))
    out = config.ROOT / "run" / "plan.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(plan, indent=1))
    print(json.dumps(plan, indent=1))


if __name__ == "__main__":
    main(sys.argv)
