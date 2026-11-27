"""Synthetic tests for run modes, labels, send and commit guards, and the plan (spec §1-§3, §5)."""
from datetime import datetime, timezone

import pytest

from mondayview import config, guards, plan


def settings(**kw):
    s = dict(config.settings())
    s.update(kw)
    return s


HTML = "<html><body><table><tr><td>x</td></tr></table></body></html>"


def test_default_mode_is_dry_run_with_one_test_recipient():
    # Guy confirmed the address on 27 Nov 2026; the default mode stays dry-run.
    s = config.settings()
    assert s["mode"] == "dry-run" and s["subject_prefix"].startswith("[TEST]")
    r = s["recipient"]
    assert isinstance(r, str) and r.count("@") == 1 and not any(c in r for c in ",; ")


def test_dry_run_plan_sends_nothing_and_writes_under_dryrun():
    p = plan.make_plan(datetime(2026, 11, 23, 4, 11, tzinfo=timezone.utc))
    assert (p["mode"], p["week"], p["sends"], p["labels_issues"], p["advances_cutoff"]) == ("dry-run", "W47", False, False, False)
    assert p["history_dir"] == "history/dryrun/W47"
    sp = guards.make_send_plan("dry-run", "W47", HTML, "x")
    assert sp["send"] is False and sp["labels"] == []
    with pytest.raises(guards.GuardError):
        guards.check_send(sp, HTML, "x", settings(recipient="a@example.org"))


def test_test_mode_plan_uses_fixed_week_and_test_folder():
    p = plan.make_plan(datetime(2026, 12, 9, 10, 0, tzinfo=timezone.utc), "mode=test")
    assert (p["week"], p["history_dir"], p["sends"], p["advances_cutoff"]) == ("W47", "history/test/W47", True, False)
    p = plan.make_plan(datetime(2026, 12, 9, 10, 0, tzinfo=timezone.utc), "mode=test week=W46")
    assert p["week"] == "W46" and p["monday"] == "2026-11-09"


def test_scheduled_plan_window_from_cutoff():
    p = plan.make_plan(datetime(2026, 11, 23, 4, 11, tzinfo=timezone.utc), "mode=scheduled",
                       prev_summary={"cutoff_utc": "2026-11-16T04:11:00+00:00"})
    assert p["window_utc"] == ["2026-11-16T04:11:00+00:00", "2026-11-23T04:11:00+00:00"]
    assert p["new_cutoff_utc"] == "2026-11-23T04:11:00+00:00" and p["history_dir"] == "history/W47"
    first = plan.make_plan(datetime(2026, 11, 23, 4, 11, tzinfo=timezone.utc), "mode=scheduled")
    assert first["window_utc"][0] == "2026-11-16T04:00:00+00:00"      # previous Monday 06:00 Athens


def test_send_guard_passes_only_the_exact_planned_email():
    s = settings(recipient="reader@example.org")
    sp = guards.make_send_plan("test", "W47", HTML, "plain", "20261126T101500Z", s)
    assert sp["subject"] == "[TEST] Monday view W47"
    assert guards.check_send(sp, HTML, "plain", s)
    for bad in (dict(sp, recipient="other@example.org"), dict(sp, cc=["x@example.org"]), dict(sp, subject="Monday view W47"),
                dict(sp, labels=["monday-view", "mv-W47"]), dict(sp, recipient="reader@example.org, x@example.org")):
        with pytest.raises(guards.GuardError):
            guards.check_send(bad, HTML, "plain", s)
    with pytest.raises(guards.GuardError):
        guards.check_send(sp, HTML + " ", "plain", s)            # HTML changed after the plan
    with pytest.raises(guards.GuardError):
        guards.check_send(sp, HTML, "", s)                       # no text part
    with pytest.raises(guards.GuardError):
        guards.check_send(sp, HTML, "plain", settings(recipient=""))   # address not confirmed
    big = "<html>" + "x" * 40000 + "</html>"
    with pytest.raises(guards.GuardError):
        guards.check_send(guards.make_send_plan("test", "W47", big, "p", "20261126T101500Z", s), big, "p", s)
    img = HTML.replace("x", '<img src="a.png">')
    with pytest.raises(guards.GuardError):
        guards.check_send(guards.make_send_plan("test", "W47", img, "p", "20261126T101500Z", s), img, "p", s)


def test_scheduled_labels_and_post_send_check():
    s = settings(recipient="reader@example.org")
    sp = guards.make_send_plan("scheduled", "W48", HTML, "plain", settings=s)
    assert sp["labels"] == ["monday-view", "mv-W48"] and guards.check_send(sp, HTML, "plain", s)
    assert guards.check_sent(sp, {"to": ["reader@example.org"], "subject": sp["subject"], "html": HTML}) == []
    assert guards.check_sent(sp, {"to": ["x@example.org"], "subject": "s", "html": "h", "cc": ["c@example.org"]}) == ["recipient", "cc/bcc present", "subject", "html hash"]


def test_commit_guard_paths():
    assert guards.check_staged_paths(["history/W47/blocks.json", "logs/W47.json"])
    for bad in (["src/mondayview/blocks.py"], ["history/W47/x.json", "config/settings.yaml"], ["README.md"]):
        with pytest.raises(guards.GuardError):
            guards.check_staged_paths(bad)
    for raw in (["history/W47/raw/a.txt"], ["history/W47/bodies/a.txt"], ["logs/a.eml"]):
        with pytest.raises(guards.GuardError):
            guards.check_staged_paths(raw)
    assert guards.check_staged_paths(["src/mondayview/blocks.py", "tests/x.py"], mode="dev")


def test_budget_holds():
    assert guards.budget_check(54, 2, 60, 40, 30) == ("ok", [])
    assert guards.budget_check(54, 6, 60, 40, 30)[0] == "hold"       # >10% extraction failures
    assert guards.budget_check(54, 0, 70, 40, 30)[0] == "hold"       # issues + 15 agents
    assert guards.budget_check(54, 0, 60, 81, 30)[0] == "hold"       # fact-check re-opens
    assert guards.budget_check(54, 0, 60, 40, 46)[0] == "hold"       # wall time


def test_body_helper_refuses_to_write_outside_run_or_scratch(tmp_path):
    import json
    from mondayview import body
    src = tmp_path / "saved.json"
    src.write_text(json.dumps({"messageId": "<a@b>", "timestamp": "t", "from": "f", "subject": "s",
                               "text": "Acme raised &euro;5m ( https://x.example/track ) today.\n" + "y" * 3000, "html": "<p>big</p>"}))
    assert body.main(["body.py", str(src), str(tmp_path / "out.txt")]) == 2
    out = tmp_path / "run" / "b.txt"
    assert body.main(["body.py", str(src), str(out)]) == 0
    text = out.read_text()
    assert "Acme raised €5m today." in text and "http" not in text and "<p>" not in text
    assert max(len(l) for l in text.split("\n")) <= body.MAX_LINE


def test_collect_reads_a_saved_agentmail_listing_and_keeps_no_body_text(tmp_path):
    """Spec §3 step 3: Python filters senders from the saved list_threads result; previews are dropped."""
    import json
    from mondayview import collect
    page = {"count": 3, "threads": [
        {"threadId": "t1", "labels": ["received"], "timestamp": "2026-11-22T03:55:56.000Z", "receivedTimestamp": "2026-11-22T03:55:56.000Z",
         "senders": ["Dragos Novac <sundaycet@substack.com>"], "subject": "AI, fusion, London", "preview": "SECRET BODY TEXT", "lastMessageId": "<a@x>", "messageCount": 1},
        {"threadId": "t2", "labels": ["received"], "timestamp": "2026-11-22T11:44:26.000Z", "senders": ["The Hustle <news@thehustle.co>"],
         "subject": "Going once", "preview": "more body", "lastMessageId": "<b@x>"},
        {"threadId": "t3", "labels": ["received", "mv-processed-W46"], "timestamp": "2026-11-20T11:00:00.000Z",
         "senders": ["AI & Deeptech by Sifted <sifted@sifted.eu>"], "subject": "x", "preview": "p", "lastMessageId": "<c@x>"}]}
    wrapped = {"result": json.dumps(page)}                       # the harness may wrap the tool result as text
    threads = [collect.from_agentmail(t) for t in collect.find_threads(wrapped)]
    assert [t["sender_email"] for t in threads] == ["sundaycet@substack.com", "news@thehustle.co", "sifted@sifted.eu"]
    assert "SECRET" not in json.dumps(threads) and all("preview" not in t for t in threads)
    issues, skipped = collect.build_issue_list(threads)
    assert [(i["family"], i["thread_id"]) for i in issues] == [("Sunday CET", "t1")]
    assert issues[0]["file"].startswith("2026-11-22_sunday-cet_") and issues[0]["file"].endswith(".json")
    assert sorted(s["reason"] for s in skipped) == ["already processed", "ignored sender"]


def test_hold_notice_goes_nowhere_in_dry_run_and_uses_hold_labels():
    """Spec §1 and §5: hold notices carry mv-hold-WNN; in dry-run, or with no confirmed address, nothing is sent."""
    from mondayview import close
    assert close.hold_plan("W48", "inbox unreachable", mode="dry-run", settings=settings(recipient="r@example.org"))["send"] is False
    assert close.hold_plan("W48", "inbox unreachable", mode="scheduled", settings=settings(recipient=""))["send"] is False
    p = close.hold_plan("W48", "fact-check failed block 1", mode="scheduled", settings=settings(recipient="r@example.org"))
    assert p["send"] and p["labels"] == ["monday-view-hold", "mv-hold-W48"] and p["subject"].startswith("[TEST] ")
    assert p["cc"] == [] and p["bcc"] == [] and "fact-check failed block 1" in p["text"]
    assert not guards.already_sent([["sent"] + p["labels"]], "W48")         # a hold notice is not "sent"
    t = close.hold_plan("W47", "x", mode="test", settings=settings(recipient="r@example.org"))
    assert "mv-hold-W47" not in t["labels"]


def test_editor_brief_holds_quotes_only(w47):
    from mondayview import editor_brief, merge
    brief = editor_brief.make(merge.jsonable(w47["blocks"]), merge.jsonable(w47["events"]))
    assert brief["block1"]["company"] == "Anthropic" and 3 <= len(brief["block1"]["candidate_facts"]) <= editor_brief.MAX_FACTS
    assert all(len(f["quote"]) <= 300 for f in brief["block1"]["candidate_facts"])
    assert any(c["company"] == "OpenAI" for c in brief["block5_candidates"])


def test_named_week_plan_has_a_whole_week_window():
    p = plan.make_plan(datetime(2026, 12, 9, 10, 0, tzinfo=timezone.utc), "mode=test week=W47")
    assert p["window_utc"] == ["2026-11-16T00:00:00+00:00", "2026-11-23T00:00:00+00:00"]
    d = plan.make_plan(datetime(2026, 11, 30, 4, 11, tzinfo=timezone.utc))            # dry-run on a Monday: last week
    assert d["week"] == "W48" and d["window_utc"][0] == "2026-11-23T00:00:00+00:00"
