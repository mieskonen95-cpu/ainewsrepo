# Daily routine

A scheduled Claude Code session runs this file once a day. It uses your Claude subscription,
so it needs no API key. Helpers in `agent/cli.py` enforce the checks. The session pushes only to a
`claude/` branch; GitHub Actions merges content-only changes into `main` and deploys.

Work in the repository root. Run every step yourself, in order, without asking questions:
nobody is watching this run. If a step fails, follow its instructions and don't improvise.

## 0. Setup
```bash
pip install -q feedparser pyyaml markdown
git fetch origin main && git checkout main && git pull --ff-only origin main
mkdir -p .routine && echo '[]' > .routine/reviews.json
DATE=$(date -u +%F)
```
If `content/posts/$DATE-*.md` already exists, stop: today is done.

## 1. Gather
`python -m agent.cli gather > .routine/items.json` and `python -m agent.cli recent`.

## 2. Research
Read `playbook.md` and `memory/lessons.md`. From the items, pick today's stories as the playbook
says, skipping anything a recent post already covered. Verify each with web search and find the
primary source (paper, official announcement, repo). If the feeds returned little, find today's
most important AI news with web search. Write research notes to `memory/notes/$DATE.md`: per story,
the headline, what happened, why it matters, key facts and numbers, and the URL behind each fact.
Mark anything you couldn't verify as UNVERIFIED.

## 3. Draft
Write `content/posts/$DATE-<slug>.md` (slug: lowercase-kebab-case, no date), following
`playbook.md` exactly and using only facts in the notes:
```markdown
---
title: ...
date: YYYY-MM-DD
summary: One or two sentences for the index page and RSS.
tags: [models, research]
sources:
  - {title: ..., url: https://...}
---

The post body in Markdown, no H1.
```

## 4. Independent review
Start a **subagent** as the editor, so the review isn't done by the context that wrote the post.
Give it the paths of `rubric.md`, the notes and the post, and ask it to write
`.routine/review.json`:
```json
{"criteria": [{"name": "Accuracy", "score": 1-5, "note": "..."}, ...all 6 rubric criteria...],
 "unsupported_claims": ["exact quotes from the post that the notes don't back"],
 "revision_instructions": "..."}
```
Then append the review to `.routine/reviews.json` (a JSON list).

## 5. Gate
```bash
python -m agent.cli finalize content/posts/$DATE-<slug>.md .routine/review.json
```
If it prints `GATE FAILED`, revise the post per the review and repeat steps 4–5. At most
2 revisions. After the last review, if the only remaining failure is unsupported claims, run
`finalize` again with `--strip` added: it deletes each sentence containing a flagged claim (the
editor must quote claims verbatim from the post). A shorter post that passes beats no post.
If it still fails, delete the post and run
`python -m agent.cli reject $DATE .routine/review.json`.

## 6. Learning (only when due)
Run `python -m agent.cli learn-due`. If it exits non-zero, skip to step 7. Otherwise:
1. `python -m agent.cli learn-signals` and read it with `playbook.md`, `sources.yaml`,
   `rubric.md` and `memory/lessons.md`. Look for patterns across issues, not one-offs. Human
   edits are the strongest signal, then audience data, then rubric scores. Never trade accuracy
   for clicks. **Never edit `rubric.md`.**
2. Write the proposed playbook to `.routine/playbook.new.md`, then
   `python -m agent.cli learn-check playbook.md .routine/playbook.new.md`. If it fails, make the
   change smaller.
3. **Eval gate.** For each date in `replay_dates`, start two subagents. One drafts a post from
   `memory/notes/<date>.md` with the old playbook, the other with the new one. Then a third,
   separate editor subagent scores both against `rubric.md` without being told which is which.
   Keep the new playbook only if its mean score is ≥ the old one's and no day drops by more than 0.5.
4. If accepted, copy it over `playbook.md` and apply any feed changes to `sources.yaml` (add
   with `quality: 3`, remove dead or low-value feeds per `feed_health`).
5. Whether accepted or not, append a dated paragraph to `memory/lessons.md` (mark it
   applied or rejected), write `.routine/learn.json` as
   `{"accepted": bool, "reasoning": "...", "old_scores": [...], "new_scores": [...], "added": [...], "removed": [...]}`
   and run `python -m agent.cli learn-record .routine/learn.json`.

## 7. Commit and push (never to `main`)
```bash
git checkout -b "claude/daily-$DATE"
git add content memory metrics playbook.md sources.yaml
git commit -m "post: $DATE"          # add a learn line and the reasoning if step 6 ran
git push origin "claude/daily-$DATE"
```
Never push to `main`, and never commit files outside those paths. The `Publish` workflow merges
the branch into `main` only if it changes nothing but content paths, then deploys. If pushing
`claude/daily-$DATE` is refused, push to the branch this session was assigned (it starts with
`claude/`).

Finish with a two-line summary: the post title and score, and the learning outcome if one ran.
