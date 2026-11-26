"""One test per T row of README §5 (pitfalls 1-29, 32, 34). Synthetic inputs; no network, no bodies."""
from datetime import date, datetime, timezone

import pytest

from conftest import build_blocks, issue, prepared, story
from mondayview import blocks, collect, guards, merge, money, prices, render_email, validate, week


def ev(events, company, etype=None):
    keys = merge.name_keys(company)
    hits = [e for e in events if e["company"] and (merge.name_keys(e["company"]) & keys) and (etype is None or e["event_type"] == etype)]
    assert hits, f"no event for {company}"
    return hits[0]


# ---------------------------------------------------------------- dating and status

def test_p01_story_dated_by_its_own_event_not_the_cluster():
    """R1: 'Nvidia reinstates Huang' happened on 23 Nov; W47 coverage of other Nvidia news must not pull it in."""
    iss = [
        issue("Term Sheet", "2026-11-18", [story("Nvidia", "other", "reported", subtype="leadership", story_date="2026-11-18", date_basis="stated")]),
        issue("TLDR", "2026-11-18", [story("Nvidia", "other", "reported", subtype="leadership")]),
        issue("Sifted", "2026-11-23", [story("Nvidia", "other", "reported", subtype="product", story_date="2026-11-23", date_basis="stated",
                                             headline="Nvidia reinstates Huang")]),
    ]
    events, b = build_blocks(iss)
    reinstated = [e for e in events if "reinstates" in e["headline"]][0]
    assert reinstated["event_date"] == date(2026, 11, 23)
    mon, sun = week.week_bounds(2026, 47)
    assert not blocks.in_week(reinstated, mon, sun)
    assert "reinstates" not in render_email.render_md(b)


def test_p01_cluster_does_not_cross_merge_window():
    iss = [issue("Sifted", "2026-11-02", [story("Acme")]), issue("TLDR", "2026-11-20", [story("Acme")])]
    events, _ = build_blocks(iss)
    assert len([e for e in events if e["company"] == "Acme"]) == 2


def test_p02_new_status_this_week_is_included_even_if_seen_before():
    """R2: the Anthropic IPO was reported (planned, filed) in earlier weeks and priced in W47."""
    iss = [issue("Techmeme", "2026-11-19", [story("Anthropic", "ipo", "priced", story_date="2026-11-18", date_basis="stated")]),
           issue("Sifted", "2026-11-17", [story("Anthropic", "ipo", "planned")])]
    events, _ = build_blocks(iss)
    e = ev(events, "Anthropic", "ipo")
    prior = {blocks.event_key(e): ["planned", "filed"]}
    mon, sun = week.week_bounds(2026, 47)
    assert blocks.in_week(e, mon, sun, prior)
    assert [h["status"] for h in blocks.new_statuses_in_week(e, mon, sun, prior)] == ["priced"]
    # same status as before, nothing new: it does not come back
    assert not blocks.in_week(e, mon, sun, {blocks.event_key(e): ["planned", "filed", "priced"]})


def test_p03_in_talks_is_not_a_closed_round():
    """B1: Monzo in talks; Cohere 'up to $5B'."""
    iss = [issue("Sifted", "2026-11-18", [
        story("Monzo", status="in_talks", equity_amount=400_000_000, stage="series_d_plus"),
        story("Cohere", status="closed", equity_amount=5_000_000_000, amount_qualifier="up_to", stage="unstated", hq=[{"city": "London", "country": "GB"}]),
        story("Realco", status="closed", equity_amount=120_000_000, stage="series_b", hq=[{"city": "Berlin", "country": "DE"}])])]
    events, b = build_blocks(iss)
    assert [r["company"] for r in b["block3"]["rows"]] == ["Realco"]
    assert b["block3"]["mega_count_world"] == 1
    assert {t["company"] for t in b["block3"]["in_talks"]} == {"Monzo", "Cohere"}


def test_p03_talks_and_closed_never_merge():
    iss = [issue("Sifted", "2026-11-17", [story("Sierra", status="in_talks", equity_amount=1_500_000_000)]),
           issue("TLDR", "2026-11-19", [story("Sierra", status="closed", equity_amount=1_500_000_000)])]
    events, _ = build_blocks(iss)
    assert len([e for e in events if e["company"] == "Sierra"]) == 2


def test_p04_undated_stories():
    s = {"story_date": None, "date_basis": "undated"}
    assert week.story_date(s, "2026-11-18", "Term Sheet", "daily") == (date(2026, 11, 18), "issue_date")
    # a morning daily recaps the previous day
    assert week.story_date(s, "2026-11-18", "Techmeme", "daily") == (date(2026, 11, 17), "issue_date_minus_1")
    # a weekly digest looks back; a Monday digest's undated items belong to the week just ended
    assert week.story_date(s, "2026-11-16", "Sifted", "weekly")[0] == date(2026, 11, 15)
    assert week.story_date(s, "2026-11-22", "Sunday CET", "weekly")[0] == date(2026, 11, 21)
    stated = {"story_date": "2026-11-12", "date_basis": "stated"}
    assert week.story_date(stated, "2026-11-18", "Techmeme") == (date(2026, 11, 12), "stated")
    # a 'stated' date after the issue went out cannot be right
    bad = {"story_date": "2026-11-25", "date_basis": "stated"}
    assert week.story_date(bad, "2026-11-18", "TLDR")[0] == date(2026, 11, 18)


def test_p05_report_week_on_a_monday_run():
    """A6: a run on Monday 23 Nov 06:11 Athens reports W47, not W48."""
    run = datetime(2026, 11, 23, 4, 11, tzinfo=timezone.utc)
    y, w, mon, sun = week.report_week(run)
    assert (y, w, mon, sun) == (2026, 47, date(2026, 11, 16), date(2026, 11, 22))
    # just after midnight Athens on Monday is still the new report day
    assert week.report_week(datetime(2026, 11, 22, 22, 30, tzinfo=timezone.utc))[1] == 47
    # year boundary: Monday 4 Jan 2027 reports 2026-W53
    assert week.report_week(datetime(2027, 1, 4, 4, 11, tzinfo=timezone.utc))[:2] == (2026, 53)


def test_p06_window_from_stored_cutoff_and_summer_time():
    """A13, H7: no overlap and no gap across a clock change; processed threads are skipped."""
    # clocks go back on 25 Oct 2026: 06:11 Athens is 03:11 UTC before and 04:11 UTC after
    run1 = datetime(2026, 10, 19, 3, 11, tzinfo=timezone.utc)
    run2 = datetime(2026, 10, 26, 4, 11, tzinfo=timezone.utc)
    w1 = week.collection_window(run1, None)
    assert w1[0] == datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc)      # previous Monday 06:00 Athens (EEST)
    w2 = week.collection_window(run2, w1[1].isoformat())
    assert w2[0] == w1[1] and (w2[1] - w2[0]).total_seconds() == 7 * 86400 + 3600
    threads = [
        {"sender": "TLDR IT", "sender_email": "dan@tldrnewsletter.com", "subject": "a", "date": "2026-10-19T03:10:59.000Z", "lastMessageId": "<1>", "labels": []},
        {"sender": "TLDR IT", "sender_email": "dan@tldrnewsletter.com", "subject": "b", "date": "2026-10-19T03:11:00.000Z", "lastMessageId": "<2>", "labels": []},
        {"sender": "TLDR IT", "sender_email": "dan@tldrnewsletter.com", "subject": "c", "date": "2026-10-20T11:00:00.000Z", "lastMessageId": "<3>", "labels": ["mv-processed-W43"]},
    ]
    got1, _ = collect.build_issue_list(threads, w1)
    got2, skipped = collect.build_issue_list(threads, w2)
    assert [i["message_id"] for i in got1] == ["<1>"] and [i["message_id"] for i in got2] == ["<2>"]
    assert any(s["reason"] == "already processed" for s in skipped)


def test_p07_first_reporter_by_send_timestamp():
    """recheck R1: same-day ties are settled by send time; Techmeme's morning email recaps the previous day."""
    iss = [issue("Sifted", "2026-11-18", [story("Acme")], sent_at="2026-11-18T05:12:00.000Z"),
           issue("Techmeme", "2026-11-18", [story("Acme")], sent_at="2026-11-18T01:03:00.000Z"),
           issue("Term Sheet", "2026-11-18", [story("Acme")], sent_at="2026-11-18T13:05:00.000Z")]
    events, _ = build_blocks(iss)
    e = ev(events, "Acme")
    assert merge.first_family(e) == ("Techmeme", "2026-11-18T01:03:00.000Z")
    assert e["event_date"] == date(2026, 11, 17)


# ---------------------------------------------------------------- money

def test_p08_debt_grants_and_customer_value_funds_are_not_equity():
    """R5: Hone = $28M Series A + $200M customer-value fund. Elysian: grants and equity in one figure."""
    iss = [issue("Term Sheet", "2026-11-18", [
        story("Hone Health", equity_amount=28_000_000, stage="series_a", hq=[{"city": "Lisbon", "country": "PT"}],
              other_finance=[{"type": "customer_value_fund", "amount": 200_000_000, "currency": "USD"}]),
        story("Elysian Aircraft", equity_amount=None, currency=None, stage="unstated", tech_area="defence_aerospace", hq=[{"city": None, "country": "NL"}],
              mixed_total={"amount": 12_000_000, "currency": "EUR", "qualifier": "at_least", "includes": ["grant", "equity"]})])]
    events, b = build_blocks(iss)
    assert blocks.round_usd(ev(events, "Hone Health")) == 28_000_000
    assert b["block3"]["rows"] == [] and b["block3"]["mega_count_world"] == 0
    el = [r for r in b["block2"]["named"] if r["company"] == "Elysian Aircraft"][0]
    assert el["amount"] == "€12m+ in grants and equity" and el["mixed"]


def test_p09_valuation_is_not_a_raise():
    """Isomorphic's $5B is a raise; Tiberius's '$1B+' is a valuation."""
    iss = [issue("Sifted", "2026-11-18", [
        story("Isomorphic Labs", equity_amount=5_000_000_000, stage="series_c", hq=[{"city": "London", "country": "GB"}]),
        story("Tiberius Aerospace", equity_amount=85_000_000, stage="series_a", hq=[{"city": "London", "country": "GB"}],
              valuation={"amount": 1_000_000_000, "currency": "USD", "qualifier": "more_than"}),
        story("Samey", equity_amount=70_000_000, stage="series_b", quote="Samey raised $70M",
              valuation={"amount": 70_000_000, "currency": "USD"})])]
    events, b = build_blocks(iss)
    rows = {r["company"]: r for r in b["block3"]["rows"]}
    assert rows["Isomorphic Labs"]["amount"] == "$5B" and rows["Isomorphic Labs"]["valuation"] is None
    assert rows["Tiberius Aerospace"]["amount"] == "$85M" and rows["Tiberius Aerospace"]["valuation"] == "$1B+"
    assert ev(events, "Samey")["valuation"] is None        # a 'valuation' equal to the raise, with no valuation wording


def test_p10_run_rate_is_never_a_raise():
    """B1: Kalshi's '$5B' is a run rate."""
    q = "Kalshi has hit a $5B annualized run rate in trading volume"
    assert validate.looks_like_non_raise(q, 5_000_000_000)
    assert not validate.looks_like_non_raise("Kalshi raised $5B in a round led by X", 5_000_000_000)
    s, flags = validate.clean_story(story("Kalshi", equity_amount=5_000_000_000, quote=q))
    assert s["equity_amount"] is None and "amount_was_non_raise" in flags
    events, b = build_blocks([issue("TLDR", "2026-11-18", [story("Kalshi", equity_amount=5_000_000_000, quote=q, stage="unstated")])])
    assert b["block3"]["mega_count_world"] == 0


def test_p11_combined_rounds_excluded_from_medians_and_n_shown():
    """R10: Seawolf seed + Series A."""
    us = [{"city": "Boston", "country": "US"}]
    iss = [issue("Term Sheet", "2026-11-17", [
        story("Seawolf", equity_amount=100_000_000, stage="seed", is_combined_round=True, hq=us),
        story("A1", equity_amount=4_000_000, stage="seed", hq=us), story("A2", equity_amount=6_000_000, stage="seed", hq=us),
        story("A3", equity_amount=10_000_000, stage="seed", hq=us)])]
    events, _ = build_blocks(iss)
    m = prices.medians(events)[("seed", "US")]
    assert m == {"n": 3, "median_usd": 6_000_000, "excluded_combined": 1, "label": "reported rounds"}
    assert prices.medians(events)[("series_a", "Europe")]["n"] == 0


def test_p12_no_dollar_totals(w47):
    assert guards.find_totals("Rounds totalling $9.1B this week") and guards.find_totals("a total of $3B")
    assert not guards.find_totals("14 rounds of $100M or more were reported, equity only.")
    assert guards.find_totals(w47["md"]) == []
    flat = str(merge.jsonable(w47["blocks"]))
    assert "total_usd" not in flat and "sum_usd" not in flat


def test_p13_currency_kept_and_conversion_logged():
    assert money.fmt(6_000_000, "EUR") == "€6m" and money.fmt(110_000_000, "USD") == "$110M"
    assert money.fmt(1_000_000_000, "EUR") == "€1bn" and money.fmt(1_000_000_000, "USD", "more_than") == "$1B+"
    assert money.fmt(1_500_000_000, "USD", "about") == "~$1.5B" and money.fmt(27_200_000, "EUR") == "€27.2m"
    log = []
    assert money.to_usd(54_000_000, "EUR", log) > 50_000_000
    assert log and log[0]["currency"] == "EUR" and log[0]["usd_per_unit"] and log[0]["as_of"]
    iss = [issue("EU-Startups", "2026-11-19", [story("Commit Biologics", equity_amount=54_000_000, currency="EUR", stage="seed",
                                                      tech_area="health", hq=[{"city": "Copenhagen", "country": "DK"}])])]
    _, b = build_blocks(iss)
    assert b["block3"]["rows"][0]["amount"] == "€54m" and b["fx_log"]


# ---------------------------------------------------------------- entities, merging, dots

def test_p14_company_comes_from_extraction_not_headline_regex():
    """The prototype read 'Robotics' as the company in 'Robotics startup Mosaico raises €7.5m'."""
    iss = [issue("Sifted", "2026-11-16", [story("Mosaico", headline="Robotics startup Mosaico raises €7.5m", equity_amount=7_500_000, currency="EUR")])]
    events, _ = build_blocks(iss)
    assert [e["company"] for e in events] == ["Mosaico"]
    import mondayview
    from pathlib import Path
    src = "".join(p.read_text() for p in Path(mondayview.__file__).parent.glob("*.py"))
    assert "reference/data" not in src and "reference/prototype" not in src


def test_p15_duplicates_merge_across_case_accents_language_and_currency():
    """R3 and Stryx AI (EN + FR): one round, counted once, families counted."""
    iss = [issue("Sifted", "2026-11-20", [story("Stryx AI", equity_amount=7_700_000, currency="EUR")]),
           issue("Maddyness", "2026-11-20", [story("STRYX", equity_amount=7_700_000, currency="EUR", headline="Défense : Stryx lève 7,7 millions d'euros")]),
           issue("Maddyness", "2026-11-19", [story("Rémanence", equity_amount=30_000_000, currency="USD")]),
           issue("Techmeme", "2026-11-19", [story("Remanence", equity_amount=27_500_000, currency="EUR")]),
           issue("Sifted", "2026-11-18", [story("Tiberius", equity_amount=85_000_000), story("Model ML", equity_amount=250_000_000)]),
           issue("Term Sheet", "2026-11-20", [story("Tiberius Aerospace", equity_amount=85_000_000), story("ModelML", equity_amount=250_000_000)])]
    events, b = build_blocks(iss)
    rounds = [e for e in events if e["event_type"] == "round"]
    assert len(rounds) == 4
    assert ev(events, "Stryx AI")["families"] == ["Maddyness", "Sifted"]
    assert b["block2"]["count_world"] == 4          # six mentions, four rounds
    assert ev(events, "Remanence")["families"] == ["Maddyness", "Techmeme"] and ev(events, "Model ML")["n_families"] == 2
    # a different amount is a different round
    iss2 = [issue("Sifted", "2026-11-18", [story("Mistral", equity_amount=3_000_000_000, currency="EUR")]),
            issue("EU-Startups", "2026-11-19", [story("Mistral AI", equity_amount=100_000_000, currency="EUR")])]
    assert len(build_blocks(iss2)[0]) == 2


def test_p16_dots_only_from_extracted_entities():
    """V2: 'Mountain View' is not MountAIn. H1: 'pluralisme' is not Plural."""
    assert not (merge.name_keys("Mountain View") & merge.name_keys("MountAIn"))
    assert not (merge.name_keys("pluralisme") & merge.name_keys("Plural"))
    iss = [issue("Sifted", "2026-11-19", [story("MountAIn", equity_amount=7_300_000, currency="EUR")]),
           issue("DeepLearning.AI", "2026-11-20", [story("Mountain View Labs", "other", "reported", quote="the Mountain View company said")]),
           issue("Sifted", "2026-11-17", [story("Plural", "fund", "closed", fund_size={"amount": 1e9, "currency": "EUR"})]),
           issue("Maddyness", "2026-11-20", [story("Autorité du pluralisme", "other", "reported")])]
    events, _ = build_blocks(iss)
    assert ev(events, "MountAIn")["families"] == ["Sifted"]
    assert ev(events, "Plural", "fund")["families"] == ["Sifted"]
    # nothing in the pipeline searches free text for names: a quote that mentions a name adds no family
    iss.append(issue("TLDR", "2026-11-20", [story("Other Co", "other", "reported", quote="MountAIn and Plural were at the event")]))
    events, _ = build_blocks(iss)
    assert ev(events, "MountAIn")["families"] == ["Sifted"]


def test_p17_deal_list_mentions_count_for_every_company():
    """V3: Newcomer's deal list names Mailchimp and Applied Compute in one line each."""
    lst = [story("Mailchimp", "acquisition", "announced", mention_type="deal_list", acquirer="Bending Spoons"),
           story("Applied Compute", "acquisition", "announced", mention_type="deal_list", acquirer="Palo Alto Networks")]
    iss = [issue("Newcomer", "2026-11-20", lst),
           issue("Techmeme", "2026-11-20", [story("Mailchimp", "acquisition", "announced", acquirer="Bending Spoons")]),
           issue("Techmeme", "2026-11-19", [story("Applied Compute", "acquisition", "announced", acquirer="Palo Alto Networks")])]
    events, _ = build_blocks(iss)
    assert ev(events, "Mailchimp")["families"] == ["Newcomer", "Techmeme"]
    assert ev(events, "Applied Compute")["families"] == ["Newcomer", "Techmeme"]


def test_p18_reprints_flagged_legend_says_coverage_no_ranking_by_dots():
    """R4: Daisytuner's press release was reprinted by three digests."""
    iss = [issue(f, "2026-11-17", [story("Daisytuner", equity_amount=6_000_000, currency="EUR", tech_area="ai_infrastructure",
                                         is_press_release_reprint=(f != "Sifted"))]) for f in ("Sifted", "Term Sheet", "EU-Startups")]
    iss.append(issue("Sifted", "2026-11-19", [story("Dcubed", equity_amount=27_200_000, currency="EUR", stage="series_a", tech_area="space")]))
    iss.append(issue("Sifted", "2026-11-18", [story("Aaa Chips", equity_amount=3_000_000, currency="EUR", tech_area="chips_photonics")]))
    events, b = build_blocks(iss)
    assert ev(events, "Daisytuner")["n_reprints"] == 2
    assert all("is_press_release_reprint" in m for m in ev(events, "Daisytuner")["mentions"])
    assert "Breadth of coverage, not importance" in render_email.LEGEND and "press release" in render_email.LEGEND
    # the named list is ordered by area, not by dots: chips (1 dot) comes before space, and the big round by amount
    names = [r["company"] for r in b["block2"]["named"]]
    assert names.index("Daisytuner") < names.index("Aaa Chips") < names.index("Dcubed")


# ---------------------------------------------------------------- geography, tagging, sources

def test_p19_every_stated_hq_is_kept():
    """B1: Tiberius is London / Newport Beach; Hypersonica had a wrong single HQ."""
    iss = [issue("Sifted", "2026-11-18", [story("Tiberius Aerospace", equity_amount=85_000_000, stage="series_a", hq=[{"city": "London", "country": "GB"}])]),
           issue("Techmeme", "2026-11-18", [story("Tiberius Aerospace", equity_amount=85_000_000, stage="series_a",
                                                   hq=[{"city": "Newport Beach", "country": "US"}, {"city": None, "country": "GB"}])]),
           issue("Term Sheet", "2026-11-18", [story("Ramon.Space", equity_amount=124_000_000, stage="series_b", hq=[])])]
    events, b = build_blocks(iss)
    assert b["block3"]["rows"][0]["hq"] == "London / Newport Beach"
    assert merge.is_europe(ev(events, "Tiberius Aerospace"))
    # no stated HQ means not European: it cannot be a block-3 row
    assert [r["company"] for r in b["block3"]["rows"]] == ["Tiberius Aerospace"]
    assert merge.is_europe({"hq": [{"city": "Zurich", "country": "CH"}]}) and merge.is_europe({"hq": [{"city": "London", "country": "GB"}]})


def test_p20_tags_come_from_the_taxonomy_not_keywords():
    from mondayview import config
    tax = config.taxonomy()
    assert tax["ai_infrastructure"]["deep_tech"] and not tax["ai_applications"]["deep_tech"]
    assert not tax["health"]["deep_tech"] and not tax["fintech"]["deep_tech"]
    # 'AI' in the name does not make a company deep tech; an unknown tag is flagged and falls to 'other'
    s, flags = validate.clean_story(story("Robot AI Health", tech_area="Robotics & autonomy"))
    assert s["tech_area"] == "other" and "unknown_tech_area" in flags
    iss = [issue("Sifted", "2026-11-18", [story("Chat AI Robotics", tech_area="ai_applications"),
                                           story("Commit Bio", tech_area="health"), story("Fuse", tech_area="quantum")])]
    _, b = build_blocks(iss)
    assert [r["company"] for r in b["block2"]["named"]] == ["Fuse"]
    assert {a["area"] for a in b["block2"]["area_table"]} == {"ai_applications", "health", "quantum"}


def test_p21_source_mix_line_and_dominance_flag():
    """R6: one family carrying most of a count is said so, with the count without it."""
    ts = issue("Term Sheet", "2026-11-18", [story(f"T{i}", hq=[{"city": "Austin", "country": "US"}]) for i in range(6)] + [story("Both")])
    other = issue("Sifted", "2026-11-18", [story("Both"), story("S1"), story("S2")])
    _, b = build_blocks([ts, other])
    mix = b["block2"]["mix_world"]
    assert (mix["family"], mix["carried"], mix["total"], mix["without"], mix["dominant"]) == ("Term Sheet", 7, 9, 3, True)
    md = render_email.render_md(b)
    assert "Term Sheet carried 7 of the 9; the total is 3 without it." in md
    assert b["block2"]["lead_with_raw_count"] is False          # under 8 weeks of history


def test_p22_footer_counts_from_collected_list():
    """V4, R12."""
    meta = ([{"family": "TLDR", "letter": "TLDR IT"}] * 3 + [{"family": "Maddyness", "letter": "Maddyness"}] * 2
            + [{"family": "Sifted", "letter": "Sifted Daily"}])
    f = collect.footer_counts(meta)
    assert f["total"] == 6 and f["per_family"] == {"TLDR": 3, "Maddyness": 2, "Sifted": 1}
    assert "Maddyness IA" in f["silent_letters"]
    assert "Term Sheet" in f["silent_deal_carrying"] and "Techmeme" in f["silent_families"]


def test_p23_unconfirmed_ma_goes_to_single_source_list_with_source():
    """R8: Iceye-Avio and MongoDB-Firebolt. H6: a single-source closed round just shows one dot."""
    iss = [issue("Sunday CET", "2026-11-22", [story("Avio", "acquisition", "bid", acquirer="Iceye", price={"amount": 2.05e9, "currency": "EUR"})]),
           issue("TLDR", "2026-11-19", [story("Firebolt", "acquisition", "announced", acquirer="MongoDB")]),
           issue("Techmeme", "2026-11-19", [story("Applied Compute", "acquisition", "announced", acquirer="Palo Alto Networks")]),
           issue("TLDR", "2026-11-20", [story("Applied Compute", "acquisition", "announced", acquirer="Palo Alto Networks")]),
           issue("Sifted", "2026-11-19", [story("Dcubed", equity_amount=27_200_000, currency="EUR", stage="series_a", tech_area="space")])]
    _, b = build_blocks(iss)
    assert [a["target"] for a in b["block4"]["confirmed"]] == ["Applied Compute"]
    single = {a["target"]: a for a in b["block4"]["single_source"]}
    assert set(single) == {"Avio", "Firebolt"}
    md = render_email.render_md(b)
    assert "Iceye → Avio, €2.05bn, bid (Sunday CET)" in md and "MongoDB → Firebolt (TLDR)" in md
    assert [r["dots"] for r in b["block2"]["named"] if r["company"] == "Dcubed"] == ["●"]
    # talks reported by two families are still not a confirmed deal
    iss2 = [issue(f, "2026-11-20", [story("Zscaler", "acquisition", "in_talks", acquirer="CrowdStrike")]) for f in ("Techmeme", "TLDR")]
    assert build_blocks(iss2)[1]["block4"]["confirmed"] == []


def test_p24_fund_strategy_european_early_first():
    """R11."""
    iss = [issue("Term Sheet", "2026-11-16", [story("Norwest", "fund", "closed", fund_size={"amount": 4e9, "currency": "USD"}, fund_strategy="multi_stage", fund_geography="US")]),
           issue("Sifted", "2026-11-17", [story("Plural", "fund", "closed", fund_size={"amount": 1e9, "currency": "EUR"}, fund_strategy="early_stage", fund_geography="Europe")]),
           issue("Maddyness", "2026-11-17", [story("Sofinnova Partners", "fund", "final_close", fund_size={"amount": 725e6, "currency": "EUR"},
                                                   fund_strategy="late_stage", fund_geography="Europe", fund_focus="life sciences")]),
           issue("Sifted", "2026-11-20", [story("Redalpine", "other", "reported", subtype="leadership")])]
    _, b = build_blocks(iss)
    assert [f["firm"] for f in b["block4"]["funds_european_early"]] == ["Plural"]
    assert {f["firm"] for f in b["block4"]["funds_other"]} == {"Norwest", "Sofinnova Partners"}
    md = render_email.render_md(b)
    assert md.index("Plural") < md.index("Sofinnova") and "Redalpine" not in md
    assert "late stage" in md and "life sciences" in md


def test_p25_price_measure_and_source_must_be_named():
    """V1: 'one-third of the cost' is per task on OpenAI's own evals, not a price cut."""
    src = [{"file": "f.json", "quote": "tokens 20% cheaper at $8 / $40 per million; under one-third of the cost per task on OpenAI's evals"}]
    ev_ = [{"mentions": [{"file": "f.json", "quote": src[0]["quote"]}], "facts": []}]
    good = {"block5": {"text": "API tokens 20% cheaper, at $8 / $40 per million input/output tokens (Techmeme). OpenAI claims under one-third of the cost per task on its own evals.", "sources": src}}
    assert guards.check_editorial(good, ev_) == []
    bad = {"block5": {"text": "OpenAI cut prices to one-third.", "sources": src}}
    assert any("measure" in p for p in guards.check_editorial(bad, ev_))
    assert any("no source" in p for p in guards.check_editorial({"block5": {"text": "20% cheaper per token", "sources": []}}, ev_))


def test_p26_no_trend_claims_before_eight_weeks():
    """C1: one storyline is not a trend."""
    assert guards.find_trend_claims("Defence rounds are trending up, up from last week", weeks_of_history=1)
    assert guards.find_trend_claims("a clear trend", weeks_of_history=7)
    assert guards.find_trend_claims("a clear trend", weeks_of_history=8) == []
    assert guards.find_trend_claims("W47 was Slush week, so no comparison with previous weeks.", 0) == []


def test_p27_only_listed_senders_are_collected():
    """H9: sign-up confirmations, bigpi.vc tests and unknown senders are logged, never extracted."""
    def t(sender, email, subject, mid):
        return {"sender": sender, "sender_email": email, "subject": subject, "date": "2026-11-18T08:00:00.000Z", "lastMessageId": mid, "labels": []}
    threads = [t("Sifted Daily", "sifted@sifted.eu", "news", "<1>"), t("TLDR", "dan@tldrnewsletter.com", "TLDR - Confirm your signup", "<2>"),
               t("Guy", "someone@bigpi.vc", "test", "<3>"), t("Promo", "deals@unknown.example", "Buy now", "<4>"),
               t("Sifted Pro", "marketing@sifted.eu", "offer", "<5>"), t("Maddyness IA", "ia@maddyness.com", "IA", "<6>"),
               t("AI & Deeptech by Sifted", "Sifted <sifted@sifted.eu>", "x", "<7>")]
    issues, skipped = collect.build_issue_list(threads)
    assert [(i["family"], i["letter"]) for i in issues] == [("Sifted", "Sifted Daily"), ("Maddyness", "Maddyness IA"), ("Sifted", "AI & Deeptech by Sifted")]
    assert sorted(s["reason"] for s in skipped) == ["ignored sender", "ignored sender", "ignored subject", "unknown sender"]
    assert all(set(s) == {"sender", "sender_email", "subject", "reason"} for s in skipped)


# ---------------------------------------------------------------- run safety

def test_p28_factcheck_reopens_sources_by_message_id(w47):
    """A5: the fact-checker is given message IDs for blocks 1, 3, 4 and every dot count, not the extractor's word."""
    from mondayview import factcheck_plan
    plan = factcheck_plan.make(w47["blocks"], w47["events"], w47["editorial"])
    assert plan["checks"] and all(c["sources"] and all(s["message_id"].startswith("<") for s in c["sources"]) for c in plan["checks"])
    blocks_covered = {str(c["block"]) for c in plan["checks"]}
    assert {"1", "3", "4"} <= blocks_covered
    dot_items = {c["item"] for c in plan["checks"] if c["kind"] == "dots"}
    shown = ({r["company"] for r in w47["blocks"]["block3"]["rows"]} | {r["company"] for r in w47["blocks"]["block2"]["named"]}
             | {a["target"] for a in w47["blocks"]["block4"]["confirmed"]})
    assert shown <= dot_items
    assert plan["reopens"] <= 80


def test_p29_counts_recomputed_after_drops():
    """A14: when the fact-check drops an item, every count is rebuilt."""
    from mondayview import blocks as B
    iss = prepared([issue("Sifted", "2026-11-18", [story("Keep"), story("Dropme", equity_amount=120_000_000, stage="series_a")])])
    events = merge.merge(iss)
    mon, sun = week.week_bounds(2026, 47)
    meta = [{"family": "Sifted", "letter": "Sifted Daily"}]
    before = B.build(events, meta, mon, sun)
    after = B.build([e for e in events if e["company"] != "Dropme"], meta, mon, sun)
    assert (before["block2"]["count_world"], before["block3"]["mega_count_world"], len(before["block3"]["rows"])) == (2, 1, 1)
    assert (after["block2"]["count_world"], after["block3"]["mega_count_world"], len(after["block3"]["rows"])) == (1, 0, 0)
    assert after["block2"]["area_total"] == after["block2"]["count_europe"] - len(after["block2"]["big_early_europe"])
    assert guards.factcheck_action({"checks": [{"block": 3, "kind": "number", "verdict": "fail"}] + [{"block": 3, "kind": "number", "verdict": "pass"}] * 9})[0] == "rebuild"
    assert guards.factcheck_action({"checks": [{"block": 1, "kind": "number", "verdict": "fail"}]})[0] == "hold"
    assert guards.factcheck_action({"checks": [{"block": 2, "kind": "number", "verdict": "fail"}] * 3 + [{"block": 2, "kind": "number", "verdict": "pass"}] * 7})[0] == "hold"


def test_p32_double_send_and_test_labels():
    """A9, H10: only mv-WNN counts as sent; test sends use mv-test-… and never block a real one."""
    assert guards.labels_for("scheduled", "W47") == ["monday-view", "mv-W47"]
    assert guards.labels_for("test", "W47", "20261126T101500Z") == ["monday-view-test", "mv-test-W47-20261126T101500Z"]
    with pytest.raises(guards.GuardError):
        guards.labels_for("dry-run", "W47")
    assert guards.already_sent([["sent", "monday-view", "mv-W47"]], "W47")
    assert not guards.already_sent([["sent", "monday-view-test", "mv-test-W47-20261126T101500Z"]], "W47")
    assert not guards.already_sent([["received", "mv-W47"]], "W47")
    assert not guards.already_sent([["sent", "mv-W46"], ["sent", "mv-hold-W47"]], "W47")


def test_p34_usual_issue_count_has_a_base():
    """A15: usual = median of recent weeks, seeded from W45-W47."""
    assert collect.usual_issues() == 55
    assert collect.usual_issues([40, 60, 50]) == 50
    assert collect.volume_check(54)[0] == "ok" and collect.volume_check(27)[0] == "hold" and collect.volume_check(91)[0] == "hold"
