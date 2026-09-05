# Tech approach research: evidence-to-case-theory app (Singapore small claims)

Researched 2026-09-05. Sources are official docs and GitHub unless marked otherwise.

---

## 1. Claude API citations, PDF/image input, models, pricing

### Enabling citations

Doc: https://platform.claude.com/docs/en/build-with-claude/citations

Set `citations: {enabled: true}` on each `document` content block (must be all-or-none across a request). Three document source types:

| Type | Source `type` | Chunking | Citation format |
|---|---|---|---|
| Plain text | `text` (or `file` file_id) | sentence | `char_location`, 0-indexed, exclusive end |
| PDF | `base64` / `url` / `file` | sentence (text extracted per PDF support) | `page_location`, 1-indexed, exclusive end |
| Custom content | `content` (list of your own blocks) | none — you control granularity | `content_block_location`, 0-indexed, exclusive end |

Request shape (plain text example):
```json
{
  "model": "claude-opus-5",
  "max_tokens": 1024,
  "messages": [{
    "role": "user",
    "content": [
      {
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": "The grass is green. The sky is blue."},
        "title": "My Document",
        "context": "This is a trustworthy document.",
        "citations": {"enabled": true}
      },
      {"type": "text", "text": "What color is the grass and sky?"}
    ]
  }]
}
```

PDF (base64) swaps the source for `{"type": "base64", "media_type": "application/pdf", "data": "<b64>"}`; a `file_id` from the Files API also works for any of the three types.

For WhatsApp .txt export or any exhibit list, use **custom content documents** — put each message/line as its own `{"type": "text", "text": "..."}` block, so a citation resolves to an exact block (line) index rather than a fuzzy sentence chunk. This is the cleanest way to map a citation straight back to a WhatsApp line number.

### Response shape

Response splits into multiple `text` blocks; only cited claims carry a `citations` array:
```json
{
  "content": [
    {"type": "text", "text": "According to the document, "},
    {
      "type": "text",
      "text": "the grass is green",
      "citations": [{
        "type": "char_location",
        "cited_text": "The grass is green.",
        "document_index": 0,
        "document_title": "Example Document",
        "start_char_index": 0,
        "end_char_index": 20
      }]
    }
  ]
}
```
PDF citation object: `{"type": "page_location", "cited_text": "...", "document_index": 0, "document_title": "...", "start_page_number": 1, "end_page_number": 2}` (page numbers 1-indexed, end exclusive).
Custom content citation object: `{"type": "content_block_location", ..., "start_block_index": 0, "end_block_index": 1}`.

Streaming: citations arrive as `citations_delta` inside `content_block_delta` events, one citation per delta.

Key notes:
- `cited_text` does not count toward output tokens (cost saving vs prompting Claude to quote).
- Citations are **incompatible with structured outputs** (`output_config.format`) — 400 error if both set on the same request. This matters for your evidence-matrix extraction: you cannot get citations AND a strict JSON schema in the same call. Practical fix: do extraction with structured outputs to get the fact list, then a **separate** citations-enabled call (or tool-use call) per fact to fetch its exact quote/location, or use tool-use (function calling) instead of `output_config.format`, since tool calls ARE compatible with citations (citations govern the source documents, tool_use is a different mechanism — confirm in your own testing since docs specifically call out `output_config.format`, not tool use).
- Image citations are not supported yet — only text/PDF documents are citable. Screenshots/photos cannot get citations; you'll need to have Claude describe/locate content in images via plain vision + prompted references (no exact-location guarantee).
- Scanned PDFs with no extractable text are not citable.

### Sending images (PNG/JPG)

Doc: https://platform.claude.com/docs/en/build-with-claude/vision

Content block: `{"type": "image", "source": {"type": "base64"|"url"|"file", "media_type": "image/png", "data": "..."}}`. Files API not required for a single hackathon-scale request — base64 is simplest.

Limits:
- Formats: JPEG, PNG, GIF, WebP.
- Size: 10 MB base64-encoded on the direct Claude API (5 MB on Bedrock/Vertex).
- Max dimensions 8000x8000 px; images >20 per request trigger a stricter per-image dimension cap (resize to ≤2000px per side to be safe, or keep ≤20 images/request).
- Up to 100 images per request for 200k-context models, 600 for others; claude.ai caps at 20/turn.
- No Files API required for one-off images; use it only if reusing the same image across many requests to cut payload size.

### PDF support

Doc: https://platform.claude.com/docs/en/build-with-claude/pdf-support

- Max request size 32 MB (whole payload, not just the PDF).
- Max pages: 600 (100 if model's context window is under 1M tokens).
- No password/encryption.
- Provide via base64, URL, or Files API `file_id`. Files API not required for a single hackathon PDF quotation upload — base64 is fine and simplest.
- Each page is converted to an image AND text-extracted; both go to the model. ~1,500–3,000 text tokens/page plus image tokens (same cost table as vision).

### Current models and pricing (per the claude-api skill, cached 2026-06-24 — verify against https://claude.com/pricing before final submission if judging on cost accuracy)

| Model | Model ID | Context | Input $/1M | Output $/1M |
|---|---|---|---|---|
| Claude Fable 5.1 | `claude-fable-5-1` | 1M | $10.00 | $50.00 |
| Claude Fable 5 | `claude-fable-5` | 1M | $10.00 | $50.00 |
| Claude Opus 5 | `claude-opus-5` | 1M | $5.00 | $25.00 |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | $5.00 | $25.00 |
| Claude Sonnet 5 | `claude-sonnet-5` | 1M | $2.00 | $10.00 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | $1.00 | $5.00 |

Recommendation for this hackathon build: **Claude Sonnet 5** (`claude-sonnet-5`) for extraction/citations calls — good balance of cost, speed and quality for structured extraction over short documents (quotations, chat exports); reserve Opus 5 only if extraction quality with Sonnet proves weak on the demo's actual documents.

---

## 2. Highlighting the source location in the browser

### PDFs — simplest working approach

There is **no built-in single API call** in pdf.js to "jump to page N and highlight exact quoted text" — this needs to be composed from two separate pieces (confirmed via GitHub issue https://github.com/mozilla/pdf.js/issues/9657, which is still open/unresolved for exact scroll-to-text-position):

1. **Page navigation**: trivial — pdf.js viewer supports the URL hash `#page=N`, e.g. `viewer.html?file=doc.pdf#page=3`.
2. **Text search + highlight**: pdf.js's built-in `PDFFindController` can be driven programmatically via its `eventBus`, dispatching a `find` event with `{query: "<quoted text>", phraseSearch: true, highlightAll: true}`. This highlights all matches of the string but you still have to combine it with the page jump (search will auto-scroll to the first match in newer pdf.js viewer builds). Reference approaches: https://medium.com/mesciusinc/how-to-find-and-highlight-text-in-pdf-using-javascript-a56ab7b95230, https://github.com/mozilla/pdf.js/issues/6307, https://dev.to/gabrielweidmann/multi-highlighting-in-pdfjs-403l

**Recommended hackathon shortcut**: since you already have Claude's `cited_text` (the exact quoted string) and `page_location` (page number) from the citations API, you don't need pixel-perfect highlight boxes. Do:
- Embed pdf.js's stock viewer (or `<iframe>` to `pdf.js/web/viewer.html?file=...`) and set `#page=<start_page_number>` on the iframe src/hash to jump to the right page.
- Fire the viewer's find controller (via `eventBus.dispatch('find', {query: cited_text, highlightAll: true, phraseSearch: true})`) once the viewer's `documentloaded` event fires, to highlight the exact cited sentence on that page.
This gives "click citation → jump to page → highlighted quote" without writing a custom text layer.

**Higher-fidelity alternative**: `react-pdf-highlighter` (built on pdf.js, React components for text/rect highlights, viewport-independent highlight storage) — https://github.com/agentcooper/react-pdf-highlighter. More setup than needed for a demo; only reach for it if the pdf.js `find` approach isn't visually convincing in the time available. Forks with more features exist: `react-pdf-highlighter-extended` (https://github.com/DanielArnould/react-pdf-highlighter-extended), `react-pdf-highlighter-plus` (https://github.com/QuocVietHa08/react-pdf-highlighter-plus).

### WhatsApp .txt — no PDF machinery needed

Export line format (confirmed via web search of export guides): each line is `<date>, <time> - <Sender Name>: <message>`, e.g.
```
12/30/24, 10:42 AM - Jane: Hey, are you free this weekend?
12/30/24, 10:45 AM - You: Yes!
```
- Date format follows the exporting phone's locale (not the computer's) — don't assume a fixed date format.
- iOS and Android produce the same line shape.
- Multi-line messages continue without a new `date, time - sender:` prefix — a naive line-by-line parser must detect "does this line start with a date-time-dash pattern" to know where a message starts vs continues.
- Media/system lines have no sender (e.g. "Messages and calls are end-to-end encrypted").

Because you control the chunking, the simplest robust approach for citing WhatsApp text is: parse the file into one message per line index yourself, feed it to Claude as a **custom content document** (one block per message), and the citation's `start_block_index`/`end_block_index` IS the message index — trivial to highlight (scroll list to that index, highlight that row). No PDF viewer complexity at all for this evidence type.

Parser library: **whatstk** (Python, pandas-based) — https://github.com/lucasrodes/whatstk — `df_from_whatsapp("chat.txt")` returns a DataFrame with date, sender, message columns; handles multiple date/locale formats and multi-line messages. GPL-3.0 licensed (check compatibility with your intended license before shipping). For a hackathon, given license and the fact citations need block-index control anyway, a small hand-rolled regex parser (split on a `^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}\s?(?:AM|PM)? - ` pattern) may be less risk than pulling in a GPL dependency — your call depending on time left.

---

## 3. Structured extraction via tool use

Pattern (from the claude-api skill / Anthropic tool-use docs): define a tool whose `input_schema` is the shape you want (facts array, each with date/parties/amount/source id/quote), set `strict: true` for guaranteed schema-valid output, and either force it via `tool_choice: {"type": "tool", "name": "extract_facts"}` (note: forced tool_choice is rejected — 400 — on Claude Fable 5.1/Mythos 5.1 only; fine on Sonnet 5/Opus 5) or use `tool_choice: "auto"` plus an explicit instruction.

Example tool definition:
```json
{
  "name": "record_facts",
  "description": "Record structured facts extracted from the evidence document, each with its exact source quote.",
  "input_schema": {
    "type": "object",
    "properties": {
      "facts": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "fact": {"type": "string"},
            "date": {"type": "string"},
            "parties": {"type": "array", "items": {"type": "string"}},
            "amount": {"type": "number"},
            "source_id": {"type": "string", "description": "document_index or id of the source evidence"},
            "quote": {"type": "string", "description": "exact quoted text supporting this fact"},
            "strength": {"type": "string", "enum": ["strong", "weak"]}
          },
          "required": ["fact", "source_id", "quote", "strength"],
          "additionalProperties": false
        }
      }
    },
    "required": ["facts"],
    "additionalProperties": false
  },
  "strict": true
}
```
Because citations and `output_config.format`/strict structured-outputs interact awkwardly with each other in some combos, the safe hackathon pattern is:
1. Send the document(s) with `citations.enabled: true` and ask Claude in plain language to make each fact claim (using citations for exact-location backing).
2. Separately (or in the same turn using tool use, not `output_config.format`), also call a tool to emit the structured `facts` array, having Claude copy the `cited_text`/location it just produced into the tool call's `quote`/`source_id` fields.
Test early whether tool_use + citations can coexist in one turn — the documented incompatibility is specifically with `output_config.format`, not with tool definitions, but this should be verified against your actual SDK version before relying on it for the demo.

---

## 4. Retrieval for ~40 statute sections + guides

Recommendation for a hackathon with this small a corpus: **SQLite FTS5**, not embeddings, not `rank_bm25`.

Why: FTS5 ships built into Python's stdlib `sqlite3` module (no extra dependency to install), supports a real inverted index with built-in BM25 ranking out of the box, and is more than sufficient at 40 documents — you don't need vector search's semantic fuzziness for statute lookup where users/queries will often share vocabulary with the statute text. `rank_bm25` (pure-Python, pip-installable) is a fine fallback if FTS5's SQL syntax is unfamiliar, but it's one more dependency for no real benefit at this corpus size, and FTS5's ranking column comes for free.

Key facts from research:
- FTS5 is a virtual table type in SQLite, ships by default, maintains an inverted index, ranks with BM25 automatically via a hidden `rank` column (lower = better match) — https://www.geeksforgeeks.org/sqlite/sqlite-full-text-search/, https://coddy.tech/docs/sqlite/full-text-search
- Basic usage: `CREATE VIRTUAL TABLE statutes USING fts5(section_id, title, text); SELECT section_id, title, text, rank FROM statutes WHERE statutes MATCH 'quotation OR estimate' ORDER BY rank;`
- If you want a semantic (embeddings) layer later, Voyage AI is Anthropic's recommended embeddings partner, but it adds an API key, cost, and infra you don't need to prove the demo at 40 sections. Skip it unless FTS5 keyword search visibly fails on a demo query.

---

## 5. Timeline UI

**vis-timeline** (part of the vis.js family) — https://github.com/visjs/vis-timeline — "Create a fully customizable, interactive timeline and 2D-graphs with items and ranges." CDN: `https://unpkg.com/vis-timeline@latest/dist/vis-timeline-graph2d.min.js`. Drop-in `<div>` + a JS array of `{id, content, start, group}` items; built-in zoom/pan; no build step needed for a plain-HTML front end. This is the lightest path to a working timeline widget without hand-rolling one.

If the whole front end is meant to be genuinely minimal (plain HTML/CSS only, no JS charting lib at all), a manual CSS flexbox/grid timeline (styled `<ol>` of date-stamped cards) is also viable and one less dependency — reasonable if the demo only needs to show ~10-20 events, not pan/zoom interactivity.

---

## 6. Existing open-source projects to borrow patterns from

- **FactBinder** — https://www.factbinder.com/ (product, not open source; found via https://www.factbinder.com/blog/organise-evidence-landlord-dispute and https://www.factbinder.com/blog/organise-whatsapp-messages-court). Directly does what this hackathon app does: accepts WhatsApp exports, email threads, PDFs, and voice transcripts; AI extracts facts into a prioritized timeline (Critical/Important/Contextual); outputs a "court-ready brief" with source references. This is your closest competitor/reference for scope and feature framing, not a codebase to copy from since it's closed-source.
- GitHub topic **evidence-management** (https://github.com/topics/evidence-management) surfaces an offline-first, end-to-end-encrypted "habitability evidence" tool for tenant unions with RFC 3161 timestamps and hash-linked chain of custody (project explicitly flagged by its own README as not yet ready for real legal reliance) — relevant for chain-of-custody/tamper-evidence ideas if judges care about evidentiary integrity, but not for UI/extraction patterns.
- No single well-known open-source "evidence → timeline → case theory for litigants" reference implementation (e.g. no DoNotPay-equivalent open-sourced) turned up in search; the closest analogues are closed-source products (FactBinder) or narrowly-scoped tenant evidence-locker tools. Treat this space as open for you to define rather than one with an established pattern to copy.

---

## Open questions / things to verify with a live API key before the demo

1. Whether tool_use (function calling) can run in the **same** request as `citations.enabled: true` on the documents (docs only state the incompatibility is with `output_config.format` structured outputs, not tool use — but confirm empirically).
2. Whether pdf.js's `find` eventBus call reliably highlights AND scrolls in whatever pdf.js build/version you vendor (behaviour has shifted across pdf.js versions per the GitHub issues found).
3. whatstk's licence (GPL-3.0) — check before bundling if the hackathon's distribution rules care about licence contamination; the fallback is a ~20-line regex parser you own outright.
