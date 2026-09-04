---
name: resume
model: inline
description: Use at the start of a session when Jeremy says "resume", "continue where we left off", "pick up <topic>", "read the latest handoff and go", or any near-equivalent. Finds the newest handoff file (optionally filtered by a topic keyword), reads it, states the next step in one line, and continues from there. This replaces manually typing handoff filenames.
---

# Resume from the latest handoff

Purpose: make session resume one word instead of a hand-typed filename. The save side is the `session-handoff` skill; this is the load side.

## Steps

1. **Find candidates.** Run `python tools/find_handoff.py [keyword]` (keyword optional: "resume chess" -> `chess`). It globs `handoffs/` plus every project `docs/` handoff, filters by the keyword (matched against the whole relative path, so `chess` catches `chess/docs/`), sorts newest first by filename date (mtime tie-break), and prints the top 3 with age and a STALE marker. Nonzero exit means nothing matched.
2. **Pick the newest** (the script's top line). If the top two candidates are same-day but clearly different workstreams and no keyword was given, ask which one (one short question, two options) instead of guessing.
3. **Read it fully.** Then tell Jeremy in one or two lines: which handoff you loaded, and what the next step is. Do not paste the handoff back into chat.
4. **Check staleness.** If the script marked the newest match STALE (older than 7 days), say so and confirm it is still current before acting on it.
5. **Execute the handoff's next steps** under normal rules: anything needing a green light (push, deploy, spend, sending anything external) is surfaced, not run. If the handoff's next step conflicts with something that changed since (git log tells you), surface the conflict first.

## Rules

- Scope stays with the handoff's workstream. Do not pull in other open handoffs unless asked.
- If no handoff matches the keyword (script exits nonzero), re-run `python tools/find_handoff.py` without the keyword and show its output (the newest handoffs that DO exist) rather than free-associating.
- Chess handoffs: chess rules still apply — read `chess/README.md` before touching any lesson.
