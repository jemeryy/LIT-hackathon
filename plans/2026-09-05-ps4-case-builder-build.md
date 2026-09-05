---
status: built and reviewed
plan: PS4 Case Builder — hackathon build
owner: Jeremy
created: 2026-09-05 16:02 SGT
---

# PS4 Case Builder — build plan

## Goal + Why now
Build a working demo that takes a self-represented person's own evidence and turns it into a
Small Claims Tribunals case pack: guided intake, a jurisdiction gate, ranked evidence with
click-to-highlight on the real source, gap and blind-spot prompts, a timeline, and a claim pack
export. It is now Sat 5 Sep 2026 16:02 SGT. Hard deadline Sun 6 Sep 12:00 SGT; rooms close Sat
21:00. The scope is already locked by the grill (`notes/grill-2026-09-05-build-scope.md`); this
plan turns it into time-boxed, parallel slices so the demo in `notes/demo-script.md` runs end to
end by the freeze.

Definition of done: `python selfcheck.py` passes on the sample pack (gate passes, six exhibits
ranked, xlsx + claim-pack zip written, written request drafted), and a person can click through
all seven screens on the sample pack in under 90 seconds with the PDF highlight (E1 clause 4,
page 2) visibly working, verified by a screenshot.

## Constraints (binding)
- Time is the only hard limit. Build window ~10 h: Sat 16:00-21:00 (SMU, 5 h), Sat 22:00-00:30
  (remote, 2.5 h), Sun 08:00-10:30 (2.5 h). Feature freeze Sun 10:30, deck 11:00, submit 11:30.
- Ship the demo. Working and demoable beats complete. Build only what the demo script touches.
- Ponytail: stdlib and already-installed packages only. Installed: `anthropic` 0.103, `fastapi`,
  `uvicorn`, `pdfplumber`, `PyMuPDF`, `Pillow`, `pytesseract` (tesseract.exe on PATH), `openpyxl`,
  `reportlab`, `python-docx`, `rank-bm25` (do NOT use), `httpx`; `ffmpeg` on PATH; Python 3.12.
  No new dependencies unless unavoidable. Fewest files. No auth, no DB, no deploy, no test suite
  beyond `selfcheck.py`.
- Model calls go through the `anthropic` SDK only: `client.messages.create` with a `tools` list and
  `tool_choice`, then `json.loads` on the tool input. Credits are OpenRouter (key in `.env` as
  `OPENROUTER_API_KEY`, $15 cap, checked 5 Sep 16:25 SGT). OpenRouter accepts the Anthropic
  Messages format at `https://openrouter.ai/api/v1/messages`, so `anthropic.Anthropic(api_key=
  OPENROUTER_API_KEY, base_url=ANTHROPIC_BASE_URL)` works unchanged. Tested: tool call plus a base64
  image on `anthropic/claude-sonnet-5` returned a correct tool_use. `.env` now holds
  `ANTHROPIC_BASE_URL=https://openrouter.ai/api` and `MODEL=anthropic/claude-sonnet-5`. Sonnet 5
  ($2 in / $10 out per 1M) for every call: a full sample-pack run is about $0.10, so the cap
  covers ~100 real runs. Develop on fixtures; real calls only for demo dry runs and the demo.
  No structured outputs, no citations, no prefill. Vision
  input is a base64 image content block. `llm.py` returns fixture JSON when `USE_FIXTURES=1` so every
  lane keeps moving.
- Secrets only in `.env` (already gitignored). Never push/deploy/submit without Jeremy's green light.

## Approach

### Shape
FastAPI backend + one static `index.html` (vanilla JS, no build step), run on a laptop. Folder
`builds/case-builder/`. One `case.json` per case under `data/`. Single case, no login. This copies
the fara pattern (known) and gives the two things the wireframe needs: file upload and a
click-to-highlight source viewer.

### The split that makes parallel work possible
Model does judgment-free reading only: per-file fact extraction and per-file metadata, plus three
short text generations. Everything scored or decided is a rule in code. So:

- **`llm.py`** (lane A, tiny): `extract_facts(exhibit) -> facts[] + meta`, `write_text(kind, case)
  -> str` (story, 500-char summary, written request). `USE_FIXTURES=1` -> return fixture JSON keyed
  by filename from `fixtures.json`. Real calls go to OpenRouter through the `anthropic` SDK (see
  Constraints).
- **`extract.py`** (lane A): parse each upload to text + word boxes. PDF via pdfplumber (copy
  fara `_extract_pdf`, keep `_PDF_WORD_SPACING`); image via pytesseract `image_to_data` for word
  boxes + vision (through `llm.py`) for meaning; video via ffmpeg one cached keyframe at a fixed
  timestamp (72 s for E5), the frame treated as an image, locator = timestamp. WhatsApp `.txt`
  parsing is a dropped stretch (E2 is screenshots, so no `.txt` viewer is needed). Quote-to-location
  uses the constrained matcher below, NOT fara's bag-of-words matcher.
- **`rules.py`** (lane A): gate (4 checks), strength (strong/medium/weak table + `needs_check`
  flag), rank (strength then category weight then evidence-key), gaps (fill from content + exhibit
  categories), blind-spots state, timeline (dated facts + today + fixed future steps + time-bar +
  computed refund-due), next steps, fee. See the frozen strength+rank rules below.
- **`viewer.py`** (lane A): render one page/image/frame to PNG (PyMuPDF for PDF, Pillow for image,
  cached ffmpeg frame for video) and return the stored normalized boxes unchanged. One code path
  for every format. No pdf.js.
- **`exports.py`** (lane A): evidence sheet xlsx (openpyxl), claim-pack zip (`claim_form.txt`, one
  PDF per asset measured against 5 MB, `events.txt`), written request `.txt`.
- **`app.py`** (lane A): FastAPI routes; orchestrates parse -> extract -> rules -> case.json.
- **`index.html`** (lane B): the seven screens copied from `notes/wireframe/gen.py`, the shell
  (left rail, footer), and the viewer overlay (`<img>` + percentage-positioned highlight rects).
- **`content/*.json`** (lane C): `statutes.json` (gate section quotes), `gaps.json`,
  `blindspots.json`, `nextsteps.json`, `fixtures.json` (extraction fixtures so ranks match the
  wireframe), all per claim type (tenancy + goods).

### Coordinates: one canonical space (locks the viewer maths)
Every locator is stored and sent as **normalized 0-1 top-left coordinates** for every format
(fara `doc_ocr.ocr_page` already returns boxes this way; confirmed). PDF: divide pdfplumber point
coords by the extracted page width/height. Image: normalize against the same EXIF-transposed image
used for both OCR and rendering. Video: normalize against the extracted frame. The front end draws
an ordinary `display:block; width:100%; height:auto` `<img>` inside a `position:relative` wrapper
and places each rectangle with percentages. No zoom/DPI/resize maths crosses the wire. Rotated or
cropped PDFs outside the synthetic sample are out of scope (the sample is unrotated reportlab).

### Quote-to-location matching (do NOT copy fara's matcher unchanged)
fara `_locator_for_match` is bag-of-words: it unions every page word whose text appears anywhere in
the quote, which can span the whole page. Instead implement a constrained matcher in `extract.py`:
normalize quote and words (NFKC, lowercase, strip punctuation, keep the original box per word);
find an ordered, consecutive token window that matches the quote tokens; reject a match under a
fixed floor (>= 4 consecutive tokens); split the matched boxes by text line and return one
normalized rectangle per line (the `boxes` array). For the controlled E1 fixture use a short unique
clause-4 phrase, not the whole multi-line clause.

### Why highlight works even on fixtures
The locator is computed by matching the model's exact `quote` back into our own pdfplumber/tesseract
text, never from the model. So as long as the sample PDF contains the clause-4 phrase and the
fixture quote is that same phrase, the highlight is real without a key. Guard: `make_pack.py` and
`fixtures.json` share one clause-4 constant, and the E1 token-match is tested the moment E1 is
generated (Step 2).

### The JSON contract (STEP 1 — frozen; both lanes build against a checked-in real case.json)
Step 1 checks a complete, valid `data/case.json` for the full sample pack (6 exhibits, 6 evidence
rows, gate, gaps, blind spots, timeline, next steps, all locators) into the scaffold. That file IS
the integration boundary: the front end reads it immediately; the backend's job is to make the
pipeline reproduce it. The shape below is the contract (a real filled example lives in the file, no
placeholders).

`data/case.json`:
```json
{
  "case_id": "mei-ling",
  "claim_type": "tenancy",
  "app_name": "Case Builder",
  "intake": {
    "questions": [{"id": "q1", "prompt": "...", "why": "...", "answer": "..."}],
    "parties": {
      "claimant": {"name": "Mei Ling", "address": "...", "id_type": "NRIC"},
      "respondent": {"name": "Mr Tan", "address": "...", "in_singapore": true, "is_company": false}
    },
    "amount": 2600,
    "consent_30k": false,
    "cause_of_action_date": "2026-08-15",
    "premises": {"residential": true, "lease_months": 12, "refund_days": 14}
  },
  "story": "plain-words paragraph from llm.write_text",
  "summary": "<=500 char summary from llm.write_text",
  "exhibits": [
    {
      "id": "E2",
      "kind": "image_set",
      "status": "ready",
      "title": "WhatsApp screenshots",
      "assets": [
        {"id": "E2-4", "filename": "WhatsApp_04.png", "kind": "image", "size_bytes": 82000,
         "viewer_url": "/api/viewer?asset_id=E2-4"}
      ]
    },
    {
      "id": "E1",
      "kind": "pdf",
      "status": "ready",
      "title": "Tenancy_Agreement_2025.pdf",
      "assets": [{"id": "E1", "filename": "Tenancy_Agreement_2025.pdf", "kind": "pdf", "pages": 6,
                  "size_bytes": 240000, "viewer_url": "/api/viewer?asset_id=E1&page_index=0"}],
      "meta": {"author": "both", "signed": true, "dated": true, "has_amount": true, "from_picture": false},
      "facts": [
        {"evidence_key": "deposit_terms",
         "fact": "Deposit $2,600, refund within 14 days of moving out, less damage",
         "date": "2025-08-03", "party": "both", "amount": 2600, "category": "agreement",
         "quote": "refund the deposit within 14 days",
         "locator": {"asset_id": "E1", "page_index": 1,
                     "boxes": [[0.14, 0.31, 0.72, 0.34]], "coord_space": "normalized"}}
      ]
    }
  ],
  "evidence": [
    {"id": "deposit_terms", "rank": 1, "evidence_key": "deposit_terms",
     "what": "Deposit $2,600, refund within 14 days of moving out, less damage",
     "category": "agreement", "strength": "strong", "needs_check": false,
     "reason": "Signed by both of you, has amount and dates",
     "sources": [{"exhibit_id": "E1", "asset_id": "E1", "label": "cl. 4, p.2",
                  "viewer_url": "/api/viewer?evidence_id=deposit_terms&source_index=0",
                  "locator": {"asset_id": "E1", "page_index": 1,
                              "boxes": [[0.14, 0.31, 0.72, 0.34]], "coord_space": "normalized"}}]}
  ],
  "gate": {"pass": true, "checks": [
    {"text": "Your claim fits a CJTS category: residential lease up to 2 years, refund of deposit.",
     "pass": true, "section_id": "scta_s5_schedule"}]},
  "statutes": {"scta_s5_schedule": {
    "title": "Small Claims Tribunals Act 1984 s 5 + Schedule", "quote": "verbatim...",
    "source_url": "https://sso.agc.gov.sg/Act/SCTA1984", "retrieved_date": "2026-09-05"}},
  "gaps": [{"category": "Communication", "have": ["WhatsApp screenshots (E2)"], "missing": ["..."]}],
  "blindspots": {"total": 6, "answered": 4,
    "questions": [{"id": "b1", "q": "...", "hint": "...", "answer": "unsure"}]},
  "timeline": [{"id": "refund_due", "label": "Refund due (E1 cl.4)", "date": "2026-08-14",
    "future": false, "marker": false, "computed": true,
    "detail": "14 days after move-out under clause 4.",
    "sources": [{"exhibit_id": "E1", "asset_id": "E1", "label": "cl. 4",
                 "viewer_url": "/api/viewer?asset_id=E1&page_index=1"}]}],
  "next_steps": [{"n": 1, "title": "Send a written request for the deposit",
    "note": "...", "action": "written_request",
    "source_label": "Guide s.12", "source_url": "https://www.judiciary.gov.sg/..."}],
  "fee": {"amount": 10, "basis": "up to $5,000"}
}
```
`exhibits` = the files, each with one or more `assets` (a grouped exhibit like E2 or E6 has many).
`evidence` = the ranked rows, each with a stable `id`; a row may cite several assets and an asset
may back several rows, so `rank` lives on the row. Every source names both `exhibit_id` and
`asset_id`.

**Fixed enums (frozen so both lanes agree):**
- `category`: `agreement`, `payment`, `other_side_words`, `condition`, `dispute`.
- tenancy `evidence_key`: `deposit_terms`, `deposit_paid`, `handover_acceptance`,
  `moveout_condition`, `damage_allegation`, `movein_condition`.
- `strength`: `strong`, `medium`, `weak`. `blindspot answer`: `yes`, `no`, `unsure`.
- exhibit `status`: `ready`, `reading`, `waiting`, `error`. `exhibit kind`: `pdf`, `image_set`,
  `video`, `chat`.

**API routes** (all return the whole updated `case.json` unless noted; errors return `{error, code}`):
- `POST /api/case/reset` -> build case from the sample pack, return case.json. (Run before the demo,
  not during it: OCR + frame extraction is slow. The stage path loads a precomputed case.json.)
- `GET  /api/case` -> current case.json.
- `POST /api/intake` body `{answers: {q1: value, ...}}` -> save, recompute gate, return case.json.
- `POST /api/upload` (multipart; fields `exhibit_id`, `asset_id`, plus the file) -> parse + extract +
  re-rank, return case.json. Bad/oversized/unsupported file -> case.json unchanged + `{error, code}`;
  never breaks navigation. (python-multipart is installed; UploadFile works.)
- `POST /api/blindspot` body `{id, answer}` (answer in yes/no/unsure) -> save, return `blindspots`.
- `GET  /api/viewer?evidence_id=deposit_terms&source_index=0` -> viewer response (below). Addresses
  the clicked evidence source by evidence id + source index, never by row number. Also accepts the
  generic form `GET /api/viewer?asset_id=E1&page_index=1` so any source that names an asset (a
  timeline event, the intake file sidebar, a gate/statute link) can open the same viewer; when no
  locator applies it returns an empty `boxes`. Every source object in `case.json` (evidence,
  timeline, intake) carries an opaque `viewer_url` string the front end opens verbatim.
- `GET  /api/render?asset_id=E1&page_index=1` -> PNG bytes (opaque `<img>` src; the front end uses
  the `image_url` string verbatim and never builds render params itself).
- `GET  /api/statute?section_id=scta_s5_schedule` -> `{title, quote, source_url, retrieved_date}` for
  the gate text panel (same viewer surface).
- `GET  /api/export/xlsx` | `/api/export/claimpack` -> file download.
- `GET  /api/written-request` -> `{text}` for the modal.

Viewer response shape (`GET /api/viewer`):
```json
{"image_url": "/api/render?asset_id=E1&page_index=1",
 "boxes": [[0.14, 0.31, 0.72, 0.34]],
 "coord_space": "normalized",
 "caption": "Text found: \"refund the deposit within 14 days\", p.2. Check it against the page."}
```
`boxes` are normalized `[left, top, right, bottom]`, one per matched line. The front end draws each
as a percentage-positioned rectangle over the image. Video sources return the cached keyframe as
`image_url` with an empty or single whole-frame box.

### Strength + rank rules (frozen; reproduce wireframe ranks 1-6 exactly)
Strength (evidential, separate from `needs_check`):
- **strong**: signed by both, or a third-party record (bank, courier), or the other side's own
  document, AND carries a date and an amount.
- **medium**: a dated statement by the other side, a dated contemporaneous message between the
  parties, or dated direct condition media (photo/video).
- **weak**: undated user-only material, vague material, or material that does not show the fact.
- `needs_check: true` is set whenever a number or text was read off a picture (vision/OCR). It is a
  warning shown next to the row, NOT a strength cap. (This refines grill decision 7, which capped
  picture-read evidence at weak; the wireframe needs the bank screenshot Strong.)

Rank = sort by strength (`strong` > `medium` > `weak`), then category weight
(`agreement` 0 > `payment` 1 > `other_side_words` 2 > `condition` 3 > `dispute` 4), then a fixed
evidence-key order as the tie-break. This yields the six wireframe rows:

| rank | evidence_key | category | strength | needs_check | wireframe row |
|---|---|---|---|---|---|
| 1 | deposit_terms | agreement | strong | no | E1 cl.4 p.2 |
| 2 | deposit_paid | payment | strong | yes | E4 transfer |
| 3 | handover_acceptance | other_side_words | medium | yes | E2 shot 4 "ok, all good" |
| 4 | moveout_condition | condition | medium | no | E5 video 1:12 |
| 5 | damage_allegation | dispute | medium | yes | E2 shot 5 + E3 |
| 6 | movein_condition | condition | weak | no | E6 photos |

## Steps (each: lane, minutes, cut-if-over)

Lanes run in parallel. A = backend, B = front end, C = legal content, J = Jeremy integrating.
Times are focused-work minutes, not calendar. The riskiest slice (E1 highlight) is proven FIRST.

**Step 1 — Scaffold + frozen contract + precomputed case.json + fixture llm + env loader. [J, 45 min]**
`builds/case-builder/` skeleton; a complete, valid `data/case.json` for the full sample pack (6
exhibits, 6 evidence rows, gate, statutes, gaps, blind spots, timeline, next steps, all normalized
locators) checked in as the integration boundary; `app.py` routes serving it; `llm.py` returning
fixtures from `fixtures.json`; a ~10-line stdlib `.env` loader (read `.env`, `os.environ.setdefault`
for `MODEL`, `ANTHROPIC_BASE_URL`, key). Unblocks all lanes at once. Cut if over: tenancy-only
case.json (drop the goods enum for now).

**Step 2 — E1 vertical slice spike (prove the highlight). [A, 60 min] (do this in hour 1)**
Generate ONLY the agreement PDF (reportlab, clause 4 on page index 1, one shared clause-4 constant
used by both `make_pack.py` and `fixtures.json`). In `extract.py`: pdfplumber extract (copy
`_extract_pdf` + `_PDF_WORD_SPACING`) + the constrained consecutive-token matcher -> normalized
line boxes. In `viewer.py`: PyMuPDF render page index 1 to PNG + `/api/render` + `/api/viewer`. Wire
the front-end overlay for this one row and screenshot clause 4 highlighted. This proves the hardest
claim before anything else is built. Cut if over: hardcode the E1 box in case.json from a one-off
measurement, keep the render + overlay real.

**Step 3 — Rest of the sample pack. [A/C, 55 min]**
`sample/make_pack.py` adds: 6 WhatsApp screenshots + 1 email + 1 transfer screenshot (Pillow), 5
move-in photos (Pillow placeholders), a 4-min slideshow mp4 (ffmpeg) with the sofa on screen at
0:72. All synthetic; screenshot text ("ok, all good") matches `fixtures.json`. Cut if over: still
image for E5 (drop the mp4); 2 photos instead of 5.

**Step 4 — Intake + upload + multi-format parse. [A, 70 min]**
`extract.py` gains: tesseract `image_to_data` word boxes (normalized); ffmpeg keyframe at a fixed
timestamp (72 s for E5) cached for reuse by the viewer. `/api/intake` and `/api/upload` (multipart
with `exhibit_id`/`asset_id`; bad file -> unchanged case + `{error, code}`). Cut if over: single
cached keyframe per video (no per-30s loop); WhatsApp `.txt` parse dropped (E2 is screenshots, so no
`.txt` viewer is needed for the demo).

**Step 5 — Extraction across all files + quote-to-location. [A, 60 min]**
`llm.extract_facts` (fixture path first, real SDK path behind the same signature: `messages.create`
with a tools list + `tool_choice`, `json.loads` on the tool input, vision as a base64 image block).
Locator via the Step-2 matcher for every asset. A fact whose quote is not found is dropped (closed
world). Cut if over: PDF + image locators only; video facts carry the keyframe locator, no box.

**Step 6 — Gate + statute panel. [A/C, 40 min]**
`rules.gate`: 4 checks from intake (category in Schedule using `premises.residential` +
`lease_months`; amount <= $20k or $30k with consent; within 2 years of cause of action; respondent
in Singapore), each with a `section_id`. `content/statutes.json` holds SCTA 1984 s 2, s 5, Schedule
and Limitation Act s 6, quoted verbatim with URL + retrieved date; `/api/statute` serves the panel.
Fail -> stop text naming the right forum. Cut if over: hardcode the 4 pass results for the sample;
keep the section links + panel.

**Step 7 — Evidence rank + full viewer. [A, 60 min]**
`rules.strength` + `rules.rank` per the frozen table above (evidential strength separate from
`needs_check`; sort strength -> category weight -> evidence-key). `viewer.py` broadened to image +
video keyframe (E1 already proven in Step 2). `/api/viewer` addresses the source by
`evidence_id` + `source_index`. Cut if over: PDF + image highlight; video opens without a box.

**Step 8 — Gaps. [A/C, 30 min]**
`rules.gaps` fills the 5 categories from `content/gaps.json` + each exhibit's category ("You have"
from uploads, "Missing" static). Cut if over: static list straight from `gaps.json`.

**Step 9 — Blind spots + Next-lock. [A/C, 35 min]**
`content/blindspots.json` (6 questions per claim type); `/api/blindspot` saves one answer; the
front end shows the count (4 of 6) and locks Next until 6/6. The two clicks that take 4/6 -> 6/6 and
unlock Next are a scripted demo interaction, so verify them in the dry run. Cut if over: answers in
front-end state only (skip the save route); still gate Next on 6/6.

**Step 10 — Timeline (with computed refund-due). [A, 30 min]**
`rules.timeline`: dated facts + today + fixed future SCT steps + time-bar (cause of action + 2
years) + the computed refund-due event (move-out date + `intake.premises.refund_days`, the scalar
sourced to clause 4). Plain CSS list; selected-event panel uses `detail` + `sources` (each with a
`viewer_url`). Cut if over: static ordered list, refund-due seeded as a fixed date.

**Step 11 — Next steps + xlsx + claim pack zip + written request. [A, 70 min]**
`rules.next_steps` (+ fee table, with `source_label`/`source_url` per step); `exports.py`: xlsx
(openpyxl); claim-pack zip (`claim_form.txt` = both sides' particulars + 500-char summary + money
order + exhibit list with page refs; one PDF per asset, each measured and labelled `ready` or
`oversized` against 5 MB; `events.txt`); written request `.txt` in a modal. Cut if over: xlsx +
`claim_form.txt` + written request + a file manifest; skip per-asset PDF conversion.

**Step 12 — Front end: seven screens + viewer wiring. [B, parallel throughout, ~240 min total]**
B copies the seven screens from `gen.py` into `index.html`, swaps placeholders for `fetch` calls,
and wires the viewer overlay (percentage rectangles from normalized `boxes` inside a
`position:relative` wrapper) plus the two export buttons and the written-request modal. Runs
alongside Steps 2-11 against the checked-in case.json, then the live routes. Cut if over: static
screens fed by `GET /api/case`; only the viewer + exports interactive.

**Step 13 — selfcheck.py + stage-path dry run. [J, 35 min]**
Runs the sample pack through the pipeline and asserts: gate passes; `len(exhibits) == 6`; the six
exact `evidence_key`s appear in rank order 1-6; the E1 `deposit_terms` locator resolves to a
non-empty normalized box; xlsx + zip written; written request non-empty. Then a manual (or
Playwright) click-through of the exact stage path: load case, seven screens, answer two blind-spot
prompts to unlock Next, open evidence row 1, see clause-4 boxes, close viewer, download both files,
open the written request, all under 90 s, screenshot captured. Cut if over: keep the locator
assertion (drop conversion-breadth checks first, per the plan's degradation order).

**Step 14 — review-with-codex. [J, 30 min]** Standing reflex after the build; fix correctness inline.

**Step 15 — Deck + AI-tool disclosure + citations. [C/J, after freeze]** `make-slides`, disclosure
slide, library/API/dataset citations. Not part of the runnable-demo definition of done.

## Open questions (for Jeremy — do NOT block the plan)
1. **API key** — resolved 5 Sep 16:25: OpenRouter key in `.env`, $15 cap. Model
   `anthropic/claude-sonnet-5`.
2. **App name** — wireframe says "[App name]". Grill assumed "Case Builder". Confirm or replace.
3. **Lane assignments** — who is A (backend) / B (front end) / C (legal x2). Grill assumed 3 dev + 2
   legal, never confirmed.

## Alternatives considered
- **pdf.js viewer with find+highlightAll (fara/research original).** Rejected: `find` scroll and
  highlight behaviour varies by pdf.js version (noted as an open risk in the research), and it is a
  second code path (PDF only). Render-to-PNG + overlay box is one path for every format and has no
  version risk.
- **SQLite FTS5 statute corpus + 10-Act fetch.** Rejected: nothing in the demo searches statutes;
  the gate links four fixed sections. Static `statutes.json` with verbatim quotes is smaller and
  removes the SSO-fetch dependency.
- **Per-exhibit strength/rank.** Rejected: the wireframe ranks evidence rows, and a row cites
  several exhibits while an exhibit backs several rows, so rank must live on the row.
- **One monolithic `app.py`.** Rejected: the A/B lane split needs the `extract.py` / `viewer.py`
  seams so the two riskiest reused-from-fara pieces can be built and tested on their own.

## Notes

### Codex critique — round 1
Verdict: directionally strong, but the contract was not frozen enough for parallel work. Seven
BLOCKING items: (1) grouped exhibits (E2 = 6 screenshots, E6 = 5 photos) have no per-asset id, and
`?exhibit=&row=` cannot address the clicked source; (2) fara `_locator_for_match` is bag-of-words
and unions every matching token into a page-spanning box; (3) the coordinate contract mixed three
spaces (points*zoom, image px, rendered px) and the front end cannot know the display factor; (4)
the "read from a picture = weak" rule contradicts the wireframe (bank screenshot is Strong); (5)
evidence-row aggregation (merging E2 shot 5 + E3 into one row) is unspecified, so ranking facts
yields more than six rows; (6) multipart upload needs python-multipart; (7) the contract lacks
fields several screens need (gate lease/residential + statute content, timeline detail+sources,
next-step links, both sides' particulars). RISKS: highest-risk slice (E1 highlight) scheduled too
late; byte-identical fixture fragile; JSON examples were pseudocode not valid; sync upload/reset
could hang the browser; "PDFs passed through" does not guarantee 5 MB; .env is not auto-loaded;
selfcheck ambiguous. MISSING: 30-s video sampling misses the 1:12 frame; no render path for
WhatsApp .txt; refund-due (move-out + 14 days) is computed not extracted; route request/error
shapes absent; blind-spot click interaction not a step; no early stage-path acceptance check; no
failure state for bad uploads. ALTERNATIVES: build the E1 vertical slice first; make normalized
0-1 locators the canonical storage; freeze one complete precomputed case.json as the integration
boundary; treat video as one exact keyframe; cut conversion breadth before the locator assertion.
AGREE: FastAPI + one static HTML; fixtures; server-rendered images + overlay over pdf.js; rank on
evidence rows; deterministic gate/strength/rank/fee/timeline; static legal content; the sample
generator, cut lines, freeze and dry-run script; PDF-only highlight as the minimum guarantee.

### Claude rebuttal — round 1
Accepted all seven BLOCKING items and every RISK/MISSING/ALTERNATIVE, with two factual
corrections verified against the environment:
- BLOCKING #6 is wrong on its premise: `python-multipart` IS installed (checked), so FastAPI
  `UploadFile` works. I keep multipart rather than raw-body, but I adopt the real point behind it:
  the upload route must carry `exhibit_id` and `asset_id` so grouped exhibits (E2, E6) are
  addressable. That is now in the contract.
- BLOCKING #3 / ALTERNATIVE #2: confirmed fara `doc_ocr.ocr_page` already returns boxes normalized
  to 0-1. Normalized 0-1 coordinates are now the single canonical storage and wire format for
  every locator (PDF, image, video); the front end places rectangles with percentages inside a
  `position:relative` wrapper. This removes zoom/DPI/resize maths from the contract.
On BLOCKING #4 (the one locked grill decision this reopens): the grill said "read from a picture =
weak" and the research repeats it, but the wireframe makes the bank-transfer screenshot Strong.
Codex is right that this is a real correctness conflict, not a style choice. Resolution: split
evidential strength (what the evidence is) from `needs_check` (that a number/text was read off a
picture, a warning). "From a picture" no longer caps strength; it sets `needs_check: true`. This
is the minimal change that lets the demo reproduce its own wireframe. Recorded as the single grill
refinement, with reason.
Worked out and froze the strength/category mapping that reproduces wireframe ranks 1-6 exactly
(see Approach). All other items folded into the revised contract and steps.

### Codex critique — round 2
Confirmed the frozen strength+rank table sorts to exactly ranks 1-6 (deposit_terms, deposit_paid,
handover_acceptance, moveout_condition, damage_allegation, movein_condition). No new blocking. Two
round-1 contract gaps still open: (a) `refund_due` had no structured `refund_days` input, so the
timeline could not compute it without parsing prose; (b) timeline/intake source links named an
asset but `/api/viewer` only took `evidence_id + source_index`, so they could not open the viewer.

### Claude revision — round 2
Accepted both. (a) Added `intake.premises.refund_days` (14) as the deterministic scalar the
timeline uses, sourced to clause 4. (b) `/api/viewer` now also accepts a generic
`asset_id [+ page_index]` form, and every source object (evidence, timeline, intake) carries an
opaque `viewer_url` the front end opens verbatim. Both fixes are in the contract and Step 10.

### Codex critique — round 3
Refund calc and timeline links resolved. One consistency nit: the `exhibits[].assets[]` example did
not carry the `viewer_url` the prose promised for the intake sidebar.

### Claude revision — round 3
Added `viewer_url` to the asset examples (E1, E2-4). No design change. Sent for final confirm.

### Codex critique — round 4 (final)
CONVERGED. No remaining blocking objections.

## Changelog
- 2026-09-05 16:02 SGT: v1 drafted from the locked grill, demo script, wireframe, research and
  handoff. Sent to Codex for critique.
- 2026-09-05 16:20 SGT: v2 after Codex round 1. Froze the contract (per-asset addressing for
  grouped exhibits, evidence `id`/`evidence_key`/`category` enums, statute panel, timeline
  detail+sources, next-step links, both-sides particulars); switched all locators to normalized
  0-1 coordinates; replaced fara's bag-of-words matcher with a constrained consecutive-token
  matcher; split evidential strength from `needs_check` and froze the strength+rank table that
  reproduces wireframe ranks 1-6 (the one refined grill decision); reordered so the E1 highlight
  slice is proven first; video keyframe at 72 s; dropped the `.txt` viewer; computed refund-due;
  added the stdlib `.env` loader, upload error banner, and sharper selfcheck assertions. Corrected
  Codex: python-multipart is installed (kept multipart). Sent for re-critique.
- 2026-09-05 16:35 SGT: v3. Codex rounds 2-4: added `intake.premises.refund_days` for a
  deterministic refund-due event, a generic `/api/viewer?asset_id=` form + `viewer_url` on every
  source object (evidence, timeline, intake assets). Plan locked after Claude/Codex debate
  (Codex CONVERGED, no blocking).
- 2026-09-05 16:25 SGT: OpenRouter key landed. Anthropic SDK via OpenRouter tested (tool call + image). Model fixed at anthropic/claude-sonnet-5, $15 cap, fixtures for dev.

- 2026-09-05 ~17:00 SGT: Steps 1-13 built by Claude in one session (`builds/case-builder/`, 16 files). `python selfcheck.py` passes: gate passes, six rows rank 1-6 exactly as the frozen table, E1 clause-4 locator resolves to two normalised line boxes on page index 1, xlsx + claim-pack zip written, written request drafted. Browser click-through of all seven screens done via Playwright; screenshot `notes/screens/shot-3-evidence-highlight.png` shows clause 4 highlighted on page 2. SCTA 1984 s 5 and the Schedule fetched verbatim from SSO with Playwright (WebFetch got 403). Two deviations: fixtures are on by default even with a key (`USE_FIXTURES=0` for real calls); the generic `/api/viewer?asset_id=` form also returns the boxes of any fact found on that page. Cuts taken: none. OpenRouter spend so far $0.03. Step 14 (review-with-codex) next.

## Pre-merge review — Claude (fresh non-author subagent)
Reviewed all 22 files under builds/case-builder/ against the plan, demo script and grill.
BLOCKING: none. The scripted demo path holds: rank sort genuinely reproduces the frozen
table (rules.py:114 sorts strength -> CAT_WEIGHT -> KEY_ORDER; rules.py __main__ builds
from fixtures, not case.json); E1 highlight is real (make_pack.py and fixtures.json share
one CLAUSE4 constant; extract.locate is a constrained consecutive-token matcher, MIN_RUN=4,
one box per line); viewer maths correct (normalised [l,t,r,b] -> left:l*100% width:(r-l)*100%,
index.html:328); all seven screens wired and their data present.
RISKS: (1) header "Reset sample" button hits live /api/case/reset = ~1 min OCR+ffmpeg and
spends credits if USE_FIXTURES=0 (footgun mid-demo); (2) blind-spot Next-lock enforced only
at step===4, so clicking a later rail item skips it (demo uses Next, unaffected); (3) bad
upload was not "case.json unchanged" (mutated + saved on the caught failure); (4) absolute
asset paths baked into case.json (same-laptop demo fine); (5) generic /api/viewer?asset_id=
unions every fact box on the page (documented deviation).
MISSING: (1) blind-spot screen renders a uniform 6-question grid, not the left/right split the
demo narration (beat 55-67) describes; (2) demo-script.md:48 still lists a WhatsApp .txt parser
that the plan deliberately dropped. Minor drift: exhibit-level meta/facts placement differs from
the frozen example but is self-consistent (no consumer breaks).

## Pre-merge review — Codex (fresh thread, high effort)
BLOCKING (as raised): (C1) intake only propagates amount+date; edits to party/residential/lease
never reach the gate (app.py:154-157); (C2) bad supported uploads mutate state before validation,
make_asset opens the PDF outside the try so a corrupt PDF 500s, caught failures retain an error
exhibit and save (app.py:172-194); (C3) case.json stores Jeremy-specific absolute asset paths,
breaks on clone/move (case.json, make_asset app.py:47); (C4) quote matcher floor min(len(q),4)
admits <4-token quotes (extract.py:88); (C5) contract puts questions at intake.questions, code
uses top-level (app.py:56); (C6) scta_s5_time/service mark verbatim:true + one SSO URL over a
block that appends State Courts / Judiciary guidance (statutes.json, index.html:337).
RISKS: selfcheck saves a fixed 5-Sep "today" (Sunday demo shows yesterday unless reset is re-run);
generic viewer unions page boxes; synchronous OCR/ffmpeg/model inside async routes with no timeout;
strength() ignores meta.signed; real (USE_FIXTURES=0) model output unvalidated; claim pack keeps
oversized PDFs (labelled); README advertises --no-video but E5 mp4 always required.
MISSING: sale-of-goods unreachable in the UI; WhatsApp .txt promised in demo script, not parsed;
claim_form.txt lists 6 rows not all 15 asset PDFs; Limitation Act s 6 absent from statutes.json.

## Pre-merge review — Reconcile
Rebuttal round (Codex, resume): on C1, C3, C4, C5 Codex CONCEDED they do not break the scripted
demo (all fixture quotes are >= 4 normalised tokens so the matcher floor is always 4 and never
page-spanning; questions is internally consistent; the two live gate toggles used on stage do
update; reset regenerates valid paths on this laptop). C6 HELD with a concrete case: a judge
opening the time/service gate source sees "check it yourself at <SSO URL>" over text that is
partly Judiciary guidance not on SSO.

Fixed inline (2, both re-verified RESOLVED by Codex, no new blocking):
1. Upload failure safety (app.py /api/upload): snapshot the whole case, move make_asset + all
   mutation + recompute inside one try, roll back CASE and do not save on any failure. A corrupt
   PDF now returns 400 parse_failed with case.json byte-identical and E1 still ready; unsupported
   /oversized already returned unchanged. Verified by TestClient (not committed).
2. Statute attribution (statutes.json + index.html openStatute): for scta_s5_time and
   scta_s5_service, quote now holds only the verbatim SCTA text (which is at the SSO URL); the
   court-guide sentence moved to a new `guide` field shown in a separate block labelled
   "Plain-language court guidance, not the Act." The "verify at SSO" line now covers only Act text.

Left for Jeremy (judgment / operational, none block the demo): reset-button footgun + re-run
reset on demo morning so Today is correct; demo-script.md still names a WhatsApp .txt parser that
does not exist; blind-spot screen is a uniform grid vs the narration's left/right split; absolute
asset paths (fine on this laptop, make relative post-demo); intake only updates amount+date live.
Dismissed with reason: matcher floor (no demo impact, no page-spanning), questions placement
(self-consistent), sale-of-goods unreachable (by grill decision 14, content-only, not on stage),
Limitation Act s6 (gate uses SCTA's own 2-year bar), strength ignores meta.signed (no fixture
mis-ranks), unvalidated real model output (demo runs on fixtures), oversized PDF handling (no
sample asset is oversized), README --no-video (pack ships with the mp4).
- 2026-09-05 17:30 SGT: Step 14 done (review-with-codex, see Notes). Reviewer fixes: upload rollback, statute/guide text split. Claude's calls on the 5 open items applied (reset confirm, today refresh, demo script wording x2; paths and intake left). Three live-model dry runs ($0.63 total): model layer hardened (flat meta fields, meta inferred from facts, max 3 facts per file, dated events fed to the text prompts, sentence-safe 500-char cut). Live path ranks the six keys 1-6 with sane strengths. Demo recommendation: fixtures on stage, live path for Q&A. Handoff: handoffs/handoff-2026-09-05-ps4-built.md. Step 15 (deck) next.

- 5 Sep ~18:10 SGT: intake rebuilt as a chat for any Small Claims matter (Jeremy: "make it general"). `POST /api/chat`
  runs one model turn (`llm.intake_turn`), merges the fields (`app.apply_fields`), recomputes. Eight-item checklist
  replaces the eight fixed questions. Claim types: tenancy, goods, services, property_damage, other, unknown; content
  falls back to a `general` set. Fixtures replay a three-turn Mei Ling chat; live run on a services claim filled every
  field in 39 s. selfcheck extended and passing; browser click-through done; screenshot `notes/screens/01-chat-intake.png`.
