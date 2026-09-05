# Grill: build scope for the PS4 demo (self-grilled, 5 Sep 2026 16:00 SGT)

Inputs: notes/demo-script.md (v4), notes/wireframe/gen.py (v6), BRIEF.md, research/ps4-how-each-part-works.md,
research/raw/fara-reuse.md, research/raw/tech-approach.md, handoffs/handoff-2026-09-05-ps4-research-wireframe.md.
Clock: now Sat 5 Sep 16:00 SGT. Hard deadline Sun 6 Sep 12:00 SGT. Rooms close Sat 21:00.

Decisions. `(?)` = unsure, Jeremy can flip.

1. What shape is the app? -> FastAPI backend + one static `index.html` (vanilla JS, no build step), run on a laptop. Because the wireframe needs file upload and a click-to-highlight viewer, and the fara pattern is already known.
2. App name? -> "Case Builder", folder `builds/case-builder/`. (?) Because the wireframe file is already called sct-case-builder.
3. How do we call the model? -> `anthropic` SDK, `ANTHROPIC_BASE_URL` + `MODEL` from `.env`, default `claude-sonnet-5`, effort low, streaming off (small outputs). One file `llm.py` with two functions: `extract_facts(doc)` and `write_text(prompt)`. Until a key arrives, `llm.py` returns fixture JSON for the sample pack so every other lane keeps moving. If organiser credits turn out to be OpenRouter, only `llm.py` changes. (?) key source.
4. What does the model do, what do rules do? -> Model: per-file fact extraction (fact, date, party, amount, exact quote, category) plus file metadata (author, signed, dated, has amount, read from picture); plain-words story; 500-char summary; written request draft. Rules in code: gate, strength, rank, gaps, blind spots, timeline, next steps, fee. Because team said no legal advice and the pitch says "rules, not a model".
5. Which file types are read for real? -> PDF (pdfplumber, fara `_extract_pdf` + locators), PNG/JPG (tesseract word boxes for locating + vision for meaning), MP4 (ffmpeg one frame per 30 s, then the image path, locator = timestamp). WhatsApp .txt export is a stretch (20-line regex). Because the sample pack in the wireframe is PDF, screenshots, photos and one video.
6. Source viewer? -> Server renders the page or image to PNG (PyMuPDF for PDF, Pillow for images, ffmpeg frame for video) and returns highlight boxes from word bboxes. Front end shows `<img>` plus an overlay rectangle. One viewer for every format. No pdf.js. Because pdf.js find-and-scroll is a known version risk and this is one code path.
7. Strength and rank? -> Rule table: Strong = third party or the other side or signed by both, plus date and amount; Medium = dated chat between the parties; Weak = made by user alone, undated, no amount, vague, or read from a picture. Rank = sort by strength then category weight (agreement > payment > other side's words > condition > dispute). Deterministic.
8. Gate and statute links? -> Four checks in code from the intake answers. Section text in `content/statutes.json`: SCTA 1984 s 2, s 5, Schedule; Limitation Act s 6; quoted verbatim from the SSO PDF with URL and retrieved date; shown in the same viewer as a text panel. No corpus search, no FTS5, no 10-Act fetch. Because nothing in the demo script searches statutes.
9. Gaps and blind spots? -> Static JSON per claim type (tenancy, goods) in `content/`. "You have" fills from each exhibit's category. Blind-spot answers saved; Next locked until all six answered. Because the content is legal-team work and the logic is a lookup.
10. Timeline? -> Dated facts from extraction + today + fixed future SCT steps + time-bar date (cause of action + 2 years). Plain CSS list. No timeline library.
11. Exports? -> Evidence sheet xlsx via openpyxl. Claim pack = zip: `claim_form.txt` (particulars, 500-char summary, money order, exhibit list with page refs), one PDF per exhibit under 5 MB (images via Pillow, PDFs passed through, video as a frames PDF), `events.txt` for the Submission for Hearing form. Written request as `.txt` shown in a modal. Portal filing stubbed, said aloud.
12. State? -> One `case.json` per case under `data/`, single case, no DB, no auth, no login.
13. Sample pack? -> `sample/make_pack.py` generates it: 6-page tenancy agreement PDF (reportlab, clause 4 on page 2, clause 6 inventory), 6 WhatsApp screenshots + 1 email screenshot + 1 transfer screenshot (Pillow), 5 move-in photos (Pillow placeholders), a 4-minute slideshow mp4 (ffmpeg, sofa frame at 1:12). All synthetic, disclosed on the pitch.
14. Sale of goods? -> Content JSON only (gate categories, gaps, blind spots). Not shown on stage. Tenancy only in the pitch, one line that goods is supported.
15. Tests? -> One `selfcheck.py`: runs the sample pack through the pipeline and asserts gate passes, six exhibits ranked, xlsx and zip written. It doubles as the demo dry run. No test suite.
16. Team split? -> Lane A backend (parse, extract, rules, exports). Lane B front end (7 screens from gen.py + viewer). Lane C legal x2 (statute quotes, gap and blind-spot JSON for both claim types, next-steps copy, deck, AI disclosure slide, citations). Jeremy integrates, runs selfcheck, demos. (?) 3 dev + 2 legal assumed.
17. Time budget? -> Sat 16:00-21:00 at SMU (5 h), Sat 22:00-00:30 remote (2.5 h), Sun 08:00-10:30 (2.5 h). Feature freeze Sun 10:30. Deck done Sun 11:00. Submit Sun 11:30. Total build time about 10 h.
18. API key? -> Ask @tauporky now. Build on fixtures until it lands. Jeremy's own Anthropic key as backup costs money, so that is his call. (open)
19. Demo script line "Corpus is ~40 sections" -> change to "the sections the gate links, plus the court guide". Because decision 8.
20. Repo hygiene? -> `.env` gitignored, `requirements.txt`, README with AI tool disclosure and library citations (judging asks for both). No deploy. Public repo only on Jeremy's green light.

Open for Jeremy (do not block the plan): API key requested or not; app name; who is in which lane.
