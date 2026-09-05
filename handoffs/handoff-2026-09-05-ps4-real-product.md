# Session Handoff — Case Builder: chat intake for any SCT claim, made a real product, layman UI pass next

## Where it started
Jeremy read the built handoff and redirected: step 1 must gather the story in natural language (chat plus
file upload), not eight fixed tenancy questions; it must be general (any Small Claims matter, not only
tenancy); and the tool must be a fully working product he can use like a real client, not a demo. Session ran
Sat 5 Sep 2026 ~17:45 to ~19:10 SGT. Hard deadline Sun 6 Sep 12:00 SGT. Deck not started.

## Important discoveries and decisions
- Vision is already in: images and the video frame go to the model as pictures alongside OCR text. Nothing added.
- Reusing FARA's document pipeline rejected: ~10k lines tied to insurance fields, PII redaction, encrypted store.
  Case Builder's own extract.py does the same core job in one small file.
- Live chat works: three turns fill every field on a made-up services claim (painting contractor) in ~39 s.
  Model replies are slightly chirpy ("Your claim looks complete!"), acceptable but see the UI pass below.
- Live real-user run on the server (New case, own words, one uploaded quote image) passed: services claim,
  gate green, two facts ranked, exact line highlighted, story written. 38 s end to end.
- Facts read before the claim type is known use the general evidence keys; the app re-reads those files once the
  chat sets the type (costs one model call per file).
- Rank-1 row can show "E1, E1" when two facts from one file map to one key. Cosmetic, not fixed.
- Console error on load is only the missing favicon.

## Decisions locked + what shipped
All in `C:\Users\jemer\code\hackathon\builds\case-builder\`:
- Chat intake. `POST /api/chat` runs one model turn (`llm.intake_turn`), merges fields (`app.apply_fields`),
  recomputes. `POST /api/chat/clear` restarts the chat. Old `/api/intake` and the 8-question form are gone.
- Claim types: tenancy, goods, services, property_damage, other, unknown. `rules.ctype()` maps services and
  property_damage (and unknown) to a `general` content set added to `content/gaps.json`, `blindspots.json`,
  `nextsteps.json`, plus `KEY_ORDER["general"]` and `llm.EVIDENCE_KEYS["general"]`. `other` fails the gate
  category check with a stop; `unknown` and missing amount / date / in-Singapore give "Tell us..." fails.
- `content/questions.json` is now an eight-item `checklist` (story, claimant, respondent, category, agreed,
  amount, when, files); `app.checklist_state` ticks it. Shown on the right of step 1. JEREMY WANTS IT REMOVED.
- Real product: `POST /api/case/new` starts empty (default when no case.json); `POST /api/case/reset` loads the
  worked example (Mei Ling, six sample files). Front-end buttons "New case" and "Load the example".
- Live model by default: `USE_FIXTURES` defaults to 0 when a key exists (`llm.use_fixtures`). `USE_FIXTURES=1`
  replays the saved run. selfcheck still forces fixtures.
- Story and summary are rewritten only when the facts behind them change (`_text_key` in `app.recompute`), and
  are blank until there is evidence. Keeps chat turns to one model call.
- Video frame time follows the clip: 1:12, or the middle of a clip shorter than 2:24 (`extract.keyframe_seconds`),
  stored as `asset["frame_label"]` and used in captions and the model prompt.
- Example-only wording scrubbed from tenancy gaps, blind spots and next steps (no cl. 6, no E5 at 1:12, no sofa,
  "the landlord" instead of he/his).
- Fixtures: `content/fixtures.json` gained `chat` (three scripted bot turns with fields) and `chat_user` (the
  three Mei Ling messages). selfcheck replays them, asserts the gate passes, then leaves case.json with the
  example files read and the chat empty.
- Screenshots of all seven steps at 1440 wide: `C:\Users\jemer\code\hackathon\notes\screens\step-1-chat-intake.png`
  to `step-7-next-steps.png` (step 3 with the clause highlight open). Made by a Python Playwright script.
- Git: checkpoint commit `ee9befc` ("chat intake for any SCT claim, step screenshots, demo script v5") made at
  Jeremy's "save this example first". Everything after (real-product changes) is uncommitted.
- Docs updated: README (real use, live default, example button), `notes/demo-script.md` v5 (beat 10-22 is the
  chat, decisions list), plan changelog.

## Key files for next session
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-real-product.md` — this file.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — the whole UI; the layman pass edits this.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — routes, chat_turn, checklist_state, recompute.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — SYSTEM_INTAKE prompt (tone of the chat replies).
- `C:\Users\jemer\code\hackathon\builds\case-builder\content\*.json` — all user-facing wording outside index.html.
- `C:\Users\jemer\code\hackathon\notes\demo-script.md` — v5.
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` (changelog at the end).
- Scratch scripts (session temp, may be gone): `real_user.py` (Playwright real-user run), `shots.py` (step
  screenshots) in `C:\Users\jemer\AppData\Local\Temp\claude\c--Users-jemer-code-hackathon\f8aac02c-1a8b-465e-addc-f4c7f905c5f4\scratchpad\`.
- Memory files touched: none.

## Running state
- Background shell `bf4z98zjj`: uvicorn on http://127.0.0.1:8000 in LIVE mode (no USE_FIXTURES), started from
  `builds/case-builder`. Kill: `netstat -ano | grep ":8000 " | grep LISTEN`, then `taskkill //PID <pid> //F`.
  Its in-memory case is the Daniel Koh services test; `data/case.json` matches.
- Playwright MCP browser is open on http://127.0.0.1:8000/ (used earlier; the later runs used Python Playwright).
- Open worktrees / branches: none, on `main`.
- OpenRouter spend this session: roughly $0.30 more (two live chat runs, one live upload read, story/summary).

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder && python rules.py` — prints "rules ok".
- `python selfcheck.py` — prints "selfcheck ok: [...]"; replays the chat fixtures and checks the whole path.
- `python -m uvicorn app:app --port 8000` then http://127.0.0.1:8000, press New case, type a story, add a file:
  ticks fill, gate turns green, step 3 shows ranked rows with a highlight. `USE_FIXTURES=1` for the free replay.

## Deferred / pending tasks + open questions
- NEXT (Jeremy's instruction, interrupted before any work): layman UI pass.
  1. Remove the "What we need (8 of 8)" checklist panel on step 1 (keep the files panel).
  2. Audience is old uncles and aunties: no small text anywhere (the `.muted` 13-14 px captions, hints,
     footer), short plain sentences, simple words. Applies to the chat replies too: tighten `SYSTEM_INTAKE` in
     llm.py (short sentences, no "Your claim looks complete!"), and the fixture replies in fixtures.json.
  3. Every step after Evidence blind spots (timeline, next steps) must stay locked until all six blind spots
     are answered. Today only the 4-to-5 move is blocked in `go()`; the rail lets you jump to 6 or 7.
  4. Check layout and alignment on desktop and mobile with the browser (Playwright, viewport 390 wide and
     1440 wide); the layout is fixed-width flex today and will not fit a phone.
- Deck (`make-slides`), AI-disclosure slide, citations: not started.
- Devpost submission by Sun 12:00 SGT and repo push: need Jeremy's green light.
- Cosmetic: "E1, E1" duplicate source labels on one row; favicon 404.
- Commit of the real-product changes: waiting for Jeremy to say commit.

## Plan
- `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` — status built + reviewed; this
  session's two changes are logged in its changelog. The layman UI pass is not in the plan yet; small enough
  to do straight from the list above.

## Next steps
1. Layman UI pass (the four items above), test at 390 and 1440 wide with Playwright, rerun selfcheck.
2. Retake the seven step screenshots.
3. Commit when Jeremy says. Then the deck.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-real-product.md, then do the layman UI pass (drop the checklist panel, big plain text everywhere including chat replies, lock steps 6-7 behind the blind spots, test mobile and desktop with Playwright), then retake the step screenshots.
