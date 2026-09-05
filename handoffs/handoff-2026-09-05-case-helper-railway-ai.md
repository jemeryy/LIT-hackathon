# Session Handoff — Case Helper deployed with live AI, broad uploads, and GitHub collaboration

## Where it started
Jeremy asked to continue from the layman-UI handoff, remove the in-app example button, put the worked example on a separate landing page, and make the app ready for smoke testing. The session then renamed Case Builder to Case Helper, deployed it to Jeremy's Railway account, restored the intended contextual AI intake, and expanded uploads beyond PNG/JPEG/WebP to PDFs and broadly supported image formats.
The completed product snapshot was then committed and pushed to the public GitHub repository. Repository and secret-handling expectations were clarified for additional collaborators.

## Important discoveries and decisions
- `/api/case/reset` built the six example exhibits but did not replay the sample chat. Browser Back also restored the example landing page with its buttons disabled while the server-side reset continued. The example now includes its full conversation, repeated resets reuse a ready example, and `pageshow` resets the landing-page controls.
- The first Railway Docker image forced `USE_FIXTURES=1`. That caused every real story, including a fish-order dispute, to receive Mei Ling's prerecorded tenancy reply. Railway now has the existing OpenRouter configuration and `USE_FIXTURES=0`; new cases use live AI.
- The deployed unpinned `anthropic` dependency resolved to 1.4.0 and raised a `TypeError` on the existing tool-call contract. Pinning `anthropic==0.103.1`, the locally proven version, fixed the live Railway call.
- The model can infer the wrong claim total when a story contains several amounts. An explicit total stated as "I want to claim $4,000" or equivalent now overrides model inference in `app.explicit_claim_amount`; it does not calculate an amount when the user did not state one.
- The model could set `done` while the files checklist item was still missing. Completion is now checked by the server, respondent address is required, and the last intake reply tells the user which evidence to add for that claim type.
- Railway rebuilds took roughly 20–40 seconds because the Docker image installs Tesseract, ffmpeg, Python dependencies, and now the HEIC decoder. Live chat calls were roughly 4–7 seconds.
- Uploads were extension-gated. They now detect PDF/image content, retain MP4/MOV, register HEIC/HEIF decoding, and expose an `image/*` plus PDF picker. Corrupt or unsupported content still returns an error without changing the case.
- The app still holds one global case in process and writes to Railway's ephemeral filesystem. Concurrent visitors can overwrite each other's state. The public URL is suitable for a controlled demo, not real confidential cases, until storage and per-user isolation are added.
- `https://github.com/jemeryy/LIT-hackathon` is public. Anyone can clone, pull, fork, edit a fork, and open a pull request. GitHub does not allow unrestricted public pushes; direct push access requires inviting specific GitHub usernames or an organization team with write access.
- AI credentials belong only in Railway's server-side Variables/Secrets. The backend accepts `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY`; browser code and Git history must never contain either value. Git does not track an `.env` file, and the repository root `.gitignore` excludes `.env` at both root and nested paths.

## Decisions locked + what shipped
- Product name is **Case Helper** — visible name changed in `C:\Users\jemer\code\hackathon\builds\case-builder\app.py`, `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html`, `C:\Users\jemer\code\hackathon\builds\case-builder\static\example.html`, and `C:\Users\jemer\code\hackathon\builds\case-builder\README.md`.
- The normal entry at `https://case-helper-production.up.railway.app/` starts a new blank case. Only `https://case-helper-production.up.railway.app/example.html` loads Mei Ling's worked example; it redirects to `/?example=1`.
- The worked example uses saved chat, saved evidence facts, saved generated text, a reset lock, and ready-example reuse — `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` and `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py`.
- New-case chat is live through OpenRouter. The intake prompt must reflect the user's actual goods, service, tenancy, or property-damage story, ask only one or two missing questions, avoid example facts, and not repeat answered questions — `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py`.
- Explicit claim totals and server-verified intake completion are deterministic safeguards around model output — `C:\Users\jemer\code\hackathon\builds\case-builder\app.py`.
- Railway variables were set for `OPENROUTER_API_KEY`, `ANTHROPIC_BASE_URL`, `MODEL`, and `USE_FIXTURES=0`. Values were not written to source or this handoff.
- The Case Helper snapshot was committed as `fb60f84` (`Case Helper: deploy live AI workflow and broaden uploads`) and pushed to `origin/main` at `https://github.com/jemeryy/LIT-hackathon/commit/fb60f84`.
- The GitHub repository remains public for pull/fork/pull-request collaboration. Grant direct write access only to named collaborators; their GitHub usernames were not provided in this session, so no collaborator invitations were sent.
- Railway deployment support was added with `C:\Users\jemer\code\hackathon\builds\case-builder\Dockerfile` and `C:\Users\jemer\code\hackathon\builds\case-builder\.dockerignore`. The image binds uvicorn to Railway's `$PORT` and installs Tesseract and ffmpeg.
- Broad image support was added through content detection plus `pillow-heif` — `C:\Users\jemer\code\hackathon\builds\case-builder\app.py`, `C:\Users\jemer\code\hackathon\builds\case-builder\extract.py`, `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py`, `C:\Users\jemer\code\hackathon\builds\case-builder\requirements.txt`, and both upload inputs in `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html`.
- Supported and detected raster formats include PNG, JPEG/JFIF, WebP, HEIC/HEIF, AVIF, GIF, BMP/DIB, TIFF, ICO, PPM/PGM/PBM/PNM, PCX, and TGA. PDF, MP4, and MOV remain supported.
- The latest Railway deployment `6c50f13c-96b4-41fa-bc17-2ac43ec8e068` completed successfully.

## Key files for next session
- Plan file: `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md` — original architecture, legal/ranking contract, and build history.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-railway-ai.md` — this handoff.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-layman-ui.md` — state immediately before this session.
- `C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-ps4-real-product.md` — intended contextual chat design and live-product architecture.
- `C:\Users\jemer\code\hackathon\builds\case-builder\app.py` — case state, intake safeguards, sample flow, upload detection, and API routes.
- `C:\Users\jemer\code\hackathon\builds\case-builder\llm.py` — OpenRouter client, contextual intake prompt/tool schema, evidence reading, and generated text.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\index.html` — seven-step UI and default/example entry behavior.
- `C:\Users\jemer\code\hackathon\builds\case-builder\static\example.html` — separate worked-example landing page.
- `C:\Users\jemer\code\hackathon\builds\case-builder\Dockerfile` — Railway production image and start command.
- `C:\Users\jemer\code\hackathon\builds\case-builder\selfcheck.py` — deterministic end-to-end checks, explicit-amount assertions, completion guard, and format-detection checks.
- Memory files touched: none.

## Running state
- Background processes: local Python PID `15180`, serving `http://127.0.0.1:8000/`; it was started with `USE_FIXTURES=1` before the later backend edits, so restart it before relying on local backend behavior. Kill with `Stop-Process -Id 15180 -Force` after verifying the PID still owns port 8000.
- Dev servers / ports: local `http://127.0.0.1:8000/` returns 200. Railway production is `https://case-helper-production.up.railway.app/`; project ID `62f978e8-43f7-401f-9dce-69fc09b5daed`, service ID `f076ff97-b535-44e6-b90b-18ded88b3db2`, latest deployment ID `6c50f13c-96b4-41fa-bc17-2ac43ec8e068`.
- Open worktrees / branches: main checkout at `C:\Users\jemer\code\hackathon`; no separate worktrees. `main` and `origin/main` both reached commit `fb60f84`. Runtime-only `C:\Users\jemer\code\hackathon\builds\case-builder\data\case.json` and `C:\Users\jemer\code\hackathon\builds\case-builder\data\llm_log.jsonl` were deliberately left uncommitted. This handoff has been edited after that commit and is also an uncommitted documentation change.

## Verification — how to confirm things still work
- `cd C:\Users\jemer\code\hackathon\builds\case-builder; $env:USE_FIXTURES='1'; C:\Users\jemer\AppData\Local\Programs\Python\Python312\python.exe selfcheck.py` — expected `selfcheck ok:` with six evidence keys and E1 highlight boxes. The full check last passed before the broad-upload patch; fast compile and format checks passed after it.
- `C:\Users\jemer\AppData\Roaming\npm\railway.ps1 deployment list --json` from `C:\Users\jemer\code\hackathon\builds\case-builder` — latest deployment should be `SUCCESS`.
- `git -C C:\Users\jemer\code\hackathon rev-parse HEAD` and `git -C C:\Users\jemer\code\hackathon rev-parse origin/main` — both should report `fb60f84` until a newer collaboration commit is pushed.
- `git -C C:\Users\jemer\code\hackathon ls-files --error-unmatch .env builds/case-builder/.env` — expected to fail because neither `.env` path is tracked. `git -C C:\Users\jemer\code\hackathon check-ignore -v .env builds/case-builder/.env` should show the root `.gitignore` rule.
- Public live-AI acceptance already passed with the fish-order story: reply referenced the fish dispute and Uncle Seng, claim type was `goods`, total was `$4,000`, refusal date was `2026-10-01`, and the respondent was recorded. The test reset the hosted case to blank afterward.
- Public example acceptance already passed: seven chat messages, six ready exhibits, gate pass, and about 2.8 seconds after saved-example separation.
- Fast local content-detection check passed for PNG, JPEG, GIF, BMP, TIFF, WebP, and PDF.
- Public broad-upload acceptance passed with a generated BMP: API returned exhibit status `ready`, kind `image`, then the hosted case was reset to blank.

## Deferred / pending tasks + open questions
- Deferred/pending: run a browser smoke test of the latest public build with a real PDF and phone-origin HEIC/HEIF file. BMP was tested end to end; HEIC support built successfully but was not exercised with a real phone file.
- Deferred/pending: add per-user/session case isolation and persistent storage before asking real users to upload private evidence. Current global `CASE` and ephemeral filesystem are demo-only.
- Deferred/pending: add an upload progress state and clearer timing text. Live OCR plus the evidence model can take several seconds.
- Deferred/pending: restart the local server in live mode before local testing; its current process predates the latest backend changes.
- Deferred/pending: do not commit runtime case/LLM logs unless intentionally preserving fixtures. The server log pattern is now ignored by `C:\Users\jemer\code\hackathon\builds\case-builder\.gitignore`.
- Deferred/pending: invite named GitHub collaborators with write access if they need direct pushes. Until usernames are supplied, collaborators should fork and open pull requests.
- Deferred/pending: commit and push this post-checkpoint handoff update if it should be preserved on GitHub.
- Deferred/pending: deck, AI-disclosure slide, citations, and Devpost submission remain from the prior handoffs.
- Open: whether the Railway URL is strictly a controlled hackathon demo or should be made safe for multiple real users.
- Open: which GitHub usernames, if any, should receive direct write access.

## Plan
- Plan file is `C:\Users\jemer\code\hackathon\plans\2026-09-05-ps4-case-builder-build.md`.
- Continue the original seven-step Case Helper plan, but treat per-user state/privacy as the next production prerequisite. Then complete browser verification, collaborator setup if requested, deck, and submission work.

## Next steps
Run the latest Railway build through a browser with one contextual multi-turn claim, one PDF, and one real HEIC file. If the app is meant for anyone beyond a controlled demo, replace the global case with per-user session storage before further public testing. Invite only named GitHub collaborators who need direct pushes; everyone else can fork and open pull requests. Commit the updated handoff if it should be included in the shared repository.

## Next step (for the next session after /clear)
Next step: read C:\Users\jemer\code\hackathon\handoffs\handoff-2026-09-05-case-helper-railway-ai.md, then browser-smoke-test live AI plus PDF/HEIC uploads and decide the per-user storage and named-collaborator scope.
