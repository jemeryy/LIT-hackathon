# Demo script (90 seconds) — PS4, SCT self-represented persons

Status: v5, 5 Sep 2026 ~18:10 SGT. Intake is now a chat for any Small Claims matter (Jeremy's call). Earlier: v4 after team feedback and a check against the CJTS filing guide. Figures checked against the State Courts
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
| 10-22 | Chat intake. She types what happened in her own words. The assistant sorts it (home tenancy), pulls out the amount and dates, and asks for the two things missing, saying why each is needed. Eight-item checklist on the right ticks off as she answers. Files added on the same panel. | Any Small Claims matter: goods, services, a home lease, damage to property. No legal words. Her words are her account. Only files are evidence. Three turns and every box is ticked. |
| 22-30 | Gate. "Can the SCT hear this?" Four checks, each with its section: tenancy up to 2 years, $2,600 under the $20,000 limit, within 2 years of 15 Aug 2026, landlord in Singapore. Green. | Rules, not a model. Same answer every time. Fail a check and it stops and points her to the right place. |
| 30-45 | Evidence, ranked. Plain-words summary. Table ranked 1 to 6 with strength and a one-line reason. Click row 1: agreement opens at page 2, clause 4 highlighted. "Export evidence sheet" button. | Every row points at a real place in her own files. Rank tells her what to stress first. Click. Highlight. |
| 45-55 | What else to gather. Five categories: communication, prior arrangement, payment, condition, her request. Have / Add per category with why it matters. Stamp duty certificate flagged. | The tool never makes evidence. It tells her what to go and get, and why. |
| 55-67 | Evidence blind spots. Six questions in a grid: what the landlord could bring (his own photos, a repair invoice, the signed inventory, messages on other channels) and what she may have missed (witnesses, any deduction accepted). Each has a hint saying what covers it. A note on his counterclaim. Answer the last two to unlock Next (4 of 6 becomes 6 of 6). | This is the confirmation-bias fix the brief asks for. We do not argue his case. We list what could exist so she is not surprised at the Consultation. |
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
- On stage the chat replays a saved model run (three turns, fixed replies). Live for Q&A with `USE_FIXTURES=0`.
- Case strength score, counterarguments and the law panel removed. Statute links stay on the gate; court guide links on next steps.
- Blind spots lists evidence the other side could hold and questions for what she may have missed. It never argues either side.
- Portal integration is a claim-pack export, not a live filing.

## Build only what this script touches
Chat intake with the eight-item checklist, sample pack, parser for PDF / screenshots and photos / video frame, fact extractor with source
locations, gate rules, evidence ranking rules + viewer with highlight, gap list per claim type,
blind-spot list and prompt set per claim type, timeline, statute sections for the gate links,
evidence sheet xlsx, written request draft, claim pack (form text, PDF conversion, events list). Nothing else.
