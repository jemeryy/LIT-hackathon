# Case Helper

Build your Small Claims case from your evidence. Built at the LIT Hackathon 2026 for problem statement 4
(self-represented persons at the Small Claims Tribunals). It does not give legal advice.

It works for a real case, not only the example. Open it, press New case, type what happened, add your own files
(PDF, screenshots, photos, video). The model reads your words and your files live. Everything after that is rules.

## Run it

```
cd builds/case-builder
python sample/make_pack.py        # makes the synthetic sample files (needs ffmpeg on PATH; add --no-video to skip the mp4)
python selfcheck.py               # replays the worked example on fixtures and checks the whole path (no credits)
python -m unittest test_chat_flow.py test_relevance.py  # chat and evidence regression checks (no credits)
node test_chat_ui.cjs             # refresh, retry and pending-request UI checks
uvicorn app:app --port 8000       # then open http://127.0.0.1:8000 and press New case, or Load the example
```

Needs Python 3.12, the packages in `requirements.txt`, `tesseract` and `ffmpeg` on PATH.

Model calls: `.env` in the repo root holds `OPENROUTER_API_KEY`, `ANTHROPIC_BASE_URL` and `MODEL`. With a key
the model is live by default. `USE_FIXTURES=1` (forced when there is no key) replays the saved run of the worked
example from `content/fixtures.json` instead, so the example is repeatable on stage without credits.

Each visitor's case is stored in `data/cases/`, with uploads in a separate visitor folder.
Refreshing resumes the saved case; New case starts a new one. Load the example reads the six sample exhibits
in `sample/pack/` (Mei Ling's tenancy deposit). Open the app through the server URL, not the HTML file on disk.

The server chooses the next intake question from recorded facts and unresolved tribunal checks.
Short Yes/No answers to its location and residential-property questions are recorded directly. Unknown
details are tracked individually and can be supplied later. Model questions are used to clarify uncertain
messages; file-upload instructions and navigation come from the server.

Both evidence lists assess relevance separately from strength. Related notices, plans and follow-up messages
are retained as context, even when they do not establish a ranked point. An empty extraction alone means
needs review, not irrelevant. Clearly unrelated files, placeholders and needs-review files remain visible
without a strength rank and are excluded from the claim pack, with the exclusion recorded in its manifest.
Related context is included in the pack. The other side's hypothetical evidence from Yes/Not sure answers
is displayed separately from actual uploaded files. The worked example uses saved relevance results and visibly
labels its placeholder photos/video; they do not establish the flat's actual condition.

## AI boundaries

The intake model collects facts; it does not decide legal rights or give advice. Its output is a structured
scope decision, confidence level, neutral `You say...` reflection, and one or two fact questions. The server
rejects legal conclusions and recommendation language, refuses unrelated or prompt-injection requests, does
not apply new facts from unsafe or low-confidence turns, and independently decides when intake is complete.
A person may correct a fact they gave earlier. On a low-confidence turn the server still writes a field the
model names as changed, but only when that field is already recorded and the new value differs, so a
correction can never add a fact that was not there before. Conversation text, filenames, OCR, images, and
document contents are always treated as untrusted data rather than instructions. These controls reduce risk;
they do not make model output infallible.

General web access is intentionally disabled. A future legal-fact verifier should be separate from intake and
restricted to an allowlist of official sources: Singapore Statutes Online (`sso.agc.gov.sg`), Singapore Courts
and Judiciary (`judiciary.gov.sg`), and CJTS (`cjts.judiciary.gov.sg`). It should quote and link the exact
supporting passage, record its retrieval date, treat retrieved pages as untrusted data, and abstain when no
current authoritative passage supports the statement. Blogs, forums, law-firm pages, and unrestricted search
should not be used for legal assertions.

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
