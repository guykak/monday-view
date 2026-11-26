"""Money helpers: original currency for display, USD only for thresholds (pitfall 13)."""
from . import config

SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£"}


def to_usd(amount, currency, fx_log=None):
    """Convert for threshold and median use only. Every non-USD use is appended to fx_log."""
    if amount is None or not currency:
        return None
    fx = config.settings()["fx"]
    rate = fx["usd_per"].get(currency)
    if rate is None:
        if fx_log is not None:
            fx_log.append({"currency": currency, "rate": None, "note": "no rate: not compared"})
        return None
    if currency != "USD" and fx_log is not None:
        entry = {"currency": currency, "usd_per_unit": rate, "as_of": fx["as_of"]}
        if entry not in fx_log:
            fx_log.append(entry)
    return amount * rate


def _num(x):
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s


def fmt(amount, currency, qualifier=None):
    """'$110M', '$5B', '€6m', '€1bn', '$1B+', '~$1.5B' as in the approved sample:
    dollars use M/B, other currencies use m/bn."""
    if amount is None:
        return None
    sym = SYMBOL.get(currency, (currency or "") + " ")
    usd = currency == "USD"
    if amount >= 1e9:
        body = _num(amount / 1e9) + ("B" if usd else "bn")
    elif amount >= 1e6:
        body = _num(amount / 1e6) + ("M" if usd else "m")
    elif amount >= 1e3:
        body = _num(amount / 1e3) + ("K" if usd else "k")
    else:
        body = _num(amount)
    out = sym + body
    if qualifier in ("at_least", "more_than"):
        out += "+"
    elif qualifier == "about":
        out = "~" + out
    elif qualifier == "up_to":
        out = "up to " + out
    return out
