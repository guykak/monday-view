"""Render blocks.json as markdown (view.md), HTML email (640 px, inline styles, no images) and text.

Nothing here computes a number: it prints what blocks.py computed and the editor's sourced words.
"""
import html
import math
from datetime import date
from pathlib import Path

from .week import fmt_day

LEGEND = ("Each ● is one source family (Sifted, TLDR, Term Sheet, Techmeme, etc.) carrying the item. "
          "●●●●● means 5 or more. Breadth of coverage, not importance: a press release reprinted by "
          "three deal digests gets three dots.")

AREA_SHORT = {"ai_infrastructure": ("AI infrastructure", "compilers, edge, model training")}


def _d(x):
    return date.fromisoformat(x) if isinstance(x, str) else x


def _join(items, last=" and "):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + last + items[-1]


def _sentence(s):
    s = (s or "").strip()
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    return s if s[-1] in ".!?" else s + "."


def round_line(r, max_leads=2):
    """'**Daisytuner** (Darmstadt), €6m seed, Elaia and LEA Ventures. Description. ●●●'"""
    head = f"**{r['company']}**" + (f" ({r['hq']})" if r["hq"] else "")
    bits = []
    if r["amount"]:
        bits.append(r["amount"] + (f" {r['stage']}" if r["stage"] and not r["mixed"] else ""))
    elif r["stage"]:
        bits.append(r["stage"])
    if r["leads"] and max_leads:
        bits.append(_join(r["leads"][:max_leads]))
    line = ", ".join([head] + bits) + "."
    if r.get("description"):
        line += " " + _sentence(r["description"])
    return line + " " + r["dots"]


def acq_line(a, with_source=False):
    name = f"{a['acquirer']} → {a['target']}" if a.get("acquirer") else a["target"]
    bits = []
    if a.get("price"):
        p = a["price"]
        if a.get("consideration") == "stock":
            p += " in stock"
        elif a.get("consideration") == "cash_and_stock":
            p += " in cash and stock"
        elif a.get("consideration") == "cash":
            p += " cash"
        bits.append(p)
    if a["status"] in ("in_talks", "rumour"):
        bits.append("talks")
    elif a["status"] == "bid":
        bits.append("bid")
    s = name + (", " + ", ".join(bits) if bits else "")
    if with_source:
        return s + f" ({_join(a['families'], ', ')})"
    return s


def fund_phrase(f):
    desc = []
    strat = {"early_stage": "early stage", "multi_stage": "venture and growth", "growth": "growth",
             "late_stage": "late stage", "secondaries": "secondaries", "other": None}.get(f.get("strategy"))
    if f["european_early"]:
        desc.append("European early stage")
    elif f.get("description"):
        desc.append(f["description"])
    else:
        d = " ".join(x for x in [f.get("geography"), strat] if x)
        if f.get("focus"):
            d = (d + ", " if d else "") + f["focus"]
        desc.append(d)
    fn = f.get("fund_name") or ""
    if fn.lower().startswith(f["firm"].split()[0].lower()):
        name = fn
    elif fn and not f["european_early"] and len(fn.split()) <= 3:
        name = f"{f['firm']} {fn}"
    else:
        name = f["firm"]
    return name, f["size"], "; ".join(x for x in desc if x)


# ------------------------------------------------------------------ markdown

def render_md(b, compact=0):
    """How much is said shrinks with `compact` until the view fits the word limit (fit_md).
    0: everything.
    1: single-source overflow as names grouped by source; areas with one round share a row.
    2: also one notable-team entry; no description for one-dot rounds.
    3: also four single-source deals in full; descriptions for 3+ dots only; one lead investor.
    4: also no lead investors for rounds under 3 dots.
    Counts, required lines and every named deep-tech round stay at every level."""
    L = []
    L.append(f"# Monday view — week of {b['week']['label']}")
    L.append("")
    if b.get("headline"):
        L.append(f"**{b['headline']}**")
        L.append("")
    L.append(LEGEND)
    L.append("")
    L.append("---")
    L.append("")
    b1 = b.get("block1")
    if b1:
        title = b1.get("title") or b1["company"]
        L.append(f"## 1. The week's story: {title} {b1['dots']} ({b1['n_families']} families)")
        L.append("")
        for f in b1.get("facts", []):
            L.append(f"- **{fmt_day(_d(f['date']))}:** {f['text']}")
        if b1.get("for_us"):
            L.append("")
            L.append(f"For us: {b1['for_us']}")
        L.append("")
    b2 = b["block2"]
    L.append("## 2. Early-stage rounds (pre-seed to Series A, all sizes)")
    L.append("")
    mix = b2["mix_world"]
    s = f"**{b2['count_world']} rounds reported, {b2['count_europe']} in Europe.**"
    if mix:
        s += f" {mix['family']} carried {mix['carried']} of the {mix['total']}; the total is {mix['without']} without it."
    if b.get("context_note"):
        s += " " + b["context_note"]
    L.append(s)
    L.append("")
    L.append("| Europe, by area | Rounds |")
    L.append("|---|---|")
    singles = [a for a in b2["area_table"] if a["rounds"] == 1] if compact >= 1 else []
    for a in b2["area_table"]:
        if a not in singles or len(singles) < 2:
            L.append(f"| {a['label']} | {a['rounds']} |")
    if len(singles) >= 2:
        L.append(f"| {'; '.join(a['label'] for a in singles)} | 1 each |")
    L.append("")
    n_big = len(b2["big_early_europe"])
    L.append(f"{b2['area_total']} = {b2['count_europe']} European rounds less the {n_big} of $50M or more"
             + (" (section 3)" if n_big else "") + f". Rest of world: {b2['big_early_rest_of_world']} early rounds of $50M or more.")
    L.append("")
    if b2["named"]:
        L.append("**European deep tech:**")
        for r in b2["named"]:
            bare = (compact >= 2 and r["n_families"] == 1) or (compact >= 3 and r["n_families"] < 3)
            leads = 0 if compact >= 4 and r["n_families"] < 3 else 1 if compact >= 3 else 2
            L.append("- " + round_line({**r, "description": None} if bare else r, leads))
        L.append("")
    if b2["notable_team"]:
        parts = []
        for r in (b2["notable_team"][:1] if compact >= 2 else b2["notable_team"]):
            line = round_line({**r, "description": None}, 1 if compact >= 3 else 2)
            dots = line.rsplit(" ", 1)[1]
            parts.append(f"{line.rsplit(' ', 1)[0]} {_sentence(r['founder_background'])} {dots}")
        L.append("Notable team: " + " ".join(parts))
        L.append("")
    b3 = b["block3"]
    L.append("## 3. Big rounds and marks")
    L.append("")
    if b3["rows"]:
        L.append("| Company | Round | Valuation | Sources |")
        L.append("|---|---|---|---|")
        for r in b3["rows"]:
            who = r["company"] + (f" ({r['hq']})" if r["hq"] else "")
            L.append(f"| {who} | {r['amount']}{' ' + r['stage'] if r['stage'] else ''} | {r['valuation'] or '–'} | {r['dots']} |")
        L.append("")
    s = ""
    if b3["more"]:
        s += f"Also $50M or more in Europe: {_join(b3['more'], ', ')}. "
    s += f"{b3['mega_count_world']} rounds of $100M or more were reported, equity only."
    if b3["in_talks"]:
        s += " In talks, not closed: " + ", ".join(
            t["company"] + (f" {t['amount']}" if t["amount"] else "") + (f" at {t['valuation']}" if t["valuation"] else "")
            for t in b3["in_talks"]) + "."
    L.append(s)
    L.append("")
    b4 = b["block4"]
    L.append("## 4. Exits and new funds")
    L.append("")
    for a in b4["confirmed"]:
        s = f"- **{acq_line(a).split(',')[0]}**"
        rest = acq_line(a)[len(acq_line(a).split(',')[0]):].lstrip(", ")
        s += (": " + rest if rest else "") + "."
        if a.get("note"):
            s += " " + _sentence(a["note"])
        L.append(s + " " + a["dots"])
    for i in b4["ipos"]:
        L.append(f"- IPO: {i['company']} {i['status']}. {i['dots']}")
    if b4["single_source"] or b4["single_source_more"]:
        L.append("- Single source, unconfirmed:")
        full = b4["single_source"][:4] if compact >= 3 else b4["single_source"]
        rest = b4["single_source"][len(full):] + b4["single_source_more"]
        for a in full:
            L.append("  - " + acq_line(a, with_source=True))
        if rest and compact >= 1:
            by_src = {}
            for a in rest:
                by_src.setdefault(_join(a["families"], ", "), []).append(a["target"])
            L.append("  - Also, one source each: " + "; ".join(f"{', '.join(v)} ({k})" for k, v in by_src.items()))
        elif rest:
            L.append("  - Also: " + "; ".join(acq_line(a, with_source=True) for a in rest))
    fe, fo = b4["funds_european_early"], b4["funds_other"]
    if fe or fo:
        parts = []
        for f in fe:
            name, size, desc = fund_phrase(f)
            parts.append(f"{name} closes {size} for {desc}" + (f", {f['note']}" if f.get("note") else "") + f". {f['dots']}")
        s = "- **Funds:** " + " ".join(parts)
        if fo:
            s += (" Also closed: " if fe else "Closed: ") + "; ".join(
                f"{fund_phrase(f)[0]} {f['size']}" + (f" ({fund_phrase(f)[2]})" if fund_phrase(f)[2] else "") + f" {f['dots']}" for f in fo) + "."
        L.append(s)
    L.append("")
    if b.get("block5") and b["block5"].get("text"):
        L.append("## 5. Market move")
        L.append("")
        L.append(b["block5"]["text"])
        L.append("")
    L.append("---")
    L.append("")
    L.append("*" + footer_text(b) + "*")
    return "\n".join(L) + "\n"


def footer_text(b):
    f = b["footer"]
    multi = [(k, v) for k, v in f["per_family"].items() if v > 1]
    ones = [k for k, v in f["per_family"].items() if v == 1]
    s = "Sources this week (issues): " + ", ".join(f"{k} {v}" for k, v in multi)
    if ones:
        s += "; others 1 each" if len(ones) > 3 else "; " + ", ".join(f"{k} 1" for k in ones)
    s += "."
    silent = f["silent_families"] + f["silent_letters"]
    if silent:
        s += f" {_join(silent)} sent none."
    if f.get("withheld"):
        s += f" {f['withheld']} items withheld after the fact-check."
    s += f" Next monthly price check: {f['next_price_check']}."
    return s


# ------------------------------------------------------------------ plain text

def render_text(b):
    md = fit_md(b)[0]
    out = []
    for line in md.split("\n"):
        if line.startswith("|---"):
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            line = "  " + "  ·  ".join(c for c in cells if c)
        line = line.replace("**", "").lstrip("#").strip() if line.startswith("#") else line.replace("**", "")
        if line.startswith("*") and line.endswith("*"):
            line = line.strip("*")
        out.append(line)
    return "\n".join(out)


# ------------------------------------------------------------------ HTML

INK, MUTE, RULE, BG, CARD, BLUE, GREY = "#1a1a1a", "#6b665e", "#d9d4c8", "#f8f6f1", "#ffffff", "#1f56a8", "#a8a39a"
SANS = "font-family:Helvetica,Arial,sans-serif;"
SERIF = "font-family:Georgia,'Times New Roman',serif;"


def e(s):
    return html.escape(str(s if s is not None else ""), quote=False)


def dots_html(n, cap=5):
    k = min(n, cap)
    return (f'<span style="color:{INK};letter-spacing:1px;">{"●" * k}</span>'
            f'<span style="color:{RULE};letter-spacing:1px;">{"●" * (cap - k)}</span>')


def _label(num, name):
    return (f'<tr><td style="padding:26px 0 2px 0;border-top:2px solid {INK};{SANS}font-size:11px;letter-spacing:1.5px;'
            f'color:{MUTE};text-transform:uppercase;">{num} · {e(name)}</td></tr>')


def _h(text):
    return f'<tr><td style="padding:0 0 10px 0;{SERIF}font-size:22px;line-height:27px;color:{INK};">{text}</td></tr>'


def _p(text, size=14, color=INK, pad="0 0 10px 0"):
    return f'<tr><td style="padding:{pad};{SANS}font-size:{size}px;line-height:{size + 7}px;color:{color};">{text}</td></tr>'


def _squares(n, color):
    cells = "".join(f'<td width="12" height="12" bgcolor="{color}" style="font-size:0;line-height:0;">&nbsp;</td><td width="3" style="font-size:0;">&nbsp;</td>'
                    for _ in range(n))
    return f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>{cells}</tr></table>'


def _bar(usd, lo=5e7, hi=1e10, width=250):
    w = max(8, int(width * (math.log10(max(usd, lo)) - math.log10(lo * 0.6)) / (math.log10(hi) - math.log10(lo * 0.6))))
    w = min(w, width)
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="{w}" height="14" bgcolor="{INK}" style="font-size:0;line-height:0;">&nbsp;</td></tr></table>')


def render_html(b):
    R = []
    R.append(f'<tr><td style="{SANS}font-size:11px;letter-spacing:1.5px;color:{MUTE};text-transform:uppercase;padding:0 0 6px 0;">'
             f'Monday view · week of {e(b["week"]["label"])}</td></tr>')
    if b.get("headline"):
        R.append(f'<tr><td style="{SERIF}font-size:26px;line-height:32px;color:{INK};padding:0 0 12px 0;"><b>{e(b["headline"])}</b></td></tr>')
    R.append(_p(e(LEGEND), 12, MUTE, "0 0 6px 0"))
    b1 = b.get("block1")
    if b1:
        R.append(_label(1, "The week's story"))
        R.append(_h(f'{e(b1.get("title") or b1["company"])} &nbsp;<span style="font-size:13px;">{dots_html(b1["n_families"])}</span>'
                    f' <span style="{SANS}font-size:12px;color:{MUTE};">{b1["n_families"]} families</span>'))
        rows = "".join(
            f'<tr><td width="92" valign="top" style="{SANS}font-size:13px;line-height:20px;color:{INK};padding:0 0 8px 0;"><b>{e(fmt_day(_d(f["date"])))}</b></td>'
            f'<td valign="top" style="{SANS}font-size:14px;line-height:20px;color:{INK};padding:0 0 8px 0;">{e(f["text"])}</td></tr>'
            for f in b1.get("facts", []))
        R.append(f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>')
        if b1.get("for_us"):
            R.append(f'<tr><td style="padding:4px 0 4px 12px;border-left:3px solid {BLUE};{SANS}font-size:14px;line-height:21px;color:{INK};">'
                     f'<b>For us:</b> {e(b1["for_us"])}</td></tr>')
    b2 = b["block2"]
    R.append(_label(2, "Early-stage rounds"))
    R.append(_h(f'Pre-seed to Series A: {b2["count_world"]} rounds, {b2["count_europe"]} in Europe'))
    mix = b2["mix_world"]
    s = ""
    if mix:
        s = f'<b>Source mix: {e(mix["family"])} carried {mix["carried"]} of the {mix["total"]}.</b> Without it the count is {mix["without"]}.'
    if b.get("context_note"):
        s += " " + e(b["context_note"])
    if s:
        R.append(_p(s, 13))
    R.append(f'<tr><td style="{SANS}font-size:11px;letter-spacing:1px;color:{BLUE};text-transform:uppercase;padding:4px 0 6px 0;"><b>Europe · under $50M · {b2["area_total"]} rounds</b></td></tr>')
    rows = ""
    for a in b2["area_table"]:
        name, sub = AREA_SHORT.get(a["area"], (a["label"], None))
        rows += (f'<tr><td width="230" style="{SANS}font-size:13px;line-height:17px;color:{INK};padding:3px 0;">{e(name)}'
                 + (f'<br><span style="font-size:11px;color:{MUTE};">{e(sub)}</span>' if sub else "")
                 + f'</td><td style="padding:3px 0;">{_squares(a["rounds"], BLUE)}</td>'
                 f'<td width="28" align="right" style="{SANS}font-size:13px;color:{INK};"><b>{a["rounds"]}</b></td></tr>')
    R.append(f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>')
    n_big = len(b2["big_early_europe"])
    R.append(_p(f'{b2["area_total"]} = {b2["count_europe"]} European rounds less the {n_big} of $50M or more'
                + (f' ({e(_join(b2["big_early_europe"], ", "))}; see block 3)' if n_big else "")
                + f'. Rest of world: {b2["big_early_rest_of_world"]} early rounds of $50M or more.', 12, MUTE, "6px 0 12px 0"))
    if b2["named"] or b2["notable_team"]:
        R.append(f'<tr><td style="{SANS}font-size:13px;color:{INK};padding:2px 0 6px 0;"><b>European deep tech this week</b> <span style="color:{MUTE};">· amount, stage, lead investors</span></td></tr>')
    for r in b2["named"] + [dict(x, _notable=True) for x in b2["notable_team"]]:
        top = INK if r.get("_notable") else BLUE
        desc = _sentence(r["founder_background"]) if r.get("_notable") else _sentence(r.get("description"))
        stage = ("in " + r["amount"].split(" in ", 1)[1]) if r["mixed"] else (r["stage"] or "")
        amt = r["amount"].split(" in ", 1)[0] if r["amount"] else ""
        R.append(
            f'<tr><td style="padding:0 0 8px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{CARD}" '
            f'style="border:1px solid {RULE};border-top:3px solid {top};"><tr><td style="padding:8px 12px 9px 12px;">'
            + (f'<div style="{SANS}font-size:10px;letter-spacing:1.5px;color:{MUTE};">NOTABLE TEAM</div>' if r.get("_notable") else "")
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td style="{SANS}font-size:15px;color:{INK};"><b>{e(r["company"])}</b>' + (f' <span style="color:{MUTE};">· {e(r["hq"])}</span>' if r["hq"] else "")
            + f'</td><td align="right" style="font-size:12px;">{dots_html(r["n_families"])}</td></tr>'
            f'<tr><td style="{SERIF}font-size:18px;line-height:24px;color:{INK};">{e(amt)}</td>'
            f'<td align="right" style="{SANS}font-size:12px;color:{MUTE};">{e(stage)}</td></tr></table>'
            f'<div style="{SANS}font-size:13px;line-height:18px;color:{INK};">{e(desc)}</div>'
            + (f'<div style="{SANS}font-size:12px;line-height:17px;color:{MUTE};">Lead: {e(_join(r["leads"]))}</div>' if r["leads"] else "")
            + '</td></tr></table></td></tr>')
    b3 = b["block3"]
    R.append(_label(3, "Big rounds and marks"))
    R.append(_h("Round size and stated valuation"))
    R.append(_p(f'<b>{b3["mega_count_world"]} rounds of $100M or more</b> were reported worldwide, equity only. European rounds of $50M or more are below; bar = round size, log scale.', 13))
    rows = ""
    for r in b3["rows"]:
        rows += (f'<tr><td width="170" valign="top" style="{SANS}font-size:14px;line-height:17px;color:{INK};padding:5px 0;"><b>{e(r["company"])}</b><br>'
                 f'<span style="font-size:11px;color:{MUTE};">{e(r["hq"])}</span></td>'
                 f'<td valign="top" style="padding:6px 0 5px 0;">{_bar(r["usd"])}'
                 f'<div style="{SANS}font-size:13px;line-height:18px;color:{INK};"><b>{e(r["amount"])}{" " + e(r["stage"]) if r["stage"] else ""}</b>'
                 + (f' <span style="color:{MUTE};">◇ valued at {e(r["valuation"])}</span>' if r["valuation"] else "")
                 + f'</div></td><td width="62" valign="top" align="right" style="font-size:12px;padding:6px 0;">{dots_html(r["n_families"])}</td></tr>')
    R.append(f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>')
    if b3["more"]:
        R.append(_p("Also $50M or more in Europe: " + e(_join(b3["more"], ", ")) + ".", 13))
    if b3["in_talks"]:
        R.append(_p(f'<span style="font-size:11px;letter-spacing:1px;color:{MUTE};text-transform:uppercase;"><b>In talks, not closed</b></span><br>'
                    + "; ".join(f'<b>{e(t["company"])}</b>' + (f' {e(t["amount"])}' if t["amount"] else "") + (f' at {e(t["valuation"])}' if t["valuation"] else "")
                                for t in b3["in_talks"]) + ".", 13, INK, "8px 0 6px 0"))
    b4 = b["block4"]
    R.append(_label(4, "Exits and new funds"))
    R.append(_h("Who sold, who raised a fund"))
    for a in b4["confirmed"]:
        line = acq_line(a)
        head, _, rest = line.partition(", ")
        R.append(f'<tr><td style="padding:0 0 9px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                 f'<td style="{SANS}font-size:14px;line-height:20px;color:{INK};"><b>{e(head)}</b>' + (f': {e(rest)}.' if rest else ".")
                 + (f' {e(_sentence(a["note"]))}' if a.get("note") else "")
                 + f'</td><td width="62" valign="top" align="right" style="font-size:12px;">{dots_html(a["n_families"])}</td></tr></table></td></tr>')
    for i in b4["ipos"]:
        R.append(_p(f'IPO: <b>{e(i["company"])}</b> {e(i["status"])}.', 14))
    ss = b4["single_source"]
    if ss or b4["single_source_more"]:
        items = "".join(f'<div style="padding:0 0 3px 0;">· {e(acq_line(a, with_source=True))}</div>' for a in ss)
        if b4["single_source_more"]:
            items += '<div style="padding:0 0 3px 0;">· Also: ' + e("; ".join(acq_line(a, with_source=True) for a in b4["single_source_more"])) + "</div>"
        R.append(f'<tr><td style="padding:2px 0 10px 0;{SANS}font-size:13px;line-height:19px;color:{INK};">'
                 f'<span style="font-size:11px;letter-spacing:1px;color:{MUTE};text-transform:uppercase;"><b>Single source, unconfirmed</b></span>{items}</td></tr>')
    funds = b4["funds_european_early"] + b4["funds_other"]
    if funds:
        rows = ""
        for f in funds:
            name, size, desc = fund_phrase(f)
            rows += (f'<tr><td style="{SANS}font-size:13px;line-height:19px;color:{INK};padding:2px 0;"><b>{e(name)}</b> {e(size)}'
                     f' <span style="color:{MUTE};">· {e(desc)}{", " + e(f["note"]) if f.get("note") else ""}</span></td>'
                     f'<td width="62" align="right" style="font-size:12px;">{dots_html(f["n_families"])}</td></tr>')
        R.append(f'<tr><td style="{SANS}font-size:11px;letter-spacing:1px;color:{MUTE};text-transform:uppercase;padding:2px 0 2px 0;"><b>Funds closed</b></td></tr>')
        R.append(f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>')
    if b.get("block5") and b["block5"].get("text"):
        R.append(_label(5, "Market move"))
        R.append(_p(e(b["block5"]["text"]), 14, INK, "6px 0 10px 0"))
    R.append(f'<tr><td style="padding:14px 0 0 0;border-top:1px solid {RULE};{SANS}font-size:11px;line-height:17px;color:{MUTE};">{e(footer_text(b))}</td></tr>')
    body = "".join(R)
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Monday view</title></head><body style="margin:0;padding:0;background:{BG};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{BG}"><tr><td align="center" style="padding:20px 12px;">'
            f'<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" style="width:640px;max-width:640px;">{body}</table>'
            '</td></tr></table></body></html>')


def fit_md(blocks, words_max=None):
    """The fullest version that fits the word limit. Returns (markdown, compact level)."""
    from . import config
    words_max = words_max or config.settings()["thresholds"]["words_max"]
    for level in range(5):
        md = render_md(blocks, level)
        if len(md.split()) <= words_max:
            return md, level
    return md, 4


def write_all(blocks, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md, level = fit_md(blocks)
    blocks["compact_level"] = level
    (out / "view.md").write_text(md, encoding="utf-8")
    (out / "email.html").write_text(render_html(blocks), encoding="utf-8")
    (out / "email.txt").write_text(render_text(blocks), encoding="utf-8")
    return md
