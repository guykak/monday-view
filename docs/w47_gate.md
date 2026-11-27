# W47 acceptance gate

The pass/fail test for Phase 0a. It turns `reference/approved/w47_sample.md` into exact assertions and resolves the sample's ambiguities.

**Revised 26 Nov 2026 (Guy's decision).** Seven lines were corrected after the rebuild from the raw emails and an independent fact-check (`history/W47/factcheck.json`): the early-round counts and their source mix, Payhawk's valuation, and the Anthropic IPO family list. Each is marked "corrected" below with the reason. The word limit is now 500–850.

Encode it as `tests/fixtures/w47_expected.json`. The gate passes only when **two separate extraction runs both pass every line**. An independent fact-check agent ticks the lines first; Guy then reads the output.

**Required / allowed / forbidden.**
- **Required** items must appear, with the stated values.
- **Allowed** items may appear if they meet the block rule (README §2) and pass the fact-check.
- **Forbidden** items fail the gate.
- Anything not listed may appear only if it meets the rule and passes the fact-check. It does not fail the gate.

## Input window (W47 fixture only)

- **Counting set:** the 54 issues in `reference/data/issue_message_ids.json` whose file date is 16–22 Nov. Counts, dots and the footer use these only.
- **Status check only:** the 11 issues dated Mon 23 Nov may be read to confirm status and dating (e.g. the Nvidia reinstatement is W48). They add nothing to counts or dots.
- **Why this differs from production:** this is how the approved sample was built. Production uses the cut-off rule in `docs/automation_spec.md` §2, which is tested separately with synthetic timestamps.

## Dots: final family lists

Source: `reference/data/w47_family_counts.json`, as corrected (V2, V3, H1). Where `stat_tests.json` or `proposal_v1.md` differ, they are superseded.

| Item | Families | Dots |
|---|---|---|
| Anthropic IPO | Sifted, Techmeme, TLDR, Benedict Evans, Newcomer, Term Sheet, Not Boring, DeepLearning.AI, Sunday CET (9). Corrected: no AlphaSignal issue of 16–22 Nov mentions the IPO; the earlier count of 10 included it by mistake | ●●●●● |
| Isomorphic Labs | Sifted, Techmeme, Term Sheet, TLDR, EU-Startups, Newcomer, Not Boring (7) | ●●●●● |
| Genesis AI | Maddyness, Sifted, Techmeme, Term Sheet, TLDR, Newcomer, Not Boring (7) | ●●●●● |
| Payhawk | Term Sheet, Sifted, Techmeme, EU-Startups, Newcomer, Sunday CET (6) | ●●●●● |
| Remanence | Term Sheet, Maddyness, Sifted, Techmeme, Sunday CET (5) | ●●●●● |
| Model ML | Sifted, Techmeme, Term Sheet, EU-Startups (4) | ●●●● |
| Boltz | Newcomer, Not Boring, Sifted, Techmeme (4) | ●●●● |
| Plural | Sifted, Techmeme, EU-Startups, Sunday CET (4). Maddyness 20 Nov is a false match on "pluralisme" | ●●●● |
| Tiberius Aerospace | Sifted, Techmeme, Term Sheet (3) | ●●● |
| Daisytuner | Sifted, Term Sheet, EU-Startups (3) | ●●● |
| MountAIn | Term Sheet, Sifted, EU-Startups (3). The Batch's "Mountain View" is a false match | ●●● |
| Elysian Aircraft | EU-Startups, TechCrunch Mobility, Sifted (3) | ●●● |
| Applied Compute | Techmeme, Newcomer, TLDR (3) | ●●● |
| Mailchimp | Techmeme, Newcomer, Sunday CET (3) | ●●● |
| Vetaion | EU-Startups, Sifted (2) | ●● |
| Mosaico | Sifted, Term Sheet (2) | ●● |
| Stryx AI | Maddyness, Sifted (2). The EN and FR stories are the same round | ●● |
| Sofinnova Crossover II | Maddyness, Sifted (2) | ●● |
| Commit Biologics | EU-Startups | ● |
| Dcubed | Sifted | ● |
| Norwest fund 18 | Term Sheet | ● |

Dates in `w47_family_counts.json` are coverage dates (when a family mentioned the item), not story dates. Do not test story dating against them.

## Headline, length, footer

- One bold headline sentence, then the dot legend (as in the sample). Wording is free.
- The markdown version is **500–850 words** by `wc -w`, everything included. The sample is 725; the limit was raised from 750 so that the deep-tech list keeps its descriptions and lead investors in a busy week.
- **Footer issue counts, exact:** TLDR 12, Sifted 9, AlphaSignal 6, Techmeme 6, Term Sheet 5, Maddyness 5, Newcomer 4. Seven others have 1 each: Benedict Evans, Sunday CET, EU-Startups, TechCrunch Mobility, DeepLearning.AI, Import AI, Not Boring. Total 54. The footer says Maddyness IA sent none.

## Block 1: the week's story

- **Required:** the Anthropic IPO, ●●●●● (9 families), with these facts and dates:
  - Wed 18 Nov: priced at $83, above the range; about $81.3bn raised; largest IPO on record.
  - Thu 19 Nov: opened at $111.50 (+34%), closed at $97.17 (+17%); market cap about $1.3T.
  - Fri 20 Nov: AI sell-off: SoftBank about −15%, TSMC −5%+, Samsung and SK Hynix −6%+.
  - The greenshoe took proceeds to $93.5bn.
- **Required:** one "for us" line (wording free).
- **Forbidden:** "Nvidia reinstates Huang" (W48). CrowdStrike–Zscaler as a done deal (in W47 it was talks only).

## Block 2: early-stage rounds

**Counts** (tolerance ±2 unless marked exact):
- Early rounds: 63. In Europe: 36. Corrected from 55 and 28: the prototype missed rounds with a stated stage (LATO, Numina, Seva Money, Traitomic, Athlete To Athlete) and small rounds with no stated stage (Alecto, Ancep, Anyos); all were confirmed from the emails.
- Source mix: Term Sheet carried 33; the count without Term Sheet is 41. Corrected from 30 and 35, following the count.
- European $50M+ early rounds: 4, **exact** (Genesis AI, Boltz, Tiberius, Commit Biologics). Rest-of-world $50M+ early rounds: 3 (±1), counted only.
- The area table covers European rounds under $50M. **Its total must equal European count − European $50M+ early rounds** (W47: 32 = 36 − 4). The note under the table says so.

**Named European deep tech, required** (amount, stage, HQ; dots per the table above):
- Daisytuner (Darmstadt), €6m seed
- MountAIn (Grenoble), €7.3m seed
- Vetaion (Munich), €5.7m pre-seed
- Mosaico, €7.5m
- Stryx AI (Paris), €7.7m seed
- Elysian Aircraft (NL), €12m+ in grants and equity, labelled as such
- Dcubed (Munich), €27.2m Series A
- Remanence (Paris), $30m seed, on the "notable team" line or in the list

**Allowed:** other European deep-tech rounds under $50M. The prototype flagged Fermat, Arva AI, Wilgot and IntelliProve; all are unverified.

## Block 3: big rounds and marks

**Required rows** (amount, stage and valuation exact):

| Company | Round | Valuation |
|---|---|---|
| Isomorphic Labs (London) | $5B Series C | – |
| Genesis AI (Paris / San Carlos) | $500M Series A | $3.5B |
| Payhawk (London) | $280M Series C | $2B (corrected: stated by Techmeme and EU-Startups, 19 Nov) |
| Model ML (London) | $250M Series B | $1.5B |
| Boltz (London) | $110M Series A | – |
| Tiberius Aerospace (London / Newport Beach) | $85M Series A | $1B+ |
| Commit Biologics (Copenhagen) | €54m seed | – |

- **Required lines:**
  - "14 rounds of $100M or more" (±2), worldwide, equity only.
  - In talks: Sierra (~$1.5B at ~$30B) and Cognition ($2B+ at $75B).
- **Allowed:** Stark Future (Barcelona), €150m+ at €1.2B pre-money, led by Highland Europe (●●●). The valuation must be shown as pre-money. It meets the rule; the sample left it out. Mistral's additional €100M (EU-Startups 19 Nov) is allowed only if the fact-check confirms it is equity.
- **Forbidden:**
  - Hone Health as a $228M round (it is $28M Series A + $200M customer-value fund).
  - Ramon.Space, Megarobo, Corma and Hone as rows. None has a stated European HQ: check this, and if one has, it becomes allowed.
  - Any dollar total.

## Block 4: exits and new funds

- **Required:**
  - Palo Alto Networks → Applied Compute: $4.5B in stock; earlier valuation $3.25B. ●●●
  - Bending Spoons → Mailchimp: $3.68B; Intuit paid ~$12B in 2021. ●●●
  - Single-source list naming each source:
    - Nvidia–Inception, $500M+, talks (Techmeme)
    - MongoDB–Firebolt (TLDR)
    - Iceye–Avio, €2.05B (Sunday CET)
    - CrowdStrike–Zscaler, talks (Techmeme)
  - Funds:
    - Plural €1bn, European early stage, ●●●●
    - Sofinnova Crossover II €725m, late-stage life sciences, ●●
    - Norwest fund 18 $4B, US venture and growth, ●
- **Forbidden:**
  - Redalpine (a hire: people moves are out of scope).
  - Creandum (a lead on a round and a co-investor statistic, not a fund event).

## Block 5: market move

- **Required:**
  - GPT-6.2 Astra tokens 20% cheaper, $8 / $40 per million input/output tokens.
  - "Under one-third of the cost per task" attributed to OpenAI's own evals.
  - Gemini 4 Neon at $3 / $15 per million tokens.
- **Forbidden:** "one-third" presented as a price cut.

## Whole output

- None of the errors in README §5 recurs.
- Every amount and valuation shown is exact against its source.
