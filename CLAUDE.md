# Hackathon — Jeremy

Jeremy's hackathon repo. One folder per event build under `builds/`. The point
of every session here is a working demo by the deadline.

**Read `BRIEF.md` first.** It holds the event, the deadline, the theme, the
judging criteria, the team, and the rules that bind the build. If it still says
TBD, ask Jeremy to fill the blanks before planning anything.

## Layout
- `BRIEF.md` — the event: rules, theme, judging, deadline. Source of truth.
- `builds/<name>/` — the actual code for the entry.
- `plans/` — build plans, `YYYY-MM-DD-slug.md`, with a `status:` field.
- `research/` — problem, market, sponsor-API and competitor notes.
- `notes/` — scratch: ideas, judge questions, demo script.
- `deck/` — pitch deck and exports.
- `handoffs/` — session handoffs.
- `tools/` — scripts. Run as `python tools/<name>.py --help`.
- `archives/` — superseded work. Never delete, `git mv` it here.

## Hard rules
- @.claude/rules/communication-style.md — tone and formatting. Plain words,
  gloss any jargon, British spelling, no em dashes.
- **Ship the demo.** Working and demoable beats complete. Build the shortest
  path to something a judge can watch. No auth, no admin panel, no test
  pyramid, no deploy pipeline unless it is in the demo or the rules.
- **Demo path first.** Before anything else, write the 90-second demo script in
  `notes/demo-script.md`, then build only what that script touches.
- **Time is the binding constraint.** Every plan gets a time budget per step.
  If a step blows its budget, cut scope, do not extend the clock.
- **Fake what is not judged.** Seeded data, hardcoded happy path, mocked third
  party. Say clearly in the pitch what is real and what is stubbed. Never claim
  a stub is real to a judge.
- **Never push, deploy, or submit** without Jeremy's explicit green light in
  that session.
- **Date/time claims:** verify with `Get-Date` before stating any date, time or
  deadline. Times are SGT.
- **Secrets live only in `.env`.** Never in code, never in the repo.

## How to work
1. **Read `BRIEF.md`.** Then check `plans/` for the active plan.
2. **Before building anything non-trivial:** run `grilling` (user-level) to lock
   what we are actually making, then `plan-with-codex` for the build plan.
3. **Build.** Small vertical slices that each leave the demo runnable.
4. **After a non-trivial build:** run `review-with-codex`. Standing reflex.
5. **Checkpoint at 20% context:** offer a `session-handoff`.

## Skills
Honour the `model:` in each SKILL.md frontmatter: `opus` / `sonnet` → spawn a
foreground agent (`subagent_type: skill-opus` or `skill-sonnet`) and have it read
`.claude/skills/<skill>/SKILL.md` and run to done. `inline` → run it yourself.

- `council` — roast the idea before building it. Worth 20 minutes on day one.
- `forge` — pick the architecture when there are competing approaches.
- `plan-with-codex` / `review-with-codex` — the plan and review loop.
- `self-drive` — drive a locked plan to done autonomously. Never ships.
- `impeccable` — the demo UI. Judges see the interface, so it carries weight.
- `storm-research` — sourced briefing on the problem space or a sponsor's API.
- `make-slides` + `notebooklm-use` — the pitch deck.
- `session-handoff` / `resume` — end and restart a session.
- User-level, load everywhere: `grilling`, `tdd`, `codebase-design`,
  `domain-modeling`, `to-spec`, `visualise`, `dataviz`.

## Access
`playwright` MCP drives a real Chromium for any site a fetch cannot reach. Also
available: web search, WebFetch, and the Google Docs/Drive/Gmail, Tasks, Maps,
YouTube MCPs.

## Note on the parent folder
`C:\Users\jemer\code\CLAUDE.md` describes a WAT framework for automation repos.
This is not one. This file takes precedence.
