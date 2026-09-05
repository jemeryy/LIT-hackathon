# Session Handoff — PS4 chosen, research done, demo script and wireframe v6

## Where it started
Jeremy confirmed the team chose PS4 (MinLaw, self-represented persons at the Small Claims
Tribunals) and submitted the Google Form. He described a 7-stage pipeline (intake, structured
facts, evidence matrix, timeline, eligibility, statute search, explanation + devil's advocate,
next steps) and asked for research on how each part works, a demo script, then a wireframe.
Team feedback arrived mid-session and reshaped the flow. Session ran 5 Sep ~1300 to ~1700 SGT.

## Important discoveries and decisions
- Verified SCT figures (State Courts "A Guide to Small Claims" + SSO): limit $20,000, $30,000 with
  consent; 2-year time bar; fees $10 / $20 / 1% for individuals; serve within 7 working days;
  no lawyers before Registrar or Magistrate; leave to appeal 14 days, law or jurisdiction only.
- Courts' GenAI guide: Registrar's Circular No. 1 of 2024, 23 Sep 2024, in force 1 Oct 2024,
  covers SCT. User is responsible for accuracy; verify statutes on SSO and cases on eLitigation,
  never via another AI; no pre-emptive declaration unless asked.
- The Judiciary already runs a Harvey-built case summariser for SCT (self-represented users from
  Nov 2025). It summarises filed documents and gives no orientation. Our slot is before filing.
- SSO has no API. `https://sso.agc.gov.sg/Act/<CODE>?ViewType=Pdf` with a browser user agent works,
  6 s between requests. Ten statutes confirmed downloadable (list in research file).
- Claude citations feature is not needed and may not pass through OpenRouter credits. Plan is
  own text extraction + quote matching (fara locators) for source highlighting.
- CJTS filing guide (`C:\Users\jemer\code\hackathon\documents\cjts_guide_to_filing_sct.pdf`,
  text extracted to `research/raw/cjts_guide_text.txt`): pre-filing assessment gives an ID valid
  7 days; claim form has 6 parts; brief summary max 500 characters; uploads PDF only, 5MB each,
  with page numbers; money order / work order; Submission for Hearing form = events in date order
  + witnesses; Defects Schedule form for renovation and residential tenancy; counterclaim at least
  3 days before Consultation; e-Negotiation 5 rounds. Fees are not in this guide.
- Team feedback (legal teammates): no likelihood score (legal advice), no counterarguments,
  no legal argument, focus on tenancy and sales, rank evidence, spreadsheet export of evidence,
  suggest missing evidence by category, prompt for one-sidedness. Then Jeremy: add an
  "evidence blind spots" step after gather (what the other side may hold, what user missed),
  remove the "check your account" step, all file formats in the source viewer, Next on blind
  spots locked until all questions answered.
- Statistics (9,113 SCT claims 2022, ~160 renovation disputes/year) are second-hand only. Not slide-safe.
- No verified renovation or deposit SCT appeal case found. Cases are no longer needed by the
  current design (past-cases cards were dropped with the strength score).

## Decisions locked + what shipped
- PS4 recorded in `C:\Users\jemer\code\hackathon\BRIEF.md` (team line + checklist).
- Demo scenario: Mei Ling, $2,600 tenancy deposit withheld by landlord Mr Tan. Evidence: tenancy
  agreement PDF, 6 WhatsApp screenshots, email screenshot, deposit transfer image, move-out video,
  move-in photos. Sale of goods is the second supported claim type.
- Final flow (7 screens): 1 Tell us what happened, 2 Can the SCT hear it (4 deterministic checks
  with statute links, mirrors CJTS pre-filing), 3 Your evidence ranked (rank + strength + source
  preview for any format, export evidence sheet xlsx), 4 What else to gather (5 categories, You
  have / Missing bullets, Upload per card), 5 Evidence blind spots (6 yes/no/not sure questions
  covering what the other side may hold and what user missed; Next locked until all answered;
  counterclaim note), 6 Timeline (past from files, future SCT steps, time-bar date; maps to the
  Submission for Hearing form), 7 Next steps in CJTS order + evidence sheet + claim pack.
- Claim pack defined: everything the 6-part CJTS form asks for, ready to paste and upload: particulars,
  500-char summary, each file converted to PDF under 5MB with description and page ref, money order
  amount, events list. Not a filing (no CJTS API; Singpass).
- No legal advice anywhere: no score, no arguments for either side, no law panel. Statute links
  live on the gate; court guide links on next steps.
- Demo script v4: `C:\Users\jemer\code\hackathon\notes\demo-script.md`.
- Research synthesis: `C:\Users\jemer\code\hackathon\research\ps4-how-each-part-works.md`
  (sections 2d "case strength" and 4 "explanation / other side" are now superseded by team
  feedback; the CJTS facts section at the bottom is current). Raw notes in
  `C:\Users\jemer\code\hackathon\research\raw\` (sct-process-and-rules, legal-data-sources,
  tech-approach, fara-reuse, cjts_guide_text).
- Wireframe v6 generator: `C:\Users\jemer\code\hackathon\notes\wireframe\gen.py` writes seven
  `*.dc.html` artboards + `canvas.json`. `build_pdf.py` renders
  `C:\Users\jemer\code\hackathon\notes\wireframe\sct-case-builder-wireframe.pdf` via Playwright.
  Live canvas: https://claude.ai/code/artifact/35989e83-ab83-4e76-8047-49800610bfc3
  (Claude Design preview; republish by re-seeding from gen.py output, same file path in scratchpad
  `sct-case-builder-wireframe.html`, contract 0.1.31).
- Codex was used once for a UI pass on gen.py (session 01a07058-249c-7bf2-96c7-4d968bfe436b).
- Commit + push to origin main done at end of session (see Running state for result).

## Key files for next session
- `C:\Users\jemer\code\hackathon\notes\demo-script.md` — the build scope. Read first.
- `C:\Users\jemer\code\hackathon\research\ps4-how-each-part-works.md` — how each part is built,
  what to copy from fara, CJTS facts. Ignore the strength score and "other side" sections.
- `C:\Users\jemer\code\hackathon\notes\wireframe\gen.py` — the agreed UI, screen by screen.
- `C:\Users\jemer\code\hackathon\research\raw\fara-reuse.md` — exact fara file paths and functions to copy.
- `C:\Users\jemer\code\hackathon\BRIEF.md` — clock, rules, judging.
- Plan file: none yet.
- Memory files touched: none.

## Running state
- Background processes: none (Codex task task-mto1149f-r6je4g finished).
- Dev servers / ports: none.
- Open worktrees / branches: `main` at `C:\Users\jemer\code\hackathon`, remote origin =
  https://github.com/jemeryy/LIT-hackathon.git.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\notes\wireframe; python gen.py` — prints `wrote 7 artboards`.
- `python build_pdf.py` in the same folder — writes the PDF (~340 KB), needs Playwright Chromium.
- `git status --short` — clean after the push; `git log origin/main --oneline -1` matches local.

## Deferred / pending tasks + open questions
- Deferred: build plan. Repo rule says `grilling` then `plan-with-codex` before building. Not started.
- Deferred: `builds/<name>/` scaffold and sample evidence pack (tenancy agreement PDF, WhatsApp
  screenshots, email screenshot, transfer image, short video, photos). Not started.
- Deferred: API key from organisers (@tauporky on Telegram). Unknown whether requested. If credits
  are OpenRouter, confirm model IDs there.
- Deferred: statute corpus fetch (10 Acts via SSO PDF link) and the 2-year time-bar subsection in
  SCTA 1984 s 5 still to be quoted verbatim.
- Deferred: app name. Wireframe says "[App name]".
- Open: team split (who codes what). Assumed 3 dev + 2 legal, never confirmed.
- Open: whether the pitch should show the sale-of-goods path too, or tenancy only.

## Plan
No plan file. Intended sequence: grilling on the wireframe scope -> plan-with-codex with time
budgets -> scaffold builds/ -> vertical slices in demo-script order (intake + parse, gate, evidence
rank + preview, gather, blind spots, timeline, next steps + exports) -> review-with-codex -> deck ->
Devpost by 6 Sep 1200 SGT.

## Next steps
1. Read the demo script and gen.py, then run `grilling` to lock the build scope and the team split.
2. `plan-with-codex` with a time budget per slice. Hard deadline 6 Sep 1200 SGT.
3. Scaffold `builds/<name>/`, build the sample pack, then slices in demo order.
4. Ask for the API key if not yet requested.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-research-wireframe.md, then grill the build scope from notes/demo-script.md and gen.py, and run plan-with-codex.
