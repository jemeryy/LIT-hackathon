# Session Handoff — Case Helper: fish supplier scenario test in the browser, fixes, push and deploy

## Where it started
Jeremy asked for a browser test of the Case Helper on the Mark v Uncle Seng Seafood scenario (1,000 kg yellowtail, $2,000 deposit, $4,000 claim) using the PDFs in `C:\Users\jemer\code\hackathon\test docs\`, plus edge cases, fixing every bug and wording problem found, then push, deploy and hand off. He gave the green light for push and deploy in the same message.

## Important discoveries and decisions
- The hackathon hard deadline is 6 Sep 2026 12:00 SGT (from `BRIEF.md`). The scenario's dates (Sep to Oct 2026) sit after today, so Today now sorts into the timeline by date rather than always after the file events.
- uvicorn `--reload` is broken here: WatchFiles printed "Reloading" but the old worker kept serving old code, so fixes looked dead. Port 8002 is now held by a dead process (PID 44920, cannot be killed) and cannot be bound. Local server moved to port 8003, started without `--reload`; every code change needs a manual restart.
- The Sonnet reader marked the chat-export PDF as author `both`, so every row read "Signed by both of you". Root cause was `_clean` in `llm.py` keeping `both` for any PDF; now `both` survives only when the file is signed.
- The written request came back as `{}` twice on the first run: the letter hit the 700-token cap and the SDK returns an empty tool input on a cut-off. Caps raised (story 800, summary 800, letter 2000) and `_tool_call` now raises on `stop_reason == "max_tokens"`.
- An employment claim (kind `other`) crashed `rules.gate` with `UnboundLocalError` (`cat_known` unset in that branch). Every chat turn calls the gate, so any "other" claim returned a 400.
- The goods content set was written for faulty goods only. Reworded blind spots and gaps so goods not delivered fit, and added a 7th blind spot (b7): the seller offered a swap, a smaller delivery or a later date and you refused. This is Uncle Seng's exact defence.
- A file that does not match the claim (the tenancy deposit screenshot in the goods case) ranked strong. The reader tool now has a required `fits` boolean; a misfit fact ranks weak with the reason "The names, dates or amounts do not match your account", stays out of the story prompt and the timeline. A file the reader finds nothing in (the pet WhatsApp PDF) now shows "Read, nothing found for this claim".
- SSO Schedule text for the SCTA (checked live via playwright) has no motor vehicle exclusion, only the Community Disputes Resolution Act s 4 carve-out. The "other" gate text now says the tribunal does not hear work disputes, loans, or a neighbour dispute about noise, smell or the like. `CATEGORY_TEXT` for property damage still says "not from a motor accident"; left as the team wrote it, unverified either way. A neighbour aircon leak still routes to property_damage and passes the gate.
- The $30,000 consent was never recordable from chat (`consent_30k` was not a model field). Added; the gate amount text now says "If both sides sign the court's consent form for the $30,000 limit, tell us." The Judiciary site calls it a Memorandum of Consent.
- `describe_changes` printed "the $30,000 agreement is now True" because False is the default; False is now treated as unknown there.
- Chat wording fixes in `app.py`: a vague detail in a known case ("refusal was last Tuesday") now replies "I am not sure I got that right." plus the model's own exact-detail question, instead of "I cannot safely tell what this concerns"; an off-topic or legal question after the story ("Will I win?") replies "I can only collect facts. I cannot say who is right, or what you will get." and carries on with the next gap; "I dont have his address" now matches `NO_DETAIL` and gives up the item it names (`NO_DETAIL_ITEM` maps date/amount/my address/his address); an empty reply falls back to "Noted." plus the next question rather than "Nothing else is missing".
- UI: Add a file on a blind-spot card now shows only for the answer that means the other side has it (`x.when`), not always on Yes. Their files are skipped in gaps and in the claim pack zip. The viewer eyebrow says "The other side's file" for their file. "1 pages" is now "1 page".
- Model text now loses en and em dashes; the form summary is capped at 450 in the prompt and gets " I claim $X." appended when the amount is missing from it.
- While killing servers I also stopped a stray uvicorn on port 8000 (PID 15180) that matched the search; it was not one this session started.
- Playwright notes: `window.C` is not on window (top-level `let`); use `typeof C !== 'undefined'` in waits. `page.on('dialog')` inside `browser_run_code_unsafe` conflicts with the MCP's own dialog handling; override `window.confirm = () => true` instead. File upload paths must be under `c:\Users\jemer\code\hackathon`.

## Decisions locked + what shipped
- Commit `b9db897` (all the fixes above except the dash and summary ones): `C:\Users\jemer\code\hackathon\builds\case-builder\app.py`, `llm.py`, `rules.py`, `exports.py`, `static\index.html`, `content\blindspots.json`, `content\gaps.json`.
- Commit `b521319`: dashes stripped from model text, summary ends with the amount, in `llm.py`.
- Commit `dff172e`: the two earlier 6 Sep handoffs committed.
- Pushed to `origin/main` (`https://github.com/jemeryy/LIT-hackathon.git`). Deployed with `railway up --detach`; live at `https://case-helper-production.up.railway.app/` and verified end to end on the scenario (chat, gate, upload, 7 blind spots, rank, timeline, letter, summary ending "I claim $4,000.").
- `test docs/` left untracked on purpose (Jeremy's PDFs).

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-fish-supplier-test-deploy.md` — this handoff.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-their-evidence-sources.md` — previous state, Railway IDs, how evidence is split.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — `chat_turn` reply rules, `NO_DETAIL`, `NO_DETAIL_ITEM`, `describe_changes`, `_viewer_payload` eyebrow.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — `_clean` author rule, `fits` field, `TEXT_SPECS` caps, `write_text` post-processing, `consent_30k` field.
- `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` — `gate` other branch and consent text, `evidence` misfit, `timeline` today sort, `TIMELINE_LABEL`, `gaps` skips their files.
- `C:\Users\jemer\code\hackathon\builds\case-builder\content\blindspots.json` — goods set with b7.
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (unchanged).
- Memory files touched: none.
- Edge-case script (scratch, may be gone): `C:\Users\jemer\AppData\Local\Temp\ch\edge.py`, run as `python edge.py <n>` against port 8003.

## Running state
- Background processes: local uvicorn on port 8003, started detached with `python -m uvicorn app:app --port 8003` from the build folder (no shell ID, no reload). Kill with `for p in $(netstat -ano | grep ":8003 " | grep LISTEN | awk '{print $5}' | sort -u); do taskkill //F //PID $p; done` in Git Bash. Port 8002 is dead-locked by PID 44920; do not use it.
- Dev servers / ports: local `http://127.0.0.1:8003/` (`?example=1` for the worked example). Production `https://case-helper-production.up.railway.app/` on the pushed head, project `62f978e8-43f7-401f-9dce-69fc09b5daed`, service `f076ff97-b535-44e6-b90b-18ded88b3db2`.
- Open worktrees / branches: `main` at `dff172e`, in sync with `origin/main`. Untracked `test docs/`.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder; python rules.py` — `rules ok:`.
- `$env:USE_FIXTURES='1'; python selfcheck.py` — `selfcheck ok:`; then `git checkout -- data/` (the log file is tracked).
- Browser `http://127.0.0.1:8003/`: paste the Mark scenario with both addresses in one message, expect "I have enough details about your claim against Uncle Seng Seafood"; Next twice; add `SCT_Fishball_Dispute_Messy.pdf`; three strong rows with reason "The other side's own words, has amount and dates"; answer all 7 cards; rank; step 4 shows Today first, then Agreed, Paid, Seller replies; step 5 Open the letter gives a full letter.
- Add `deposit_transfer.jpg` from `sample\pack` to a goods case: one weak row, reason starts "The names, dates or amounts do not match your account".
- Chat "My boss did not pay my salary of $2,800 ... refused on 15 August 2026": no 400, reply says the tribunal does not hear work disputes.

## Deferred / pending tasks + open questions
- Deferred/pending: persistent storage; cases and files die on redeploy (this deploy wiped every visitor's case).
- Deferred/pending: `ranked` flag is front-end only; a page reload starts a new case (`load()` posts to `/api/case/new`).
- Deferred/pending: their-side files still go through the fact reader (spends credits, facts unused).
- Deferred/pending: the model sometimes asks a tenancy-style question ("What did the deposit agreement say about refunds?") in a goods case; harmless, the checklist still completes.
- Deferred/pending: the cause-of-action date for the scenario comes out as 28 Sep or 1 Oct 2026 depending on the run; both defensible.
- Deferred/pending: motor vehicle accident claims: whether the tribunal hears them is unverified; the taxi test message came back "cannot safely tell".
- Deferred/pending: the worked-example fixture reasons still say "His own words" (`content/fixtures.json`), untouched by the earlier they/them pass.
- Deferred/pending: deck, AI-disclosure slide, citations, Devpost submission before 12:00 SGT today.
- Deferred/pending: missing favicon (404 in console, harmless).
- Open: none.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` still governs. This session was a test-and-fix pass plus deploy; no new plan.

## Next steps
Deck, AI-disclosure slide, citations and the Devpost submission for the 12:00 SGT deadline. If time remains after that, persistent storage so a redeploy keeps cases.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-fish-supplier-test-deploy.md, then deck and submission items for the 12:00 SGT deadline.
