# Legal data sources for an SCT self-represented-person assistant

Research date: 2026-09-05. All URLs tested live on this date unless noted.

---

## 1. Singapore Statutes Online (SSO) — how to fetch programmatically

**No public API.** SSO (sso.agc.gov.sg) is an Angular single-page app. Confirmed by testing:

- `robots.txt` (https://sso.agc.gov.sg/robots.txt): only `disallow: /search`, `crawl-delay: 6`. Act/section pages are NOT disallowed.
- A direct `curl`/`WebFetch` GET of an Act page (e.g. `https://sso.agc.gov.sg/Act/SCTA1984?ProvIds=P1`) returns HTTP 200 but the HTML is just the app shell — the section text is injected client-side and was NOT present in the raw HTML (confirmed: `grep` for known section headings found nothing in the raw fetched HTML, and Playwright's `document.body.innerText` was empty until further JS ran that never fully populated the on-page reader view in a scriptable way).
- WebFetch tool with default UA got a plain 403 (likely blocked as an obvious bot UA / no cookies). Plain `curl` with a standard Chrome user-agent string got HTTP 200 fine on the same URL — so the 403 is a UA/header check, not a hard IP block.

**What works reliably: the PDF download link.** Every Act page has a PDF download button whose href is:

```
https://sso.agc.gov.sg/Act/<ActCode>?ViewType=Pdf
```

e.g. `https://sso.agc.gov.sg/Act/SCTA1984?ViewType=Pdf`. Tested with plain `curl -A "<chrome UA>"`: HTTP 200, `content-type: application/pdf`, no cookies/session needed, no JS needed. Also works for historical/dated versions:
`https://sso.agc.gov.sg/Act/<ActCode>/Historical/<date>?DocDate=...&ValidDate=...&ViewType=Pdf` and for subsidiary legislation under `/SL/<Code>?ViewType=Pdf` (confirmed on Small Claims Tribunals Rules, code `SCTA1984-R1`).

Text extraction from the PDF is clean: used `pypdf` (`PdfReader(...).extract_text()`) on the downloaded PDF and got well-formed section text with section numbers, headings, and paragraph lettering intact (tested on Small Claims Tribunals Act 1984 — full text of s 4 and s 5 came back correctly, including cross-references like "under section 19(1)"). Minor artefact: OCR/kerning splits some words with a stray space or non-breaking space in the middle of a word (e.g. "T ribunal" for "Tribunal", "V ariation" for "Variation") — a simple regex cleanup (`re.sub(r'(?<=[a-z]) (?=[a-z])', '', text)` applied carefully, or a small known-word-fix list) is needed before using the text for RAG chunking/embedding.

**Recommended fetch pattern for the hackathon corpus:**
1. `curl -A "<browser UA>" "https://sso.agc.gov.sg/Act/<CODE>?ViewType=Pdf" -o <code>.pdf` (one request per Act, respect the 6-second crawl-delay between requests).
2. Extract text with `pypdf` in Python.
3. Clean the split-word artefact.
4. Chunk by section number (section headings are on their own line before the number, e.g. "Jurisdiction of tribunal\n5.—(1) ...").

There is also a **Print view** (`?ViewType=Print&ProvIds=P1`) that lets a human select provisions and print to HTML/PDF/Word, but it requires interactive checkbox selection in the browser — not useful for unattended scraping. The PDF-download link is simpler and sufficient.

A third-party MCP connector "sg-eli-mcp" / "Singapore Statutes Online" was found referenced (mcpmarket.com listing) claiming to programmatically fetch SSO content respecting robots.txt, but it was not tested here — the direct PDF-download method above is simpler and needs no extra tooling.

**Legal note found on SSO itself:** SSO explicitly states it "does not contain the authoritative text of Singapore legislation but consolidates and reproduces an unofficial version for the convenience of the general public" — worth a disclaimer line in the demo.

Terms of Use / Privacy Statement links exist in the page footer (`https://sso.agc.gov.sg/Terms-of-Use`, not separately fetched here) — check before any commercial reuse; for a hackathon demo citing/quoting statute sections with attribution is standard practice.

---

## 2. Statutes relevant to SCT claims — URLs, codes, and key sections

All confirmed live and PDF-downloadable via `https://sso.agc.gov.sg/Act/<CODE>?ViewType=Pdf` (or `/SL/<CODE>?ViewType=Pdf` for the Rules), tested 2026-09-05.

### Small Claims Tribunals Act 1984 — code `SCTA1984`
URL: https://sso.agc.gov.sg/Act/SCTA1984
- **s 4** — Tribunal magistrates: who presides (District Judge/Magistrate designated by Presiding Judge of the State Courts, or a qualified person appointed by the President).
- **s 5** — Jurisdiction of tribunal: a tribunal may only hear a claim that is a "specified claim" (listed in the Schedule) AND was served on the respondent in Singapore; excludes motor-vehicle accident property damage claims and anything the State Courts have no jurisdiction over. (Full text extracted and verified.)
- **s 2** — Interpretation: defines "prescribed limit" = $20,000 and "prescribed extended limit" = $30,000 (the claim-value caps), "work order," "claimant," "respondent."
- **The Schedule** — "Specified claims": lists exactly which claim types SCT can hear (contract for sale of goods, contract for services, tort for damage to property up to the limit, certain tenancy disputes, etc.) — this is the single most important pinpoint reference for "can SCT even hear my case."

### Small Claims Tribunals Rules — code `SCTA1984-R1` (subsidiary legislation, path `/SL/` not `/Act/`)
URL: https://sso.agc.gov.sg/SL/SCTA1984-R1
- Procedural rules: how to file, forms, consultation/hearing procedure, time limits for responding. (PDF downloaded, 144 KB; not deep-read for individual rule numbers in this pass — flagged for a follow-up fetch if the build needs specific rule citations.)

### Consumer Protection (Fair Trading) Act 2003 — code `CPFTA2003`
URL: https://sso.agc.gov.sg/Act/CPFTA2003
- **s 4** — Meaning of "unfair practice": deceiving/misleading, making a false claim, taking advantage of a consumer who can't protect their own interests, or anything listed in the Second Schedule. (Full text extracted and verified.)
- **s 6** — Consumer's right to sue for unfair practice (civil redress route).
- **s 12** — Limitation period for unfair-practice claims.
- **Part 3 (ss 13–18) — "Lemon Law"**: additional consumer rights for non-conforming goods — right to repair/replacement (s 15), reduction in price or rescission (s 16), for goods that don't conform to contract within 6 months of delivery (statutory presumption of non-conformity at time of delivery).
- **s 35** — No contracting out: a supplier cannot exclude these rights by contract term.

### Sale of Goods Act 1979 — code `SGA1979`
URL: https://sso.agc.gov.sg/Act/SGA1979
- **s 13** — Sale by description: goods must correspond with description.
- **s 14** — Implied terms about quality or fitness: goods sold in the course of business must be of "satisfactory quality" (defined: fitness for common purposes, appearance/finish, freedom from minor defects, safety, durability) and, if the buyer made known a particular purpose, reasonably fit for that purpose. (Full text extracted and verified — this is the core "the thing I bought is faulty" section.)
- **s 15** — Sale by sample.
- **s 35** — Acceptance: when a buyer is deemed to have accepted goods (relevant to how long you have to reject faulty goods).

### Supply of Goods Act 1982 — code `SGA1982`
URL: https://sso.agc.gov.sg/Act/SGA1982
- Mirrors Sale of Goods Act implied terms but for contracts that are NOT a sale of goods (e.g. hire of goods, or transfer of goods bundled with services — like a renovation contract that also supplies materials).
- **s 2** — Implied terms about title for a contract to transfer property in goods.
- **s 4** — Implied terms about quality or fitness (the "hire/non-sale" equivalent of SGA s 14).
- **s 7 / s 9** — Same implied terms but for contracts of hire.
- **Note:** Part 2 (ss 12–16, "supply of services") is explicitly marked "not applicable" in Singapore — services quality is instead governed by common law / the contract itself, not this Act.

### Contracts (Rights of Third Parties) Act 2001 — code `CRTPA2001`
URL: https://sso.agc.gov.sg/Act/CRTPA2001
- **s 2** — Right of a third party (not one of the contracting parties) to enforce a contract term if the contract expressly allows it or the term purports to benefit them by name/class/description. Relevant when e.g. a family member benefits from a contract but wasn't the signing party.
- **s 1(2)–(3)** — Only applies to contracts made after 1 Jan 2002 (or 6 months after, unless the contract expressly opts in).

### Limitation Act 1959 — code `LA1959`
URL: https://sso.agc.gov.sg/Act/LA1959
- **s 6** — Limitation of actions of contract and tort: 6 years from when the cause of action accrued (the standard "how long do I have to sue" answer for most consumer/contract claims). (Full text extracted and verified.)
- **s 24** — Extension of limitation period in case of disability (e.g. claimant was a minor or of unsound mind).
- **s 4** — Limitation is a defence that must be specially pleaded (i.e. it doesn't automatically bar the claim unless the other side raises it).

### Frustrated Contracts Act 1959 — code `FCA1959`
URL: https://sso.agc.gov.sg/Act/FCA1959
- **s 2** — Adjustment of rights when a contract becomes impossible/frustrated: money already paid is generally recoverable (subject to deduction for expenses the payee incurred), and a party who got a "valuable benefit" (not money) before discharge may have to pay a just sum for it. Whole Act is short (only 3 sections). (Full text extracted and verified.)

### Misrepresentation Act 1967 — code `MA1967`
URL: https://sso.agc.gov.sg/Act/MA1967
- **s 1** — Removes old bars to rescinding a contract for innocent misrepresentation even if the misrepresentation became a contract term or the contract was performed.
- **s 2** — Damages for misrepresentation: if the misrepresentation would have been fraudulent-level liability, the maker is liable for damages unless they can prove they reasonably believed the statement was true (i.e. burden shifts to the seller/supplier).
- Whole Act is very short (5 sections). (Full text extracted and verified.)

### Unfair Contract Terms Act 1977 — code `UCTA1977`
URL: https://sso.agc.gov.sg/Act/UCTA1977
- **s 2** — Cannot exclude liability for negligence causing death/injury; other negligence-caused loss can only be excluded if the term is "reasonable."
- **s 3** — Liability arising in contract: restricts a business's ability to exclude/limit liability for its own breach when dealing with a consumer or on its own written standard terms.
- **s 6** — Sale and hire-purchase: cannot exclude the SGA implied terms (title, description, quality/fitness, sample) against a consumer at all; against a business, only if reasonable.
- **s 11 / s 12** — Defines the "reasonableness" test and "dealing as consumer."

---

## 3. Case law — where SCT-related decisions are public

- **eLitigation (elitigation.sg)**: the official platform of the Singapore Courts. `https://www.elitigation.sg/gd/Home/Index` provides free public search of judgments (Supreme Court, State Courts, etc.). Confirmed via search results that eLitigation is described as providing free public access including Small Claims Tribunals-related decisions (typically these surface as **District Court judgments on SCT appeals**, since SCT orders themselves are usually short and not separately published — the appeal to the District Court is what generates a reasoned, citable judgment). Example format: `https://www.elitigation.sg/gd/s/2021_SGHC_174`.
- **judiciary.gov.sg**: the parent site — `https://www.judiciary.gov.sg/judgments` and `/judgments/judgments-case-summaries` host selected written judgments and case summaries; `https://www.judiciary.gov.sg/civil/appeal-small-claims-order` explains the SCT-appeal route (leave to appeal from the District Court, on a question of law or jurisdiction only).
- **Singapore Law Watch (singaporelawwatch.sg/Judgments)**: free daily legal news; its free judgments database covers Supreme Court (2000–present), IPOS (2018–present), and PDPC (2018–present) — **does NOT include District Court or SCT-appeal judgments** for free (confirmed via search summary — not independently verified by direct fetch of the page, flagged as secondary-source confirmation only).
- **LawNet free resources** (`lawnet.sg/lawnet/web/lawnet/free-resources`): LawNet is normally a paid legal database (Singapore Academy of Law); it has a free-resources section but is unlikely to include full District Court/SCT judgments for free — not independently verified by direct fetch; treat as needing a follow-up check if the build wants to lean on it.
- **SG Case Law (sgcaselaw.com)**: a free, searchable third-party database — confirmed (via WebFetch of the homepage) to hold "2,012 Singapore court judgments from 15 courts (2023–2026)," sourced from eLitigation.sg (via CrimsonLogic). No stated API or bulk-download option.
- **Open datasets**: found `isaacus/singaporean-judicial-keywords` on Hugging Face — a dataset of Singapore court judgment catchwords/keywords extracted from publicly available judgments, licensed CC BY 4.0 (non-commercial and commercial use allowed with attribution). This is keywords/catchwords, not full judgment text — useful for classification/tagging, not for a full-text RAG corpus. No dedicated Singapore court-judgments dataset was found on data.gov.sg.
- **State Courts specifically**: no separate State Courts judgments portal was found distinct from eLitigation/judiciary.gov.sg — the State Courts' decisions (which include SCT appeals) are published through the same eLitigation/judiciary.gov.sg channel.

**Bottom line for the hackathon**: for real, citable case law text, eLitigation.sg (official, free, has a UI search) or sgcaselaw.com (free, third-party, same underlying source, might be easier to scrape) are the two live free options. Full-text bulk case law for RAG will likely need to be scraped page-by-page from one of these rather than downloaded as a dataset — not tested for scraping mechanics or robots.txt in this pass (time did not allow); flag as a follow-up if the build wants case law citations, not just statute citations.

---

## 4. Government/NGO consumer guidance pages

- **CASE (Consumers Association of Singapore), case.org.sg**:
  - `https://www.case.org.sg/consumer-guide/` — hub of consumer guide topics; the renovation-specific resource found here is a single infographic PDF: `https://www.case.org.sg/wp-content/uploads/2023/04/Renovation_contractor_infographic.pdf`.
  - `https://www.case.org.sg/cpfta-lemon-law/` — plain-English explainer of the CPFTA and the Lemon Law: covers what counts as an unfair practice (24 specified practices), and Lemon Law coverage (repair/replace/reduce price/rescind for defective goods, including second-hand goods and vehicles; excludes houses, land, rental goods, services; consumer loses protection if they damaged/misused the item, tried self-repair, were told about the fault beforehand, changed their mind, or it's normal wear and tear).
  - `https://www.case.org.sg/casetrust/renovation/` — CaseTrust accreditation scheme for renovation contractors; accredited firms must adopt the **CaseTrust Standard Renovation Contract**, a template found at `https://www.case.org.sg/casetrust/wp-content/uploads/2023/11/Info-Kit-Renovation-01-Nov-2023.pdf`, which mandates milestone-based progressive payments, itemised pricing, a 12-month workmanship warranty from completion, and mediation for disputes.
  - `https://www.case.org.sg/list/` — a public "alert list" of companies with complaint histories (e.g. named renovation contractors and a car-rental company with deposit-forfeiture complaints) — could be a useful "check before you sign" data point in the demo, but treat named-company content as reputational/sensitive and cite CASE directly rather than reproducing it verbatim.
  - `https://www.case.org.sg/submit-a-complaint/` — CASE's own complaint/mediation intake, an alternative/precursor to SCT.
- **Judiciary / State Courts (judiciary.gov.sg)**:
  - `https://www.judiciary.gov.sg/civil/small-claims` — overview: SCT jurisdiction cap is **$30,000** (confirmed against the Act's "prescribed extended limit"), covers goods/services/residential tenancy ≤ 2 years disputes; links out to filing, responding, outcomes, consultation prep, default orders (1 month to challenge), enforcement, and appeals sub-pages.
  - `https://www.judiciary.gov.sg/civil/file-small-claim`, `/civil/cases-eligible-small-claim`, `/civil/at-small-claims-consultation`, `/civil/appeal-small-claims-order` — step-specific self-help pages (titles found via search; not all individually fetched in this pass).
  - `https://www.judiciary.gov.sg/services/cjts` and `https://cjts.judiciary.gov.sg/` — the **Community Justice and Tribunals System (CJTS)**, the online e-filing platform covering SCT, Employment Claims Tribunals, Community Disputes Resolution Tribunals, and the Protection from Harassment Court. This is where a claimant actually files online.
- **Ministry of Law**: not separately fetched in this pass — judiciary.gov.sg appears to be the primary operational site for SCT; a follow-up search of mlaw.gov.sg may find higher-level consumer-protection policy pages if needed.

---

## 5. Existing Singapore government tools in this space (competitive landscape)

This is the most important finding for judging comparison:

- **The Singapore Judiciary already has a generative-AI case-summarisation tool for SCT, built with Harvey.AI.** Confirmed via judiciary.gov.sg media release (fetched 2026-09-05):
  - Initial MOU with Harvey.AI: August 2023; renewed/expanded MOU: 8 September 2025.
  - What it does: generates plain-language summaries of case documents (including messy evidence like WhatsApp chats and emails) for **both** tribunal magistrates and self-represented parties — "clear and easy-to-read summaries of the case presented by both the claimant and the respondent," covering facts, evidence, and the legal issues in contention.
  - Explicit limit stated by the Judiciary: it is "carefully designed to provide factual summaries without offering case-specific legal advice" — it does not tell a party what the law says or what their odds are, and does not replace legal counsel or the magistrate's decision.
  - Rollout: tribunal magistrates got it first (September 2025); self-represented individuals were slated to get access from November 2025 onward.
  - A companion translation feature (Chinese/Malay/Tamil, via QR code on the Notice of Consultation/Claim Form) launched December 2024.
  - Source: judiciary.gov.sg media release "New Generative AI-powered Case Summarisation Tool to Help Small Claims Tribunals Users"; also covered by Mothership.SG ("Making small claims at S'pore State Courts: New gen AI-powered case-summarisation tool now in use," Dec 2025).
- **GovTech's "Pair"** (`pair.gov.sg`, `tech.gov.sg` product page): a general-purpose generative AI assistant for **public officers** (drafting, research, ideation) — not consumer/public-facing, not SCT-specific. Not a competitor for a public-facing SCT assistant.
- **CJTS** itself is a filing/case-management system, not an advice or explanation tool — it doesn't interpret the law for the user, it just moves the paperwork.
- **Community Justice Centre (CJC)** (`ww3.cjc.org.sg`): a human-staffed service (volunteers/pro bono lawyers) helping litigants-in-person; no chatbot/AI tool found for it in this search.
- No evidence found of a "LawNet GPT-Legal" or equivalent public tool aimed at consumers; LawNet's tools are aimed at legal professionals.

**Implication for positioning the hackathon build**: the Judiciary's own tool summarises the specific case documents already filed (it works on your own claim/response, and explicitly avoids legal advice). A build that instead helps someone **before or while drafting a claim** — explaining which statute/section applies, whether SCT even has jurisdiction over their claim type and value, and what remedy to ask for — sits in a different, currently-unfilled slot: general legal orientation and claim-drafting help, not case-document summarisation. That is the gap to point at when pitching against what already exists.

---

## Files referenced / downloaded during this research (local, for the build)
PDFs of the following Acts were downloaded and text-extracted to confirm the fetch method works (saved under the OS temp dir used during this session, not committed to the repo — re-download at build time using the URLs above):
SCTA1984, SCTA1984-R1 (Rules), CPFTA2003, SGA1979, SGA1982, CRTPA2001, LA1959, FCA1959, MA1967, UCTA1977.
