# Demo script (90 seconds) — PS4, SCT self-represented persons

Status: v6, 6 Sep 2026 00:10 SGT. Five steps: files, gaps, blind spots and both rankings now sit in one step 3 (Jeremy's call). Earlier v5: Intake is now a chat for any Small Claims matter (Jeremy's call). Earlier: v4 after team feedback and a check against the CJTS filing guide. Figures checked against the State Courts
guide and SSO, see `research/ps4-how-each-part-works.md`. Wireframe: `notes/wireframe/`.

Team feedback applied: no case strength score, no counterarguments, no legal argument, no separate
law panel. Added evidence gaps by category, evidence ranking, spreadsheet export, evidence blind spots. Claim types in
scope: residential tenancy and sale of goods.

## The story we demo
Mei Ling rented Mr Tan's flat for 12 months and paid a $2,600 deposit. She moved out on
31 Jul 2026 and he wrote "ok, all good". On 15 Aug he refused to return the deposit, saying the
sofa was damaged. She has: the tenancy agreement PDF, a WhatsApp export, the deposit transfer
screenshot, move-in photos and move-out photos. She has been asking ChatGPT what to do.

Persona is fictional. All evidence is a seeded sample pack in `builds/<name>/sample/`.
The upload and parsing on those files is real.

## Beats (time in seconds)

| t | Screen | What the presenter says |
|---|---|---|
| 0-10 | Landing, one line: "Build your Small Claims case from your evidence." | SRPs already use ChatGPT for this and get misled. Ours only speaks from her documents and the actual court guide. It does not give legal advice. |
| 10-22 | Chat intake, full width. She types what happened in her own words. The assistant sorts it (home tenancy), pulls out the amount and dates, and asks for the two things missing. The text box grows as she types. | Any Small Claims matter: goods, services, a home lease, damage to property. No legal words. Her words are her account. Three turns and every box is ticked. |
| 22-30 | Gate. "Can the tribunal hear this?" Four checks, each with its section: tenancy up to 2 years, $2,600 under the $20,000 limit, within 2 years of 15 Aug 2026, landlord in Singapore. Green. | Rules, not a model. Same answer every time. Fail a check and it stops and points her to the right place. |
| 30-67 | Step 3, Your evidence, one page in five parts. A: add files. B: what else to gather, five headings with have / still missing and an Add a file button each. C: what the other side may have, six Yes / No / Not sure questions. D: press "I have added everything" and her evidence is ranked 1 to 6 with strength and a one-line reason; click row 1 and the agreement opens at page 2, clause 4 highlighted. E: the other side's evidence, ranked from her answers, each with what of hers answers it. | The tool never makes evidence. It tells her what to go and get. The other side's list is the confirmation-bias fix the brief asks for: we do not argue his case, we list what he could bring so she is not surprised at the first court meeting. |
| 67-75 | Timeline. Lease start, move out, refund due, refusal, today, then the SCT steps ahead and the time-bar date. Maps onto the CJTS Submission for Hearing form. | Past and future on one line. She sees the deadline. |
| 75-90 | Next steps, in CJTS order: written request, gather list, pre-filing assessment (ID lasts 7 days), six-part claim form with the 500-character summary and PDF-only uploads under 5MB, $10 fee, serve within 7 working days, Submission for Hearing. Evidence sheet (xlsx) she can add to. Claim pack: everything the form asks for, ready to paste and upload. | Portal filing is stubbed. Everything above it is real. Under the Courts' GenAI guide she is responsible for what she files, and the tool says so. |

## What is real and what is stubbed (say this to the judge)
- Real: chat intake (the model reads her words and fills the form fields, checked live on a services claim too), upload, extraction with source locations, ranked evidence table with click-to-highlight,
  gate rules, evidence gap list, blind-spot list and prompts, timeline, evidence sheet export,
  claim pack (form text, PDFs under 5MB, events list), written request draft.
- Stubbed: CJTS portal submission (no public API). Statute text is only the sections the gate links, plus the court guide, not all of Singapore law.
- Refusals: outside SCT scope (employment, over limit, time-barred, commercial lease) gives a stop screen
  with the right place to go. No invented evidence, no invented case names, no outcome prediction.

## Decisions taken (say if wrong)
- Demo scenario switched from renovation to a tenancy deposit, since the team wants tenancy and sales.
- Intake is general (5 Sep evening): the chat sorts any matter into tenancy, goods, services or damage to
  property. Tenancy and goods have their own gap list, blind spots and next steps; the other two share a
  general set. Anything else fails the category check with a stop screen.
- The product is live by default (Jeremy, 5 Sep evening: usable for a real case, not only a demo). New case starts
  from nothing; Load the example brings back Mei Ling. To replay the saved run on stage start the server with
  `USE_FIXTURES=1`. Checked live with a made-up painting contractor claim: own words, one uploaded quote image, gate
  green, two facts ranked with the exact line highlighted, story written, 38 seconds end to end.
- Case strength score, counterarguments and the law panel removed. Statute links stay on the gate; court guide links on next steps.
- Blind spots lists evidence the other side could hold and questions for what she may have missed. It never argues either side.
- Portal integration is a claim-pack export, not a live filing.

## Build only what this script touches
Chat intake with the eight-item checklist, sample pack, parser for PDF / screenshots and photos / video frame, fact extractor with source
locations, gate rules, evidence ranking rules + viewer with highlight, gap list per claim type,
blind-spot list and prompt set per claim type, timeline, statute sections for the gate links,
evidence sheet xlsx, written request draft, claim pack (form text, PDF conversion, events list). Nothing else.
