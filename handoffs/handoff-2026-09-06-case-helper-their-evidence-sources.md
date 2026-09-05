# Session Handoff — Case Helper: live test, other side's files as their evidence, source and why columns, wording leaks

## Where it started
Jeremy asked to read the previous handoff, test the live site on a fresh case, then pick up persistent storage or the deck. He also asked how the tool splits your evidence from the other side's. Mid-test he stopped it and asked for four changes to step 3: a Source column (not "Where") on the other side's table, files grouped into for and against, a file added under a "what the other side may have" card shown in that card, and a Why column for strong / medium / weak. Then: fix every place where fixed wording assumes the wrong case (the gate said "a deposit refund" for a landlord claiming rent).

## Important discoveries and decisions
- Live bug found on the first chat turn: the model (Sonnet 5 via OpenRouter) returned the two questions as one string with quotes inside instead of a list. The safety filter iterated the string's letters and kept only the two "?" characters, so the reply read "You say ... ? ?". Local calls returned a proper list; it is nondeterministic. Fixed by normalising in `llm.question_list`.
- The live log is readable with `MSYS_NO_PATHCONV=1 railway ssh -- tail -c 3000 /app/data/llm_log.jsonl` from the build folder (Git Bash mangles `/app` without the env var).
- Someone else (teammate) was clicking the live site at the same time (uploads of unrelated PDFs at 16:53 UTC).
- Jeremy's three test PDFs in `C:\Users\jemer\code\hackathon\test docs\` are a landlord's case (Lim Tan Chia v tenant Chua Tay Lau, no-pets breach, S$2,000 a month, 5 May 2026 to 4 Jul 2027). A story that does not match the files gets flagged by the reader as "different parties" but still ranks strong; a matching story gives two strong rows from the lease and one medium from the WhatsApp log.
- How evidence is split: a file added in section A is yours and goes through the reader and `rules.evidence` (strength from author, date, amount). A file added with the Add a file button on a Yes card in section C is the other side's: it is stored with `side: "theirs"` and `spot: <question id>`, skipped by `rules._facts` so it never enters your ranking, gaps or timeline, and shown as the source on the matching row of their table. Their strength stays the fixed value in `content/blindspots.json`, one step weaker on Not sure.
- `rules.ctype` already sent a landlord (respondent role tenant) to the general content set. The extractor in `llm.extract_facts` used `case["claim_type"]` instead, so a landlord's files were read against the tenant deposit keys. Now both use `rules.ctype`. A seller chasing a buyer (goods with respondent role buyer or customer) also goes to general now.
- Playwright: `#say` is the chat box (a second textarea `#wr-text` exists). File upload paths must start with lowercase `c:\` to pass the allowed-roots check. The Add a file control is a `label`, click it then call file upload.

## Decisions locked + what shipped
- Commit `3f46fd7`: `question_list` in `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py`, two asserts appended to `selfcheck.py`.
- Commit `54ff627`: `/api/upload` accepts `side` and `spot` form fields (`app.py`); `rules._facts` skips `side == "theirs"`; `rules.their_evidence(qs, exhibits)` adds `sources` (file label, title, viewer_url) and `why` from `THEIR_WHY`; `rules.blindspots` passes the exhibits; rules self-test covers it. `static/index.html`: `addFile(cls, spot)`, `upload(input, id, spot)`, section A split into "Your evidence" and "The other side's evidence (added under C below)", `spotCard` lists its files, `exh` hoisted to top level, both tables have a Source column, their table has a Why column and drops "What answers it".
- Commit `257b0fa`: gate category line is "a dispute under a home lease of 2 years or less"; time-bar lines say "the day the {role} refused or the loss happened"; `ctype` sends goods with a buyer or customer respondent to general; extractor uses `rules.ctype`; he/him/his in tenancy content replaced with they/them; "Cleaner or mover receipt, 31 Jul" lost its example date (`content/gaps.json`).
- Not deployed. Live site still runs `bb8bb43`. Jeremy has not given a green light this session.

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-their-evidence-sources.md` — this handoff.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-one-evidence-step.md` — previous state, Railway IDs, layout notes.
- `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` — `ctype`, `_facts`, `gate`, `their_evidence`, `THEIR_WHY`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — `addFile`, `upload`, `exh`, `evidence`, `spotCard`, `ranking`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — `/api/upload` side and spot.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — `question_list`, `extract_facts` key set.
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (unchanged).
- Memory files touched: none.

## Running state
- Background processes: local uvicorn on port 8002, started detached with `python -m uvicorn app:app --port 8002` from the build folder (no shell ID). Kill with `taskkill //F //PID $(netstat -ano | grep ":8002 " | grep LISTEN | awk '{print $5}' | head -1)`. It runs the latest committed code.
- Dev servers / ports: local `http://127.0.0.1:8002/` (`?example=1` for the worked example). Production `https://case-helper-production.up.railway.app/`, project `62f978e8-43f7-401f-9dce-69fc09b5daed`, service `f076ff97-b535-44e6-b90b-18ded88b3db2`, still on `bb8bb43`.
- Open worktrees / branches: `main` at `257b0fa`, three commits ahead of `origin/main`. Untracked `test docs/` and the two handoffs.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder; python rules.py` — `rules ok:`.
- `$env:USE_FIXTURES='1'; python selfcheck.py` — `selfcheck ok:`; then `git checkout -- data/`.
- Browser `http://127.0.0.1:8002/?example=1`, step 3: answer the first card Yes, Add a file on that card, wait; the file appears in the card and under "The other side's evidence" in A, your evidence count stays 6, press the rank button; their table shows Source (the file) and Why.
- Landlord gate wording: in python, `rules.gate` on a tenancy case with respondent role `tenant` prints "a dispute under a home lease of 2 years or less".

## Deferred / pending tasks + open questions
- Deferred/pending: deploy (`railway up --detach` from the build folder) and push once Jeremy says go. A redeploy wipes every visitor's case.
- Deferred/pending: persistent storage; cases and files die on redeploy.
- Deferred/pending: `ranked` flag is front-end only; a reload hides the tables until the button is pressed again.
- Deferred/pending: a file that does not match the story (different parties) is still ranked strong; the reader flags it in the fact text only.
- Deferred/pending: their-side files still go through the fact reader (spends credits, facts unused).
- Deferred/pending: "Still missing" lists in step 3 B are static per category.
- Deferred/pending: deck, AI-disclosure slide, citations, Devpost submission.
- Deferred/pending: missing favicon (404 in console, harmless).
- Open: none.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` still governs. This session was a live test, bug fixes and step 3 changes on top of it; no new plan.

## Next steps
Get Jeremy's go, then push and deploy, hard refresh the live site and re-run the landlord case from `test docs/` end to end. Then persistent storage if the demo needs cases to survive a redeploy, else the deck and submission items.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-their-evidence-sources.md, then ask Jeremy for the go to push and deploy, retest the landlord case live, then storage or the deck.
