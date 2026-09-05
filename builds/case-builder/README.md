# Case Builder

Build your Small Claims case from your evidence. A demo for the LIT Hackathon 2026, problem statement 4
(self-represented persons at the Small Claims Tribunals). It does not give legal advice.

## Run it

```
cd builds/case-builder
python sample/make_pack.py        # makes the synthetic sample files (needs ffmpeg on PATH; add --no-video to skip the mp4)
python selfcheck.py               # builds the sample case through the pipeline and checks the demo path
uvicorn app:app --port 8000       # then open http://127.0.0.1:8000
```

Needs Python 3.12, the packages in `requirements.txt`, `tesseract` and `ffmpeg` on PATH.

Model calls: `.env` in the repo root holds `OPENROUTER_API_KEY`, `ANTHROPIC_BASE_URL` and `MODEL`.
`USE_FIXTURES=1` (the default when no key is set) answers from `content/fixtures.json` instead of calling
the model. Set `USE_FIXTURES=0` to read the files with the model for real.

## What is real and what is stubbed

- Real: file upload, text and word boxes from PDF (pdfplumber), images (tesseract) and video (one ffmpeg frame at
  1:12); the quote for every fact is matched back into that text, so every highlight is a real place in the file;
  the four gate checks, strength, rank, gaps, blind spots, timeline, fee and next steps are rules in `rules.py`;
  the evidence sheet (xlsx), claim pack (zip of form text, one PDF per file measured against 5 MB, events list)
  and the written request.
- Model (Claude Sonnet 5 through OpenRouter): runs the intake chat (reads what the person types, sorts the claim
  into tenancy, goods, services or damage to property, fills the form fields, asks for what is missing); reads each
  file, as text plus the picture for screenshots, photos and the video frame, and returns facts with exact quotes;
  and writes the story, the 500-character summary and the written request. With fixtures on, the chat replays a
  saved three-turn conversation and the file reads come from a file instead.
- Rules, not the model, decide everything after the chat: the four gate checks, ranking, gaps, blind spots,
  timeline, fee. Tenancy and goods have their own content sets; services and property damage share a general set.
- Stubbed: filing on the CJTS portal (no public API). Statute text is only the sections the gate links
  (SCTA 1984 s 2, s 5 and the Schedule, quoted verbatim from Singapore Statutes Online on 5 Sep 2026).
- The sample pack in `sample/pack/` is synthetic. The persona is fictional.

## AI tools used to build it

Claude Code (Claude Fable 5.1 and Claude Sonnet 5) and OpenAI Codex CLI were used for planning, code, and
review. Every legal figure was checked against the State Courts guide and Singapore Statutes Online.

## Libraries and sources

fastapi, uvicorn, python-multipart, anthropic, pdfplumber, PyMuPDF, Pillow, pytesseract (Tesseract OCR),
openpyxl, reportlab, ffmpeg. Small Claims Tribunals Act 1984 (sso.agc.gov.sg). State Courts, A Guide to Small
Claims (judiciary.gov.sg). CJTS filing guide (cjts.judiciary.gov.sg).
