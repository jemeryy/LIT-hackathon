# Session Handoff — Case Helper: five steps, one evidence step with both rankings, chat fixes, deployed

## Where it started
Jeremy asked to read the previous handoff, pull and merge the teammate's GitHub main, then restructure the steps: step 1 tell us what happened (chat only, bigger), step 2 the tribunal gate, step 3 everything about evidence (upload, what to gather, what the other side may have, then rank the user's evidence and separately rank the other side's evidence). Later asks: upload spinner with the file shown but not clickable while reading, cleaner step 1 with no scrolling to reach the chat box, stop the chat repeating itself when the person has no address for the other side, and finally push and deploy.

## Important discoveries and decisions
- The teammate's merge on GitHub (`47e91b2`, merging `37ebaa2` "Dynamic Update between Step 1 and Step 2") was broken: `chat_turn` used `blocked`, `in_scope`, `NEXT_QUESTION` and `INTAKE_COMPLETE` that the merge dropped, so every chat turn crashed with NameError. Restored from their commit and rewired into our flow.
- The `/api/blindspot` route updated answers by hand and never re-ran `rules.blindspots`, so any derived field (now `theirs`) was stale. Fixed to recompute.
- The chat kept asking for the other side's address because the checklist item `respondent` needs name, address and in-Singapore, and the model obeys the MISSING list. The model gets the whole chat, the known facts, the checklist and the file names every turn (`llm.intake_turn`).
- `let C` in `index.html` is not `window.C`; a Playwright wait loop on `window.C` hung 30 minutes. Call `render()` and read `C` directly in evaluate.
- Bash cwd drifts between calls in this environment; use absolute paths for `cd`.
- Railway `railway up --detach` from the build folder deploys in about 40 seconds; each redeploy wipes every visitor's case (still no persistent storage).

## Decisions locked + what shipped
- Five steps: Tell us what happened, Can the tribunal hear it, Your evidence, Your timeline, What to do next. `maxStep()` returns 1 while the gate fails, 2 until all blind spots are answered, else 4 — `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html`.
- Step 3 is one scrolling page: A add your files (chips with status, spinner while reading, link only when read), B what else to gather (gap cards with Add a file), C what the other side may have (six Yes / No / Not sure cards, Add a file on Yes), D a button "I have added everything. Rank my evidence" (enabled once at least one file is read and all six are answered; front-end flag `ranked`, lost on reload), which reveals the story, D your evidence table, E the other side's evidence table.
- Other side's ranking is deterministic: each blind-spot question in `content/blindspots.json` now carries `they` (what they may show), `strength` and `when` (`yes` or `no`, the answer that means they have it). `rules.their_evidence` ranks the matching answers; Not sure counts one step weaker and is labelled — `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py`, `content/blindspots.json`.
- Step 1 is chat plus text box only. Start over lives in the bottom bar. Layout is height-bound: `#shell` is 100vh, `main` hides overflow, `#body` scrolls, the chat fills the remaining space, the text box auto-grows and has a drag corner. Send and Next are always on screen.
- Upload: a placeholder exhibit with status `reading` is pushed before the request; on error it is removed. `upload()` in `index.html`.
- Chat: "no", "dont have", "not sure", "no idea" and the like (`NO_DETAIL` regex) give up the next missing item among `SKIPPABLE` (claimant, respondent, agreed, amount, when); it is stored in `intake.skipped` and counted done by `checklist_state`; an empty address becomes "not known". A reflection already said in an earlier bot message is dropped. When nothing is left: "I have everything I can get from you. Press Next to check if the tribunal can hear it." When only files are left the reply says press Next then add files in step 3 — `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` `chat_turn`, `checklist_state`.
- Intake prompt tells the model to record a detail the person does not have as "not known" and not ask again; "add files on the right" wording replaced everywhere (questions.json, fixtures.json, llm.py, app.py).
- Demo script updated to v6 with the five-step beats — `C:\Users\jemer\code\hackathon\notes\demo-script.md`.
- Commits on `main`: `4c928cc`, `dc2ff63`, `c4d37c2`, `bb8bb43`. Pushed to `https://github.com/jemeryy/LIT-hackathon` (main at `bb8bb43`). Railway deployment `e09c8c44-2b3c-49fa-9285-5801a6c36ddc` SUCCESS; live page confirmed serving the five-step build.

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-one-evidence-step.md` — this handoff.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-per-visitor-corrections.md` — previous state, per-visitor cases, test cases, Railway IDs.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — `evidence()`, `ranking()`, `gapCard`, `spotCard`, `upload()`, layout CSS.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — `chat_turn` (NO_DETAIL, SKIPPABLE, blocked), `checklist_state`, `/api/blindspot`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` — `blindspots`, `their_evidence`.
- `C:\Users\jemer\code\hackathon\builds\case-builder\content\blindspots.json` — `they` / `strength` / `when` per question.
- `C:\Users\jemer\code\hackathon\test docs\` — Jeremy's three test PDFs (untracked).
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (unchanged).
- Memory files touched: none.

## Running state
- Background processes: a local uvicorn on port 8002 started with `python -m uvicorn app:app --port 8002 &` from the build folder (no shell ID; it was started detached). Kill with `taskkill //F //PID $(netstat -ano | grep ":8002 " | grep LISTEN | awk '{print $5}' | head -1)`.
- Dev servers / ports: local `http://127.0.0.1:8002/` (may still be up). Production `https://case-helper-production.up.railway.app/`, project `62f978e8-43f7-401f-9dce-69fc09b5daed`, service `f076ff97-b535-44e6-b90b-18ded88b3db2`.
- Open worktrees / branches: `main` at `bb8bb43`, equal to `origin/main`. Untracked `test docs/`. Runtime files under `builds/case-builder/data/` get modified by selfcheck; discard with `git checkout -- builds/case-builder/data/` before pulling.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder; $env:USE_FIXTURES='1'; python selfcheck.py` — ends with `selfcheck ok:`.
- `python rules.py` from the build folder — `rules ok:`.
- Browser: `http://127.0.0.1:8002/?example=1` (or live). Step 1 shows no page scroll, Send and Next visible. Step 3: answer all six, press the rank button, two tables appear; the other side's table lists Yes and Not sure answers strongest first.
- Live chat (spends credits): new case, give a story with the other side's name, reply "dont have" to the address question — reply moves to the next missing item and never asks for the address again.
- `railway deployment list --json` from the build folder — latest `SUCCESS`.

## Deferred / pending tasks + open questions
- Deferred/pending: persistent storage; a redeploy wipes every visitor's case and files.
- Deferred/pending: `ranked` flag is front-end only; a reload hides the ranking tables until the button is pressed again.
- Deferred/pending: no live-credit test was run this session on a fresh case with a real upload; only the example and the selfcheck fixtures.
- Deferred/pending: "Still missing" lists in step 3 B are static per category.
- Deferred/pending: deck, AI-disclosure slide, citations, Devpost submission.
- Deferred/pending: judiciary claim types not modelled (unfair practice, motor vehicle deposit, statutory).
- Open: none.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` still governs. This session was a step restructure and bug fixes on top of it; no new plan.

## Next steps
Have Jeremy click the live site through a fresh case end to end (hard refresh first). Then persistent storage if the demo needs cases to survive a redeploy, else the deck and submission items.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-one-evidence-step.md, then test the live site on a fresh case and pick up persistent storage or the deck.
