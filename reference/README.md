# reference/: index

Frozen inputs from the interactive prototype session (26 Nov 2026). Don't edit them. Precedence and rules are in the top-level `README.md`. The W47 target is `docs/w47_gate.md`.

**Status key**
- **Authoritative**: use as truth.
- **Superseded**: corrected elsewhere; named below.
- **Evidence**: the reasoning record.
- **Data**: produced by the flawed prototype; check before use.
- **Throwaway**: do not reuse.

## approved/
| File | What it is | Status |
|---|---|---|
| `w47_sample.md` | The approved Monday view for W47 (16–22 Nov). Read it with `docs/w47_gate.md`, which resolves its ambiguities | Authoritative |
| `w47_visual.html` / `.png` | The approved 1440 px full page (Phase 0b) | Authoritative for layout and encodings |
| `email/w47_block1–5.png` | The approved look per block. The v1 email rebuilds it with HTML table cells | Authoritative for look only |
| `proposal_v1.md` | The 5-block proposal, noise rules and the rejected ideas. **Known errors:** block 2 "under $50M" (V5); block 5 "one-third of GPT-6's cost" (V1); MountAIn ●●●● (is ●●●); Plural ●●●●● (is ●●●●) | Intent only; superseded on rules and dots |

## reviews/
| File | What it is | Status |
|---|---|---|
| `weekly_factcheck.json` | R1–R12 issues and fixes; `visual_check` V1–V5. Its "Plural 5+" predates the H1 correction (Plural = 4) | Evidence |
| `directions_review.json` | Review of the earlier A/B/C directions, B1 and C1, and its `recheck` (send-time ordering, one-story trends). Source of the funding-data errors | Evidence |
| `automation_review.json` | A1–A18 on the automation spec | Evidence (built in) |

## data/
| File | What it is | Status |
|---|---|---|
| `w47_family_counts.json` | Per-item family lists for W47, **corrected**: MountAIn 3 (V2), Mailchimp 3 (V3), Plural 4 (H1: Maddyness "pluralisme" was a false match). **The source for dots** | Authoritative for families. Its dates are coverage dates, not story dates (some precede the event, e.g. a "sell-off" entry on 16 Nov) |
| `stat_tests.json` | Statistical tests behind the proposal. Key `revision_2026_11_26` has W47 family lists and facts | Superseded for dots (MountAIn 4, Mailchimp 2, Plural 5 there are wrong). Evidence for the block-1 facts |
| `issue_message_ids.json` | 223 AgentMail message IDs (29 Oct–26 Nov) → `date_family_hash`. Fetch with `get_message` from `chief.geek@agentmail.to` | Authoritative |
| `inbox_inventory.json` | All 3,254 threads (10 Apr–26 Nov): sender, sender_email, subject, date, last message ID. Regenerated with correct keys. Used to seed `config/families.yaml`; can be dropped later | Authoritative (metadata only) |
| `w47_rounds.json`, `funding_clean.json` | Rounds as the prototype built them | Data: `company` is often wrong (e.g. "Robotics"); areas are keyword-tagged |

## Other
| File | What it is | Status |
|---|---|---|
| `findings_directions_round.md` | Findings of the first, rejected round (media analytics). Several figures were later corrected | Evidence of what Guy found low-value |
| `prototype/` | Regex parsers, keyword tagging, clustering, hand fixes, render scripts. Hard-coded paths (`/home/claude/newsviz/...`) do not exist in a fresh session | Throwaway; never import |
