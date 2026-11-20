# The AI Brief — a self-improving AI news blog

Fully automatic after setup: every day a scheduled Claude Code task researches AI news, writes a post,
scores it against a fixed rubric, publishes it to GitHub Pages, and every 4 posts improves
its own playbook — but only if the change wins a replay eval.

**The model stays fixed; its playbook learns.**

## How it works

| Loop | When | What | Where |
|---|---|---|---|
| Production | daily 05:17 UTC | gather feeds → research with web search → draft → a separate editor agent scores it against `rubric.md` → revise (≤2) → publish only if score ≥ 4.0 and zero unsupported claims | `ROUTINE.md` steps 1–5, gate in `agent/cli.py` |
| Learning | after every 4 new issues | signals (human edits > audience data > rubric scores, feed health) → propose new playbook + feeds → **eval gate**: replay last 3 days with old vs new playbook, blind-scored → keep only if no worse | `ROUTINE.md` step 6 |
| Site | whenever a post lands on `main` | Markdown → static HTML + RSS → GitHub Pages | `.github/workflows/publish.yml`, `site/build.py` |

The writing runs as a **Claude Code scheduled task** on the owner's Claude subscription, so it
needs **no API key**. GitHub Actions needs no secrets: it only merges content and deploys.

### What can change (all in git, so every self-change is a diff you can revert)
- `playbook.md` — voice, structure, story selection (edited by the learning loop)
- `sources.yaml` — feeds with quality scores (edited by the learning loop)
- `memory/` — research notes per day, lessons log, covered URLs
- `metrics/` — per-issue reviews and per-cycle learning results
- `rubric.md` — **fixed**; the routine never edits it, and the workflow refuses to auto-merge a
  branch that changes anything outside content paths

### Guardrails
Batch changes over 4 issues · cap playbook change at 35% per cycle · blind eval gate on replayed
days · rubric outranks clicks · posts that fail review are not published (logged in `metrics/`).

## Setup
1. Settings → Pages → Source: **GitHub Actions**.
2. The daily scheduled task lives in your Claude account (claude.ai → Claude Code → scheduled tasks).
   You can run it now from there, or change its time.

The `ANTHROPIC_API_KEY` secret is no longer used and can be deleted.

Site URL: `https://<owner>.github.io/<repo>/`

## Optional knobs
- Model (API mode only): env `NEWS_MODEL` (default `claude-opus-5-5`).
- Site name: `SITE_TITLE`, `SITE_TAGLINE` env on the build step in `.github/workflows/publish.yml`.
- Audience signal: drop analytics into `metrics/audience.json` (any JSON); the learning loop reads it.
- Steering: edit a post or `playbook.md` by hand — your commits are the strongest learning signal.

## Optional: API mode
`agent/produce.py` and `agent/learn.py` run the same loops through the Claude API, for use
outside Claude Code (needs `ANTHROPIC_API_KEY`):
```bash
pip install -r requirements.txt
python -m agent.produce --force && python -m agent.learn && python site/build.py
```
