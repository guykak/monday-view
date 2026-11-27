import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def story(company, event_type="round", status="closed", **kw):
    """A minimal extracted story for synthetic tests."""
    s = {"headline": f"{company} news", "quote": kw.pop("quote", f"{company} raised money"), "story_date": None,
         "date_basis": "undated", "timing": "new", "event_type": event_type, "status": status,
         "mention_type": "story", "company": company, "confidence": "high"}
    if event_type == "round":
        s.update(stage="seed", equity_amount=5_000_000, currency="USD", tech_area="ai_applications", hq=[{"city": "Paris", "country": "FR"}])
    if event_type == "acquisition":
        s.update(tech_area="ai_applications", acquirer_type="company")
    s.update(kw)
    return s


def issue(family, issue_date, stories, letter=None, sent_at=None, n=[0]):
    n[0] += 1
    return {"schema_version": 1, "message_id": f"<m{n[0]}@x>", "family": family, "letter": letter or family,
            "issue_date": issue_date, "sent_at": sent_at or f"{issue_date}T08:00:00.000Z", "subject": "s",
            "stories": stories, "_file": f"{issue_date}_{family}_{n[0]}.json"}


def prepared(issues):
    """Run the same cleaning the build does on synthetic issues."""
    from mondayview import validate
    out = []
    for i in issues:
        sts = []
        for k, s in enumerate(i["stories"]):
            c, _ = validate.clean_story(s)
            c["_idx"] = k
            sts.append(c)
        out.append(dict(i, stories=sts))
    return out


def build_blocks(issues, week="2026-W47", prior=None, editorial=None):
    from mondayview import blocks, merge, week as wk
    y, w = week.split("-W")
    mon, sun = wk.week_bounds(int(y), int(w))
    issues = prepared(issues)
    events = merge.merge(issues)
    meta = [{"family": i["family"], "letter": i["letter"]} for i in issues]
    return events, blocks.build(events, meta, mon, sun, prior=prior, editorial=editorial or {})


@pytest.fixture(scope="session")
def expected():
    return json.loads((ROOT / "tests/fixtures/w47_expected.json").read_text(encoding="utf-8"))


def _w47(extracted_dir, editorial_path):
    from mondayview import build, render_email
    il = build.load_issue_list(ROOT / "tests/fixtures/w47_issues.json")
    ed = json.loads(Path(editorial_path).read_text(encoding="utf-8")) if Path(editorial_path).exists() else {}
    hist = ROOT / "history/W47"
    drops = ()
    if (hist / "factcheck.json").exists():          # the fixture is the post-fact-check build, as Guy sees it
        rc = json.loads((hist / "factcheck_recheck.json").read_text()) if (hist / "factcheck_recheck.json").exists() else None
        drops = build.drops_from(json.loads((hist / "factcheck.json").read_text()), rc)
    res = build.run("2026-W47", extracted_dir, il, editorial=ed, drop_ids=drops)
    res["md"], res["compact"] = render_email.fit_md(res["blocks"])
    res["html"] = render_email.render_html(res["blocks"], res["compact"])
    res["text"] = render_email.render_text(res["blocks"])
    res["editorial"] = ed
    return res


@pytest.fixture(scope="session")
def w47():
    """The W47 regression fixture: the committed extraction of the 54 counting-set issues."""
    return _w47(ROOT / "history/W47/extracted", ROOT / "history/W47/editorial.json")
