# Devpost submission text (paste into the form)

Deadline: 6 Sep 2026 12:00 SGT. Site: https://smu-lit-hackathon-2026.devpost.com/
Uploads: `deck/case-helper-deck.pptx`, screenshots from `notes/screens/deck-*.png`.
Links: repo https://github.com/jemeryy/LIT-hackathon (make it public first), live https://case-helper-production.up.railway.app/

## Project name
Case Helper

## Tagline
Build your Small Claims case from your evidence. No lawyer, no legal advice, no made up cases.

## Problem statement
PS4, MinLaw: self-represented persons at the Small Claims Tribunals.

## Description

### Inspiration
At the Small Claims Tribunals you cannot bring a lawyer, so people prepare the case themselves. Many now ask ChatGPT. It agrees with them, invents cases, and does not know the court's steps. They turn up with a story and the wrong proof. The Courts' guide on generative AI says the person is responsible for what they file. Nothing helps them meet that duty.

### What it does
Five steps on one page.
1. Tell us what happened. A chat in your own words. The model pulls out the facts (who, what, when, how much) and asks for what is missing.
2. Can the tribunal hear it? Four rule checks (type of claim, amount, time bar, other side in Singapore), each quoting the section of the Small Claims Tribunals Act from Singapore Statutes Online.
3. Your evidence. Add files (PDF, screenshots, photos, video). Every fact carries an exact quote matched back into the file; press a row and the file opens at that line. A list of what else to gather for your kind of claim. Seven questions about what the other side may bring, then their evidence ranked for them, with how to answer each from your own files.
4. Your timeline. Events from the files, today, then the court's steps and the two year time bar.
5. What to do next, in the court's order, with an evidence sheet, a written request letter, and a claim pack (form text plus every file as a PDF under 5 MB) ready to paste into the court's portal.

It works for a real case, not only the demo: tenancy deposit, goods, services, damage to property.

### How we built it
Python, FastAPI, one HTML page. Claude Sonnet 5 (through OpenRouter) does three jobs only: read what the person types, read each file and return facts with exact quotes, and write the story, summary and request letter. Everything else is rules in code: the gate, strength and rank, gather list, blind spots, timeline, fee, next steps. Files are read with pdfplumber, PyMuPDF, Tesseract OCR and ffmpeg.

Guards: a quote that is not found in the file is dropped. Legal conclusions and advice words from the model are rejected by the server. File text, names and chat are treated as data, not instructions. No case names, no guess at who wins, no invented evidence. Every page says the person is responsible for what they file.

### Challenges
Keeping the model to facts. Making the reader admit when a file does not fit the claim (a misfit file now ranks weak and stays out of the story). Wording every screen in plain words for someone who has never been to court. Matching each step to the court's own filing order.

### What we learned
The useful part is not the answer, it is the sorting: what you have, what is missing, and what the other side will say. Rules give the same answer every time and can be checked line by line; the model is only worth using where the words are the person's own.

### What's next
Keep cases across restarts. Own content sets for services and damage to property. Prepare people for e-Negotiation on CJTS. Test with Community Justice Centre volunteers on consented cases.

## Built with
python, fastapi, uvicorn, anthropic-sdk, openrouter, claude-sonnet-5, pdfplumber, pymupdf, tesseract, pillow, openpyxl, reportlab, ffmpeg, railway, html, javascript

## AI tools used to build it (disclosure)
Claude Code (Anthropic; Claude Opus and Fable models) for planning, code, browser tests and the deck. OpenAI Codex for plan cross-checks and code review. Playwright, driven by Claude Code, for end to end browser tests. All design decisions were the team's; see the plan file and commit history.

## References
- Small Claims Tribunals Act 1984, s 2, s 5, s 23 and the Schedule. https://sso.agc.gov.sg/Act/SCTA1984 (read 5 Sep 2026)
- State Courts, A Guide to Small Claims. https://www.judiciary.gov.sg/docs/default-source/civil-docs/sct_guide_to_small_claims.pdf
- Judiciary: https://www.judiciary.gov.sg/civil/file-small-claim and https://www.judiciary.gov.sg/civil/how-to-file-serve-small-claim
- CJTS: https://cjts.judiciary.gov.sg/
- Registrar's Circular No. 1 of 2024, Guide on the Use of Generative AI Tools by Court Users
- Libraries: FastAPI, Uvicorn, python-multipart, httpx, Anthropic Python SDK, pdfplumber, PyMuPDF, Pillow, pillow-heif, pytesseract, openpyxl, reportlab, python-pptx
- Data: synthetic sample pack made by the team. No real or organiser data.
