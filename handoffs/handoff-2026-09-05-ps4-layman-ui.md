# Session Handoff — Case Builder: layman UI pass done, screenshots retaken, deck next

## Where it started
Jeremy read the real-product handoff and asked for the layman UI pass: drop the "What we need" checklist
panel, big plain text everywhere including chat replies, lock steps 6 and 7 behind the blind spots, test
mobile and desktop with Playwright, retake the step screenshots. Mid-session he added "consult codex for the
UI". Audience is old uncles and aunties: no small text, no jargon, no unnecessary UI. Session Sat 5 Sep 2026
~18:20 to ~19:00 SGT. Hard deadline Sun 6 Sep 12:00 SGT. Deck not started.

## Important discoveries and decisions
- Bug found via the screenshots: the file preview for E1 (tenancy agreement) showed the Ah Seng quote from the
  earlier live test on page 1. Cause: page images and video frames were cached by exhibit id only
  (`E1_p0.png`), so a new case's E1 reused the last case's pictures. Fixed by keying the cache on id plus an
  md5 of the file path (`extract.cache_key`). `data/cache` was wiped.
- Playwright cannot overwrite a PNG in `notes/screens` while it is open in the VS Code image viewer (OSError 22).
  Workaround: screenshot to the scratchpad and copy over.
- Codex review (codex-rescue agent) returned 9 findings. Applied: preview squeezing the layout at 1440,
  tiny tap targets on links, keyboard access, buttons live before load, no fetch error handling, step 2 fail
  message, three jargon lines, faint locked-step grey. Skipped: turning every clickable div into a real
  `<button>` (tabindex + Enter handler covers it).
- The checklist backend (`content/questions.json`, `app.checklist_state`) stays because it feeds the model
  prompt; only the panel is gone.

## Decisions locked + what shipped
All in `C:\Users\jemer\code\hackathon\builds\case-builder\`:
- `static/index.html` rewritten. Base 20px, nothing under 17px, buttons 52px tall. Checklist panel gone.
  `maxStep()` gates: gate must pass to go past step 2, all blind spots answered to go past step 5; rail shows
  "Locked", Next disabled, `go(n)` refuses. `@media (max-width: 900px)`: rail hidden, side panels stack,
  evidence table becomes cards (`td[data-h]`). `body.pv` (preview open) hides the rail and stacks panels.
  `api()` wraps fetch in try/catch with a plain banner. Duplicate source labels on one row deduped.
  Step names: "Can the tribunal hear it?", "Your evidence, best first", "What the other side may say",
  "Your timeline".
- `llm.py` `SYSTEM_INTAKE`: short sentences under 12 words, simple words, no praise or exclamation marks,
  reply under 50 words. `app.py` `FIRST_MESSAGE` split into short questions.
- `content/fixtures.json` three bot replies shortened. `content/gaps.json`, `blindspots.json`,
  `nextsteps.json`: plain words (no CJTS, Consultation, e-Negotiation, Submission for Hearing, Respondent
  Copy, Declaration of Service, counterclaim). Categories now "Messages and calls", "The agreement",
  "Payments", "Photos and video", "Your letter asking for the money".
- `rules.py`: timeline future labels ("Send your letter", "File your claim online", "Give the other side a
  copy", "First court meeting"), gate texts without "CJTS category" or "cause of action".
- `extract.py` `cache_key()`, used by `keyframe_path`, `keyframe_seconds` note and `viewer.render`.
- `notes/demo-script.md`: step names updated, note that 6 and 7 stay locked.
- Screenshots retaken: `C:\Users\jemer\code\hackathon\notes\screens\step-1-chat-intake.png` to
  `step-7-next-steps.png` (1440 wide, step 3 with the highlight preview open) and `phone-1-...` to
  `phone-7-...` (390 wide). Older `shot-*.png` and `01-chat-intake.png` are stale leftovers.
- Git: nothing committed this session. Everything since `ee9befc` is uncommitted (real-product changes from
  the last session plus this UI pass).

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-layman-ui.md` — this file.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-real-product.md` — previous session, the
  architecture and the chat intake design.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — the whole UI.
- `C:\Users\jemer\code\hackathon\notes\demo-script.md` — v5 with this session's step-name edits.
- `C:\Users\jemer\code\hackathon\BRIEF.md` — judging criteria and submission rules, needed for the deck.
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (changelog not
  updated for this session; the UI pass and the cache fix should be added as two lines).
- Scratch scripts (may be gone): `uitest.py` (layout, font-size and lock checks at 1440 and 390),
  `shots.py` (step screenshots, both widths) in
  `C:\Users\jemer\AppData\Local\Temp\claude\c--Users-jemer-code-hackathon\ef0c67af-4a24-4f73-9d43-dafd43efbb5a\scratchpad\`.
- Memory files touched: none.

## Running state
- Background: uvicorn on http://127.0.0.1:8000 started with `USE_FIXTURES=1` (free replay mode) via nohup
  from `builds/case-builder`, no shell ID. Kill: `netstat -ano | grep ":8000 " | grep LISTEN`, then
  `taskkill //PID <pid> //F`. In-memory case: the Mei Ling example with the fixture chat replayed, gate
  green, 4 of 6 blind spots answered. `data/case.json` on disk is selfcheck's output (chat empty), so a
  restart needs the example reset plus the three fixture chat messages posted to `/api/chat` again.
- Playwright MCP browser: not used this session (Python Playwright instead).
- Open worktrees / branches: none, on `main`.
- OpenRouter spend this session: none (fixtures only).

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder && python rules.py` — "rules ok".
- `USE_FIXTURES=1 python selfcheck.py` — "selfcheck ok: [...]".
- With the server up and the example loaded, run the scratch `uitest.py <outdir>`: every step prints "ok"
  with an empty list, and the lock test prints `[0, 0, True, 4]`.
- In the browser at 1440: rail shows steps 6 and 7 as Locked; step 5 Next disabled until all 6 answered.
  Open E1 from step 1: page 1 is the tenancy agreement, not a quote.

## Deferred / pending tasks + open questions
- Deck (`make-slides`), AI-disclosure slide, citations: not started. Deadline Sun 6 Sep 12:00 SGT.
- Plan changelog: add the layman UI pass and the cache-key fix.
- Cosmetic: favicon 404; stale `shot-*.png` in `notes/screens` could be moved to `archives/`.
- Open: commit of everything since `ee9befc`, repo push and Devpost submission need Jeremy's green light.
- Not done from Codex: real `<button>` elements for rail, rows, dots; loading state during the example reset
  on slow machines.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` — status built + reviewed.
  This session's work is outside the plan (small enough to do straight from the handoff list).

## Next steps
1. Ask Jeremy to say commit, then commit the uncommitted work as one checkpoint.
2. Deck: `make-slides` from `notes/demo-script.md`, the step screenshots and `BRIEF.md` judging criteria;
   include the AI-disclosure slide and citations.
3. Update the plan changelog. Then Devpost submission on Jeremy's green light.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-layman-ui.md, then get Jeremy's commit call and start the deck with make-slides from the demo script and step screenshots.
