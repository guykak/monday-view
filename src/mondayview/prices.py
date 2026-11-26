"""Monthly price check (Phase 0b): 4-week rolling median round size. Pitfalls 11 and 13.

Reported rounds only. Combined rounds (one figure covering seed + Series A) are excluded,
and n is shown for every split.
"""
from statistics import median

from .merge import is_europe
from .money import to_usd

US = {"US"}


def region(event):
    if is_europe(event):
        return "Europe"
    if any(h["country"] in US for h in event["hq"]):
        return "US"
    return None


def medians(events, stages=("seed", "series_a"), fx_log=None):
    """-> {(stage, region): {"n": n, "median_usd": m or None, "excluded_combined": k}}"""
    out = {}
    for st in stages:
        for reg in ("Europe", "US"):
            pool = [e for e in events if e["event_type"] == "round" and e["status"] in ("closed", "announced")
                    and e.get("stage") == st and region(e) == reg and e.get("equity_amount")]
            combined = [e for e in pool if e.get("is_combined_round")]
            vals = [to_usd(e["equity_amount"], e["currency"], fx_log) for e in pool if not e.get("is_combined_round")]
            vals = [v for v in vals if v]
            out[(st, reg)] = {"n": len(vals), "median_usd": median(vals) if vals else None,
                              "excluded_combined": len(combined), "label": "reported rounds"}
    return out
