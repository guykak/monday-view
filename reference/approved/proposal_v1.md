# The Monday view: a weekly market read from 15 newsletters (revised after fact-check)

This is a proposal for Guy at Big Pi Ventures. It was tested on 2,620 stories from 220 issues, covering 29 Oct to 26 Nov 2026. The full weeks are W45 (2–8 Nov), W46 (9–15 Nov) and W47 (16–22 Nov). This version addresses the fact-check in `weekly/review.json`, points R1 to R12.

- **Code:** `weekly/stat_tests.py`, `augment.py`, `w47_fix.py`
- **Results:** `weekly/stat_tests.json` (see the key `revision_2026_11_26`) and `weekly/w47_family_counts.json`
- **Finished example:** `weekly/w47_sample.md`

## 1. The short answer

The newsletters can support a weekly view of where early-stage money went, who sold, who raised a fund and what it cost. From week 1 that works as lists, counts and rankings. They cannot yet support trend lines: three full weeks is not a baseline. Any week-on-week arrow waits for 8–12 weeks of stored history.

The view has five blocks and runs to 500–700 words.

## 2. Rules that apply to every block

- **Date items by their own story date.** The cluster date is not used. An event belongs to the week in which it was first reported or changed status (rumoured, priced, signed, closed, refused). The fact-check caught two cases of the old bug:
  - "Nvidia reinstates Huang" is W48 (23 Nov). In W47 the board ruled out his return.
  - CrowdStrike–Zscaler was only talks in W47 (21 Nov).
- **Merge by company and amount before counting sources.** Use an LLM to extract the company, then a fuzzy name match within ±10 days. The old clusterer under-counted Mailchimp, Applied Compute, Tiberius, Remanence and Boltz. Recounted from the raw text for 16–22 Nov:

  | Item | Old count | Recounted |
  |---|---|---|
  | Remanence | 2 | 5 |
  | Boltz | 2 | 4 |
  | Tiberius | 2 | 3 |
  | Mailchimp | 2 | 3 |
  | Applied Compute | 1 | 3 |

- **Show breadth as dots, not as a ranking.** Each item carries one dot per independent source family (Sifted's five newsletters count as one, TLDR's four as one), capped at ●●●●● for five or more. Three families can be one press release reprinted by three deal digests. Daisytuner's €6m seed reached 3 families that way. So dots mark coverage; they do not measure importance.
- **Count equity only.** Debt, revenue-based finance and grants are split out at extraction. Example: Hone Health is $28M Series A equity plus $200M from General Catalyst's Customer Value Fund, not a $228M Series A. With that fixed, W47 has 14 rounds of $100M or more, not 15.
- **Give each item one home.** Rounds of $50M or more go in block 3; smaller rounds go in block 2.
- **Record conflicting headquarters as stated.** Tiberius is London per Sifted and Newport Beach, CA per Term Sheet; it is written "London / Newport Beach".
- **Show the source mix on every count.** Each count gets one line: how many items the largest family carried, and the count without that family. W47 example: "55 early rounds, 30 carried by Term Sheet; 35 without it."

## 3. The five blocks

### 1. The week's story
**Shows:** the single event covered by the most source families within the week, with its numbers.
**Why it matters:** it gives the context for every other number on the page.
**W47:** the Anthropic IPO, covered by 10 families.
- Priced on 18 Nov at $83 a share, above the range, raising about $81.3bn.
- Listed on 19 Nov: opened at $111.50 (+34%) and closed at $97.17 (+17%), about $1.3T market cap.
- The greenshoe took the total raised to $93.5bn.
- On Friday 20 Nov an AI sell-off followed: SoftBank fell about 15%, Samsung and SK Hynix more than 6%.

**Illustration:** two or three lines with a date for each step. No chart.
**Noise rule:** most families within the week, counted on story dates. The event must have reached a new status this week.

### 2. Early-stage rounds by technical area
**Shows:** pre-seed to Series A rounds under $50M, counted by technical area, Europe vs rest. Below the counts, European deep-tech rounds are named with their dots.
**Why it matters:** this is Big Pi's deal market. It shows where peers write first cheques and which rounds Big Pi did not see.
**W47:** 55 early rounds, 28 in Europe. Source mix: Term Sheet carried 30 of the 55, and the count is 35 without it; Sifted carried most of the European rounds, and the European count is 21 without it. European deep tech:
- Daisytuner €6m seed ●●●
- MountAIn €7.3m seed ●●●●
- Vetaion €5.7m pre-seed ●●
- Mosaico €7.5m ●●
- Stryx AI €7.7m seed ●●
- Elysian Aircraft €12m+ in grants and equity ●●●
- Dcubed €27.2m Series A ●

**Illustration:** one bar per area, with the named list underneath.
**Noise rule:**
- Counts and rankings only, with the source-mix line.
- Area tags come from an LLM reading the deal text. Keyword tags scored 16 of 29 in a spot-check.
- The headline does not lead with the raw count until there are 8 weeks of history. W47 was Slush week, when European announcements cluster.

### 3. Big rounds and marks
**Shows:** rounds of $50M or more with stage and stated valuation. Rounds still "in talks" go on a separate line.
**Why it matters:** these set the reference prices for follow-ons and exits.
**W47:**
- Genesis AI (Paris / San Carlos) $500M Series A at $3.5B ●●●●●
- Boltz (London) $110M Series A ●●●●
- Tiberius (London / Newport Beach) $85M Series A at $1B+ ●●●
- Commit Biologics €54m seed ●
- Isomorphic $5B ●●●●●, Payhawk $280M ●●●●●, Model ML $250M at $1.5B ●●●●

**Illustration:** a table of 5–7 rows.
**Noise rule:** closed equity only. No dollar total: the largest round made up 55% of W47's dollars and 66% of W45's.

### 4. Exits and new funds (merged)
**Shows:** acquisitions of tech companies and VC-backed startups, IPOs that changed status, and VC funds that closed this week. European early-stage funds come first.
**Why it matters:** it shows exit routes and prices, and who will co-invest or compete for the same rounds.
**W47:**
- Palo Alto Networks buys Applied Compute for $4.5B in stock, after a $3.25B valuation earlier in November ●●●
- Bending Spoons buys Mailchimp for $3.68B; Intuit paid ~$12B in 2021 ●●●
- Single-source items: Nvidia in talks for Inception ($500M+), MongoDB–Firebolt, Iceye's €2.05B bid for Avio (reported by Sunday CET)
- Plural closes a €1bn early-stage fund ●●●●●
- Other funds, on one line: Sofinnova Crossover II €725m (late-stage life sciences), Norwest $4B (US venture and growth)

**Illustration:** a list of acquirer → target with price, then the funds.
**Noise rule:**
- PE buy-and-build deals are excluded.
- Rumours are labelled.
- Single-source items carry one dot and name the source.
- No "pattern" claims unless they hold across 4+ weeks.

### 5. Market move (optional, one line)
**W47:** OpenAI's GPT-6.2 at one-third of GPT-6's cost and Gemini 4 Neon at $3 per million tokens both cut inference prices.
**Rule:** included only if it changes price, distribution or legality for a named startup category.

## 4. Monthly, not weekly

The price check moves to the first Monday of each month: 4-week rolling medians of reported equity rounds, with n for every split. Combined rounds such as Seawolf's seed-plus-A are excluded. Between months it appears only if the median moves by more than 15%.

Figures for 29 Oct–22 Nov:

| Stage | All | Europe | US |
|---|---|---|---|
| Seed | $7.9M (n=85) | $6.3M (n=46) | $10.0M (n=28) |
| Series A | $27.5M (n=59) | $20.5M (n=20) | $25.8M (n=18) |

These rounds skew larger than the market, because small rounds go unreported.

## 5. What was rejected and why

| Rejected | Why |
|---|---|
| Total dollars raised | One round swings it: Isomorphic was 55% of W47 |
| Europe's share of rounds | Set by which newsletters are subscribed to; the dollar share went 4.5%, 47%, 87% |
| Deep-tech share, AI share | Keyword tagging scored 55% on deep tech |
| Lead-investor ranking | The lead is named in only a minority of items |
| Sentiment, topic attention | Media metrics that move with one storyline |
| People moves, layoffs | Too few items; the W47 layoff hits were false positives |
| Consensus list as a standalone section | Its items overlapped the other blocks, and syndication inflates the count |

## 6. Input caveats

- The families that carry deals (Sifted, TLDR, Term Sheet, Techmeme) sent the same number of issues each week. Newcomer (6/2/4) and Maddyness (5/4/5) varied.
- EU-Startups sent no issue in W45, and Sunday CET none in W46.
- A footer line in each weekly view flags any family that is missing that week.

## 7. To build before it runs weekly

1. LLM extraction of each deal: company, HQ (multiple HQs kept), stage, equity amount, other finance, valuation, lead investor, technical area and team origin.
2. Deduplication by company across languages within ±10 days. Stryx AI was counted twice in W47, once in English and once in French. Event clusters must not cross week boundaries or status changes.
3. Weekly values stored, so the baselines exist by February.
4. A spot-check of 10 random items a week against the raw text, including their source counts, before the view is sent.
