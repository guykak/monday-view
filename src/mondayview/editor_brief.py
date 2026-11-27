"""What the editor (the main session) may draw on when writing editorial.json: quotes already extracted,
never an email body. Usage: python -m mondayview.editor_brief <history dir>  -> run/editor_brief.json

The editor writes: headline, context_note (optional), block1 {company, event_type, title, facts[3-4], for_us},
block5 {text, sources} or null, block4_notes, fund_notes, descriptions. Every figure must sit in a cited quote:
guards.check_editorial rejects the file otherwise."""
import json
import sys
from pathlib import Path

from . import config

MAX_FACTS = 40


def make(blocks, events):
    by_id = {e["id"]: e for e in events}
    mon, sun = blocks["week"]["monday"], blocks["week"]["sunday"]
    out = {"week": blocks["week"]["label"], "how": __doc__.split("\n\n")[1]}
    b1 = blocks.get("block1")
    if b1:
        ev = by_id[b1["id"]]
        facts = [f for f in ev["facts"] if not f.get("date") or mon <= f["date"] <= sun]
        heads = [{"date": m["story_date"], "text": m["headline"], "quote": m["quote"], "file": m["file"], "family": m["family"]}
                 for m in ev["mentions"] if m["mention_type"] == "story" and mon <= m["story_date"] <= sun]
        out["block1"] = {"company": b1["company"], "event_type": b1["event_type"], "n_families": b1["n_families"],
                         "status_history": b1["status_history"], "runner_up": b1["runner_up"],
                         "candidate_facts": (heads + facts)[:MAX_FACTS]}
        related = [e for e in events if e["event_type"] == "other" and e.get("subtype") == "market_move" and mon <= e["event_date"] <= sun]
        out["block1"]["related_market_moves"] = [{"text": m["headline"], "quote": m["quote"], "file": m["file"], "date": m["story_date"]}
                                                 for e in related for m in e["mentions"]][:12]
    out["block5_candidates"] = [{"company": e["company"], "families": e["families"],
                                 "facts": [{"text": f["text"], "quote": f["quote"], "file": f["file"]} for f in e["facts"]][:8]
                                          + [{"text": m["headline"], "quote": m["quote"], "file": m["file"]} for m in e["mentions"]][:4]}
                                for e in events if e["event_type"] == "pricing" and mon <= e["event_date"] <= sun and e["n_families"] >= 2]
    out["block4_confirmed"] = [{"target": a["target"], "facts": [{"text": f["text"], "quote": f["quote"], "file": f["file"]}
                                                                 for f in by_id[a["id"]]["facts"]][:6]} for a in blocks["block4"]["confirmed"]]
    out["funds"] = [{"firm": f["firm"], "quotes": [{"quote": m["quote"], "file": m["file"]} for m in by_id[f["id"]]["mentions"]][:4]}
                    for f in blocks["block4"]["funds_european_early"]]
    out["descriptions_now"] = {r["company"]: r["description"] for r in blocks["block2"]["named"] + blocks["block2"]["notable_team"]}
    return out


def main(argv):
    d = Path(argv[1])
    brief = make(json.loads((d / "blocks.json").read_text()), json.loads((d / "events.json").read_text()))
    out = config.ROOT / "run" / "editor_brief.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(brief, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main(sys.argv)
