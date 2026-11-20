# The AI Brief — a self-improving AI news blog

Fully automatic after setup: every day a GitHub Action researches AI news, writes a post,
scores it against a fixed rubric, publishes it to GitHub Pages, and every 4 posts improves
its own playbook — but only if the change wins a replay eval.

**The model stays fixed; its playbook learns.**

## How it works

| Loop | When | Steps | Code |
|---|---|---|---|
| Production | daily 05:17 UTC | gather feeds → research with web search → draft → independent rubric review → revise (≤2) → publish only if score ≥ 4.0 and zero unsupported claims | `agent/produce.py` |
| Learning | after every 4 new issues | collect signals (human edits > audience data > rubric scores, feed health) → reflect → propose new playbook + feed changes → **eval gate**: replay last 3 days with old vs new playbook, keep only if no worse → commit | `agent/learn.py` |
| Site | after each run, and on any push touching `content/` or `site/` | Markdown → static HTML + RSS → GitHub Pages | `site/build.py` |

### What can change (all in git, so every self-change is a diff you can revert)
- `playbook.md` — voice, structure, story selection (edited by the learning loop)
- `sources.yaml` — feeds with quality scores (edited by the learning loop)
- `memory/` — research notes per day, lessons log, covered URLs
- `metrics/` — per-issue reviews and per-cycle learning results
- `rubric.md` — **fixed**; the agent never writes it

### Guardrails
Batch changes over 4 issues · cap playbook change at 35% per cycle · eval gate on replayed days ·
rubric outranks clicks · posts that fail review are not published (logged in `metrics/`).

## One-time setup (≈3 minutes)
1. **Secret:** repo → Settings → Secrets and variables → Actions → New secret `ANTHROPIC_API_KEY`.
2. **Pages:** repo → Settings → Pages → Source: **GitHub Actions**.
3. **Merge** this branch into `main` (the schedule only runs on the default branch).
4. **First post:** Actions → Publish → Run workflow. After that it runs daily on its own.

Site URL: `https://<owner>.github.io/<repo>/`

## Optional knobs
- Model: set repo variable/env `NEWS_MODEL` (default `claude-opus-5-5`).
- Site name: `SITE_TITLE`, `SITE_TAGLINE` env in `.github/workflows/publish.yml`.
- Audience signal: drop analytics into `metrics/audience.json` (any JSON); the learning loop reads it.
- Steering: edit a post or `playbook.md` by hand — your commits are the strongest learning signal.

## Run locally
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python -m agent.produce --force && python site/build.py
```

Cost: roughly $0.50–1.50 per daily post on Opus 5.5 (research with web search + 2–6 short calls),
plus ~12 calls per learning cycle.
