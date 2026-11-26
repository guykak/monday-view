"""What the fact-check agent must re-open (pitfall 28): every shown number in blocks 1, 3 and 4 and
every dot count, each with the message IDs to check it against. The agent gets claims and message
IDs only: never the extractors' reasoning.

Usage: python -m mondayview.factcheck_plan history/W47  -> history/W47/factcheck_plan.json
"""
import json
import sys
from pathlib import Path

from . import config
from .merge import jsonable


def _sources(event, limit=None):
    seen, out = set(), []
    for m in event["mentions"]:
        if m["message_id"] not in seen:
            seen.add(m["message_id"])
            out.append({"message_id": m["message_id"], "family": m["family"], "file": m["file"]})
    return out[:limit] if limit else out


def make(blocks, events, editorial=None):
    editorial = editorial or {}
    by_id = {e["id"]: e for e in events}
    by_file = {}
    for e in events:
        for m in e["mentions"]:
            by_file[m["file"]] = {"message_id": m["message_id"], "family": m["family"], "file": m["file"]}
    checks = []

    def add(block, kind, item, claim, sources, event_id=None):
        checks.append({"id": f"c{len(checks) + 1:03d}", "block": block, "kind": kind, "item": item, "claim": claim,
                       "event_id": event_id, "sources": sources})

    def dots(block, item, ev):
        add(block, "dots", item, f"{item} is carried by exactly these families: {', '.join(ev['families'])} ({ev['n_families']}). "
            "Each listed issue reports or refers to this same event.", _sources(ev), ev["id"])

    b1 = blocks.get("block1")
    if b1:
        ev = by_id[b1["id"]]
        dots(1, b1["company"], ev)
        for f in (editorial.get("block1") or {}).get("facts", []):
            add(1, "number", b1["company"], f"{f['date']}: {f['text']}", [by_file[s["file"]] for s in f.get("sources", []) if s["file"] in by_file], ev["id"])
    for r in blocks["block2"]["named"] + blocks["block2"]["notable_team"]:
        ev = by_id[r["id"]]
        dots(2, r["company"], ev)
        add(2, "number", r["company"], f"{r['company']} ({r['hq']}): {r['amount']} {r['stage'] or ''}; leads: {', '.join(r['leads']) or 'none stated'}"
            + (f"; team: {r['founder_background']}" if r in blocks["block2"]["notable_team"] else ""), _sources(ev, 2), ev["id"])
    for r in blocks["block3"]["rows"]:
        ev = by_id[r["id"]]
        dots(3, r["company"], ev)
        add(3, "number", r["company"], f"{r['company']}: closed equity round of {r['amount']}, stage {r['stage'] or 'not stated'}, "
            f"valuation {r['valuation'] or 'not stated'}; HQ {r['hq']} (every stated HQ, at least one in Europe)", _sources(ev, 3), ev["id"])
    for t in blocks["block3"]["in_talks"]:
        ev = by_id[t["id"]]
        add(3, "number", t["company"], f"{t['company']}: in talks, not closed; {t['amount'] or 'amount not stated'} at {t['valuation'] or 'no valuation stated'}", _sources(ev, 2), ev["id"])
    for a in blocks["block4"]["confirmed"]:
        ev = by_id[a["id"]]
        dots(4, a["target"], ev)
        add(4, "number", a["target"], f"{a['acquirer']} acquires {a['target']}: {a['price'] or 'price not stated'}"
            f"{' in ' + a['consideration'] if a.get('consideration') in ('stock', 'cash') else ''}; status {a['status']}."
            + (f" Note: {a['note']}" if a.get("note") else ""), _sources(ev, 3), ev["id"])
    for a in blocks["block4"]["single_source"] + blocks["block4"]["single_source_more"]:
        ev = by_id[a["id"]]
        add(4, "number", a["target"], f"{a['acquirer']} / {a['target']}: {a['price'] or 'no price'}; status {a['status']}; "
            f"reported only by {', '.join(a['families'])}", _sources(ev, 2), ev["id"])
    for f in blocks["block4"]["funds_european_early"] + blocks["block4"]["funds_other"]:
        ev = by_id[f["id"]]
        dots(4, f["firm"], ev)
        add(4, "number", f["firm"], f"{f['firm']} closed a fund of {f['size']}; strategy {f['strategy']}; geography {f['geography']}; focus {f['focus']}"
            + (f"; {f['note']}" if f.get("note") else ""), _sources(ev, 3), ev["id"])
    b5 = editorial.get("block5")
    if b5 and b5.get("text"):
        add(5, "number", "market move", b5["text"], [by_file[s["file"]] for s in b5.get("sources", []) if s["file"] in by_file])
    reopens = len({s["message_id"] for c in checks for s in c["sources"]})
    return {"week": blocks["week"]["iso_week"], "inbox": config.settings()["inbox"], "checks": checks, "reopens": reopens,
            "sample_tags": [{"company": r["company"], "tech_area": r["tech_area"], "description": r["description"]}
                            for r in blocks["block2"]["named"]]}


def main(argv):
    d = Path(argv[1])
    blocks = json.loads((d / "blocks.json").read_text())
    events = json.loads((d / "events.json").read_text())
    ed = json.loads((d / "editorial.json").read_text()) if (d / "editorial.json").exists() else {}
    plan = make(blocks, events, ed)
    (d / "factcheck_plan.json").write_text(json.dumps(jsonable(plan), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(plan['checks'])} checks, {plan['reopens']} messages to re-open")


if __name__ == "__main__":
    main(sys.argv)
