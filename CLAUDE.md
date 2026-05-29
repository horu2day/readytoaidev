# CLAUDE.md — readytoaidev

> Project-specific guide. Inherits the global guidelines in `../CLAUDE.md`
> (Think Before Coding · Simplicity First · Surgical Changes · Goal-Driven Execution).
> This file adds rules specific to the lecture site and its multi-agent workflow.

## 1. What this project is

A **Korean-language web lecture site that teaches non-developers how to build
software with AI tools** (ChatGPT, Claude, VS Code). The reader has *zero*
coding background.

- Entry point: `vscode-lecture.html` (currently a single static page).
- No build system yet; plain HTML/CSS. Keep it that way until complexity forces otherwise.

## 2. Audience rules (override style preferences)

Every content or feature decision is judged against the non-developer reader:

1. **Plain Korean, no jargon.** If a technical term is unavoidable, define it in
   one short sentence the first time it appears.
2. **Follow-along, small wins.** Steps are concrete, ordered, and verifiable by
   the reader ("you should now see…").
3. **Encouraging, never condescending.** Manage expectations; don't overpromise.
4. **Accessibility and mobile are first-class**, not afterthoughts. Beginners
   skew older, non-technical, and mobile-first.
5. **AI-tool facts go stale.** Anything version- or UI-specific must be easy to
   update and dated where possible.

## 3. Start-of-session protocol (IMPORTANT)

Work on this project is split across multiple Claude Code agents. **Before doing
anything, read both:**

1. **`PLAN.md`** — the roadmap: phases, tasks, owners, success criteria.
2. **`PROGRESS.md`** — the live log: what is done, in progress, and blocked.

Then:
- Pick up the next unblocked task from `PLAN.md` (or the one the user names).
- After meaningful work, **update `PROGRESS.md`** (what you did, status, any
  blockers, next step). Keep `PLAN.md` current if scope changes.
- Do not duplicate work already marked done in `PROGRESS.md`.

This is how parallel agents stay coordinated. Treat `PLAN.md` + `PROGRESS.md` as
the shared source of truth for "what should I do next".

## 4. Testing philosophy

The site ships with automated tests (see `PLAN.md` test layers): markup
validity, E2E flows, accessibility (WCAG), visual regression, performance
budgets, and **content quality** (a custom lint for jargon/reading-level aimed
at the non-developer audience). A change isn't "done" until the relevant suite
passes — apply Goal-Driven Execution from the global guide.

## 5. Tooling available

Custom agents, slash commands, skills, and hooks live under `.claude/`. Use them
instead of ad-hoc work where they fit:
- Agents: `content-writer`, `a11y-auditor`, `e2e-tester`, `content-linter`,
  `test-planner`. (See `.claude/agents/`.)
- Commands: `/new-lesson`, `/run-tests`, `/update-progress`, `/a11y-check`.
- Skills: `lecture-content` (writing standards), `test-automation` (how to run/extend tests).

When unsure which to use, read the file headers in `.claude/` — each describes when it applies.
