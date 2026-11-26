"""Build stage: extracted issue files -> events.json, blocks.json, view.md, email.html, email.txt.

Usage: python -m mondayview.build --week 2026-W47 --extracted history/W47/extracted \
          --issues tests/fixtures/w47_issues.json --out history/W47 [--editorial history/W47/editorial.json]
          [--prior history/W46/summary.json] [--drop history/W47/factcheck.json]
"""
import argparse
import json
from datetime import date
from pathlib import Path

from . import blocks as blocks_mod
from . import merge, validate, week
from .merge import jsonable


def load_issue_list(path, only_set="counting"):
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [i for i in items if i.get("set", "counting") == only_set]


def run(week_id, extracted, issue_list, out=None, editorial=None, prior=None, drop_ids=(), run_date=None, weeks_of_history=0):
    y, w = week_id.split("-W")
    monday, sunday = week.week_bounds(int(y), int(w))
    issues, failed, flags = validate.load_dir(extracted, issue_list)
    events = [e for e in merge.merge(issues) if e["id"] not in set(drop_ids)]
    blocks = blocks_mod.build(events, issue_list, monday, sunday, prior=prior, editorial=editorial or {},
                              run_date=run_date, weeks_of_history=weeks_of_history)
    blocks["footer"]["withheld"] = len(set(drop_ids))
    blocks["extraction"] = {"issues": len(issue_list), "loaded": len(issues), "failed": failed, "flags": flags}
    result = {"events": events, "blocks": blocks, "issues": issues, "failed": failed}
    if out:
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "events.json").write_text(json.dumps(jsonable(events), indent=1, ensure_ascii=False), encoding="utf-8")
        (out / "blocks.json").write_text(json.dumps(jsonable(blocks), indent=1, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--extracted", required=True)
    ap.add_argument("--issues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--editorial")
    ap.add_argument("--prior")
    ap.add_argument("--drop")
    ap.add_argument("--run-date")
    ap.add_argument("--mode")
    ap.add_argument("--stamp", help="UTC timestamp for a test label, e.g. 20261126T101500Z")
    ap.add_argument("--cutoff", help="the collection cut-off this run used (UTC), stored for the next run")
    ap.add_argument("--usage", help="a JSON file with time, sub-agent and message counts per stage")
    a = ap.parse_args(argv)
    editorial = json.loads(Path(a.editorial).read_text(encoding="utf-8")) if a.editorial and Path(a.editorial).exists() else {}
    prior = json.loads(Path(a.prior).read_text()).get("status_history") if a.prior and Path(a.prior).exists() else None
    drop = []
    if a.drop and Path(a.drop).exists():
        drop = [f["event_id"] for f in json.loads(Path(a.drop).read_text()).get("findings", []) if f.get("verdict") == "fail" and f.get("action") == "drop"]
    res = run(a.week, a.extracted, load_issue_list(a.issues), a.out, editorial, prior, drop,
              date.fromisoformat(a.run_date) if a.run_date else None)
    from . import config, factcheck_plan, guards, render_email
    render_email.write_all(res["blocks"], a.out)
    b = res["blocks"]
    out = Path(a.out)
    (out / "blocks.json").write_text(json.dumps(jsonable(b), indent=1, ensure_ascii=False), encoding="utf-8")
    html, text, md = (out / "email.html").read_text(), (out / "email.txt").read_text(), (out / "view.md").read_text()
    mode = a.mode or config.settings()["mode"]
    label = "W" + a.week.split("-W")[1]
    send_plan = guards.make_send_plan(mode, label, html, text, a.stamp)
    (out / "send_plan.json").write_text(json.dumps(send_plan, indent=1), encoding="utf-8")
    plan = factcheck_plan.make(b, res["events"], editorial)
    (out / "factcheck_plan.json").write_text(json.dumps(jsonable(plan), indent=1, ensure_ascii=False), encoding="utf-8")
    problems = guards.check_editorial(editorial, res["events"], computed_numbers=[
        b["block2"]["count_world"], b["block2"]["count_europe"], b["block3"]["mega_count_world"]]) if editorial else ["no editorial.json"]
    words = guards.word_count(md)
    th = config.settings()["thresholds"]
    summary = {
        "week": a.week, "mode": mode, "built_for_run_date": a.run_date,
        "cutoff_utc": a.cutoff, "issues": b["footer"]["total"], "issues_per_family": b["footer"]["per_family"],
        "extraction_failed": sorted(res["failed"]), "repairs": b["extraction"]["flags"],
        "events": len(res["events"]), "words": words, "compact_level": b.get("compact_level"),
        "html_bytes": send_plan["html_bytes"],
        "checks": {"words_in_range": th["words_min"] <= words <= th["words_max"], "html_under_limit": send_plan["html_bytes"] < th["html_max_bytes"],
                   "editorial_problems": problems, "dollar_totals": guards.find_totals(md), "trend_claims": guards.find_trend_claims(md, 0)},
        "status_history": blocks_mod.status_snapshot(res["events"], prior),
        "usage": json.loads(Path(a.usage).read_text()) if a.usage and Path(a.usage).exists() else None,
    }
    (out / "summary.json").write_text(json.dumps(jsonable(summary), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"words {words} (trim level {b.get('compact_level')})  html {send_plan['html_bytes']} bytes  send={send_plan['send']}  "
          f"fact-check: {len(plan['checks'])} checks over {plan['reopens']} messages  editorial problems: {problems or 'none'}")
    print(f"issues {b['extraction']['loaded']}/{b['extraction']['issues']}  events {len(res['events'])}  "
          f"early {b['block2']['count_world']} (Europe {b['block2']['count_europe']})  failed {list(res['failed'])}")


if __name__ == "__main__":
    main()
