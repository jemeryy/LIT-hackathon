# PS4 build: how each part works

Written 5 Sep 2026 ~13:45 SGT from four research passes. Raw notes with every URL are in
`research/raw/`. This file is the one to build from.

Pipeline (Jeremy's diagram): intake -> structured facts -> {evidence matrix, timeline,
eligibility} -> statute retrieval -> {explanation, other side, next steps} -> checks.

## Verified figures (State Courts guide + SSO, 5 Sep 2026)
| Item | Value | Source |
|---|---|---|
| Claim limit | $20,000, or $30,000 if both sides sign a Memorandum of Consent | SCTA 1984 s 2 definitions; Guide p.4 |
| Time bar | 2 years from when the cause of action arose | Guide p.4 (find the subsection in s 5 from the Act PDF) |
| Filing fee, individual | $10 up to $5k; $20 from $5k to $10k; 1% above $10k | Guide p.5 |
| Filing fee, company | $50; $100; 3% | Guide p.5 |
| Serve respondent | within 7 working days of filing, personal delivery or registered post | Guide p.11 |
| Lawyers | not allowed before Registrar or Tribunal Magistrate (s 23) | Guide p.6 |
| Appeal | leave from District Court within 14 days, law or jurisdiction only | Guide p.22, s 38, s 40 |
| e-Negotiation | 5 rounds of offers each side on CJTS | Guide p.9 |
| GenAI guide | Registrar's Circular No. 1 of 2024, 23 Sep 2024, in force 1 Oct 2024, covers SCT | judiciary.gov.sg circulars |

Covered claim types: sale of goods, services (renovation named), residential tenancy up to 2 years,
damage to property (not motor accidents, not neighbour damage to movables), unfair practice under
the Consumer Protection (Fair Trading) Act, motor vehicle deposit refunds. Excluded: over $30k,
respondent outside Singapore, employment, commercial tenancy.

Second-hand only, do not put on a slide until checked against data.gov.sg: 9,113 SCT claims in 2022,
about 160 renovation disputes a year, average renovation contract ~$7,400 (Law Gazette article, fetch got 403).

## 1. Guided intake
- 8 plain questions, each with a one-line "why we ask". Answers feed the gate and the fact list:
  who is the other side (person or company, in Singapore?), what was agreed, what was paid and how,
  what went wrong, when did it go wrong (drives time bar), what have you asked them for, what do you want
  (money back, work done, both), consent to $30k limit if needed.
- Upload prompts sit inside the questions ("Upload the quote or contract", "Upload the chat").
- File types and how we read them:
  - PDF: copy `doc_extract._extract_pdf` from fara (pdfplumber, keeps page + word boxes).
  - WhatsApp .txt: 20-line regex parser, one message per index. Line shape is `date, time - sender: message`.
    Date format follows the phone locale, so parse both d/m and m/d. Continuation lines have no prefix. Skip whatstk (GPL).
  - Images (transfer screenshot, photos): Claude vision reads them. Anything read from an image is marked
    "read by AI from a picture, check it" and can never be rated strong on its own (fara rule: vision max confidence 0.6).
- Nothing the user types becomes evidence. Their answers are "your account". Only files are exhibits.

## 2a. Structured facts, in plain words
- One Claude tool-use call per document, strict schema: facts[] with fact, date, parties, amount,
  source_id, quote (exact text), plus the doc type and author (who made the document).
- Location comes from our own text, not from the API: match the quote back into the extracted text
  with fara's `_locator_for_match` / `_locator_in_page`. Gives page + box for PDF, line index for chat.
  This avoids the Claude citations feature entirely, so it works through OpenRouter credits too
  (citations blocks likely do not pass through OpenRouter; also citations cannot combine with structured output).
- A fact whose quote is not found in the source is dropped. Closed world.
- Plain-English rewrite is a second cheap call (Haiku 4.5 or Sonnet 5) over the fact list only.

## 2b. Evidence matrix (strong / weak)
Rating is a rule table in code, not the model's opinion. The model only supplies the inputs
(doc type, author, has date, has amount, signed, third party). Rules:
- Strong: made by a third party (bank, courier), or made by the other side, or signed by both, and carries a date and an amount.
- Medium: contemporaneous chat between the parties that states the point.
- Weak: made by the user alone, no date, no amount, vague words ("about 3 weeks"), or read by AI from an image.
- Each row: fact, exhibit, rating, one-line reason, "click to see".
Click-to-highlight:
- PDF: pdf.js viewer in an iframe, `#page=N`, then dispatch `find` with the quote and `highlightAll`. No custom text layer.
- Chat: scroll to line index, highlight the row.
- Image: open image with the AI-read text next to it and the check-it warning.

## 2c. Timeline
- Past events: every dated fact. Computed dates: time bar day (cause of action + 2 years), today.
- Future steps, fixed from the Guide: file on CJTS, serve within 7 working days, file Declaration of Service,
  Consultation, then Hearing if not settled, order, 14 days to seek leave to appeal.
- UI: plain CSS ordered list of dated cards. vis-timeline only if pan and zoom is needed for the demo. It is not.

## 2d. Eligibility gate and case strength
Gate (deterministic, same answer every time, each check shows its section):
1. Claim type in the Schedule to SCTA 1984 (s 5, Schedule).
2. Amount at or under $20,000, or under $30,000 with consent (s 2).
3. Within 2 years of the cause of action (s 5, subsection to confirm).
4. Respondent can be served in Singapore (s 5).
5. Not an excluded type (motor accident, employment, commercial lease, neighbour damage to movables).
Fail any: stop screen with the right place (CASE, Employment Claims Tribunals, Magistrate's Court).

Case strength (Jeremy kept it; built so it is not a prediction):
- A checklist per claim type. Services contract: agreement exists; terms (scope, price, timeline) are written;
  payment proven; breach proven (stopped work, defective, late); loss quantified; demand made and time to fix given;
  user kept their side (access, payments on schedule).
- Each item: proven / partly / missing, with the exhibit rows it rests on. Weighted sum gives a number out of 100.
- Wording on screen: "Case strength from your evidence. Not a prediction of the result. The Tribunal decides."
- "Similar cases": 2-3 hand-picked reported appeal decisions from eLitigation, shown as cards with
  citation and link. Not a statistics base. Gap: no verified renovation or deposit SCT appeal case found yet.
  Legal teammates to find 2-3 on elitigation.sg today. One confirmed SCT case for the finality point:
  Lakshmi d/o Kumaravelu v Lazada [2021] SGHC 174.

## 3. Statute and authoritative source search
- Fetch: no API. `https://sso.agc.gov.sg/Act/<CODE>?ViewType=Pdf` with a browser user agent works, no login,
  6-second gap between requests (robots.txt). Rules are under `/SL/`. Extract with pypdf, fix split words
  ("T ribunal"), split on section headings. SSO stamps "Current version as at <date>", strip before hashing.
- Seed set (all confirmed downloadable today): SCTA1984, SCTA1984-R1, CPFTA2003 (s 4 unfair practice, s 6,
  Part 3 Lemon Law ss 13-18, s 35 no contracting out), SGA1979 (s 13, s 14, s 35), SGA1982 (s 4; Part 2 services
  is not in force in Singapore), CRTPA2001 (s 2), LA1959 (s 6), FCA1959 (s 2), MA1967 (s 1, s 2), UCTA1977 (s 3, s 6, s 11).
  Plus HTML: judiciary.gov.sg small-claims pages and the Guide PDF, CASE renovation infographic and Lemon Law page,
  CaseTrust standard renovation contract (12-month workmanship warranty, milestone payments).
- Store: SQLite FTS5 (stdlib, BM25 built in). No embeddings, no Chroma. Fields: act_code, section, heading, text, url, retrieved_date.
- Retrieve: query from claim type + issues, top 8, plus an always-include list per claim type in code
  (services claim always gets SCTA s 5 + Schedule, SGA1982 s 4, LA1959 s 6, CPFTA s 4).
- Pinpoint URL for a section: copy from the SSO page, do not guess the pattern.
- Disclaimer line: SSO says it is an unofficial consolidation.

## 4. Explanation and the other side
- One call. Context: retrieved sections numbered [1]..[N], exhibits E1..En with their facts, the checklist result.
- Prompt contract copied from fara `_search_contract`: answer only from numbered sources, `[[N]]` is the only
  citation token, exact refusal string when not covered. Prompt caching on the system prompt.
- Output two columns. Left: how the case can be put, each sentence cited. Right: what the other side will say
  (delays caused by user, work done was worth the deposit, no fixed completion date) and what evidence answers it.
- After the call, run fara `prose_citations.verify_prose_citations` (pure, no I/O): any marker that does not
  match its source is deleted. This is the anti-hallucination story for the judges.
- Click a `[[N]]` chip: statute opens at the section (fara `renderCitationsHtml`, ~80 lines).

## 5. Next steps and claim pack
- Rule-based checklist from gaps: no demand letter -> draft one (drafting a document is allowed under the GenAI
  guide; drafting evidence is not); missing evidence -> list what to get; fee from the table; CJTS steps from the
  Guide (Singpass, pre-filing assessment, claim form, pay, pick Consultation date, serve, Declaration of Service).
- Claim pack: HTML page shaped like the CJTS claim (claimant, respondent, amount, what happened in dated
  paragraphs, remedy, exhibit list) printed to PDF from the browser. Portal filing is stubbed: CJTS needs Singpass, no public API.

## 6. Verification and safety layer (say this in the pitch)
- Closed world: only the user's exhibits and the seeded corpus. No invented cases, no invented evidence.
- Citation verifier deletes unproven citations. Facts without a found quote are dropped.
- Deterministic gate and rating rules. Same input, same answer.
- GenAI guide banner, quoting para 3(2)(b) and 5: user is responsible for accuracy; verify statutes on SSO and
  cases on eLitigation, never by asking another AI. No pre-emptive declaration needed unless the court asks.
- Refusal screens for out-of-scope matters.

## Positioning against what exists
- The Judiciary already runs a Harvey-built summariser for SCT (magistrates Sep 2025, self-represented users from Nov 2025).
  It summarises documents already filed and gives no legal orientation. Our slot is before filing: can SCT hear it,
  what does the evidence prove, what section applies, what to ask for. Say this in the pitch.
- Closest product: FactBinder (closed source). CASE and CJC are human services.

## Borrow from fara (paths in `research/raw/fara-reuse.md`)
`doc_extract._extract_pdf` + locators, `prose_citations.verify_prose_citations`, `{value, quote, page, confidence}`
shape, `renderCitationsHtml`, `_search_contract` prompt rules, `_normalize_agc_version_stamp`.

## Model and cost
Sonnet 5 (`claude-sonnet-5`, $2 in / $10 out per 1M) for extraction and the explanation call. Haiku 4.5 for the
plain-English rewrite. Check the organisers' credits: if they are OpenRouter, confirm the model IDs there.

## Open risks, in order
1. Organiser API credits may be OpenRouter, not Anthropic direct. Design above does not need Anthropic-only features.
2. No verified renovation or deposit appeal case yet. Legal team task, today.
3. SCT statistics are second-hand. Check data.gov.sg datasets before the deck.
4. pdf.js `find` scroll behaviour varies by version. Pin a version and test in the first hour.
5. 2-year time bar subsection in SCTA s 5 not yet quoted verbatim. Read it from the downloaded PDF.

## CJTS filing facts (from the CJTS guide, `documents/cjts_guide_to_filing_sct.pdf`, text in `research/raw/cjts_guide_text.txt`)
- Pre-filing assessment comes first, no login needed: pick ONE main category and a sub-category
  (example in the guide: Lease not exceeding 2 years (residential premises) > Refund of Rental Deposit),
  enter Date of Cause of Action and Claim Amount. The system checks time bar and money limit, then asks
  questions on party details, nature of dispute and service. It gives a pre-filing ID valid 7 days (guide s.2).
- Login: Singpass for individuals, Corppass for entities, CJTS Pass for people without Singpass (s.3).
- Claim form has 6 parts (s.12): A claimant, B respondent, C particulars of claim (type of goods or service
  is mandatory), D brief summary of claim, at most 500 characters, E supporting documents, PDF only, 5MB each,
  with doc type, description and the page number referred to, F claiming for: Money Order (value), Work Order
  (nature and value), costs or disbursements (need evidence). Declaration: "I am the claimant and all the
  information provided is true and correct". Drafts last 7 days. Claim counts as filed only when the fee is paid.
- After payment: pick a Consultation date and time, say if an interpreter is needed. Save Claimant Copy and
  Respondent Copy (the Respondent Copy carries the one-time reference number the other side uses to see the case).
- Respondent can start e-Negotiation, 5 rounds, options: agree, agree by instalments, propose another amount or date, disagree (s.36).
- Counterclaim: respondent may file one, at least 3 days before Consultation or Hearing (s.16).
- Submission for Hearing form: events of the case in date order plus witnesses and their language (s.21).
  Our timeline maps straight onto this.
- Defects Schedule form: only for renovation disputes and residential tenancies up to 2 years. Claimant lists
  each defect and estimated repair cost; respondent fills in remedial work (s.23).
- Submit Supporting Documents e-service for anything missed (s.24). Set aside a default order within 1 month (s.25).
  Leave to appeal within 14 days, on law or jurisdiction only (s.30).
- Fees are not stated in this guide. The $10 / $20 / 1% figures come from the State Courts "A Guide to Small Claims" p.5.

## Claim pack, defined
Everything the six-part claim form asks for, ready to paste and upload: particulars of both sides, a
500-character summary, every upload converted to a PDF under 5MB with a description and page reference,
the money order amount, plus the events list for the Submission for Hearing form. Not a filing. The user
uploads it on CJTS.
