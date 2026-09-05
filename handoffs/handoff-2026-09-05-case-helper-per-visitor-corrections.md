# Session Handoff — Case Helper: one case per browser, chat corrections re-gate steps, live tests on three new cases

## Where it started
Jeremy reported two live bugs on `https://case-helper-production.up.railway.app/`: the example's files and facts appeared inside a user's own case, and step 5 (blind spots) had no way to add a file after answering Yes. He then asked that going back to step 1 and correcting a fact must update every later step and re-lock gated steps, that the eligibility rules follow `https://www.judiciary.gov.sg/civil/cases-eligible-small-claim`, and that everything be tested live on three new cases (Mark v Uncle Seng fish order, the fishball chat-export PDF, and a landlord no-pets breach with two PDFs). Later asks: step 4 must name what each file proves per category, and the worked example must be a plain new case with the chat and files in step 1.

## Important discoveries and decisions
- Root cause of the leak: `app.py` held one global `CASE` for every visitor, uploads went to `data/uploads/<asset_id>/` and OCR/render caches were keyed by asset id (E1, E2). Anyone opening the example replaced everyone's case, and two users' E1 collided. The S$4,000 facts next to a S$2,600 PDF in Jeremy's screenshot were his own live-read lease facts attached to the example's PDF.
- `llm.use_fixtures()` also returned true when no API key was set, so a keyless server silently replayed saved Mei Ling facts keyed by filename. Now only `USE_FIXTURES=1` replays; a missing key fails loudly.
- The chat printed a fixed line ("I have enough details... add files on the right") whenever only files were missing. It swallowed the model's reply, so corrections looked ignored. Short corrections ("apologies, he is from malaysia", "the claim amount is $31000") were also marked unclear/low confidence by the model, so fields were not applied.
- `write_text` crashed with `TypeError` when a file was uploaded before the claim amount was known (`f"${amount:,.0f}"` on None). The upload error handler hid it as "Could not read ... (TypeError)".
- Tenancy gap and blind-spot content is written for a tenant claiming a deposit. A landlord claimant (respondent role "tenant") got tenant-perspective questions.
- Fixtures in `content/fixtures.json` match the sample pack (S$2,600, 3 Aug 2025). No fixture refresh needed.
- Step 2 is not gated on files. Its four checks use only typed facts (kind of claim, amount, refusal date, other side in Singapore). Steps 3 to 7 open once those pass.
- Visiting an earlier step never re-locks anything; only a changed fact does (`maxStep()` is computed from case state on each render).
- Railway deploys in about 20 seconds; live chat turns are 4 to 20 seconds; each PDF read is about 17 seconds.

## Decisions locked + what shipped
- Per-browser cases: `visitor` cookie (32-hex, httponly, 1 year) set by a Starlette middleware, `contextvars` carries it into every route, cases live in `CASES[vid]` and `data/cases/<vid>.json`, uploads in `data/uploads/<vid>/<asset_id>/`, cache glob narrowed to `extract.cache_key` — `C:\Users\jemer\code\hackathon\builds\case-builder\app.py`. `data/cases/` is gitignored.
- Example: built once into `EXAMPLE`, deep-copied per visitor on `/api/case/reset`. `?example=1` now POSTs reset itself (idempotent). Blind spots start unanswered; `SAMPLE_BLINDSPOTS` removed — `app.py`, `static/index.html`.
- Chat corrections: `describe_changes()` states every corrected known fact ("Noted: the amount you claim is now $31,000; the other side is not in Singapore."), the model reflection is dropped when a change note exists, and when the gate fails after a complete intake the reply appends `gate.stop` so the eligibility problem is said in the chat — `app.py` `chat_turn`.
- A stated claim total (`explicit_claim_amount`, now also matching "claim amount is $X") is kept even when the model marks the message unclear — `app.py`.
- `safe_intake_reply` with no questions returns the reflection or empty string instead of the unsafe-output fallback; final fallback is "Noted. Nothing else is missing." — `app.py`.
- Intake prompt tells the model a short follow-up continues the same claim and a correction replaces the known value — `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py`. Story prompt no longer says "You rented..." for every claim type. `money()` helper handles a missing amount.
- Eligibility text: category failure now names motor vehicle damage, neighbour damage and work disputes as excluded; over-limit amount text adds "You can give up the part above the limit and claim the limit instead." — `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` `gate`.
- `rules.ctype` returns "general" for tenancy when the respondent role starts with "tenant" (landlord claimant) — `rules.py`.
- Step 4 "You have" lists up to four facts per category with the exhibit id, not the file name — `rules.gaps`.
- Step 5: an "Add a file" label appears bottom-right of a blind-spot card when its answer is Yes — `static/index.html` `blindspots()`. `render()` clamps `step` to `maxStep()`.
- `selfcheck.py` now seeds `CASES["0"*32]` and passes that cookie to the TestClient; expects 0 answered blind spots in the example.
- Commits `25f9b7b` and `a4c99c4` on `main`, pushed to `https://github.com/jemeryy/LIT-hackathon`. Railway deployment `6f52d7ee-313c-405a-bf5e-84d4c8488e07` SUCCESS. Live checks after deploy: new case blank with cookie, example 6 exhibits / 7 chat messages / 0 blind spots answered, two visitors isolated.
- Judiciary items not built: consumer unfair-practice claims, motor vehicle deposit refunds, statutory claims, bankruptcy permission rule. `CLAIM_TYPES` still `tenancy/goods/services/property_damage/other/unknown`.

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-per-visitor-corrections.md` — this handoff.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-railway-ai.md` — previous state, Railway IDs, secrets handling.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — middleware, `current()`, `chat_turn`, `describe_changes`, upload path.
- `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` — `gate`, `gaps`, `ctype`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — intake prompt, `use_fixtures`, `money`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — `load()`, `render()`, `blindspots()`.
- `C:\Users\jemer\code\hackathon\test docs\` — Jeremy's three test PDFs (untracked, not committed).
- Scratch test scripts (session temp, may be gone): `C:\Users\jemer\AppData\Local\Temp\claude\c--Users-jemer-code-hackathon\491aa374-f526-463d-b4a4-34477190ce7e\scratchpad\iso_check.py` (two-visitor isolation) and `live_check.py` (three live cases; args `fish fishball lease`). Worth copying into `builds/case-builder/` if kept.
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (not changed this session).
- Memory files touched: none.

## Running state
- Background processes: none. Local uvicorn on port 8001 was started and stopped twice this session. The old PID 15180 on port 8000 from the previous session was not touched; check with `Get-NetTCPConnection -LocalPort 8000` before relying on it (it predates all changes).
- Dev servers / ports: none local. Production `https://case-helper-production.up.railway.app/`, project `62f978e8-43f7-401f-9dce-69fc09b5daed`, service `f076ff97-b535-44e6-b90b-18ded88b3db2`, deployment `6f52d7ee-313c-405a-bf5e-84d4c8488e07`.
- Open worktrees / branches: `main` at `a4c99c4`, equal to `origin/main`. Uncommitted: `handoffs/handoff-2026-09-05-case-helper-railway-ai.md` (edited last session), runtime files under `builds/case-builder/data/`, untracked `test docs/`.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder; $env:USE_FIXTURES='1'; python selfcheck.py` — ends with `selfcheck ok:` and six evidence keys.
- Two-visitor check: POST `/api/case/new` with one cookie jar, POST `/api/case/reset` with another, GET `/api/case` with the first — first stays at 0 exhibits, `visitor` values differ.
- Live correction check (spends credits): new case, send the Mark v Uncle Seng story, then "apologies, he is from malaysia" — reply starts "Noted: the other side is not in Singapore." and ends with the service failure text; `gate.pass` false; then "sorry, I mean he is in Singapore and I want to claim $4,000" — gate true again.
- `railway deployment list --json` from the build folder — latest deployment `SUCCESS`.

## Deferred / pending tasks + open questions
- Deferred/pending: persistent storage. Cases and uploads still live on Railway's ephemeral disk and in process memory; a redeploy wipes every visitor's case.
- Deferred/pending: the "Still missing" lists in step 4 are static per category; they do not shrink when a file already covers an item.
- Deferred/pending: add judiciary claim types not modelled (unfair practice, motor vehicle deposit, statutory) if the demo needs them.
- Deferred/pending: upload progress state; PDF reads take about 17 seconds with no feedback beyond "Reading".
- Deferred/pending: the example's saved facts come from `content/fixtures.json`; if the sample pack is regenerated, refresh the fixtures.
- Deferred/pending: deck, AI-disclosure slide, citations, Devpost submission (carried from earlier handoffs).
- Deferred/pending: commit or discard the edited previous handoff file.
- Open: none.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` still governs. This session was bug-fix and hardening work on top of it; no new plan was written.

## Next steps
Have Jeremy click through the live site with a fresh browser on one of the three test cases and note anything wrong. Then decide whether persistent per-visitor storage is needed before the demo. Then the deck and submission items from the earlier handoffs.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-per-visitor-corrections.md, then browser-test the live site on a new case and pick up persistent storage or the deck.
