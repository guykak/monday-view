"""Week maths and story dating. All local times are Europe/Athens via zoneinfo (pitfalls 4-7)."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ATHENS = ZoneInfo("Europe/Athens")

# Families whose email goes out in the morning and recaps the previous day.
MORNING_DAILY_FAMILIES = {"Techmeme"}


def to_athens(dt):
    if dt.tzinfo is None:
        raise ValueError("naive datetime: every timestamp must carry a zone")
    return dt.astimezone(ATHENS)


def parse_ts(s):
    """ISO 8601 timestamp -> aware datetime (UTC if 'Z')."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def week_label(d):
    iso = d.isocalendar()
    return f"W{iso.week:02d}"


def week_key(d):
    iso = d.isocalendar()
    return (iso.year, iso.week)


def report_week(run_dt):
    """Pitfall 5: report week = ISO week of (run date - 1 day), Athens time.
    Returns (iso_year, iso_week, monday, sunday)."""
    local = to_athens(run_dt).date() - timedelta(days=1)
    iso = local.isocalendar()
    monday = date.fromisocalendar(iso.year, iso.week, 1)
    return iso.year, iso.week, monday, monday + timedelta(days=6)


def week_bounds(iso_year, iso_week):
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    return monday, monday + timedelta(days=6)


def first_cutoff(run_dt, at="06:00"):
    """First run only: the previous Monday at `at`, Athens, returned in UTC."""
    local = to_athens(run_dt)
    this_monday = local.date() - timedelta(days=local.weekday())
    prev_monday = this_monday - timedelta(days=7)
    hh, mm = map(int, at.split(":"))
    return datetime.combine(prev_monday, time(hh, mm), tzinfo=ATHENS).astimezone(timezone.utc)


def collection_window(run_dt, stored_cutoff=None, first_at="06:00"):
    """Pitfall 6: collect from the stored cut-off (UTC) to the run start. No fixed 7-day window,
    so summer-time changes and late runs neither overlap nor leave a gap."""
    start = parse_ts(stored_cutoff) if isinstance(stored_cutoff, str) else stored_cutoff
    if start is None:
        start = first_cutoff(run_dt, first_at)
    end = run_dt.astimezone(timezone.utc)
    if start >= end:
        raise ValueError("cut-off is not before the run start")
    return start.astimezone(timezone.utc), end


def story_date(story, issue_date, family, cadence="daily"):
    """Pitfall 4: a story is dated by its own event. An undated story takes the issue date in an
    ordinary daily, and the issue date - 1 day in an issue that looks back: a morning daily
    (Techmeme recaps the previous US day) or a weekly digest (it covers the days before it was
    sent, so a Monday digest's undated items belong to the week that just ended).
    A story the issue itself calls older ("recap") goes back a further week when undated.
    Returns (date, basis)."""
    if isinstance(issue_date, str):
        issue_date = date.fromisoformat(issue_date)
    sd = story.get("story_date")
    if sd and story.get("date_basis", "stated") == "stated":
        d = date.fromisoformat(sd)
        # A stated date after the issue went out is an extraction error; fall back.
        if d <= issue_date:
            return d, "stated"
    if story.get("timing") == "recap":
        return issue_date - timedelta(days=8), "recap_undated"
    if family in MORNING_DAILY_FAMILIES or cadence == "weekly":
        return issue_date - timedelta(days=1), "issue_date_minus_1"
    return issue_date, "issue_date"


def in_week(d, monday, sunday):
    return monday <= d <= sunday


def fmt_day(d):
    """'Wed 18 Nov' (CLAUDE.md rule 8)."""
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def first_monday_on_or_after(d):
    """Next monthly price check: the first Monday of the next month after d."""
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    first = date(y, m, 1)
    return first + timedelta(days=(7 - first.weekday()) % 7)
