"""Line-by-line result of the W47 acceptance gate, for the fact-check agent and for Guy.

The gate is docs/w47_gate.md, encoded in tests/fixtures/w47_expected.json. Each line is compared with
a build. Where the sources contradict the gate, the line is listed under `corrections` in the same
file with the evidence; this report shows both the gate's value and the corrected one.

Usage: python -m mondayview.gate history/W47 [extracted_dir] > report
"""
import json
import sys
from pathlib import Path

from . import config


def _near(v, spec):
    return abs(v - spec["value"]) <= spec["tol"]


def _find(events, name, etype):
    hits = [e for e in events if e["event_type"] == etype and e["company"] and name.lower() in e["company"].lower()
            and (etype != "round" or e["status"] in ("closed", "announced"))]
    return max(hits, key=lambda e: e["n_families"]) if hits else None


def lines(blocks, events, expected):
    """-> list of {line, gate, actual, ok, corrected_ok, note}."""
    corr = expected.get("corrections", {})
    out = []

    def add(line, gate, actual, ok):
        c = corr.get(line)
        c_ok = None
        if c is not None:
            c_ok = _near(actual, c) if isinstance(c.get("value"), (int, float)) and "tol" in c else actual == c.get("value")
        out.append({"line": line, "gate": gate, "actual": actual, "ok": bool(ok), "corrected": c, "corrected_ok": c_ok})

    for name, spec in expected["dots"].items():
        e = _find(events, name, spec["type"])
        fam = sorted(e["families"]) if e else None
        add(f"dots.{name}", sorted(spec["families"]), fam, fam == sorted(spec["families"]))
    f = blocks["footer"]
    add("footer.per_family", expected["footer"]["per_family"], f["per_family"], f["per_family"] == expected["footer"]["per_family"])
    b1, x1 = blocks["block1"], expected["block1"]
    add("block1.event", [x1["company"], x1["event_type"]], [b1["company"], b1["event_type"]], [b1["company"], b1["event_type"]] == [x1["company"], x1["event_type"]])
    add("block1.n_families", x1["n_families"], b1["n_families"], b1["n_families"] == x1["n_families"])
    b2, x2 = blocks["block2"], expected["block2"]
    for key, val in (("count_world", b2["count_world"]), ("count_europe", b2["count_europe"])):
        add(f"block2.{key}", f"{x2[key]['value']} ±{x2[key]['tol']}", val, _near(val, x2[key]))
    mix = b2["mix_world"]
    add("block2.mix.carried", f"Term Sheet {x2['mix']['carried']['value']} ±2", mix["carried"], mix["family"] == "Term Sheet" and _near(mix["carried"], x2["mix"]["carried"]))
    add("block2.mix.without", f"{x2['mix']['without']['value']} ±2", mix["without"], _near(mix["without"], x2["mix"]["without"]))
    add("block2.big_early_europe", x2["big_early_europe"]["exact"], sorted(b2["big_early_europe"]), sorted(b2["big_early_europe"]) == x2["big_early_europe"]["exact"])
    add("block2.big_early_rest_of_world", "3 ±1", b2["big_early_rest_of_world"], _near(b2["big_early_rest_of_world"], x2["big_early_rest_of_world"]))
    add("block2.area_total_rule", "total = Europe - Europe $50M+", [b2["area_total"], b2["count_europe"], len(b2["big_early_europe"])],
        b2["area_total"] == b2["count_europe"] - len(b2["big_early_europe"]))
    pool = {r["company"]: r for r in b2["named"] + b2["notable_team"]}
    for req in x2["named_required"]:
        r = pool.get(req["company"])
        ok = bool(r) and all([req.get("hq", "") in (r["hq"] or ""), r["amount"] == req["amount"] if "amount" in req else r["amount"].startswith(req["amount_startswith"]),
                              r["stage"] == req["stage"] if "stage" in req else True])
        add(f"block2.named.{req['company']}", {k: v for k, v in req.items() if k != "company"}, r and {"hq": r["hq"], "amount": r["amount"], "stage": r["stage"]}, ok)
    b3, x3 = blocks["block3"], expected["block3"]
    rows = {r["company"]: r for r in b3["rows"]}
    for req in x3["rows_required"]:
        r = rows.get(req["company"])
        got = r and [r["amount"], r["stage"], r["valuation"]]
        add(f"block3.row.{req['company']}", [req["amount"], req["stage"], req["valuation"]], got,
            bool(r) and got == [req["amount"], req["stage"], req["valuation"]] and all(c in r["hq"] for c in req["hq"]))
    extra = sorted(set(rows) - {q["company"] for q in x3["rows_required"]})
    add("block3.extra_rows", "allowed: " + ", ".join(x3["rows_allowed"]), extra, all(any(a in n for a in x3["rows_allowed"]) for n in extra))
    add("block3.forbidden_rows", x3["rows_forbidden"], [n for n in list(rows) + b3["more"] if any(f.lower() in n.lower() for f in x3["rows_forbidden"])],
        not any(f.lower() in n.lower() for n in list(rows) + b3["more"] for f in x3["rows_forbidden"]))
    add("block3.mega_count_world", "14 ±2", b3["mega_count_world"], _near(b3["mega_count_world"], x3["mega_count_world"]))
    talks = {t["company"]: t for t in b3["in_talks"]}
    for req in x3["in_talks_required"]:
        t = talks.get(req["company"])
        add(f"block3.talks.{req['company']}", [req["amount"], req["valuation"]], t and [t["amount"], t["valuation"]], bool(t) and [t["amount"], t["valuation"]] == [req["amount"], req["valuation"]])
    b4, x4 = blocks["block4"], expected["block4"]
    conf = {a["target"]: a for a in b4["confirmed"]}
    for req in x4["confirmed_required"]:
        a = conf.get(req["target"])
        add(f"block4.confirmed.{req['target']}", [req["acquirer"], req["price"], req["n_families"]], a and [a["acquirer"], a["price"], a["n_families"]],
            bool(a) and [a["acquirer"], a["price"], a["n_families"]] == [req["acquirer"], req["price"], req["n_families"]])
    single = b4["single_source"] + b4["single_source_more"]
    for req in x4["single_source_required"]:
        hit = [a for a in single if req["target"].lower() in a["target"].lower()]
        a = hit[0] if hit else None
        add(f"block4.single.{req['target']}", [req["acquirer"], req["source"]], a and [a["acquirer"], a["families"], a["price"], a["status"]],
            bool(a) and req["acquirer"].lower() in (a["acquirer"] or "").lower() and a["families"] == [req["source"]])
    funds = b4["funds_european_early"] + b4["funds_other"]
    for req in x4["funds_required"]:
        hit = [f for f in funds if req["firm"].lower() in f["firm"].lower()]
        f = hit[0] if hit else None
        add(f"block4.fund.{req['firm']}", [req["size"], req["european_early"], req["n_families"]], f and [f["size"], f["european_early"], f["n_families"]],
            bool(f) and [f["size"], f["european_early"], f["n_families"]] == [req["size"], req["european_early"], req["n_families"]])
    return out


def passes(result_lines):
    """The gate with its documented corrections: every line is ok, or matches its correction."""
    return all(l["ok"] or l["corrected_ok"] for l in result_lines)


def render(result_lines):
    rows = ["| Line | Gate says | This build | Result |", "|---|---|---|---|"]
    for l in result_lines:
        res = "pass" if l["ok"] else ("differs from the gate; matches the sources (see note)" if l["corrected_ok"] else "FAIL")
        rows.append(f"| {l['line']} | {json.dumps(l['gate'], ensure_ascii=False)} | {json.dumps(l['actual'], ensure_ascii=False)} | {res} |")
    notes = [f"- **{l['line']}**: {l['corrected']['why']}" for l in result_lines if l["corrected"] and not l["ok"]]
    return "\n".join(rows) + ("\n\nNotes on lines that differ from the gate:\n" + "\n".join(notes) if notes else "") + "\n"


def main(argv):
    d = Path(argv[1])
    expected = json.loads((config.ROOT / "tests/fixtures/w47_expected.json").read_text())
    res = lines(json.loads((d / "blocks.json").read_text()), json.loads((d / "events.json").read_text()), expected)
    print(render(res))
    n_ok = sum(l["ok"] for l in res)
    n_corr = sum((not l["ok"]) and bool(l["corrected_ok"]) for l in res)
    print(f"{len(res)} lines: {n_ok} pass as written, {n_corr} differ from the gate but match the sources, {len(res) - n_ok - n_corr} fail.")


if __name__ == "__main__":
    main(sys.argv)
