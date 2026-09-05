# Session Handoff — SMU LIT Hackathon: brief filled, problem statement analysis, PS choice pending

## Where it started
Jeremy started the SMU LIT Legal-Tech Hackathon 2026 (24h, in person at SMU). Asked to read the
organiser PDFs in `documents/` and the Notion hub, fill BRIEF.md, then analyse the four challenge
statements and pick one. Team of 5, wants a build that is "complex enough but high quality" and
stands out. Choice of statement must be submitted by **5 Sep 1800 SGT** via Google Form.
Hard submission deadline **6 Sep 1200 SGT**. Session ended 5 Sep ~1300 SGT.

## Important discoveries and decisions
- Notion overrides the PDF: challenge choice deadline is 1800 today (PDF said 2100). Form:
  https://forms.gle/1TjvhBzk6K51UqiVA, use the sign-up email.
- Full challenge text: Notion > Challenge Statements
  (https://bottlenose-ninja-9c2.notion.site/Challenge-Statements-3d19970c91f280e6ba18d29789b74c5e).
  Summaries of all four are in BRIEF.md.
- Judging: technical feasibility 30, relevance 25, innovation 25, presentation 20. 4 min pitch +
  2 min Q&A. Team must explain own code and disclose AI tools used. Must cite libraries/APIs.
- Submission is via Devpost (https://smu-lit-hackathon-2026.devpost.com/): GitHub link, slides,
  product screenshots. One person per team.
- API credits: telegram @tauporky with team name, number, own name.
- PS3 has two halves (adoption/video, regulatory resilience). Organisers confirmed teams pick ONE
  half. So PS3-resilience is a legitimate single choice.
- Team's working Google Doc: https://docs.google.com/document/d/1kovv1UIMRmRdTAZJ4HTV0l0dvWOrNO7-Rqk28lyw1vs
  (ID `1kovv1UIMRmRdTAZJ4HTV0l0dvWOrNO7-Rqk28lyw1vs`). Holds their raw feature lists for PS1, PS2, PS4.
- GitHub repo for submission: https://github.com/jemeryy/LIT-hackathon (public, `main`, has one
  README commit unrelated to local history).

## Analysis given (so the next agent does not redo it)
Ranking for standing out: **PS3 resilience > PS4 evidence-first > PS2 > PS1**.

- **PS1 AITHENA (contracts):** over-specified, will be crowded. Ironclad/Evisort already do
  extraction + confidence + human review. Only angle: SME has no reviewer, so honesty by design
  (two independent extractors, calibration chart, refuse on stage, handoff brief as export).
  Jeremy judged this "not outstanding". Dropped.
- **PS4 MinLaw (SCT self-represented persons):** everyone builds a chatbot. Proposed mechanic:
  build the case from the EVIDENCE, not the story. Upload WhatsApp export/receipts/photos, tool
  builds exhibit-cited timeline, shows the gap between what user claims and what evidence proves,
  then argues the other side from the evidence gaps, and outputs a claim pack shaped to the CJTS
  form. Deterministic front door (forum, limit, time bar). Never predicts outcome, never
  generates evidence (Courts' Guide on GenAI). Grilled their doc: kill "likelihood of success"
  and "legal argument for your case" (both = legal advice); evidence-first not story-first;
  evidence strength by checklist not model opinion; closed-world citations (exhibits + fixed
  statute set only); add the out-of-scope refusal and the responsible-GenAI layer.
- **PS3 R&T resilience (recommended):** dependency map between firm documents (templates,
  checklists, playbooks, advisories) and the exact law sections they rely on. A rule change is
  the trigger; the tool traces which documents break, how, and drafts the fix for lawyer
  approval. Demo: change one section, watch seven documents light up. Emptiest room. Needs the
  two legal teammates to write ~30 short synthetic firm documents and pick one real past
  amendment with a known effect, by ~1400.
- Suggested 5-way split for PS3 (not yet written down anywhere): Dev1 corpus ingest + dependency
  extraction anchored to SSO section IDs; Dev2 graph store (SQLite fine) + diff + impact
  classifier; Dev3 redline generator + graph UI; Legal1 synthetic corpus + amendment; Legal2
  demo script + deck + verify every citation.

## Decisions locked + what shipped
- BRIEF.md fully filled: clock, rooms, judging weights, rules, submission, all four statements,
  suggested data sources — `C:\Users\jemer\code\hackathon\BRIEF.md`
- `documents/` gitignored (organiser PDFs are confidential per rules s.5; repo is public). Never
  committed. `.playwright-mcp/` already ignored — `C:\Users\jemer\code\hackathon\.gitignore`
- Git: remote `origin` = https://github.com/jemeryy/LIT-hackathon.git added; local branch
  renamed `master` → `main`. **Not pushed.** Uncommitted: `.gitignore`, `BRIEF.md`.
- Team: 5 people. Assumed 3 who code, 2 legal. Not confirmed.

## Key files for next session
- `C:\Users\jemer\code\hackathon\BRIEF.md` — source of truth, read first
- `C:\Users\jemer\code\hackathon\CLAUDE.md` — repo rules (demo script first, never push without green light)
- `C:\Users\jemer\code\hackathon\documents\SMU LIT Hackathon 2026 Participant's Guide.pdf` — schedule + rubric
- `C:\Users\jemer\code\hackathon\documents\SMU LIT Hackathon 2026 Rules.pdf` — T&Cs
- Plan file: none yet
- Memory files touched: none

## Running state
- Background processes: none
- Dev servers / ports: none
- Open worktrees / branches: `main` at `C:\Users\jemer\code\hackathon`, remote `origin` set, nothing pushed
- Playwright MCP browser was last on the Google Form page; harmless

## Verification — how to confirm things still work
- `git remote -v` — shows origin = jemeryy/LIT-hackathon
- `git branch` — `* main`
- `git status --short` — `.gitignore` and `BRIEF.md` modified, `documents/` not listed

## Deferred / pending tasks + open questions
- Open: **which problem statement.** Jeremy leaning PS3 resilience or PS4 evidence-first, not
  decided. Deadline 1800 today. Whoever resumes: ask which was submitted, do not re-argue.
- Open: team composition (how many code). Assumed 3 dev + 2 legal.
- Deferred: `notes/demo-script.md` (repo rule: write before building). Not started.
- Deferred: build plan via `grilling` then `plan-with-codex`. Not started.
- Deferred: first push needs `git pull origin main --allow-unrelated-histories` or a force,
  because remote has its own README commit. Needs Jeremy's explicit go.
- Deferred: commit of `.gitignore` + `BRIEF.md`.
- Deferred: verify SCT figures (claim limit, time bar) and the exact name/date of the Courts'
  GenAI guide if PS4 is chosen. Not to be quoted from memory.
- Deferred: API key from @tauporky not yet requested (as far as this session knows).

## Plan
No plan file. Intended sequence once the statement is chosen: `notes/demo-script.md` (90 s) →
`grilling` to lock scope → `plan-with-codex` with time budget per step → build in vertical
slices → `review-with-codex` → deck → Devpost by 6 Sep 1200.

## Next steps
1. Confirm which statement was submitted on the form.
2. Write `C:\Users\jemer\code\hackathon\notes\demo-script.md` for that statement.
3. Run `grilling` on the chosen concept with the team's doc as input, then `plan-with-codex`.
4. Scaffold `builds/<name>/`. Commit. Ask for push green light.

## Next step (for the next session after /clear)
Next step: read `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps-choice.md`, then confirm the submitted PS and write notes/demo-script.md.
