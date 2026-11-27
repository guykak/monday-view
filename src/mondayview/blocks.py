"""Apply the README §2 block rules to merged events. Every number in the Monday view is computed here.

Input: events (merge.py), the collected issue list, the report week, the status history of earlier
weeks, and the editor's words (editorial.json). Output: blocks.json, which render_email.py prints.
No dollar totals are computed anywhere (pitfall 12) and no trend is claimed before 8 weeks (26).
"""
import re
from collections import Counter

from . import config
from .collect import footer_counts
from .merge import is_europe, name_keys
from .money import fmt, to_usd
from .validate import COUNTED_ROUND_STATUS
from .week import first_monday_on_or_after, fmt_day

DONE_ACQ = {"signed", "announced", "completed"}
OPEN_ACQ = {"in_talks", "rumour", "bid", "planned"}
FUND_CLOSED = {"closed", "final_close", "first_close"}
IPO_SHOWN = {"filed", "priced", "listed"}


def event_key(e):
    keys = sorted(name_keys(e.get("company") or e.get("headline") or ""))
    return f"{e['event_type']}:{keys[0] if keys else e['id']}"


def new_statuses_in_week(e, monday, sunday, prior=None):
    """Pitfall 2: statuses this event reached inside the week that no earlier week recorded."""
    seen = set((prior or {}).get(event_key(e), []))
    return [h for h in e["status_history"] if monday <= h["date"] <= sunday and h["status"] not in seen]


def in_week(e, monday, sunday, prior=None):
    """Pitfalls 1 and 2: an event belongs to the week if it was first reported in it, or reached
    a new status in it. An event first recorded in an earlier week does not come back unchanged."""
    if event_key(e) in (prior or {}):
        return bool(new_statuses_in_week(e, monday, sunday, prior))
    return bool(new_statuses_in_week(e, monday, sunday, None))


def dots(n, cap=None):
    cap = cap or config.settings()["thresholds"]["dots_cap"]
    return "●" * min(n, cap)


def round_usd(e, fx_log=None):
    """Equity only. Debt, grants and customer-value funds never count toward a threshold (pitfall 8)."""
    return to_usd(e.get("equity_amount"), e.get("currency"), fx_log)


def size_for_cap_usd(e, fx_log=None):
    """For 'under $50M': the equity amount, or a mixed total when equity alone is not stated."""
    v = round_usd(e, fx_log)
    if v is None and e.get("mixed_total"):
        v = to_usd(e["mixed_total"]["amount"], e["mixed_total"]["currency"], fx_log)
    return v


def is_closed_round(e):
    return e["event_type"] == "round" and e["status"] in COUNTED_ROUND_STATUS


def is_early(e, fx_log=None):
    th = config.settings()["thresholds"]
    st = e.get("stage") or "unstated"
    if st in th["early_stages"]:
        return True
    if st in ("extension", "bridge"):
        return bool(re.search(r"seed|series\s*a\b", e.get("stage_as_written") or "", re.I))
    if st == "unstated":
        v = size_for_cap_usd(e, fx_log)
        return v is not None and v < th["unstated_stage_early_max_usd"]
    return False


STAGE_LABEL = {"pre_seed": "pre-seed", "seed": "seed", "series_a": "Series A", "series_b": "Series B",
               "series_c": "Series C", "series_d_plus": "late-stage", "growth": "growth",
               "extension": "extension", "bridge": "bridge"}


def stage_label(e):
    st = e.get("stage")
    if st == "series_d_plus":
        m = re.search(r"series\s+[d-z]\b", e.get("stage_as_written") or "", re.I)
        return "Series " + m.group(0)[-1].upper() if m else "late-stage"
    return STAGE_LABEL.get(st)


def hq_label(e, europe_only_city=False):
    parts = []
    for h in e["hq"]:
        parts.append(h["city"] or h["country"])
    return " / ".join(parts)


def amount_label(e):
    """What was raised, in the source's currency, with mixed money labelled (pitfall 8)."""
    if e.get("equity_amount") is not None:
        s = fmt(e["equity_amount"], e["currency"], e.get("amount_qualifier"))
        return s, False
    mt = e.get("mixed_total")
    if mt:
        names = {"grant": "grants", "equity": "equity", "debt": "debt", "customer_value_fund": "a customer-value fund",
                 "secondary": "secondaries", "other": "other finance"}
        inc = [names[i] for i in mt["includes"]]
        inc = sorted(inc, key=lambda x: x == "equity")
        return f"{fmt(mt['amount'], mt['currency'], mt.get('qualifier'))} in {' and '.join(inc)}", True
    return None, False


def source_mix(events, total_label):
    """Pitfall 21: which family carried most of a count, and the count without it."""
    n = len(events)
    if not n:
        return None
    carried = Counter(f for e in events for f in e["families"])
    fam, c = sorted(carried.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    without = sum(1 for e in events if set(e["families"]) - {fam})
    th = config.settings()["thresholds"]["family_dominance_flag"]
    return {"family": fam, "carried": c, "total": n, "without": without,
            "dominant": (n - without) / n > th, "label": total_label}


def _round_row(e, fx_log, editorial):
    amt, mixed = amount_label(e)
    return {"id": e["id"], "company": e["company"], "hq": hq_label(e), "hq_list": e["hq"],
            "amount": amt, "mixed": mixed, "stage": stage_label(e),
            "leads": [l + " (founder)" if l in (e.get("founder_leads") or []) else l for l in e["leads"][:2]],
            "status_note": e.get("status_note"),
            "description": (editorial.get("descriptions") or {}).get(e["company"]) or e.get("description"),
            # a pre-money valuation is said to be one (fact-check, W47: Stark Future)
            "valuation": (fmt(**{k: e["valuation"][k] for k in ("amount", "currency", "qualifier")})
                          + (" pre-money" if e.get("valuation_basis") == "pre_money" else "")) if e.get("valuation") else None,
            "valuation_basis": e.get("valuation_basis"),
            "families": e["families"], "n_families": e["n_families"], "dots": dots(e["n_families"]),
            "tech_area": e["tech_area"], "usd": round_usd(e, fx_log), "founder_background": e.get("founder_background"),
            "n_reprints": e["n_reprints"], "other_finance": e.get("other_finance") or []}


def build(events, issues, monday, sunday, prior=None, editorial=None, run_date=None, weeks_of_history=0):
    editorial = editorial or {}
    th = config.settings()["thresholds"]
    tax = config.taxonomy()
    fx_log = []
    wk = [e for e in events if in_week(e, monday, sunday, prior)]

    # ---- block 2: early-stage rounds ----
    closed = [e for e in wk if is_closed_round(e)]
    early = [e for e in closed if is_early(e, fx_log)]
    early_eu = [e for e in early if is_europe(e)]
    big_early = [e for e in early if (round_usd(e, fx_log) or 0) >= th["big_round_usd"]]
    big_early_eu = [e for e in big_early if is_europe(e)]
    eu_small = [e for e in early_eu if e not in big_early_eu]
    area_counts = Counter(e["tech_area"] or "other" for e in eu_small)
    order = list(tax)
    area_table = [{"area": a, "label": tax[a]["label"], "rounds": n}
                  for a, n in sorted(area_counts.items(), key=lambda kv: (-kv[1], order.index(kv[0])))]
    notable = sorted([e for e in early_eu if e["n_families"] >= th["notable_team_min_families"] and e.get("founder_background")
               and (round_usd(e, fx_log) or 0) < th["big_round_usd"]], key=lambda e: (-e["n_families"], e["company"]))
    notable_ids = {e["id"] for e in notable}
    named = [e for e in eu_small if tax.get(e["tech_area"], {}).get("deep_tech")
             and tax[e["tech_area"]].get("show_in_named_list", True) and e["id"] not in notable_ids]
    named.sort(key=lambda e: (order.index(e["tech_area"]), -e["n_families"], e["company"].lower()))
    block2 = {
        "count_world": len(early), "count_europe": len(early_eu),
        "mix_world": source_mix(early, "worldwide"), "mix_europe": source_mix(early_eu, "Europe"),
        "big_early_world": len(big_early), "big_early_europe": [e["company"] for e in big_early_eu],
        "big_early_rest_of_world": len(big_early) - len(big_early_eu),
        "area_table": area_table, "area_total": len(eu_small),
        "area_note_ok": len(eu_small) == len(early_eu) - len(big_early_eu),
        "named": [_round_row(e, fx_log, editorial) for e in named],
        "notable_team": [_round_row(e, fx_log, editorial) for e in notable],
        "ids_world": sorted(e["id"] for e in early), "ids_europe": sorted(e["id"] for e in early_eu),
        "lead_with_raw_count": weeks_of_history >= th["min_weeks_for_trends"],
    }

    # ---- block 3: big rounds and marks ----
    big = [e for e in closed if (round_usd(e, fx_log) or 0) >= th["big_round_usd"]]
    big_eu = sorted([e for e in big if is_europe(e)], key=lambda e: -round_usd(e))
    # a top-up to an earlier round (extension, bridge) is named on the "also" line, not given a row
    topups = [e for e in big_eu if e.get("stage") in ("extension", "bridge")]
    big_eu = [e for e in big_eu if e not in topups]
    rows = [_round_row(e, fx_log, editorial) for e in big_eu]
    mega = [e for e in closed if (round_usd(e, fx_log) or 0) >= th["mega_round_usd"]]
    talks = [e for e in wk if e["event_type"] == "round" and e["status"] not in COUNTED_ROUND_STATUS
             and (e.get("equity_amount") or e.get("valuation"))]
    talks.sort(key=lambda e: -(to_usd((e.get("valuation") or {}).get("amount"), (e.get("valuation") or {}).get("currency")) or round_usd(e) or 0))
    block3 = {
        "rows": rows[:th["block3_max_rows"]], "more": [r["company"] for r in rows[th["block3_max_rows"]:]] + [e["company"] + " (top-up)" for e in topups],
        "mega_count_world": len(mega), "mega_ids": sorted(e["id"] for e in mega),
        "in_talks": [{"id": e["id"], "company": e["company"], "amount": amount_label(e)[0],
                      "valuation": fmt(e["valuation"]["amount"], e["valuation"]["currency"], e["valuation"].get("qualifier")) if e.get("valuation") else None,
                      "families": e["families"], "status": e["status"], "status_note": e.get("status_note")} for e in talks[:th["block3_talks_max"]]],
    }

    # ---- block 1: the week's story ----
    b1 = None
    cands = sorted(wk, key=lambda e: (-e["n_families"], e["first_seen"]))
    if cands:
        top = cands[0]
        ed1 = editorial.get("block1") or {}
        ed1_ok = (ed1.get("company"), ed1.get("event_type")) == (top["company"], top["event_type"])
        b1 = {"id": top["id"], "company": top["company"], "event_type": top["event_type"],
              "families": top["families"], "n_families": top["n_families"], "dots": dots(top["n_families"]),
              "status_history": top["status_history"], "new_statuses": new_statuses_in_week(top, monday, sunday, prior),
              "title": ed1.get("title") if ed1_ok else None,
              "facts": ed1.get("facts", []) if ed1_ok else [],
              "for_us": ed1.get("for_us") if ed1_ok else None,
              "runner_up": {"company": cands[1]["company"], "n_families": cands[1]["n_families"]} if len(cands) > 1 else None}

    # ---- block 4: exits and new funds ----
    # tech or VC-backed targets only: an acquisition the extractor could not place in a tech area is left out
    acqs = [e for e in wk if e["event_type"] == "acquisition" and not e["is_pe_buy_and_build"]
            and e["status"] not in ("refused", "abandoned") and e.get("tech_area") not in (None, "other")]

    def acq_row(e):
        return {"id": e["id"], "acquirer": e.get("acquirer"), "target": e["company"],
                "price": fmt(e["price"]["amount"], e["price"]["currency"], e["price"].get("qualifier")) if e.get("price") else None,
                "price_usd": to_usd(e["price"]["amount"], e["price"]["currency"], fx_log) if e.get("price") else None,
                "consideration": e.get("consideration"), "status": e["status"], "stake": e.get("stake"), "status_note": e.get("status_note"),
                "families": e["families"], "n_families": e["n_families"], "dots": dots(e["n_families"]),
                "description": (editorial.get("descriptions") or {}).get(e["company"]) or e.get("description"),
                "note": (editorial.get("block4_notes") or {}).get(e["company"], {}).get("text"),
                "confirmed_by_company": e["confirmed_by_company"]}

    confirmed = [e for e in acqs if e["status"] in DONE_ACQ and e["n_families"] >= th["confirmed_min_families"]]
    # single-source reports need a named buyer; a financial buyer (private equity) is listed only with a stated price
    single = [e for e in acqs if e not in confirmed and e.get("acquirer")
              and (e.get("acquirer_type") != "financial" or e.get("price"))]
    confirmed.sort(key=lambda e: -(to_usd((e.get("price") or {}).get("amount"), (e.get("price") or {}).get("currency")) or 0))
    single.sort(key=lambda e: (-(to_usd((e.get("price") or {}).get("amount"), (e.get("price") or {}).get("currency")) or 0),
                               e["status"] not in OPEN_ACQ, e["company"].lower()))
    ipos = [e for e in wk if e["event_type"] == "ipo" and (not b1 or e["id"] != b1["id"])
            and e["n_families"] >= th["confirmed_min_families"]
            and any(h["status"] in IPO_SHOWN for h in new_statuses_in_week(e, monday, sunday, prior))]
    # venture and growth funds only: buyout and other private-equity funds (strategy "other") are left out
    funds = [e for e in wk if e["event_type"] == "fund" and e["status"] in FUND_CLOSED and e.get("fund_size")
             and e.get("fund_strategy") not in (None, "other")]

    def fund_row(e):
        geo = (e.get("fund_geography") or "")
        return {"id": e["id"], "firm": e["company"], "fund_name": e.get("fund_name"),
                "size": fmt(e["fund_size"]["amount"], e["fund_size"]["currency"], e["fund_size"].get("qualifier")),
                "strategy": e.get("fund_strategy"), "geography": e.get("fund_geography"), "focus": e.get("fund_focus"), "description": (editorial.get("descriptions") or {}).get(e["company"]),
                "european_early": e.get("fund_strategy") == "early_stage" and (bool(re.search(r"europ", geo, re.I)) or is_europe(e)),
                "families": e["families"], "n_families": e["n_families"], "dots": dots(e["n_families"]),
                "note": (editorial.get("fund_notes") or {}).get(e["company"], {}).get("text"), "status": e["status"],
                "size_usd": to_usd(e["fund_size"]["amount"], e["fund_size"]["currency"], fx_log)}

    fund_rows = sorted([fund_row(e) for e in funds], key=lambda r: (not r["european_early"], -r["n_families"], -(r["size_usd"] or 0)))
    full_max = th["block4_single_full_max"]
    block4 = {
        "confirmed": [acq_row(e) for e in confirmed],
        "single_source": [acq_row(e) for e in single[:full_max]],
        "single_source_more": [acq_row(e) for e in single[full_max:]],
        "ipos": [{"id": e["id"], "company": e["company"], "status": e["status"], "families": e["families"],
                  "dots": dots(e["n_families"])} for e in ipos],
        "funds_european_early": [r for r in fund_rows if r["european_early"]],
        "funds_other": [r for r in fund_rows if not r["european_early"]],
    }

    # ---- block 5 and footer ----
    block5 = editorial.get("block5")
    foot = footer_counts(issues)
    ref = run_date or sunday
    blocks = {
        "week": {"monday": monday, "sunday": sunday, "iso_week": monday.isocalendar().week, "iso_year": monday.isocalendar().year,
                 "label": f"{monday.day}–{sunday.day} {sunday.strftime('%b %Y')}" if monday.month == sunday.month
                 else f"{monday.day} {monday.strftime('%b')}–{sunday.day} {sunday.strftime('%b %Y')}"},
        "headline": editorial.get("headline"),
        "block1": b1, "block2": block2, "block3": block3, "block4": block4, "block5": block5,
        "footer": {**foot, "next_price_check": fmt_day(first_monday_on_or_after(ref)).split(" ", 1)[1],
                   "withheld": 0},
        "fx_log": fx_log,
        "context_note": editorial.get("context_note"),
    }
    return blocks


def status_snapshot(events, prior=None):
    """For summary.json: every status each event has reached, so later weeks can tell new from old."""
    snap = {k: list(v) for k, v in (prior or {}).items()}
    for e in events:
        k = event_key(e)
        cur = snap.setdefault(k, [])
        for h in e["status_history"]:
            if h["status"] not in cur:
                cur.append(h["status"])
    return snap
