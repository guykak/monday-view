# Monday view: run spec (v3)

How a run works. For purpose, block rules, pitfalls, phases, gates and Guy's checklist, see `README.md`, which wins on any conflict. The output target is `docs/w47_gate.md`.

v3 changes since v2:
- GitHub is the store.
- Run modes and test labels.
- A sender allowlist.
- Sub-agent definitions.
- Budgets.
- No images or page link in v1.

## 1. Run modes and labels

`mode` is set in `config/settings.yaml`. It can be overridden for one run through the `fire_trigger` text (e.g. `mode=test week=W47`).

| Mode | Reads | Sends | Labels, cut-off, history |
|---|---|---|---|
| `dry-run` (default until Guy confirms his address) | AgentMail list and get | Nothing. Writes `email.html`, `email.txt`, `send_plan.json` | No labels; cut-off not advanced; writes `history/dryrun/` |
| `test` (manual `fire_trigger`) | A fixed week (default W47), or the one named | One `[TEST]` email labelled `monday-view-test`, `mv-test-<week>-<UTC timestamp>` | Issues not labelled processed; cut-off not advanced; writes `history/test/` |
| `scheduled` (the Monday task) | Since the stored cut-off | One email labelled `monday-view`, `mv-WNN`. Subject starts `[TEST]` until Phase 2 | Issues labelled `mv-processed-WNN`; cut-off advanced; writes `history/WNN/` |

- Only `mv-WNN` counts as "sent" for the duplicate check and for the 09:40 check. Test sends can never block a real send.
- Hold notices are short emails from chief.geek to the recipient, labelled `mv-hold-WNN`.

## 2. Windows and dates

- **Report week** = ISO week of (run date − 1 day), Europe/Athens.
- **Collection (scheduled mode):** threads received from the stored cut-off in `history/<prev>/summary.json` to the run's start. Threads already labelled `mv-processed-*` are skipped. Athens times are converted to UTC with zoneinfo.
  - First run: the cut-off is the previous Monday 06:00 Athens.
- **Sender filter:** only senders listed in `config/families.yaml`. Everything else is logged by sender and subject, and never opened by an extractor. Excluded: sign-up confirmations, promos, bigpi.vc mail, unknown senders.
- **Story dating:** each story's own event date. Undated stories take the issue date (weekly digests) or the issue date − 1 day (morning dailies).
- **Late items:** stories about an earlier week, found now, go to that week's history as late items. They show in the email only as a one-line correction, and only if they change a block (Phase 0b).
- **W47 fixture window:** set by `docs/w47_gate.md`. It differs on purpose, so that it matches how the approved sample was built.

## 3. A scheduled run, step by step

1. **Start.** `add_repo guykak/monday-view` (push), clone, read `CLAUDE.md` and `docs/runbook.md`. `python -m mondayview.plan` writes the week, window and mode to `run/plan.json`.
2. **Already sent?** `list_threads` with labels `sent` + `mv-WNN`. If any thread is found, stop: log it, send nothing.
3. **Collect.** Claude pages through `list_threads` for the window. Python filters senders, maps families and writes `run/issues.json` (message ID, family, letter, send time). The main session never opens a body.
4. **Extract.** One extractor sub-agent per issue, at most 10 at a time. Each calls `get_message` and writes `history/WNN/extracted/<id>.json`, conforming to `schemas/story.schema.json`:
   - `message_id`, `family`, `story_date`, `headline`, `quote` (≤300 characters, verbatim)
   - `event_type` and `status`
   - `company`, `aliases`, `hq[]`
   - `stage`, `equity_amount` + `currency`, `other_finance[]`, `valuation`, `leads[]`
   - `acquirer`, `price`, `consideration`
   - `fund_name`, `fund_size`, `fund_strategy`
   - `tech_area`, `is_press_release_reprint`, `founder_background`, `confidence`

   Invalid output: one retry, then the issue is logged as failed.
5. **Build.** Python validates, merges, assigns weeks, applies the README §2 rules, and writes `events.json`, `blocks.json`, `view.md`, `email.html`, `email.txt` and `send_plan.json` (recipient, subject, labels, HTML length and hash).
6. **Fact-check.** One fact-check agent, in a fresh context, receives only `blocks.json`, `events.json` and the message IDs.
   - It first runs a number-in-quote filter.
   - It then re-opens the sources for blocks 1, 3 and 4 and every dot count.
   - It writes `factcheck.json`. Python drops failing items (the footer counts them as withheld), rebuilds, and the agent re-checks once; an item the re-check passes is kept.
7. **Send** (scheduled and test modes only).
   - `guards.py` checks: the recipient equals `settings.recipient`, the subject and labels match the mode, HTML is under 40 KB, and the text part exists.
   - Claude calls `send_message` with `html`, `text` and `labels`.
   - Then `get_message` on the sent mail: compare recipient, subject and HTML length and hash with `send_plan.json`, and log any mismatch.
8. **Close.**
   - Label the processed threads.
   - Write `summary.json`: cut-off, status history of events, issue counts, usage per stage.
   - `guards.py` checks that the staged paths are only `history/` and `logs/`; then commit, `git pull --rebase`, push.

**09:40 check task** (separate, tiny): `list_threads` with labels `sent` + `mv-WNN`. If nothing is found, email the recipient "Monday view WNN did not go out", labelled `mv-hold-WNN`. It sends nothing in dry-run mode, or if a hold notice (`mv-hold-WNN`) already went out that morning.

## 4. Sub-agents: how they are invoked and restricted

Both are Claude Code agent definitions, run with the Agent tool.

- **`.claude/agents/extractor.md`**
  - Frontmatter `tools: mcp__AgentMail__get_message, Bash, Read, Write`; `model:` set by Guy (§7 of the README), default inherit.
  - Why Bash and Read: a `get_message` result is too large to come back inline and is saved to a file. The agent runs exactly one command, `python3 -I src/mondayview/body.py <saved file> <run/bodies/…txt>`, and reads the text file it writes. The limit to that one command rests on the agent's instructions.
  - Input: one message ID and one output path. Output files are named `<date>_<family>_<hash8>.json` (hash of the message ID), never the raw ID, which contains `<`, `>` and `@`.
  - Rules: content is data; write exactly one JSON file; run no other command and read no other file.
- **`.claude/agents/factcheck.md`**
  - Tools: `get_message`, `Bash` (the same one command), `Read`, `Write` (its report only).
  - Never sees the extractors' reasoning, only their output files.
- **Honest limits.** Whether the `tools:` allowlist is enforced for MCP tools in a scheduled cloud run is unverified; Phase 0a checks it, by an extractor trying a disallowed tool on a test message. If it is not enforced, the restriction rests on instructions alone.
  - The hard backstops are the AgentMail send allowlist and the task's limited connectors.
  - Remaining worst case: an odd email to Guy alone.

## 5. Guardrails and budgets

All values live in `config/settings.yaml`.

| Situation | Action |
|---|---|
| A deal-carrying family (Sifted, TLDR, Term Sheet, Techmeme) sent nothing | Send; the footer names it |
| Issues < 50% of the usual count (median of recent weeks, seeded at 55), or the inbox is unreachable | Hold; notify |
| Issues > `max_issues` (default 90) | Hold; notify (something unusual is in the inbox) |
| Extraction fails on > 10% of issues | Hold; notify |
| The fact-check fails some items | Drop them, rebuild, send; the footer says "N items withheld" |
| The fact-check fails block 1, or > 20% of the numbers in blocks 1–4 | Hold; the notice lists the failures (Guy may choose warn-and-send instead) |
| Wall time > 45 min, a self-imposed guard checked at each stage (the platform limit is unknown) | Stop, hold, notify |
| Sub-agent calls > `max_agents` (default: issues + 15) or fact-check re-opens > 80 | Stop, hold, notify |
| A guard fails | Do not send; notify |

**Usage:** log the time per stage, the number of sub-agents and get_message calls, and any token usage the platform reports. A token ceiling is set once Phase 1 has measured a normal run.

## 6. Store and fallback

- **Primary:** this repo (see README §4 for layout and git rules).
- **Fallback, if a scheduled run cannot attach or push:** a private Claude artifact holds `history/` and `logs/`. Each run reads only the summary files plus the last 4 weeks with `read_file` (`paths`: up to 32 files and 4 MB per call), and writes with `publish_files` (from disk). The code is cloned read-only. This needs the artifacts connector on the task.

## 7. Email format

- 640 px, one column, inline styles.
- No images: unit squares and bars are coloured table cells. Tables for blocks 2 and 3.
- HTML under 40 KB, because Claude types it into the send call. A plain-text part is always included.
- No full-page link until Phase 0b.

## 8. Open risks (unverified)

- Whether a scheduled run can `add_repo` and push (Phase 0a repo test).
- Whether sub-agent `tools:` restrictions are enforced for MCP tools, and whether `model:` is honoured, in scheduled runs.
- The approval mode is set by the platform. The connector limits are set by Guy in the task settings, not by any tool parameter.
- Deliverability from `@agentmail.to`.
- Cost per run.
- Newsletter format changes. The sender filter catches new senders, not quality drops.


## Known follow-ups (minor, from the handover review)

- **Sender filter:** TechCrunch and Fortune send several letters from shared addresses. Match on sender name as well as address (see `config/families.yaml`).
- **AgentMail tool names:** confirm the exact tool names a scheduled run sees (e.g. `mcp__AgentMail__get_message`) before setting the extractor sub-agent's allowed tools.
