# FARA pieces worth reusing (explored 5 Sep 2026)

Repo: C:\Users\jemer\code\fara. Paths below are relative to it.

## Top 4 to copy
1. `business/fara/tools/doc_extract.py` — `extract_document` (L134), `_extract_pdf` (L247, pdfplumber). Returns per page: page, width, height, words with bbox, text. Locators: `_locator_for_match` (L923), `_locator_in_page` (L998), `locate_text_in_ocr_pages` (L1055). Keep `_PDF_WORD_SPACING` fix. This is the evidence-doc to cited-fact-with-page-and-bbox layer.
2. `business/fara/webapp/backend/prose_citations.py` — `verify_prose_citations` (L284) / `verify_detailed` (L298). Pure, no I/O. Scans `[[N]]` markers, checks each against the chunk it claims, deletes markers that fail. Copy as is.
3. Fact-sheet leaf shape `{value, quote, page, confidence}` with top-level `source_title, source_publisher, source_url, retrieved_date`. Use it for statute sections and for extracted facts.
4. `business/fara/webapp/frontend/index.html` — `renderCitationsHtml` (L10224), ~80 lines plus `.chip` CSS. Click citation opens source.

## Also useful
- Chunker `_split_chunks` (kb_index.py L295) and `_split_chunk_ranges` (L264), chunk metadata `_metadata_for` (L371).
- Retrieval `kb_query.py` `KBRetriever` (L562): dense (Chroma, OpenAI text-embedding-3-small) + BM25 (`rank_bm25`), RRF fusion `_retrieve_fused` (L956), `low_confidence` gate drives refusal.
- Prompt contract `prompt.py`: `render_context_block` (L383) numbers chunks `[1] Title (Publisher page N) - URL`; system prompt forces `[[N]]` as the only citation token; `REFUSAL_MARKER` (L84).
- `mcp_connector.py` `_search_contract` (~L675): 5-6 numbered rules, answer only from numbered sources, every figure carries title and URL, exact refusal string.
- `anthropic_client.py`: `stream_with_tools` (L846), `_system_param` (L316) prompt caching. MODEL_ID `claude-sonnet-4-6` (check claude-api skill for current IDs).
- `kb_fetch.py` `_normalize_agc_version_stamp` (L193): SSO stamps pages with "Current version as at <date>"; normalise before hashing. `sso.agc.gov.sg` already in allowlist (L28).
- `doc_ocr.py` (pytesseract) and `doc_vision.py` (Claude vision) for images. Confidence rule: vision-read numbers never auto-accept (`VISION_SCAN_MAX_CONFIDENCE = 0.6`).

## Skip for 24h
Budget ledger, raw httpx transport fallback, freshness/cadence machinery, spacy, playwright fetch, MCP, entailment shadow judge.

## Hackathon requirements subset
`anthropic openai chromadb pdfplumber rank_bm25 fastapi uvicorn python-multipart httpx beautifulsoup4 PyYAML python-dotenv` (real list at `business/fara/requirements.txt`).
