---
name: notebooklm-use
model: sonnet
description: The access layer for NotebookLM. Use whenever work needs NotebookLM to read something (a YouTube video, a PDF, a URL, a repo file, a web-research query) or to produce a deliverable from it (an answer, report, quiz, flashcards, slide deck, infographic, mind map, data table, podcast audio, or video), and whenever a notebook needs finding or reusing in the library. Other skills call this one rather than driving the CLI themselves. Triggers include "have NotebookLM read this", "put this in NotebookLM", "ask NotebookLM about X", "make a deck/quiz/brief from these sources", "what notebooks do I have". For raw CLI flags and error codes, read the user-level `notebooklm` skill instead.
---

# NotebookLM: the access layer

One doorway to NotebookLM for every other skill and workflow. NotebookLM reads the
source material on Google's side, so its reading is not billed as tokens and does not
consume this session's context. That is the entire reason to route work here.

**Division of labour.** `~/.claude/skills/notebooklm/SKILL.md` is the full API reference
(every flag, output shape, exit code, troubleshooting step) - read it when a command
misbehaves or you need an option not named below. THIS skill is the calling contract:
what NotebookLM can be asked for, how to get it in a repeatable way, and what a calling
skill gets back. Do not copy the reference into here.

## 0. Preflight (every time, it is one call)

```
notebooklm auth check --test --json
```
`"token_fetch": false` = the saved token is stale. **Fix it yourself: run
`notebooklm login`** (Jeremy's standing instruction, 2026-08-05). It reopens the
persistent Chromium profile, which normally still holds his Google session, prints
"Already logged in", and rewrites `storage_state.json` in seconds. Expect a browser
window to flash open; that is normal.

Only if `login` actually lands on a Google sign-in page is Jeremy needed: tell him to
close any open NotebookLM browser window (it locks the profile) and sign in within the
5-minute watcher. Cookie import from his normal Chrome does not work on Windows.

## 1. The library: reuse before you create

```
notebooklm list                       # every notebook
notebooklm use <notebook_id>          # set the working notebook
notebooklm status                     # which one is current
notebooklm source list                # what is already indexed in it
```

**Check the library before creating anything.** Re-uploading a source that is already
indexed wastes several minutes and adds a duplicate. If a notebook for this material
exists, `use` it and go straight to step 3.

**Naming convention, so notebooks stay findable by any skill:**
`<Domain>: <subject> <qualifier>` - e.g. `Video: Chase AI notebooklm pipeline`,
`Udemy: section 04 prompting`, `SMU: IS111 recursion`, `Investment: NVDA 2026-08`,
`Research: MAS adviser rules`. Domain prefix first, always. A calling skill finds its
own notebooks by matching that prefix against `notebooklm list`.

## 2. Sources: what can go in

| Input | Command |
|---|---|
| Local file (pdf, md, docx, audio, video, image) | `notebooklm source add ./path/file.pdf` |
| Any web URL | `notebooklm source add "https://..."` |
| YouTube video | `notebooklm source add "https://youtu.be/..."` (transcript only, see limits) |
| Web research, NotebookLM does the searching | `notebooklm source add-research "question" --mode deep --no-wait` |

Then **wait for indexing before asking or generating** - an unindexed source is silently
absent from the answer:
```
notebooklm source list -n <notebook_id>          # Status column: ready / processing
notebooklm source wait <source_id> -n <notebook_id>   # 30s to 10 min; SOURCE_ID is required
notebooklm research wait --import-all            # for add-research; deep mode is 15-30+ min
```
**`source wait` takes a source ID, not nothing.** Bare `source wait` errors with
`Missing argument 'SOURCE_ID'`. A YouTube source is often `ready` by the time `source
add` returns, so check `source list` first and skip the wait.

## 3. Getting something back

Two different exits. Pick deliberately.

**A. Ask (cheap, fast, no artefact).** The default. Costs no generation quota and comes
back in seconds.
```
notebooklm ask "question"
notebooklm ask "question" --json          # includes source references
notebooklm ask "question" -s <src_id>     # restrict to one source
notebooklm ask --prompt-file q.txt        # long prompt
notebooklm ask "question" --save-as-note --note-title "T"
```

**B. Generate an artefact, then download it.** Minutes, and rate-limited.

| Deliverable | Generate | Key options | Download as |
|---|---|---|---|
| Report | `generate report` | `--format briefing-doc\|study-guide\|blog-post\|custom` | `.md` |
| Quiz | `generate quiz` | `--difficulty`, `--quantity` | `.json` `.md` `.html` |
| Flashcards | `generate flashcards` | `--difficulty`, `--quantity` | `.json` `.md` `.html` |
| Slide deck | `generate slide-deck` | `--format detailed\|presenter`, `--length` | `.pdf` `.pptx` |
| Infographic | `generate infographic` | `--orientation`, `--detail`, `--style` | `.png` |
| Mind map | `generate mind-map` | `--kind interactive\|note-backed` | `.json` |
| Data table | `generate data-table` | description required | `.csv` |
| Podcast audio | `generate audio` | `--format deep-dive\|brief\|critique\|debate`, `--length` | `.mp3` |
| Video | `generate video` | `--format explainer\|brief\|cinematic`, `--style` | `.mp4` |

```
notebooklm generate <type> "instructions" --retry 3
notebooklm artifact list                  # status
notebooklm artifact wait <artifact_id>
notebooklm download <type> ./out.ext [--format pptx|markdown]
```
`--retry N` handles rate limits with backoff on every type except `mind-map`. Slide
decks have no orientation flag; ask for `"9:16 portrait"` in the instructions text
instead.

**Slide-deck and infographic art: always ban micro-text (standing rule, 2026-08-06).**
Each slide is ONE image drawn by an image model, so it paints label-shaped scribbles
wherever small words belong: unreadable fake handwriting under zoom. Every
`generate slide-deck` / `generate infographic` instruction carries this block:

> No annotation text inside the artwork. Leader lines, dimension lines and ticks end
> in empty space; use numbered circles instead of words. Any word that does appear
> must be uppercase, at most two words, and large enough to read clearly. No
> text-like squiggles or fake handwriting anywhere. All real text lives in the
> slide title, subtitle and captions.

To clean a deck that already exists, revise per slide rather than regenerating (a
regeneration redraws all art and loses the approved design):
```
notebooklm generate revise-slide "<the block above>" --artifact <id> --slide N --wait
```
Each revision creates a NEW artifact, so re-read the newest id
(`artifact list --type slide-deck --json`, newest first) before the next slide. In a
loop over many slides, run `notebooklm login` at the top of each round: the token goes
stale after ~10 minutes of generation and the next `artifact list` returns an auth
error, not a list.

## 4. The standard sequence

Every workflow on top of this skill is the same five steps:

1. `auth check` (step 0).
2. Find or create the notebook (step 1), using the naming convention.
3. Add sources, then WAIT for indexing (step 2).
4. `ask` for answers, or `generate` + `artifact wait` + `download` for a file (step 3).
5. Land the output at a real path in the repo and commit it by explicit path. A file in
   the scratchpad has not shipped.

## 5. Contract for skills built on this one

A calling skill passes: **sources** (paths, URLs, or a research question), a **notebook
name** following the convention, and either **questions** or a **deliverable type +
output path**.

It gets back: NotebookLM's answers as text, or the downloaded file at that path, plus
the notebook ID so a later run can reuse it instead of re-uploading.

**Return answers, not source text.** `notebooklm source fulltext` exists, but pulling a
whole source back into context spends exactly the tokens this skill exists to save. Ask
a sharper question instead.

## 6. What it cannot do (know before routing work here)

- **YouTube and video ingestion is transcript-only.** Nothing on screen is understood:
  diagrams, code on screen, board positions, screen recordings. A video with no captions
  cannot be ingested at all. Visual content still needs local frame extraction.
- **No timestamps.** Answers cannot cite where in a video a claim was made.
- **Indexing latency**, 30s to 10 min per source, before anything can be asked.
- **Rate limits** on audio, video, quiz, flashcards, infographic, slide deck. Reports,
  mind maps, data tables and chat are the reliable ones. On failure: `artifact list`,
  wait 5-10 min, retry, then fall back to the web UI.
- **Unofficial API.** It can break on any Google change, so every workflow needs a
  fallback path that does not depend on it, and **nothing user-facing may be wired to
  it**, specifically never FARA the product, whose whole moat is cited, accountable
  facts.
- **Nothing it returns is verified.** Its citations point only at the sources you gave
  it. Check any figure before it reaches a lesson, a workbook, or a portfolio decision.

## 7. Long waits

Generation runs to 45 minutes. Do not block a turn watching it: kick it off with
`--no-wait` or `--json`, do other work, and come back to `artifact wait`. For anything
over ~10 minutes, hand the wait to a background agent (the subagent pattern in the
reference skill) rather than holding the session.

## 8. Standing rules

- **Pass the notebook ID on every command.** `create` does NOT set the working notebook,
  so a bare `source add` straight after it fails with "No notebook specified". Capture
  the ID from `create --json` (or `list --json`) and pass it every time: `-n <id>` on
  `source *`, `artifact *`, `research *`, `download *`, and `--notebook <id>` on `ask`
  and the rest. This also keeps parallel jobs from fighting over the single global
  current notebook.
- Partial IDs work at 6+ characters, but automation should use full UUIDs.
- Learning guardrail: for material Jeremy is actually studying, quizzes and flashcards
  are fine (they are practice). Do NOT hand him a generated study guide, summary, or
  mind map of it, the structure has to be his.
- Delete notebooks created purely as scratch (`notebooklm delete -n <id> --yes`). Keep
  the ones a workflow will want to reuse.
