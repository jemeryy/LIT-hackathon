# Session Handoff — Case Helper chat flow, evidence relevance, removal, and deployment

## Where it started
The user asked to fix evidence ranking so files uploaded under both sides were handled consistently, irrelevant evidence stayed visible without receiving a rank, and placeholder media was not treated as real evidence. The work expanded to intake-chat correctness, broken local loading, deployment, an explanation of AI boundaries, and a new option to remove visitor-uploaded files.

## Important discoveries and decisions
- The previous ranking path only ranked extracted facts with an `evidence_key`, while unrelated files under the other-side section could inherit hypothetical answer strength. Actual uploaded facts and answer-only possibilities now follow separate paths.
- Relevance and strength are distinct. AI proposes facts and file relevance; deterministic rules validate the result, decide the displayed relevance state, calculate strength, and assign numeric rank only to relevant evidence.
- Empty extraction is not proof that a file is irrelevant. It is `needs_review` unless there is an explicit mismatch. Related background is `context`, and synthetic media labelled as a placeholder is `placeholder`.
- The worked-example WhatsApp images contain related context. Its synthetic move-in photos and move-out video are placeholders and cannot establish actual condition.
- The intake model extracts fields, but the server owns progression. It tracks the exact unanswered field, handles short yes/no replies, validates corrections and data types, and prevents refresh or request failures from losing conversation state.
- AI is used for intake fact extraction, reading unstructured evidence, proposing relevance, and drafting the story, 500-character summary, and written request. Gate checks, evidence strength/rank, gaps, timeline, deadlines, fees, exports, and quote verification are deterministic.
- Railway has no persistent volume. Deployment `f1758432-f5d1-4b17-9cf2-573527d9e747` replaced the container and did not retain prior cases/uploads after the user explicitly approved deploying without a backup.

## Decisions locked + what shipped
- Chat progression and evidence-relevance fixes were committed and pushed in `78f2a19`, then merged with the contributor's newer address-handling changes in `54a0169` on `main`.
- Commit `54a0169` is deployed successfully at `https://case-helper-production.up.railway.app/?example=1`. The production synthetic example returned four ranked rows, four contextual files, six placeholders, and assessment schema version 2.
- Current local, uncommitted work adds `POST /api/upload/remove`, marks only current-visitor uploads as removable, deletes their extracted facts and ranking/timeline effects, removes stored bytes and extraction cache, and forbids deletion of bundled files. It lives in `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` and `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html`.
- Current local, uncommitted work changes every user-facing instance of “Assessment”/“assessed” to “Relevance”/“checked for relevance”. Internal saved-case keys such as `assessment` and `_assessment_version` deliberately remain unchanged for compatibility.
- The removal option appears on uploaded-file cards and in the file preview. It requires confirmation and recalculates the case after removal. Bundled worked-example files do not show the option.
- New removal coverage is in `C:\Users\jemer\code\hackathon\builds\case-builder\test_upload_removal.py`; UI removal and wording checks are in `C:\Users\jemer\code\hackathon\builds\case-builder\test_chat_ui.cjs`.

## Key files for next session
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — intake controller, upload/read/remove endpoints, saved-case migration, relevance payloads, and server validation.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — complete UI, including chat recovery, evidence cards, removal controls, relevance tables, and preview.
- `C:\Users\jemer\code\hackathon\builds\case-builder\rules.py` — deterministic relevance interpretation, evidence strength/ranking, gaps, blind spots, timeline, fees, and next steps.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — intake/file-reader schemas, prompts, fixture mode, and text drafting.
- `C:\Users\jemer\code\hackathon\builds\case-builder\content\fixtures.json` — saved worked-example facts and relevance results.
- `C:\Users\jemer\code\hackathon\builds\case-builder\test_chat_flow.py` — server-owned intake progression regressions.
- `C:\Users\jemer\code\hackathon\builds\case-builder\test_relevance.py` — relevance, ranking, context, placeholder, and export regressions.
- `C:\Users\jemer\code\hackathon\builds\case-builder\test_upload_removal.py` — upload ownership and deletion regressions.
- `C:\Users\jemer\code\hackathon\builds\case-builder\test_chat_ui.cjs` — browser-state, removal-control, and relevance-wording regressions.
- Plan file: none.
- Memory files touched: none.

## Running state
- Background processes: PID 3648 is a Python/Uvicorn preview process. Stop it with `Stop-Process -Id 3648`.
- Dev servers / ports: `http://127.0.0.1:8010/?example=1` is listening on port 8010, but it was started before the latest uncommitted removal changes and must be restarted to show them.
- Open worktrees / branches: main worktree `C:\Users\jemer\code\hackathon` is on `main` at `54a0169`; detached deployment worktree `C:\Users\jemer\code\hackathon\.tmp\deploy-54a0169` is also at `54a0169`.
- Git stash: `stash@{0}` preserves a pre-merge local runtime-log change. Do not commit the runtime log. The unrelated untracked paths `C:\Users\jemer\code\hackathon\deck\render` and `C:\Users\jemer\code\hackathon\test docs` must remain untouched.

## Verification — how to confirm things still work
- `python -m unittest test_chat_flow.py test_relevance.py test_upload_removal.py` from `C:\Users\jemer\code\hackathon\builds\case-builder` — expected: 30 tests, OK.
- `node C:\Users\jemer\code\hackathon\builds\case-builder\test_chat_ui.cjs` — expected: chat UI and ranking UI checks pass, including removable versus bundled cards and the removal request.
- `python selfcheck.py` from `C:\Users\jemer\code\hackathon\builds\case-builder` — expected: `selfcheck ok` with ranked keys `deposit_terms`, `deposit_paid`, `handover_acceptance`, and `damage_allegation`.
- `git diff --check` from `C:\Users\jemer\code\hackathon` — expected: no errors; Git may print LF-to-CRLF warnings.
- Production `https://case-helper-production.up.railway.app/?example=1` — currently serves deployed commit `54a0169`; removal controls and renamed Relevance headers are not deployed yet.

## Deferred / pending tasks + open questions
- Deferred/pending: review, commit, push, and deploy the current upload-removal and Relevance-wording changes — project rules require Jeremy's explicit shipping instruction in the next session.
- Deferred/pending: attach a persistent Railway volume if production cases/uploads need to survive future deployments — the current service has none.
- Deferred/pending: decide whether to remove the detached deployment worktree after it is no longer useful.
- Open: should the current local upload-removal and Relevance changes be pushed and deployed?

## Plan
- No plan file was created for this work.
- Overarching plan: preserve the current uncommitted source changes, rerun the three verification commands, inspect the targeted diff, commit only Case Helper source/tests, integrate any newer remote work without overwriting it, then push and deploy only after explicit approval. Smoke-test removal using a fresh visitor session so no user case is altered.

## Next steps
Review the uncommitted removal/relevance diff and run the listed tests. If Jeremy explicitly says to ship, commit only the seven Case Helper files currently changed plus `test_upload_removal.py`, pull/integrate remote `main` safely, push, deploy the exact commit to the existing Railway service, and verify the live UI and removal endpoint with a fresh session.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-06-case-helper-relevance-removal.md, then review and ship the pending upload-removal and Relevance changes only after Jeremy's explicit instruction.
