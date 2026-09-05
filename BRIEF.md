# Hackathon brief

Source: `documents/` PDFs + Notion hub (read 5 Sep 2026, 08:10 SGT).
Notion: https://bottlenose-ninja-9c2.notion.site/SMU-LIT-Legal-Tech-Hackathon-3d19970c91f28009a337d9771d852570

- **Event:** SMU LIT Legal-Tech Hackathon 2026
- **Format:** In person, SMU. 24h hacking. Prelim judging Day 2, top 4 go to TechLaw.Fest.
- **Team:** 5 people. Assumed 3 code, 2 legal (not confirmed).
- **Chosen statement:** PS4 MinLaw, self-represented persons at the Small Claims Tribunals. Decided 5 Sep ~1300 SGT. Form submission by 1800 is Jeremy's to confirm.

## Clock (SGT)
| When | What |
|---|---|
| 5 Sep 0900 | Track challenges released + in-person registration, SMU Hall B1 |
| 5 Sep 1000 | Opening brief |
| 5 Sep 1100 | **Hacking begins** |
| 5 Sep **1800** | Submit chosen challenge via Google Form (Notion overrides the PDF's 2100) |
| 5 Sep 2100 | End of day. Classrooms close. |
| 6 Sep 1200 | **HARD DEADLINE.** Slides + tool via Notion/Devpost. No late submission. |
| 6 Sep 1300 | Prelim judging, 4 min pitch + 2 min Q&A |
| 6 Sep 1430 | Closing, top 4 announced |
| 9 Sep | Finals at TechLaw.Fest (time TBC) |

Rooms 5 Sep 9am-9pm: YPHSL B2-03, B1-09, B1-13, CONNEX L4. From 3.30pm also YPHSL 1-02, CIS 3-04.
Rooms 6 Sep 9am-2pm: YPHSL B1-09, B1-13, 1-02. Morning attendance optional; submit online, arrive 1pm.
Judging rooms: SOSS/CIS 1-2 MinLaw, 3-2 AITHENA, 3-4 Rajah & Tann, 3-5 SG Academy of Law.

## Problem statement
Pick exactly ONE. Submit via https://forms.gle/1TjvhBzk6K51UqiVA by **5 Sep 1800**, using the
sign-up email. Full text: Notion > Challenge Statements.

1. **AITHENA — contract obligation extraction.** Ingest 40-80 signed SME contracts (mixed
   format, at least one scanned). Extract parties, term, renewal + notice, termination,
   payments, liability caps, exclusivity. Forward 90-day calendar. Cross-contract conflict
   detection. Every field links to page + clause with a confidence signal that separates
   "found it" from "inferred it". Hard requirements: grounding (no un-anchored legal claims,
   fabricated citations are a serious defect), calibration (a defined competence boundary the
   tool visibly hits), escalation (a handoff brief a real lawyer can act on in a minute).
   Judged on a shared corpus with known ground truth; honesty scored separately from accuracy.
2. **SAL — evaluation framework for legal AI.** Automated, scalable benchmark that scores
   quality, accuracy, bias and citation integrity of a case-law database's AI outputs. Must
   catch fake cases, test whether the AI grasps why a case matters (not keyword matching), and
   run instantly across thousands of daily queries.
3. **R&T — adoption of new legal tech.** Why firms' tool rollouts fail. Second half: use
   generative audio-video to simulate user-system interactions as short, use-case-based
   educational clips. (Separate sub-brief: build tools structurally resilient to regulatory
   change - find which documents, processes and playbooks a change touches, how, and push the
   update before the stale version does harm.)
4. **MinLaw — self-represented persons at the Small Claims Tribunals.** SRPs already use public
   GenAI to prepare claims and get misled. Build interactive guidance (system prompt, plug-in
   or custom assistant) for pre-filing and case prep: navigate SCT process, organise the claim,
   fight hallucination and confirmation bias, follow the Courts' Guide on the Use of Generative
   AI Tools by Court Users.

Organisers push a focused, achievable scope over covering the whole statement.
No real client documents. Public/synthetic only.

## Judging criteria
| Weight | Criterion | What they look for |
|---|---|---|
| 30% | Technical feasibility | It works, could be built further, code quality, use of AI tools, **team can explain their own build** |
| 25% | Relevance to problem statement | Solves a real, well-understood pain in that area of legal practice |
| 25% | Innovation | Genuinely new, or meaningfully better than existing |
| 20% | Presentation quality | Clear, structured, convincing in 4 min; handled Q&A |

## Rules that bind the build
- Address **one** problem statement only. Breaching scope is a disqualification example.
- AI coding tools allowed and expected. **Must disclose which tools were used** and explain every design decision.
- Pre-written code, templates and datasets prepared before the event are allowed.
- Open-source libraries, public APIs, organiser datasets allowed. **Must cite references.**
- Work must be original. Organiser data is confidential, event use only.
- Team names in English.

## Submission
- One person per team signs up at https://smu-lit-hackathon-2026.devpost.com/
- Create the project, link the GitHub repo, add product screenshots.
- Submit GitHub link + slide deck by 6 Sep 1200. Demo recording optional and eats into the 4 min.

## Suggested data (from PS1, usable anywhere)
Singapore Statutes Online (sso.agc.gov.sg), Singapore Law Watch, MOM/IRAS/ACRA/PDPC guidelines,
SAL public resources. Contract corpora: CUAD, LegalBench, SEC EDGAR material contracts, YC SAFE set.

## Resources
- API credits: telegram @tauporky with team name, team number, own name. They send the API key.
- OpenRouter guide and AI tools guide on the Notion hub.

## Submission checklist
- [ ] Chosen track challenge (PS4) submitted on the Google Form (5 Sep 1800)
- [ ] Working demo
- [ ] Slide deck
- [ ] GitHub repo public + screenshots on Devpost
- [ ] AI tool disclosure slide
- [ ] Citations for libraries/APIs/datasets
