---
name: make-slides
model: sonnet
description: Create a slide deck (PPTX) from any sources via NotebookLM. Use when Jeremy asks to "make slides", "create a deck", "slides for lecture N.N", "turn this into a presentation", or a workflow (Udemy, uni, investment, research) needs a deck from scripts, PDFs, URLs, or notes. Sits on the notebooklm-use access layer; read that skill for the CLI mechanics.
---

# Make slides

Turn sources into an editable PPTX deck through NotebookLM. This skill decides WHAT to
ask for; `.claude/skills/notebooklm-use/SKILL.md` is HOW (auth, library, sources,
generate, download). Read it first and follow its standard sequence and standing rules.

## Contract

In: sources (file paths, URLs, or a research question), a scope (which part of the
sources the deck covers), and an output path. Out: a `.pptx` at that path, plus the
notebook ID for reuse.

## Two modes — reconstruct is ALWAYS the default

**NotebookLM output is never element-editable** (verified 2026-08-05: both its PPTX
and its PDF are one baked raster image per slide, no text layer). "Make slides"
always means the EDITABLE deck (Jeremy, 2026-08-06): never hand over a raw
NotebookLM deck and offer to reconstruct it afterwards — finish the reconstruct in
the same run and hand over that file.

- **Reconstruct mode (the default, always)** — keep NotebookLM's exact look but
  make the text editable. Download the deck as PDF, then:
  ```
  python tools/slides_reconstruct.py deck.pdf out.pptx --font "DM Sans" \
      [--font-map map.json] [--classify-cache out.labels.json]
  ```
  Pick `--font` to match what NotebookLM actually drew: "Roboto" for the
  architectural style, "Roboto Mono" for the technical/blueprint style, "DM Sans"
  for the default look, "Roboto Condensed" for the dark corporate/pitch style
  (condensed bold caps headings; installed per-user 2026-08-23). Never guess:
  crop a heading from page 1 and compare letter WIDTH before choosing; a wrong
  width (DM Sans on a condensed deck) breaks every line. A deck that MIXES faces takes a comma-separated list,
  default first (`--font "Roboto Mono,Roboto"`): each paragraph is matched to the
  one it was really set in. Install a missing family per-user (copy the TTF to
  `%LOCALAPPDATA%\Microsoft\Windows\Fonts` + an `HKCU:\...\CurrentVersion\Fonts`
  entry) rather than settling for a poor match — including the BOLD face, because
  PowerPoint will not synthesise one and every bold line silently renders regular.
  `--classify-cache` names the JSON that records which lines are welded into the
  artwork; keep it beside the pptx so a rebuild does not re-pay for one vision call
  per page. That file is also the manual override if a page classifies wrongly.
- **Storyboard mode** — ONLY when Jeremy explicitly asks for a quick draft to look
  at. Use NotebookLM `generate slide-deck` alone (steps below). Slides can be
  reordered/deleted, not edited.
  It OCRs each page (Windows built-in OCR), turns every clean text line into a native
  text box with colour and size sampled from the pixels, lifts large non-text regions
  out as individual picture elements, and patches both out of the background image.
  Result: identical-looking slides where text is editable and icons are movable.
  Known ceilings: the font is the nearest installed match, not Google's original —
  and a substitute of the wrong WIDTH costs height. Type is sized off the box height
  and the leftover width becomes letter-spacing, but tightening past ~0.05em collides
  the glyphs, so a mono ~25% wider than the deck's (every installed one, against
  fara-overview's) still sets ~11% short in HEIGHT, width exact. Settled 2026-08-06:
  Inconsolata (0.5em advance, the only close family) was installed and run end to end
  and only moved the harness 60.1 -> 59.3 while regressing two pages, and its 'a'
  carries a tail fara-overview's does not. Roboto Mono stays; do not reopen this
  without a font that matches the LETTERFORMS too.
  Bold is read as the line's ink over the same line drawn regular; on a
  deck whose bold sits close to its regular a few headings will stay unbolded (slide 7
  of fara-overview) — that is the threshold refusing to bold body text, not a bug.
  DM Sans (installed per-user 2026-08-05) is the closest to NotebookLM's sans;
  `--font-map` maps line regexes to other fonts, e.g. handwritten lines to Comic
  Sans MS. NotebookLM redraws all art on every generation, so reconstruct the deck
  Jeremy approved; regenerating loses that exact design.
  stylised text OCR cannot read (struck-through, warped) stays baked in the
  background, which still looks right; tables are not special-cased — their text
  becomes positioned text boxes and grid lines stay in the background (upgrade to
  native table objects when a real deck needs added rows).
  **The run must finish clean.** Every vision pass (artwork classifier, footer
  reader, the body-text proofreader added 2026-08-23, object boxes) needs
  `ANTHROPIC_API_KEY`; the tool reads this repo's `.env` and falls back to it
  from a sibling repo's copy. If any pass was skipped it prints a WARNING and
  exits 2: that deck is OCR-only (garbled `~ % |`, ghost lines, wrong bake) and
  is never handed over. Google renamed the watermark "Gemini Notebook"
  (Aug 2026); the eraser regex matches both names now.
  **Verify visually**, always, with the comparison harness:
  ```
  python tools/slides_compare.py deck.pdf out.pptx <outdir> [--pages 1,4] [--top 3]
  ```
  It exports the pptx through PowerPoint, renders both sides with pymupdf and prints
  the worst-differing regions per page (an `ink` score; 4-9 is the current floor for
  a good rebuild, 20+ means something moved). Crops land in `<outdir>`: `pNN_rK.png`
  is original | rebuilt for one region, `pNN_page.png` is the whole page stacked.
  Fix what it finds in `tools/slides_reconstruct.py`, never by hand-editing the pptx.
  Before believing a region that covers ARTWORK, check the picture inside the pptx
  (`ppt/media/*.png`) against the source: PowerPoint JPEGs the page pictures on PDF
  export, which wipes 1px drawn texture the deck itself still has.
- **Native rebuild mode** — when the layout itself should be Claude's (or the deck
  must be fully vector, no baked background), build from the content spec instead:
  per-slide content from the source's own visual spec (for Udemy, the visuals-pass
  file `slides/section-NN-visuals.md`, written after the script is signed off; the
  script file itself carries no visual direction) or a NotebookLM outline, then a
  python-pptx build script creating each element.
  Worked template: `projects/udemy-course/slides-trial/build_lecture_1_1.py`.

## Steps

1. **Preflight + notebook** per notebooklm-use (auth check; reuse a notebook matching
   the naming convention before creating; pass `-n <id>` on every command).
2. **Add sources and wait for indexing.** One notebook per subject, not per deck: e.g.
   all of a Udemy section's scripts in one `Udemy: section NN scripts` notebook, decks
   generated per lecture from it.
3. **Generate with a scoped instruction.** The instruction text is where the quality
   lives:
   - Scope: name exactly what the deck covers ("ONLY Lecture 1.1", "chapters 2-3").
   - Slide count / length target if known.
   - Visual direction: if a visual spec exists alongside the source (for Udemy,
     `slides/section-NN-visuals.md`), tell it to follow those per-slide
     descriptions.
   - Art style: NotebookLM's default is flat icons, but a detailed style block in
     the instruction overrides it convincingly (verified 2026-08-05, architectural
     portfolio look). Spec five things: exact hex palette, imagery vocabulary
     (e.g. exploded axonometrics, iteration grids, hatched site plans), stroke
     and layering rules, layout/typography rules, and mood plus an explicit ban
     list ("no rounded cartoon icons, no drop shadows").
   - Text inside the art: paste the micro-text ban block from notebooklm-use
     (standing rule) into every instruction, and use `revise-slide` to clean a
     deck that already has scribbles.
   - Orientation: no flag exists; ask in the text ("16:9 landscape").
   ```
   notebooklm generate slide-deck "<instruction>" -n <id> --format detailed --retry 3
   notebooklm artifact wait <artifact_id> -n <id>
   notebooklm download slide-deck <out>.pptx -n <id> --format pptx
   ```
4. **Land and report.** Output goes to a real repo path (Udemy:
   `projects/udemy-course/slides-trial/` until the slides phase gets its own folder),
   committed by explicit path. Report the path, slide count, and notebook ID in one line.

## Rules

- Slide decks are rate-limited: `--retry 3`, and on repeated failure wait 5-10 min,
  then fall back to the NotebookLM web UI (same notebook, manual generate + download).
- Generation runs minutes; for anything over ~10 min hand the wait to a background
  agent, don't hold the session.
- Content in the deck is unverified NotebookLM output. Any figure that matters gets
  checked against the source before Jeremy presents it.
- Learning guardrail: decks ABOUT material Jeremy is studying are his to structure;
  this skill only makes decks he presents or teaches from (Udemy, briefings), not
  study summaries for him.
