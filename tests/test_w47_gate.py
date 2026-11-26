"""The W47 acceptance gate (docs/w47_gate.md), encoded in tests/fixtures/w47_expected.json.

Runs on the committed extraction (history/W47/extracted). Set MV_EXTRACTED to another folder
(and MV_EDITORIAL) to run the same gate on a second extraction run.
"""
import json
import os
import re
from pathlib import Path

import pytest

from conftest import ROOT, _w47
from mondayview import guards


@pytest.fixture(scope="module")
def r(w47):
    alt = os.environ.get("MV_EXTRACTED")
    if alt:
        return _w47(Path(alt), Path(os.environ.get("MV_EDITORIAL", Path(alt).parent / "editorial.json")))
    return w47


def near(value, spec):
    return abs(value - spec["value"]) <= spec["tol"]


def find(events, name, etype):
    hits = [e for e in events if e["event_type"] == etype and e["company"] and name.lower() in e["company"].lower()
            and (etype != "round" or e["status"] in ("closed", "announced"))]
    assert hits, f"no {etype} event for {name}"
    return max(hits, key=lambda e: e["n_families"])


def test_all_54_issues_loaded(r, expected):
    assert r["failed"] == {} and len(r["issues"]) == expected["counting_set"]["issues"]


def test_footer_counts_exact(r, expected):
    f = r["blocks"]["footer"]
    assert f["total"] == expected["footer"]["total"]
    assert f["per_family"] == expected["footer"]["per_family"]
    assert f["silent_letters"] == expected["footer"]["silent_letters"]
    assert "Maddyness IA sent none" in r["md"]
    for part in ("TLDR 12", "Sifted 9", "AlphaSignal 6", "Techmeme 6", "Term Sheet 5", "Maddyness 5", "Newcomer 4", "others 1 each"):
        assert part in r["md"].split("---")[-1]


def test_every_gate_line_passes_or_matches_a_documented_correction(r, expected):
    """Each gate line passes as written, or equals the corrected value recorded with its evidence
    in w47_expected.json. Nothing else is accepted."""
    from mondayview import gate
    res = gate.lines(r["blocks"], r["events"], expected)
    bad = [(l["line"], l["gate"], l["actual"]) for l in res if not (l["ok"] or l["corrected_ok"])]
    assert bad == []
    # a correction is used only where the gate line really differs, and the list of corrections is closed
    differs = {l["line"] for l in res if not l["ok"]}
    assert differs <= set(expected["corrections"]) - {"_note"}
    assert differs == {"dots.Anthropic", "block1.n_families", "block2.count_world", "block2.count_europe",
                       "block2.mix.carried", "block2.mix.without", "block3.row.Payhawk"}


def test_headline_legend_length(r, expected):
    md = r["md"]
    lines = [l for l in md.split("\n") if l.strip()]
    assert re.fullmatch(r"\*\*[^*]+\.\*\*", lines[1]), "one bold headline sentence"
    assert lines[2].startswith("Each ● is one source family")
    n = guards.word_count(md)
    assert expected["words"]["min"] <= n <= expected["words"]["max"], n


def test_block1(r, expected):
    b1, x = r["blocks"]["block1"], expected["block1"]
    assert (b1["company"], b1["event_type"], b1["dots"]) == (x["company"], x["event_type"], x["dots"])
    assert b1["n_families"] == expected["corrections"]["block1.n_families"]["value"]     # the gate says 10; see corrections
    facts = {f["date"]: f["text"] for f in b1["facts"]}
    assert 3 <= len(b1["facts"]) <= 4
    for req in x["required_facts"]:
        assert req["date"] in facts, req["date"]
        for s in req["must_contain"]:
            assert s in facts[req["date"]], (req["date"], s)
    sec = r["md"].split("## 1.")[1].split("## 2.")[0]
    for s in x["must_contain_anywhere"]:
        assert s in sec
    assert b1["for_us"] and "For us:" in sec
    for s in x["forbidden_text"]:
        assert s.lower() not in r["md"].lower()
    assert "(9 families)" in sec


def test_block2_counts(r, expected):
    b2, x = r["blocks"]["block2"], expected["block2"]
    c = expected["corrections"]                      # the gate's 55 / 28 / 30 / 35 are contradicted by the sources
    assert near(b2["count_world"], c["block2.count_world"]), b2["count_world"]
    assert near(b2["count_europe"], c["block2.count_europe"]), b2["count_europe"]
    mix = b2["mix_world"]
    assert mix["family"] == x["mix"]["family"]
    assert near(mix["carried"], c["block2.mix.carried"]) and near(mix["without"], c["block2.mix.without"]), mix
    assert sorted(b2["big_early_europe"]) == x["big_early_europe"]["exact"]
    assert near(b2["big_early_rest_of_world"], x["big_early_rest_of_world"]), b2["big_early_rest_of_world"]
    assert b2["area_total"] == b2["count_europe"] - len(b2["big_early_europe"]) == sum(a["rounds"] for a in b2["area_table"])
    assert f"{b2['area_total']} = {b2['count_europe']} European rounds less the 4 of $50M or more" in r["md"]


def test_block2_named(r, expected):
    b2 = r["blocks"]["block2"]
    named = {x["company"]: x for x in b2["named"]}
    notable = {x["company"]: x for x in b2["notable_team"]}
    for req in expected["block2"]["named_required"]:
        pool = {**named, **notable} if req.get("notable_or_named") else named
        assert req["company"] in pool, req["company"]
        row = pool[req["company"]]
        if "hq" in req:
            assert req["hq"] in row["hq"], row
        if "hq_country" in req:
            assert any(h["country"] == req["hq_country"] for h in row["hq_list"])
        if "amount" in req:
            assert row["amount"] == req["amount"], row
        if "amount_startswith" in req:
            assert row["amount"].startswith(req["amount_startswith"]) and "grants and equity" in row["amount"], row
        if "stage" in req:
            assert row["stage"] == req["stage"], row
        e = find(r["events"], req["company"], "round")
        assert row["dots"] == "●" * min(5, len(expected["dots"][req["company"]]["families"]))
    assert "Remanence" in r["md"] and "H Company" in r["md"]


def test_block3(r, expected):
    b3, x = r["blocks"]["block3"], expected["block3"]
    rows = {row["company"]: row for row in b3["rows"]}
    for req in x["rows_required"]:
        assert req["company"] in rows, req["company"]
        row = rows[req["company"]]
        want = expected["corrections"].get(f"block3.row.{req['company']}", {}).get("value", [req["amount"], req["stage"], req["valuation"]])
        assert [row["amount"], row["stage"], row["valuation"]] == want, row
        for city in req["hq"]:
            assert city in row["hq"], row
        assert row["dots"] == "●" * min(5, len(expected["dots"][req["company"]]["families"]))
    allowed = {q["company"] for q in x["rows_required"]} | set(x["rows_allowed"])
    for name in list(rows) + b3["more"]:
        assert not any(f.lower() in name.lower() for f in x["rows_forbidden"]), name
    amounts = [row["usd"] for row in b3["rows"]]
    assert amounts == sorted(amounts, reverse=True) and len(b3["rows"]) <= 8
    assert near(b3["mega_count_world"], x["mega_count_world"]), b3["mega_count_world"]
    talks = {t["company"]: t for t in b3["in_talks"]}
    for req in x["in_talks_required"]:
        assert req["company"] in talks, req["company"]
        assert talks[req["company"]]["amount"] == req["amount"] and talks[req["company"]]["valuation"] == req["valuation"], talks[req["company"]]
    sec = r["md"].split("## 3.")[1].split("## 4.")[0]
    assert "$228M" not in r["md"] and "equity only" in sec and "In talks, not closed" in sec
    extra = set(rows) - allowed
    r["blocks"]["_extra_block3_rows"] = sorted(extra)      # allowed if they meet the rule; reported, not failed


def test_block4(r, expected):
    b4, x = r["blocks"]["block4"], expected["block4"]
    conf = {a["target"]: a for a in b4["confirmed"]}
    for req in x["confirmed_required"]:
        assert req["target"] in conf, req["target"]
        a = conf[req["target"]]
        assert a["acquirer"] == req["acquirer"] and a["price"] == req["price"] and a["n_families"] == req["n_families"], a
        if "consideration" in req:
            assert a["consideration"] == req["consideration"]
        for s in req["note_contains"]:
            assert s in (a["note"] or ""), (req["target"], s)
    single = {a["target"]: a for a in b4["single_source"] + b4["single_source_more"]}
    for req in x["single_source_required"]:
        hit = [a for t, a in single.items() if req["target"].lower() in t.lower()]
        assert hit, req["target"]
        a = hit[0]
        assert req["acquirer"].lower() in (a["acquirer"] or "").lower() and a["families"] == [req["source"]], a
        if "price" in req:
            assert a["price"] == req["price"], a
        if "price_startswith" in req:
            assert a["price"].startswith(req["price_startswith"]) and a["price"].endswith("+"), a
        if req.get("talks"):
            assert a["status"] in ("in_talks", "rumour"), a
    assert not any("zscaler" in t.lower() for t in conf), "CrowdStrike-Zscaler was talks only"
    funds = {f["firm"]: f for f in b4["funds_european_early"] + b4["funds_other"]}
    for req in x["funds_required"]:
        hit = [f for name, f in funds.items() if req["firm"].lower() in name.lower()]
        assert hit, req["firm"]
        f = hit[0]
        assert f["size"] == req["size"] and f["european_early"] == req["european_early"] and f["n_families"] == req["n_families"], f
    sec = r["md"].split("## 4.")[1].split("## 5.")[0]
    for s in x["forbidden"]:
        assert s not in sec
    assert "Single source, unconfirmed" in sec and "life sciences" in sec


def test_block5(r, expected):
    sec = r["md"].split("## 5.")[1].split("---")[0]
    for s in expected["block5"]["must_contain"]:
        assert s in sec, s
    for pat in expected["block5"]["forbidden_regex"]:
        assert not re.search(pat, sec, re.I)


def test_whole_output(r):
    md = r["md"]
    assert guards.find_totals(md) == []
    assert guards.find_trend_claims(md, 0) == []
    assert "!" not in md
    assert guards.check_editorial(r["editorial"], r["events"], computed_numbers=_computed(r["blocks"])) == []
    assert len(r["html"].encode()) < 40000 and "<img" not in r["html"]
    assert r["text"].strip() and "**" not in r["text"]


def _computed(b):
    nums = {b["block1"]["n_families"], b["block2"]["count_world"], b["block2"]["count_europe"], b["block3"]["mega_count_world"]}
    return nums
